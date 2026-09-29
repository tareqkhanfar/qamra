"""«ارسم صاحبك» in the parent create flow (Addendum 1 §1; design CompIntro → CompUpload → CompCrop →
CompName → CompGen → CompChoose, and MyCompanions).

The drawing follows the photo rules (CLAUDE.md §3.1): the guardian's consent first; the upload is re-encoded
without its metadata (EXIF, GPS); files stay private under the child's storage prefix, so "delete all my
child's data" removes them. The original photo is deleted `photo_retention_hours` after the parent chooses
the companion (and after `draft_retention_days` at the latest when they never do). The cleaned drawing
stays: it is printed on the «وهكذا وُلد صاحبي» page, and the parent may delete the whole companion.

upload → crop / rotate / clean → name + type → 2 options drawn by the worker → choose one (3 free redraws).
A chosen companion belongs to the child and is offered again in their later books («أصحابي»).
"""

import asyncio
import io
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, File, Response, UploadFile
from PIL import Image
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func, select

from qamra_ai.pipeline.drawing import clean_drawing
from qamra_api import ratelimit, runtime_settings
from qamra_api.deps import CurrentUser, RedisDep, SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_api.store.catalog import load_catalog
from qamra_api.uploads import clean_image, read_upload
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Character,
    Child,
    Companion,
    CompanionStatus,
    CompanionType,
    Consent,
)

router = APIRouter(prefix="/api/create", tags=["create"])

MAX_ROUNDS = 4  # the first drawing and 3 free redraws (Addendum 1 §1.4)
DRAWING_MAX_SIDE = 2400  # the cleaner works at 1600 px; a little more keeps crop headroom
UPLOADS_PER_HOUR = 20
OPTIONS = 2
TRAITS = ("funny", "brave", "shy", "kind", "curious")  # design CompName chips; English for the prompts
DEFAULT_STYLE = "watercolor"
UNFINISHED = (  # a book that may still be drawn or printed with its companion
    BookStatus.draft,
    BookStatus.generating,
    BookStatus.preview,
    BookStatus.in_review,
    BookStatus.approved,
    BookStatus.ordered,
)


def prefix(comp: Companion) -> str:
    return f"children/{comp.child_id}/companions/{comp.id}/"


class Box(BaseModel):
    """The crop on the original photo, as fractions of its width and height."""

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(ge=0.1, le=1)
    h: float = Field(ge=0.1, le=1)

    @model_validator(mode="after")
    def _inside(self) -> "Box":
        if self.x + self.w > 1.001 or self.y + self.h > 1.001:
            raise ValueError("the crop leaves the photo")
        return self


class CompanionOut(BaseModel):
    id: uuid.UUID
    child_id: uuid.UUID
    status: str
    name: str
    type: str
    type_other: str | None
    traits: list[str]
    options: int  # the options of the latest drawing, to choose from
    redraws_left: int
    original: bool  # the original photo is still stored (crop and rotate still possible)
    paper_found: bool
    box: Box | None
    rotate: int
    clean: bool
    error: dict[str, str] | None  # {code, ar, en} after a failed drawing
    approved: bool
    books: int  # books with this companion


def latest(comp: Companion) -> list[dict[str, object]]:
    """The options of the latest drawing round, in order."""
    rounds = [int(str(o.get("round", 0))) for o in comp.options or []]
    last = max(rounds, default=0)
    return [o for o in comp.options or [] if int(str(o.get("round", 0))) == last]


def rounds_used(comp: Companion) -> int:
    """Drawings the parent started; one that failed on our side (or a rejected drawing) is not counted."""
    return max(0, (comp.regen_count or 0) - int((comp.params or {}).get("failed_rounds", 0)))


async def companion_out(db: SessionDep, comp: Companion) -> CompanionOut:
    params = comp.params or {}
    books = (
        await db.execute(select(func.count()).select_from(Book).where(Book.companion_id == comp.id))
    ).scalar_one()
    return CompanionOut(
        id=comp.id,
        child_id=comp.child_id,
        status=comp.status.value,
        name=comp.name,
        type=comp.type_hint.value,
        type_other=comp.type_other,
        traits=[t for t in (comp.traits or "").split(", ") if t],
        options=len(latest(comp)) if comp.status == CompanionStatus.ready else 0,
        redraws_left=max(0, MAX_ROUNDS - rounds_used(comp)),
        original=comp.drawing_key is not None,
        paper_found=bool(params.get("paper_found")),
        box=Box.model_validate(params["box"]) if params.get("box") else None,
        rotate=int(params.get("rotate", 0)),
        clean=bool(params.get("clean", True)),
        error=params.get("error") if comp.status == CompanionStatus.failed else None,
        approved=comp.approved_at is not None,
        books=int(books),
    )


async def own_child(db: SessionDep, user: CurrentUser, child_id: uuid.UUID) -> Child:
    child = await db.get(Child, child_id)
    if child is None or child.guardian_user_id != user.id:
        raise ApiError("not_found", 404)  # the same answer for someone else's child
    return child


async def own_companion(db: SessionDep, user: CurrentUser, companion_id: uuid.UUID) -> Companion:
    comp = await db.get(Companion, companion_id)
    if comp is None:
        raise ApiError("not_found", 404)
    await own_child(db, user, comp.child_id)
    return comp


def private_image(data: bytes, media_type: str) -> Response:
    return Response(data, media_type=media_type, headers={"Cache-Control": "private, no-store"})


# ---- the drawing: upload, crop, rotate, clean --------------------------------------------------------------

ROTATIONS = {90: Image.Transpose.ROTATE_270, 180: Image.Transpose.ROTATE_180, 270: Image.Transpose.ROTATE_90}


def prepare_drawing(original: bytes, box: Box | None, rotate: int, clean: bool) -> tuple[bytes, bool]:
    """The drawing as the companion is drawn from: the parent's crop of the original photo, turned clockwise,
    then (by default) the paper found, flattened and its shadows removed. → (PNG, paper found)."""
    with Image.open(io.BytesIO(original)) as im:
        img = im.convert("RGB")
    if box is not None:
        w, h = img.size
        img = img.crop(
            (
                round(box.x * w),
                round(box.y * h),
                round(min(1, box.x + box.w) * w),
                round(min(1, box.y + box.h) * h),
            )
        )
    if rotate in ROTATIONS:
        img = img.transpose(ROTATIONS[rotate])
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    if not clean:
        return buf.getvalue(), False
    try:
        cleaned = clean_drawing(buf.getvalue())
    except ValueError as e:
        raise ApiError("invalid_drawing", 422) from e
    return cleaned.png, cleaned.paper_found


async def _retention(db: SessionDep, settings: SettingsDep, key: str) -> int:
    return int((await runtime_settings.current(db, settings)).values[key])


@router.post("/children/{child_id}/companions", status_code=201)
async def upload_drawing(
    child_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    storage: StorageDep,
    redis: RedisDep,
    settings: SettingsDep,
    drawing: Annotated[UploadFile, File()],
) -> CompanionOut:
    """A photo of the child's drawing (camera or gallery): stored privately, cleaned for the next step."""
    child = await own_child(db, user, child_id)
    if await ratelimit.hit(redis, f"rl:drawings:{user.id}", 3600) > UPLOADS_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    consented = (
        await db.execute(select(func.count()).select_from(Consent).where(Consent.child_id == child.id))
    ).scalar_one()
    if not consented:
        raise ApiError("consent_required", 409)
    original = clean_image(await read_upload(drawing), DRAWING_MAX_SIDE)  # re-encoded: no EXIF, no GPS
    png, paper = await asyncio.to_thread(prepare_drawing, original, None, 0, True)
    days = await _retention(db, settings, "draft_retention_days")
    comp = Companion(
        child_id=child.id,
        name="",
        type_hint=CompanionType.creature,
        status=CompanionStatus.draft,
        drawing_delete_after=datetime.now(UTC) + timedelta(days=days),  # never chosen: gone with drafts
        params={"box": None, "rotate": 0, "clean": True, "paper_found": paper},
        options=[],
    )
    db.add(comp)
    await db.flush()
    comp.drawing_key = f"{prefix(comp)}drawing.jpg"
    comp.cleaned_key = f"{prefix(comp)}cleaned.png"
    storage.put(comp.drawing_key, original, "image/jpeg")
    storage.put(comp.cleaned_key, png, "image/png")
    await db.commit()
    return await companion_out(db, comp)


class CropIn(BaseModel):
    box: Box | None = None  # None: the whole photo, with the paper found automatically
    rotate: Literal[0, 90, 180, 270] = 0
    clean: bool = True  # «إزالة لون الورق والظلال»


@router.post("/companions/{companion_id}/crop")
async def crop_drawing(
    companion_id: uuid.UUID, body: CropIn, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> CompanionOut:
    comp = await own_companion(db, user, companion_id)
    if comp.status in (CompanionStatus.generating, CompanionStatus.approved):
        raise ApiError("companion_busy", 409)
    if comp.drawing_key is None:
        raise ApiError("drawing_gone", 409)
    original = storage.get(comp.drawing_key)
    png, paper = await asyncio.to_thread(prepare_drawing, original, body.box, body.rotate, body.clean)
    comp.cleaned_key = comp.cleaned_key or f"{prefix(comp)}cleaned.png"
    storage.put(comp.cleaned_key, png, "image/png")
    comp.params = {
        **(comp.params or {}),
        "box": body.box.model_dump() if body.box else None,
        "rotate": body.rotate,
        "clean": body.clean,
        "paper_found": paper,
    }
    await db.commit()
    return await companion_out(db, comp)


@router.get("/companions/{companion_id}/drawing")
async def drawing_image(
    companion_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    storage: StorageDep,
    kind: Literal["cleaned", "original"] = "cleaned",
) -> Response:
    comp = await own_companion(db, user, companion_id)
    key = comp.drawing_key if kind == "original" else comp.cleaned_key
    if not key:
        raise ApiError("drawing_gone" if kind == "original" else "not_found", 404)
    return private_image(storage.get(key), "image/jpeg" if kind == "original" else "image/png")


# ---- name + type → the worker draws 2 options → the parent chooses one ---------------------------------


class DrawIn(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    type: Literal["creature", "animal", "robot", "other"] = "creature"
    type_other: str | None = Field(default=None, max_length=30)  # «غير ذلك»: what it is, in the child's words
    traits: list[Literal[TRAITS]] = Field(default_factory=list, max_length=len(TRAITS))  # type: ignore[valid-type]
    style: str | None = Field(default=None, max_length=40)  # the book's art style; default: the character's

    @field_validator("name", "type_other")
    @classmethod
    def _squash(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = " ".join(v.split())
        return v or None


async def _style(db: SessionDep, comp: Companion, wanted: str | None) -> str:
    """The companion is drawn in the book's art style: the one asked for, else the latest character's."""
    catalog = await load_catalog(db)
    if wanted:
        if wanted not in catalog.styles:
            raise ApiError("invalid_style", 422)
        return wanted
    style = (
        (
            await db.execute(
                select(Character.art_style)
                .where(Character.child_id == comp.child_id, Character.approved_at.is_not(None))
                .order_by(Character.approved_at.desc())
            )
        )
        .scalars()
        .first()
    )
    return style or DEFAULT_STYLE


@router.post("/companions/{companion_id}/draw", status_code=202)
async def draw_companion(
    companion_id: uuid.UUID, body: DrawIn, user: CurrentUser, db: SessionDep, queue: QueueDep
) -> CompanionOut:
    """The first drawing or a redraw: 2 options in the book's art style (Addendum 1 §1.4)."""
    comp = await own_companion(db, user, companion_id)
    if body.name is None:
        raise ApiError("invalid_input", 422, {"fields": ["name"]})
    if comp.status == CompanionStatus.generating:
        raise ApiError("companion_busy", 409)
    if comp.status == CompanionStatus.approved:
        raise ApiError("companion_busy", 409)  # chosen already; a new drawing starts a new companion
    if not comp.cleaned_key:
        raise ApiError("drawing_gone", 409)
    if (
        comp.status == CompanionStatus.failed
        and (comp.params.get("error") or {}).get("code") == "drawing_rejected"
    ):
        raise ApiError("invalid_drawing", 422)  # the review said no: another drawing is needed, not a redraw
    if rounds_used(comp) >= MAX_ROUNDS:
        raise ApiError("redraws_used", 429)
    style = await _style(db, comp, body.style)
    comp.name = body.name
    comp.type_hint = CompanionType(body.type)
    comp.type_other = body.type_other if body.type == "other" else None
    comp.traits = ", ".join(t for t in TRAITS if t in body.traits) or None
    comp.status = CompanionStatus.generating
    comp.regen_count = (comp.regen_count or 0) + 1
    comp.params = {**(comp.params or {}), "style": style, "error": None}
    await db.commit()
    enqueue(queue, "qamra_worker.jobs.companions.generate_companion", str(comp.id))
    return await companion_out(db, comp)


@router.get("/companions/{companion_id}")
async def companion_status(companion_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> CompanionOut:
    return await companion_out(db, await own_companion(db, user, companion_id))


@router.get("/companions/{companion_id}/options/{n}/image")
async def option_image(
    companion_id: uuid.UUID, n: int, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> Response:
    comp = await own_companion(db, user, companion_id)
    shown = latest(comp)
    if comp.status != CompanionStatus.ready or not 0 <= n < len(shown):
        raise ApiError("not_found", 404)
    return private_image(storage.get(str(shown[n]["key"])), "image/png")


class ChooseIn(BaseModel):
    option: int = Field(ge=0, lt=OPTIONS)


@router.post("/companions/{companion_id}/choose")
async def choose_option(
    companion_id: uuid.UUID,
    body: ChooseIn,
    user: CurrentUser,
    db: SessionDep,
    storage: StorageDep,
    settings: SettingsDep,
) -> CompanionOut:
    """«هذا نونو!»: the option becomes the companion's sheet; the original photo gets its deletion time."""
    comp = await own_companion(db, user, companion_id)
    shown = latest(comp)
    if comp.status != CompanionStatus.ready or body.option >= len(shown):
        raise ApiError("companion_not_ready", 409)
    chosen = shown[body.option]
    now = datetime.now(UTC)
    comp.sheet_key = str(chosen["key"])
    comp.provider = str(chosen.get("provider") or "")[:32] or None
    comp.model = str(chosen.get("model") or "")[:100] or None
    comp.status, comp.approved_at = CompanionStatus.approved, now
    hours = await _retention(db, settings, "photo_retention_hours")
    due = now + timedelta(hours=hours)  # the same rule as photos (CLAUDE.md §3.1)
    comp.drawing_delete_after = min(due, comp.drawing_delete_after) if comp.drawing_delete_after else due
    for other in comp.options or []:
        if other["key"] != comp.sheet_key:
            storage.delete(str(other["key"]))  # the options not chosen are not kept
    comp.options = [chosen]
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="companion.approved",
            entity_type="companion",
            entity_id=str(comp.id),
        )
    )
    await db.commit()
    return await companion_out(db, comp)


# ---- «أصحابي»: the chosen companions, reused in later books ------------------------------------------------


class MyCompanion(CompanionOut):
    child_name: str


@router.get("/companions")
async def my_companions(user: CurrentUser, db: SessionDep) -> list[MyCompanion]:
    """Every companion the parent chose, for all their children (the account tab and the reuse picker)."""
    rows = (
        await db.execute(
            select(Companion, Child.first_name)
            .join(Child, Child.id == Companion.child_id)
            .where(Child.guardian_user_id == user.id, Companion.status == CompanionStatus.approved)
            .order_by(Companion.approved_at.desc())
        )
    ).all()
    return [
        MyCompanion(**(await companion_out(db, comp)).model_dump(), child_name=name) for comp, name in rows
    ]


@router.get("/companions/{companion_id}/image")
async def companion_image(
    companion_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> Response:
    comp = await own_companion(db, user, companion_id)
    if comp.status != CompanionStatus.approved or not comp.sheet_key:
        raise ApiError("companion_not_ready", 409)
    return private_image(storage.get(comp.sheet_key), "image/png")


@router.delete("/companions/{companion_id}", status_code=204)
async def delete_companion(
    companion_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> Response:
    """Addendum 1 §1: the parent may delete the drawing and its companion (all its files) at any time, except
    while a book that is not finished yet still draws or prints it."""
    comp = await own_companion(db, user, companion_id)
    busy = (
        await db.execute(
            select(func.count())
            .select_from(Book)
            .where(Book.companion_id == comp.id, Book.status.in_(UNFINISHED))
        )
    ).scalar_one()
    if busy or comp.status == CompanionStatus.generating:
        raise ApiError("companion_in_use", 409)
    files = storage.delete_prefix(prefix(comp))
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="companion.deleted",
            entity_type="companion",
            entity_id=str(comp.id),
            data={"files": files},
        )
    )
    await db.delete(comp)
    await db.commit()
    return Response(status_code=204)
