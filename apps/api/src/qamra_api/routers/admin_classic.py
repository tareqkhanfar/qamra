"""Admin: «قمرة كلاسيك» templates (Addendum 4 §1A, §3.4) and Classic test books.

- Templates per theme × art style × variant: generate them with the premium pipeline, or turn an approved
  sample book of a synthetic child into one; review every page, the hero boxes and the text boxes; redraw or
  lock pages; then approve and publish (draft → in_review → approved → live). Only live templates serve
  parents' books.
- Classic test books for sample children, and invented child faces for the cost proof (never a real person).
Every change is in the audit log. Images are streamed through the API; storage never needs a public address.
"""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.classic import VARIANTS, classic_budget_usd, parse_variant, variant_for
from qamra_ai.pipeline.classic_geometry import normalize_box
from qamra_ai.pipeline.theme import Theme
from qamra_ai.pipeline.vowelize import source_hash, sources, with_current_texts
from qamra_api import runtime_settings
from qamra_api.classic import CLASSIC_JOB
from qamra_api.deps import AdminUser, SessionDep, SettingsDep, StorageDep, require_admin, require_permission
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_api.uploads import clean_image, read_upload, require_face
from qamra_core.db.classic import (
    ClassicTemplate,
    ClassicTemplatePage,
    TemplateJob,
    TemplateStatus,
)
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookStatus,
    Child,
    ChildPhoto,
    Consent,
    Gender,
    Locale,
    PhotoStatus,
)
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.storage import ObjectNotFound

router = APIRouter(prefix="/api/admin/classic", tags=["admin"], dependencies=[Depends(require_admin)])

TEMPLATE_JOB = "qamra_worker.jobs.classic.generate_template"
FROM_BOOK_JOB = "qamra_worker.jobs.classic.template_from_book"
FACE_JOB = "qamra_worker.jobs.classic.synthetic_face"
TEXTS_JOB = "qamra_worker.jobs.classic.vowelize_template"
SAMPLE_CONSENT_VERSION = "sample-2026-09"  # the same written-consent rule as the Magic samples
S = TemplateStatus
MOVES: dict[TemplateStatus, tuple[TemplateStatus, ...]] = {
    S.draft: (S.in_review,),
    S.in_review: (S.approved, S.draft),
    S.approved: (S.live, S.in_review),
    S.live: (S.approved, S.in_review),
}
Variant = Literal["girl", "girl_hijab", "boy"]
assert set(VARIANTS) == {"girl", "girl_hijab", "boy"}  # nosec B101 (keep the API's list in step)


class Box(BaseModel):
    x: float
    y: float
    w: float
    h: float


class TemplatePageOut(BaseModel):
    beat: int
    layout: str | None
    status: str
    has_hero: bool
    hero_box: dict[str, Any] | None
    text_box: dict[str, Any] | None
    locked: bool
    regen_count: int
    cost_usd: float
    qa_score: float | None
    flags: list[str]
    has_image: bool


class TemplateOut(BaseModel):
    id: uuid.UUID
    theme: str
    theme_version: int
    style: str
    variant: str
    lang: str
    status: str
    job: str
    source: str
    source_book_id: uuid.UUID | None
    cost_usd: float
    flags: list[str]
    error: str | None
    progress: dict[str, Any]
    pages_drawn: int
    pages_total: int
    updated_at: datetime
    texts: dict[str, Any]  # the Arabic words vowelized once: {"vowelized", "kept", "at"}
    pages: list[TemplatePageOut] = []


def _page_out(p: ClassicTemplatePage) -> TemplatePageOut:
    return TemplatePageOut(
        beat=p.beat,
        layout=p.layout,
        status=p.status.value,
        has_hero=p.has_hero,
        hero_box=p.hero_box,
        text_box=p.text_box,
        locked=p.locked,
        regen_count=p.regen_count,
        cost_usd=float(p.cost_usd or 0),
        qa_score=float(p.qa_score) if p.qa_score is not None else None,
        flags=list(p.flags or []),
        has_image=bool(p.image_key),
    )


async def _pages(db: AsyncSession, template_id: uuid.UUID) -> list[ClassicTemplatePage]:
    q = select(ClassicTemplatePage).where(ClassicTemplatePage.template_id == template_id)
    return list((await db.execute(q.order_by(ClassicTemplatePage.beat))).scalars())


async def _out(db: AsyncSession, t: ClassicTemplate, *, pages: bool = False) -> TemplateOut:
    await db.refresh(t)  # server-side timestamps expire on commit; load them before reading
    theme = await db.get(ThemeRow, t.theme_id)
    rows = await _pages(db, t.id)
    definition = t.generation.get("theme_def") or {}
    total = 1 + len(definition.get("pages") or [])
    return TemplateOut(
        id=t.id,
        theme=theme.slug if theme else "",
        theme_version=t.theme_version,
        style=t.art_style,
        variant=t.variant,
        lang=t.lang,
        status=t.status.value,
        job=t.job.value,
        source=t.source,
        source_book_id=t.source_book_id,
        cost_usd=float(t.cost_usd or 0),
        flags=list(t.flags or []),
        error=t.error,
        progress=dict(t.generation.get("progress") or {}),
        pages_drawn=sum(bool(p.image_key) for p in rows),
        pages_total=total,
        updated_at=t.updated_at,
        texts={
            "vowelized": texts_ready(t),
            "kept": list((t.generation.get("texts") or {}).get("kept") or []),
            "at": (t.generation.get("texts") or {}).get("at"),
        },
        pages=[_page_out(p) for p in rows] if pages else [],
    )


def texts_ready(t: ClassicTemplate) -> bool:
    """The Arabic texts are vowelized for this template's gender, from its current words."""
    definition = t.generation.get("theme_def")
    cached = t.generation.get("texts") or {}
    if not definition or not cached:
        return False
    gender = parse_variant(t.variant).gender
    return bool(cached.get("hash") == source_hash(sources(Theme.model_validate(definition), gender)))


async def _template(db: AsyncSession, template_id: uuid.UUID) -> ClassicTemplate:
    t = await db.get(ClassicTemplate, template_id)
    if t is None:
        raise ApiError("not_found", 404)
    return t


async def _theme_row(db: AsyncSession, slug: str) -> ThemeRow:
    row = (await db.execute(select(ThemeRow).where(ThemeRow.slug == slug))).scalar_one_or_none()
    if row is None or not Theme.model_validate(row.definition).available:
        raise ApiError("not_found", 404)
    return row


def _audit(admin: AdminUser, action: str, t: ClassicTemplate, data: dict[str, Any] | None = None) -> AuditLog:
    return AuditLog(
        actor_user_id=admin.id,
        action=action,
        entity_type="classic_template",
        entity_id=str(t.id),
        data=data or {},
    )


# ---- templates ------------------------------------------------------------------------------------------


@router.get("/templates", dependencies=[Depends(require_permission("templates.view"))])
async def list_templates(db: SessionDep) -> list[TemplateOut]:
    rows = (await db.execute(select(ClassicTemplate).order_by(ClassicTemplate.updated_at.desc()))).scalars()
    return [await _out(db, t) for t in rows]


@router.get("/templates/{template_id}", dependencies=[Depends(require_permission("templates.view"))])
async def template_detail(template_id: uuid.UUID, db: SessionDep) -> TemplateOut:
    return await _out(db, await _template(db, template_id), pages=True)


class TemplateIn(BaseModel):
    theme: str = Field(max_length=64)
    style: str = Field(default="watercolor", max_length=40)
    variant: Variant
    lang: Literal["ar", "en"] = "ar"
    offline: bool = False  # placeholder art, no AI cost (a dry run of the whole flow)
    budget_usd: Decimal | None = Field(default=None, gt=0, le=20, decimal_places=2)


@router.post("/templates", status_code=202, dependencies=[Depends(require_permission("templates"))])
async def generate_template(
    body: TemplateIn, admin: AdminUser, db: SessionDep, queue: QueueDep
) -> TemplateOut:
    """Draw a template once with the premium pipeline (or continue one whose pages are not all drawn)."""
    row = await _theme_row(db, body.theme)
    t = (
        await db.execute(
            select(ClassicTemplate).where(
                ClassicTemplate.theme_id == row.id,
                ClassicTemplate.art_style == body.style,
                ClassicTemplate.variant == body.variant,
            )
        )
    ).scalar_one_or_none()
    if t is not None and t.job in (TemplateJob.queued, TemplateJob.running):
        raise ApiError("busy", 409)
    if t is not None and t.status in (S.approved, S.live):
        raise ApiError("template_exists", 409)
    if t is None:
        t = ClassicTemplate(
            theme_id=row.id,
            theme_version=row.version,
            art_style=body.style,
            variant=body.variant,
            lang=body.lang,
            source="generated",
            generation={"theme_def": row.definition, "offline": "sketch" if body.offline else False},
            created_by_user_id=admin.id,
        )
        db.add(t)
    if body.budget_usd is not None:
        t.budget_usd = body.budget_usd
    t.job = TemplateJob.queued
    await db.flush()
    db.add(_audit(admin, "classic.template_generate", t, {"theme": body.theme, "variant": body.variant}))
    await db.commit()
    enqueue(queue, TEMPLATE_JOB, str(t.id))
    return await _out(db, t)


class FromBookIn(BaseModel):
    book_id: uuid.UUID
    # The admin confirms the sample child is invented (a synthetic face): a real child's likeness must never
    # become artwork shown in other families' books.
    synthetic_child: Literal[True]


@router.post("/templates/from-book", status_code=202, dependencies=[Depends(require_permission("templates"))])
async def template_from_book(
    body: FromBookIn, admin: AdminUser, db: SessionDep, queue: QueueDep
) -> TemplateOut:
    """An approved sample book → the Classic template for its theme × style × variant, in review."""
    book = await db.get(Book, body.book_id)
    if book is None:
        raise ApiError("not_found", 404)
    child = await db.get(Child, book.child_id)
    ok = (
        child is not None
        and book.is_sample
        and child.is_sample
        and book.status in (BookStatus.in_review, BookStatus.approved)
        and book.pdf_interior_key
        and book.companion_id is None  # a drawn companion would not match the Classic text's companion
        and (book.generation or {}).get("line") != "classic"
    )
    if not ok or child is None:
        raise ApiError("template_source_invalid", 409)
    variant = variant_for(child.gender.value, child.wears_hijab)
    row = await db.get(ThemeRow, book.theme_id)
    if row is None:
        raise ApiError("not_found", 404)
    t = (
        await db.execute(
            select(ClassicTemplate).where(
                ClassicTemplate.theme_id == book.theme_id,
                ClassicTemplate.art_style == book.art_style,
                ClassicTemplate.variant == variant,
            )
        )
    ).scalar_one_or_none()
    if t is not None and t.job in (TemplateJob.queued, TemplateJob.running):
        raise ApiError("busy", 409)
    if t is not None and t.status in (S.approved, S.live):
        raise ApiError("template_exists", 409)
    if t is None:
        t = ClassicTemplate(theme_id=book.theme_id, art_style=book.art_style, variant=variant)
        db.add(t)
    t.theme_version = book.theme_version
    t.lang = book.language.value
    t.source, t.source_book_id = "sample_book", book.id
    t.status, t.job = S.draft, TemplateJob.queued
    t.generation = {
        "theme_def": (book.generation or {}).get("theme_def") or row.definition,
        "synthetic_child": True,
    }
    t.created_by_user_id = t.created_by_user_id or admin.id
    await db.flush()
    db.add(_audit(admin, "classic.template_from_book", t, {"book": str(book.id), "variant": variant}))
    await db.commit()
    enqueue(queue, FROM_BOOK_JOB, str(t.id), str(book.id))
    return await _out(db, t)


@router.post(
    "/templates/{template_id}/generate",
    status_code=202,
    dependencies=[Depends(require_permission("templates"))],
)
async def resume_template(
    template_id: uuid.UUID, admin: AdminUser, db: SessionDep, queue: QueueDep
) -> TemplateOut:
    """Draw the pages still missing (after a budget stop or an error). Locked pages are never redrawn."""
    t = await _template(db, template_id)
    if t.job in (TemplateJob.queued, TemplateJob.running):
        raise ApiError("busy", 409)
    t.job = TemplateJob.queued
    db.add(_audit(admin, "classic.template_resume", t))
    await db.commit()
    if t.source == "sample_book" and t.source_book_id is not None:  # copy the sample book's pages again
        enqueue(queue, FROM_BOOK_JOB, str(t.id), str(t.source_book_id))
    else:
        enqueue(queue, TEMPLATE_JOB, str(t.id))
    return await _out(db, t)


async def _page(db: AsyncSession, t: ClassicTemplate, beat: int) -> ClassicTemplatePage:
    page = (
        await db.execute(
            select(ClassicTemplatePage).where(
                ClassicTemplatePage.template_id == t.id, ClassicTemplatePage.beat == beat
            )
        )
    ).scalar_one_or_none()
    if page is None:
        raise ApiError("not_found", 404)
    return page


def _changed(t: ClassicTemplate) -> None:
    """A change to an approved or live template sends it back to review: parents' books never get unreviewed
    art (books already made keep their own copies)."""
    if t.status in (S.approved, S.live):
        t.status = S.in_review
        t.flags = list(dict.fromkeys([*(t.flags or []), "changed_after_approval"]))


@router.post(
    "/templates/{template_id}/pages/{beat}/regenerate",
    status_code=202,
    dependencies=[Depends(require_permission("templates"))],
)
async def regenerate_page(
    template_id: uuid.UUID, beat: int, admin: AdminUser, db: SessionDep, queue: QueueDep
) -> TemplateOut:
    t = await _template(db, template_id)
    page = await _page(db, t, beat)
    if page.locked:
        raise ApiError("template_locked", 409)
    if t.job in (TemplateJob.queued, TemplateJob.running):
        raise ApiError("busy", 409)
    t.job = TemplateJob.queued
    _changed(t)
    db.add(_audit(admin, "classic.template_page_redraw", t, {"beat": beat}))
    await db.commit()
    enqueue(queue, TEMPLATE_JOB, str(t.id), [beat])
    return await _out(db, t, pages=True)


class PageIn(BaseModel):
    locked: bool | None = None
    has_hero: bool | None = None
    hero_box: Box | None = None
    text_box: Box | None = None


@router.patch(
    "/templates/{template_id}/pages/{beat}", dependencies=[Depends(require_permission("templates"))]
)
async def edit_page(
    template_id: uuid.UUID, beat: int, body: PageIn, admin: AdminUser, db: SessionDep
) -> TemplatePageOut:
    """Lock or unlock a page, or correct its hero box or text box (normalized 0–1)."""
    t = await _template(db, template_id)
    page = await _page(db, t, beat)
    changes: dict[str, Any] = {}
    if body.hero_box is not None or body.has_hero is not None or body.text_box is not None:
        if page.locked and body.locked is not False:
            raise ApiError("template_locked", 409)
        _changed(t)
    if body.hero_box is not None:
        box = normalize_box(body.hero_box.x, body.hero_box.y, body.hero_box.w, body.hero_box.h)
        if box is None:
            raise ApiError("invalid_input", 422, {"fields": ["hero_box"]})
        page.hero_box = box.to_dict()
        page.flags = [f for f in (page.flags or []) if f != "no_hero_box"]
        changes["hero_box"] = page.hero_box
    if body.has_hero is not None:
        page.has_hero = body.has_hero
        changes["has_hero"] = body.has_hero
    if body.text_box is not None:
        box = normalize_box(body.text_box.x, body.text_box.y, body.text_box.w, body.text_box.h)
        if box is None:
            raise ApiError("invalid_input", 422, {"fields": ["text_box"]})
        page.text_box = {**box.to_dict(), "area": (page.text_box or {}).get("area", "top")}
        changes["text_box"] = page.text_box
    if body.locked is not None:
        page.locked = body.locked
        changes["locked"] = body.locked
    db.add(_audit(admin, "classic.template_page_edited", t, {"beat": beat, **changes}))
    await db.commit()
    return _page_out(page)


class StatusIn(BaseModel):
    to: TemplateStatus


@router.post("/templates/{template_id}/status", dependencies=[Depends(require_permission("templates"))])
async def change_status(
    template_id: uuid.UUID, body: StatusIn, admin: AdminUser, db: SessionDep
) -> TemplateOut:
    """draft → in_review → approved → live. Approving needs every page drawn and every hero page's box, and
    locks all pages; only a live template serves parents' books."""
    t = await _template(db, template_id)
    if body.to not in MOVES[t.status]:
        raise ApiError("invalid_transition", 409, {"from": t.status.value, "to": body.to.value})
    if t.job in (TemplateJob.queued, TemplateJob.running):
        raise ApiError("busy", 409)
    pages = await _pages(db, t.id)
    now = datetime.now(UTC)
    if body.to == S.approved:
        total = 1 + len((t.generation.get("theme_def") or {}).get("pages") or [])
        drawn = [p for p in pages if p.image_key]
        boxes = not any(p.has_hero and not p.hero_box for p in drawn)
        if len(drawn) < total or not boxes or not texts_ready(t):
            details = {"drawn": len(drawn), "total": total, "hero_boxes": boxes, "texts": texts_ready(t)}
            raise ApiError("template_incomplete", 409, details)
        for p in pages:
            p.locked = True
        t.approved_at, t.approved_by_user_id = now, admin.id
    if body.to == S.live:
        t.live_at = now
    before = t.status
    t.status = body.to
    t.flags = (
        [f for f in (t.flags or []) if f != "changed_after_approval"] if body.to == S.approved else t.flags
    )
    db.add(_audit(admin, "classic.template_status", t, {"from": before.value, "to": body.to.value}))
    await db.commit()
    return await _out(db, t, pages=True)


class TextsIn(BaseModel):
    refresh: bool = False  # take the theme's current words first (the story's pages must still line up)


@router.post(
    "/templates/{template_id}/texts", status_code=202, dependencies=[Depends(require_permission("templates"))]
)
async def vowelize_texts(
    template_id: uuid.UUID, body: TextsIn, admin: AdminUser, db: SessionDep, queue: QueueDep
) -> TemplateOut:
    """Vowelize the template's Arabic texts once (a Sonnet call, cached by the words' hash)."""
    t = await _template(db, template_id)
    if t.job in (TemplateJob.queued, TemplateJob.running):
        raise ApiError("busy", 409)
    if body.refresh:
        row = await db.get(ThemeRow, t.theme_id)
        if row is not None:
            before = t.generation.get("theme_def") or {}
            t.generation = {**t.generation, "theme_def": with_current_texts(before, row.definition)}
            if t.generation["theme_def"] != before:
                _changed(t)
    t.job = TemplateJob.queued
    db.add(_audit(admin, "classic.template_texts", t, {"refresh": body.refresh}))
    await db.commit()
    enqueue(queue, TEXTS_JOB, str(t.id), body.refresh)
    return await _out(db, t)


@router.get(
    "/templates/{template_id}/pages/{beat}/image",
    dependencies=[Depends(require_permission("templates.view"))],
)
async def page_image(
    template_id: uuid.UUID,
    beat: int,
    db: SessionDep,
    storage: StorageDep,
    v: Literal["preview", "print", "raw"] = "preview",
) -> Response:
    t = await _template(db, template_id)
    page = await _page(db, t, beat)
    key = {"preview": page.preview_key, "print": page.image_key, "raw": page.raw_key}[v]
    if not key:
        raise ApiError("not_found", 404)
    try:
        data = storage.get(key)
    except ObjectNotFound as e:
        raise ApiError("not_found", 404) from e
    media = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
    return Response(data, media_type=media, headers={"Cache-Control": "private, max-age=300"})


# ---- Classic test books and invented faces (the cost proof) ---------------------------------------------


class SampleOut(BaseModel):
    book_id: uuid.UUID
    child_id: uuid.UUID


@router.post("/samples", status_code=201, dependencies=[Depends(require_permission("books.review"))])
async def create_sample(
    request: Request,
    admin: AdminUser,
    db: SessionDep,
    settings: SettingsDep,
    storage: StorageDep,
    queue: QueueDep,
    theme: Annotated[str, Form(max_length=64)],
    name: Annotated[str, Form(min_length=1, max_length=40)],
    gender: Annotated[Literal["m", "f"], Form()],
    age: Annotated[int, Form(ge=2, le=10)],
    consent: Annotated[bool, Form()],
    photos: Annotated[list[UploadFile], File()],
    hijab: Annotated[bool, Form()] = False,
    glasses: Annotated[bool, Form()] = False,
    lang: Annotated[Literal["ar", "en"], Form()] = "ar",
    style: Annotated[str, Form(max_length=40)] = "watercolor",
    mode: Annotated[Literal["preview", "final"], Form()] = "final",
    offline: Annotated[bool, Form()] = False,
) -> SampleOut:
    """A Classic test book end to end. The photo is a synthetic face or a volunteer's with written consent."""
    if not consent:
        raise ApiError("consent_required", 422)
    if not 1 <= len(photos) <= 3:
        raise ApiError("invalid_input", 422, {"fields": ["photos"]})
    row = await _theme_row(db, theme)
    cleaned = [clean_image(await read_upload(p)) for p in photos]
    for data in cleaned:
        require_face(data)
    child = Child(
        guardian_user_id=admin.id,
        first_name=" ".join(name.split()),
        gender=Gender(gender),
        birth_year=date.today().year - age,
        wears_hijab=hijab and gender == "f",
        wears_glasses=glasses,
        is_sample=True,
    )
    db.add(child)
    await db.flush()
    db.add(
        Consent(
            child_id=child.id,
            guardian_user_id=admin.id,
            consent_text_version=SAMPLE_CONSENT_VERSION,
            scope="photo_processing",
            ip=request.client.host if request.client else None,
            user_agent=(request.headers.get("user-agent") or "")[:300] or None,
        )
    )
    for data in cleaned:
        photo = ChildPhoto(child_id=child.id, status=PhotoStatus.accepted)
        db.add(photo)
        await db.flush()
        photo.storage_key = f"children/{child.id}/photos/{photo.id}.jpg"
        storage.put(photo.storage_key, data, "image/jpeg")
    values = (await runtime_settings.current(db, settings)).values
    book = Book(
        child_id=child.id,
        theme_id=row.id,
        theme_version=row.version,
        created_by_user_id=admin.id,
        language=Locale(lang),
        art_style=style,
        status=BookStatus.generating,
        is_sample=True,
        budget_usd=classic_budget_usd(values),
        generation={
            "line": "classic",
            "offline": "sketch" if offline else False,
            "requested_by": str(admin.id),
        },
    )
    db.add(book)
    await db.flush()
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.classic_sample_created",
            entity_type="book",
            entity_id=str(book.id),
            data={"offline": offline, "theme": theme, "mode": mode},
        )
    )
    await db.commit()
    enqueue(queue, CLASSIC_JOB, str(book.id), mode)
    return SampleOut(book_id=book.id, child_id=child.id)


class FaceIn(BaseModel):
    gender: Literal["m", "f"]
    age: int = Field(default=5, ge=3, le=8)
    hijab: bool = False
    glasses: bool = False
    skin: str = Field(default="light olive", max_length=30, pattern=r"^[a-z -]+$")
    hair: str = Field(default="dark brown", max_length=30, pattern=r"^[a-z -]+$")
    top: str = Field(default="light blue", max_length=30, pattern=r"^[a-z -]+$")
    seed: int = Field(default=1, ge=0, le=2_000_000_000)


class FaceOut(BaseModel):
    id: uuid.UUID


def _face_key(face_id: uuid.UUID) -> str:
    return f"classic/synthetic/{face_id}.png"


@router.post("/synthetic-faces", status_code=202, dependencies=[Depends(require_permission("books.review"))])
async def synthetic_face(body: FaceIn, admin: AdminUser, db: SessionDep, queue: QueueDep) -> FaceOut:
    """An invented child's photo from the configured image model, for test books (never a real person)."""
    face_id = uuid.uuid4()
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="admin.synthetic_face",
            entity_type="synthetic",
            entity_id=str(face_id),
            data=body.model_dump(),
        )
    )
    await db.commit()
    enqueue(
        queue, FACE_JOB, _face_key(face_id), {**body.model_dump(), "hijab": body.hijab and body.gender == "f"}
    )
    return FaceOut(id=face_id)


@router.get("/synthetic-faces/{face_id}", dependencies=[Depends(require_permission("books.review"))])
async def synthetic_face_image(face_id: uuid.UUID, storage: StorageDep) -> Response:
    try:
        data = storage.get(_face_key(face_id))
    except ObjectNotFound as e:
        raise ApiError("not_ready", 409) from e
    return Response(data, media_type="image/png", headers={"Cache-Control": "private, no-store"})
