"""The parent create flow (CLAUDE.md §7–§8, design Create1–Create9, Addendum 4 §7): the child, the guardian's
consent, the photo, the character, the book preview, then the cart.

Every step needs a signed-in parent: a consent belongs to a guardian account, and so do the photos and the
"delete all my child's data" rights. A child, their photos, characters and books are only ever reachable by
that guardian. Original photos get their deletion time the moment the parent approves the character.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, File, Request, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import func, select

from qamra_ai.pipeline.character_feedback import NOTE_MAX, clean_note
from qamra_ai.pipeline.classic import classic_budget_usd
from qamra_ai.pipeline.custom_story import CUSTOM_THEME, CustomBrief, screen_brief
from qamra_ai.pipeline.theme import Theme
from qamra_api import ratelimit, runtime_settings
from qamra_api.classic import CLASSIC_JOB, live_template, resume_classic_draft
from qamra_api.consent import record_consent
from qamra_api.deps import CurrentUser, RedisDep, SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_api.portal.privacy import forget_in_class_book
from qamra_api.store.addons import fits
from qamra_api.store.cart import clean_personalization, ensure_cart
from qamra_api.store.catalog import addon_problems, load_catalog
from qamra_api.store.router import AddOnIn, CartOut, _own_item, cart_out, check_item
from qamra_api.store.workbooks import clean_latin, needs_name_en
from qamra_api.uploads import clean_image, read_upload, require_face
from qamra_core.db.models import (
    AuditLog,
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    ChildPhoto,
    Companion,
    CompanionStatus,
    Consent,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PhotoStatus,
)
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.store import ArtStyle, Cart, CartItem, CartStatus, CatalogProduct, OrderEvent, Variant
from qamra_core.storage import child_prefix

router = APIRouter(prefix="/api/create", tags=["create"])
CONSENT_VERSION = "parent-2026-09"  # the consent text shown on step 2 (messages: create.consent)
MAX_CHARACTERS = 4  # the first drawing and 3 free redraws per child
PREVIEWS_PER_DAY = 3  # Magic previews cost real money: per parent, per day
UPLOADS_PER_HOUR = 20
LINE_PRODUCTS = {"classic": ("classic-book",), "magic": ("magic-book", "magic-custom-story")}
CUSTOM_PRODUCT = "magic-custom-story"  # «قمرة سحري» with a custom story (Addendum 4 §7)


class ChildIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    gender: Literal["m", "f"]
    age: int = Field(ge=2, le=10)
    interests: list[Annotated[str, Field(max_length=30)]] = Field(default_factory=list, max_length=3)
    note: str | None = Field(default=None, max_length=60)  # "something special": woven in like an interest
    hijab: bool = False
    glasses: bool = False

    @field_validator("name")
    @classmethod
    def _squash(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("empty")
        return v


class CharacterOut(BaseModel):
    id: uuid.UUID
    status: str
    style: str
    approved: bool
    # the last time the parent approved it: the child's character is the one approved last (a parent can go
    # back to an earlier drawing), so later books reuse that one
    approved_at: datetime | None = None


class DrawingOut(CharacterOut):
    """One of the child's drawings kept for comparing (owner, 2026-10-10): every redraw stays choosable."""

    created_at: datetime
    style_name_ar: str
    style_name_en: str


class ChildOut(BaseModel):
    id: uuid.UUID
    name: str
    gender: str
    age: int
    hijab: bool
    glasses: bool
    consent: bool
    photos: int
    characters: list[CharacterOut]
    redraws_left: int
    interests: list[str] = Field(default_factory=list)  # the likes, then the note (as saved)
    name_latin: str | None = None  # the name in English letters (activity books' English name page)


def _character_out(c: Character) -> CharacterOut:
    return CharacterOut(
        id=c.id,
        status=c.status.value,
        style=c.art_style,
        approved=c.approved_at is not None,
        approved_at=c.approved_at,
    )


async def _child_out(db: SessionDep, child: Child) -> ChildOut:
    consent = (
        await db.execute(select(func.count()).select_from(Consent).where(Consent.child_id == child.id))
    ).scalar_one()
    photos = (
        await db.execute(
            select(func.count())
            .select_from(ChildPhoto)
            .where(ChildPhoto.child_id == child.id, ChildPhoto.storage_key.is_not(None))
        )
    ).scalar_one()
    characters = (
        (
            await db.execute(
                select(Character).where(Character.child_id == child.id).order_by(Character.created_at)
            )
        )
        .scalars()
        .all()
    )
    return ChildOut(
        id=child.id,
        name=child.first_name,
        gender=child.gender.value,
        age=date.today().year - child.birth_year,
        hijab=child.wears_hijab,
        glasses=child.wears_glasses,
        consent=bool(consent),
        photos=int(photos),
        # a drawing the cleanup removed is gone for the parent, but it still counts as one of the redraws
        characters=[_character_out(c) for c in characters if c.status != CharacterStatus.discarded],
        redraws_left=max(0, MAX_CHARACTERS - sum(c.status != CharacterStatus.failed for c in characters)),
        interests=list(child.interests or []),
        name_latin=child.name_latin,
    )


async def _my_child(db: SessionDep, user: CurrentUser, child_id: uuid.UUID) -> Child:
    child = await db.get(Child, child_id)
    if child is None or child.guardian_user_id != user.id:
        raise ApiError("not_found", 404)  # the same answer for someone else's child
    return child


@router.post("/children", status_code=201)
async def add_child(body: ChildIn, user: CurrentUser, db: SessionDep) -> ChildOut:
    child = Child(
        guardian_user_id=user.id,
        first_name=body.name,
        gender=Gender(body.gender),
        birth_year=date.today().year - body.age,
        interests=[" ".join(x.split()) for x in [*body.interests, body.note or ""] if x.strip()],
        wears_hijab=body.hijab and body.gender == "f",
        wears_glasses=body.glasses,
    )
    db.add(child)
    await db.commit()
    return await _child_out(db, child)


class ChildPatch(BaseModel):
    """Only the fields sent change. `interests` and `note` are one list on the child (the note last, as on
    POST): sending either replaces it. An empty `name_latin` clears it. The drawn character is never
    touched."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=40)
    gender: Literal["m", "f"] | None = None
    age: int | None = Field(default=None, ge=2, le=10)
    interests: list[Annotated[str, Field(max_length=30)]] | None = Field(default=None, max_length=3)
    note: str | None = Field(default=None, max_length=60)
    hijab: bool | None = None
    glasses: bool | None = None
    name_latin: str | None = Field(default=None, max_length=80)  # checked by `clean_latin`

    @field_validator("name")
    @classmethod
    def _squash(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = " ".join(v.split())
        if not v:
            raise ValueError("empty")
        return v


# The child's fields an activity line (no book yet) copies when the child fills it: a fixed name or age shows
# on those lines too. A story's line keeps its book's words.
LINE_FIELDS = ("child_name", "gender", "age", "hijab", "glasses", "name_en")


@router.patch("/children/{child_id}")
async def update_child(child_id: uuid.UUID, body: ChildPatch, user: CurrentUser, db: SessionDep) -> ChildOut:
    """«تعديل البيانات» (docs/plans/order-flows.md §c.4): fix the child's name, gender, age, look, likes or
    English name. Only the guardian; the audit log keeps which fields changed, never their values."""
    child = await _my_child(db, user, child_id)
    before = _editable(child)
    if "name_latin" in body.model_fields_set:
        latin = (body.name_latin or "").strip()
        try:
            child.name_latin = clean_latin(latin) if latin else None
        except ValueError as e:
            raise ApiError("name_en_invalid", 422, {"fields": ["name_latin"]}) from e
    if body.name is not None:
        child.first_name = body.name
    if body.gender is not None:
        child.gender = Gender(body.gender)
    if body.age is not None:
        child.birth_year = date.today().year - body.age
    if body.interests is not None or body.note is not None:
        child.interests = [
            " ".join(x.split()) for x in [*(body.interests or []), body.note or ""] if x.strip()
        ]
    if body.hijab is not None:
        child.wears_hijab = body.hijab
    if body.glasses is not None:
        child.wears_glasses = body.glasses
    if child.gender == Gender.m:
        child.wears_hijab = False
    after = _editable(child)
    changed = [k for k in after if after[k] != before[k]]
    if changed:
        await _refresh_lines(db, child)
        db.add(
            AuditLog(
                actor_user_id=user.id,
                action="child.updated",
                entity_type="child",
                entity_id=str(child.id),
                data={"fields": changed},
            )
        )
    await db.commit()
    return await _child_out(db, child)


def _editable(child: Child) -> dict[str, object]:
    return {
        "name": child.first_name,
        "gender": child.gender,
        "age": child.birth_year,
        "interests": list(child.interests or []),
        "hijab": child.wears_hijab,
        "glasses": child.wears_glasses,
        "name_latin": child.name_latin,
    }


async def _refresh_lines(db: SessionDep, child: Child) -> None:
    """The child's activity lines in open carts carry the new details (a story's line keeps its book)."""
    values = {
        "child_name": child.first_name,
        "gender": child.gender.value,
        "age": max(2, min(12, date.today().year - child.birth_year)),
        "hijab": child.wears_hijab,
        "glasses": child.wears_glasses,
        "name_en": child.name_latin,
    }
    rows = await db.execute(
        select(CartItem, Variant.options, CatalogProduct.line)
        .join(Cart, Cart.id == CartItem.cart_id)
        .join(Variant, Variant.id == CartItem.variant_id)
        .join(CatalogProduct, CatalogProduct.id == Variant.product_id)
        .where(CartItem.child_id == child.id, CartItem.book_id.is_(None), Cart.status == CartStatus.open)
    )
    for line, options, product_line in rows.all():
        held = dict(line.personalization)
        for key in LINE_FIELDS:
            if key == "name_en" and not (values["name_en"] and needs_name_en(product_line.value, options)):
                continue  # only a book that prints the English name gets it, and it is never emptied
            held[key] = values[key]
        line.personalization = held


@router.get("/children")
async def my_children(user: CurrentUser, db: SessionDep) -> list[ChildOut]:
    rows = (
        (await db.execute(select(Child).where(Child.guardian_user_id == user.id).order_by(Child.created_at)))
        .scalars()
        .all()
    )
    return [await _child_out(db, c) for c in rows]


# The personal fields an order or cart line may carry; the rest (format, add-ons, prices) stays for the books.
# The family book's family (names and city), the English name, the character used and a custom story's brief
# are the child's data too (docs/plans/order-flows.md §0.3-8).
PERSONAL = (
    "child_name",
    "gender",
    "age",
    "hijab",
    "glasses",
    "dedication",
    "family",
    "name_en",
    "character_id",
    "custom_brief",
)
OPEN_ORDERS = (
    OrderStatus.new,
    OrderStatus.confirmed,
    OrderStatus.generating,
    OrderStatus.review,
    OrderStatus.printing,
    OrderStatus.reprint,
)


@router.delete("/children/{child_id}", status_code=204)
async def delete_child(
    child_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> Response:
    """CLAUDE.md §3.1 "Delete all my child's data": photos, characters, companions, books and files, now.

    Orders stay (they are the shop's records) without the child's details; an open order gets a note so the
    team stops making that book. The audit log keeps only that it happened.
    """
    child = await _my_child(db, user, child_id)
    files = storage.delete_prefix(child_prefix(child.id))  # files first: a crash leaves rows to retry
    await forget_in_class_book(db, storage, child)  # their drawn likeness on a class book's shared pages too
    for line in (await db.execute(select(CartItem).where(CartItem.child_id == child.id))).scalars():
        await db.delete(line)  # a book that no longer exists cannot be bought
    orders: set[uuid.UUID] = set()
    for item in (await db.execute(select(OrderItem).where(OrderItem.child_id == child.id))).scalars():
        item.personalization = {k: v for k, v in item.personalization.items() if k not in PERSONAL}
        orders.add(item.order_id)
    for order in (
        await db.execute(select(Order).where(Order.id.in_(orders), Order.status.in_(OPEN_ORDERS)))
    ).scalars():
        db.add(
            OrderEvent(
                order_id=order.id,
                actor_user_id=user.id,
                kind="note",
                note="حذف ولي الأمر بيانات الطفل: لا يمكن تجهيز كتابه أو إعادة طباعته.",
            )
        )
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="child.deleted",
            entity_type="child",
            entity_id=str(child.id),
            data={"files": files, "orders": len(orders)},
        )
    )
    await db.delete(child)  # consents, photos, characters, companions and books go with it
    await db.commit()
    return Response(status_code=204)


class ConsentIn(BaseModel):
    accept: Literal[True]
    version: str = Field(max_length=32)


@router.post("/children/{child_id}/consent")
async def give_consent(
    child_id: uuid.UUID, body: ConsentIn, request: Request, user: CurrentUser, db: SessionDep
) -> ChildOut:
    child = await _my_child(db, user, child_id)
    if body.version != CONSENT_VERSION:
        raise ApiError("consent_outdated", 409)  # the page showed an older text: reload it
    record_consent(db, request, user_id=user.id, child_id=child.id, version=CONSENT_VERSION)
    await db.commit()
    return await _child_out(db, child)


@router.post("/children/{child_id}/photos")
async def upload_photos(
    child_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    storage: StorageDep,
    redis: RedisDep,
    settings: SettingsDep,
    photos: Annotated[list[UploadFile], File()],
) -> ChildOut:
    child = await _my_child(db, user, child_id)
    if await ratelimit.hit(redis, f"rl:photos:{user.id}", 3600) > UPLOADS_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    consented = (
        await db.execute(select(func.count()).select_from(Consent).where(Consent.child_id == child.id))
    ).scalar_one()
    if not consented:
        raise ApiError("consent_required", 409)
    if not 1 <= len(photos) <= 3:
        raise ApiError("invalid_input", 422, {"fields": ["photos"]})
    cleaned = [clean_image(await read_upload(p)) for p in photos]
    for data in cleaned:
        require_face(data)
    now = datetime.now(UTC)
    for old in (
        await db.execute(
            select(ChildPhoto).where(ChildPhoto.child_id == child.id, ChildPhoto.storage_key.is_not(None))
        )
    ).scalars():
        storage.delete(str(old.storage_key))  # "change the photo": the next drawing uses the new one
        old.storage_key, old.status, old.deleted_at = None, PhotoStatus.deleted, now
    approved = (
        await db.execute(
            select(func.count())
            .select_from(Character)
            .where(Character.child_id == child.id, Character.approved_at.is_not(None))
        )
    ).scalar_one()
    retention = int((await runtime_settings.current(db, settings)).values["photo_retention_hours"])
    for data in cleaned:
        photo = ChildPhoto(
            child_id=child.id,
            status=PhotoStatus.accepted,
            delete_after=now + timedelta(hours=retention) if approved else None,  # already approved once
        )
        db.add(photo)
        await db.flush()
        photo.storage_key = f"children/{child.id}/photos/{photo.id}.jpg"
        storage.put(photo.storage_key, data, "image/jpeg")
    await db.commit()
    return await _child_out(db, child)


class CharacterIn(BaseModel):
    style: str = Field(max_length=40)
    fixes: list[Literal["skin", "face", "hair", "age"]] = Field(default_factory=list, max_length=4)
    # «ما الذي لا يشبهه؟» in the parent's own words: read by the worker (prompts character_feedback.v1), which
    # keeps only what is about the child's looks; an unsafe or off-topic note is dropped there, silently
    note: str | None = Field(default=None, max_length=NOTE_MAX * 2)  # checked once tidied (`_tidy_note`)
    # the parent pressed «أعيدوا الرسم»: always a new drawing, never the approved one reused
    redraw: bool = False
    # the book it is drawn for: the style must be one that book's line accepts (`ArtStyle.lines`)
    line: str | None = Field(default=None, max_length=16)
    sku: str | None = Field(default=None, max_length=64)

    @field_validator("note")
    @classmethod
    def _tidy_note(cls, v: str | None) -> str | None:
        v = clean_note(v)
        if v is not None and len(v) > NOTE_MAX:
            raise ValueError("too long")
        return v


@router.post("/children/{child_id}/characters", status_code=202)
async def draw_character(
    child_id: uuid.UUID, body: CharacterIn, user: CurrentUser, db: SessionDep, queue: QueueDep
) -> CharacterOut:
    child = await _my_child(db, user, child_id)
    catalog = await load_catalog(db)
    if body.style not in catalog.styles:
        raise ApiError("invalid_style", 422)
    line = body.line
    if body.sku is not None:
        variant = catalog.variants.get(body.sku)
        if variant is None:
            raise ApiError("unknown_product", 404)
        line = catalog.product_of(variant).line.value
    if line is not None and line not in catalog.styles[body.style].lines:
        raise ApiError("invalid_style", 422)  # e.g. a coloring character for an activity book
    if not (body.fixes or body.note or body.redraw):  # Addendum 9 §6: the approved character is reused
        approved = (
            (
                await db.execute(
                    select(Character)
                    .where(
                        Character.child_id == child.id,
                        Character.art_style == body.style,
                        Character.approved_at.is_not(None),
                        Character.sheet_image_key.is_not(None),
                    )
                    .order_by(Character.approved_at.desc())
                )
            )
            .scalars()
            .first()
        )
        newer_photo = (
            await db.execute(
                select(func.max(ChildPhoto.created_at)).where(
                    ChildPhoto.child_id == child.id, ChildPhoto.storage_key.is_not(None)
                )
            )
        ).scalar_one()
        if approved is not None and (
            newer_photo is None or newer_photo <= (approved.approved_at or newer_photo)
        ):
            return _character_out(approved)  # a new photo since then means the parent wants a new drawing
    photos = (
        await db.execute(
            select(func.count())
            .select_from(ChildPhoto)
            .where(ChildPhoto.child_id == child.id, ChildPhoto.storage_key.is_not(None))
        )
    ).scalar_one()
    if not photos:
        raise ApiError("photo_required", 409)
    drawn = (
        await db.execute(
            select(func.count())
            .select_from(Character)
            .where(Character.child_id == child.id, Character.status != CharacterStatus.failed)
        )
    ).scalar_one()  # a drawing that failed on our side is not one of the parent's redraws
    if drawn >= MAX_CHARACTERS:
        raise ApiError("redraws_used", 429)
    asked: dict[str, Any] = {"attempt": drawn + 1, "fixes": sorted(set(body.fixes))}  # what didn't look right
    if body.note:
        asked["note"] = body.note  # the parent's words; the worker adds what it made of them
    character = Character(
        child_id=child.id, art_style=body.style, status=CharacterStatus.generating, params=asked
    )
    db.add(character)
    await db.commit()
    enqueue(queue, "qamra_worker.jobs.create.generate_character", str(character.id))
    return _character_out(character)


@router.get("/children/{child_id}/characters")
async def child_drawings(child_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> list[DrawingOut]:
    """The child's drawings, newest first (only the guardian): every drawing that came out, in any style, so
    the parent can compare them and go back to an earlier one. A failed drawing has no picture and is left
    out; so is one the cleanup removed (`discarded`: never approved, after 30 days). Each picture comes
    through `/characters/{id}/image`, privately."""
    child = await _my_child(db, user, child_id)
    rows = (
        (
            await db.execute(
                select(Character)
                .where(
                    Character.child_id == child.id,
                    Character.status.in_((CharacterStatus.ready, CharacterStatus.approved)),
                    Character.sheet_image_key.is_not(None),
                )
                .order_by(Character.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    names = {
        slug: (ar, en)
        for slug, ar, en in await db.execute(
            select(ArtStyle.slug, ArtStyle.name_ar, ArtStyle.name_en).where(
                ArtStyle.slug.in_({c.art_style for c in rows})
            )
        )
    }
    out = []
    for c in rows:
        ar, en = names.get(c.art_style, (c.art_style, c.art_style))
        out.append(
            DrawingOut(
                **_character_out(c).model_dump(), created_at=c.created_at, style_name_ar=ar, style_name_en=en
            )
        )
    return out


async def _my_character(db: SessionDep, user: CurrentUser, character_id: uuid.UUID) -> Character:
    character = await db.get(Character, character_id)
    if character is None:
        raise ApiError("not_found", 404)
    await _my_child(db, user, character.child_id)
    return character


@router.get("/characters/{character_id}")
async def character_status(character_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> CharacterOut:
    return _character_out(await _my_character(db, user, character_id))


@router.get("/characters/{character_id}/image")
async def character_image(
    character_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> Response:
    character = await _my_character(db, user, character_id)
    if not character.sheet_image_key:
        raise ApiError("not_ready", 409)
    return Response(
        storage.get(character.sheet_image_key),
        media_type="image/png",
        headers={"Cache-Control": "private, no-store"},
    )


@router.post("/characters/{character_id}/approve")
async def approve_character(
    character_id: uuid.UUID, user: CurrentUser, db: SessionDep, settings: SettingsDep
) -> CharacterOut:
    character = await _my_character(db, user, character_id)
    if character.status not in (CharacterStatus.ready, CharacterStatus.approved):
        raise ApiError("not_ready", 409)
    now = datetime.now(UTC)
    # approved again when the parent goes back to it: the child's character is the one approved last, so every
    # later book (stories, activity books, the class book) reuses this drawing and its style
    again = character.approved_at is not None
    character.status, character.approved_at = CharacterStatus.approved, now
    retention = int((await runtime_settings.current(db, settings)).values["photo_retention_hours"])
    for photo in (
        await db.execute(select(ChildPhoto).where(ChildPhoto.child_id == character.child_id))
    ).scalars():
        photo.delete_after = photo.delete_after or now + timedelta(hours=retention)  # CLAUDE.md §3.1
    db.add(
        AuditLog(
            actor_user_id=user.id,
            action="character.approved",
            entity_type="character",
            entity_id=str(character.id),
            data={"style": character.art_style, "again": again},
        )
    )
    await db.commit()
    return _character_out(character)


# ---- the book: preview, text edits, then the cart ----------------------------------------------------------


class BookIn(BaseModel):
    child_id: uuid.UUID
    character_id: uuid.UUID
    theme: str = Field(max_length=64)
    line: Literal["classic", "magic"]
    language: Literal["ar", "en"] = "ar"
    dedication: str | None = Field(default=None, max_length=120)
    companion_id: uuid.UUID | None = None  # «ارسم صاحبك»: the child's chosen companion; None → the theme's
    custom: dict[str, Any] | None = None  # «حكاية خاصة» (Magic): the brief, checked by `custom_brief`


class CompanionRef(BaseModel):
    id: uuid.UUID
    name: str


class PageOut(BaseModel):
    beat: int
    text: str | None
    image: bool


class BookOut(BaseModel):
    id: uuid.UUID
    status: str
    line: str
    theme: str
    style: str
    title: str | None
    dedication: str | None
    preview: bool  # Magic draws a preview before ordering; Classic uses the theme's ready template
    progress: dict[str, Any]
    pages: list[PageOut]
    custom: bool = False  # a custom story: sold as magic-custom-story
    companion: CompanionRef | None = None  # the child's drawn companion, when the book has one
    problem: str | None = None  # why the book stopped, when the parent can fix it (brief_unsafe)


async def _book_out(db: SessionDep, book: Book) -> BookOut:
    out = await _book_core(db, book)
    comp = await db.get(Companion, book.companion_id) if book.companion_id else None
    out.custom = bool(book.generation.get("custom"))
    out.companion = CompanionRef(id=comp.id, name=comp.name) if comp else None
    out.problem = "brief_unsafe" if "brief_unsafe" in (book.flags or []) else None
    return out


async def _book_core(db: SessionDep, book: Book) -> BookOut:
    theme = await db.get(ThemeRow, book.theme_id)
    pages = (
        (await db.execute(select(BookPage).where(BookPage.book_id == book.id).order_by(BookPage.index)))
        .scalars()
        .all()
    )
    return BookOut(
        id=book.id,
        status=book.status.value,
        line=str(book.generation.get("line", "magic")),
        theme=theme.slug if theme else "",
        style=book.art_style,
        title=book.title,
        dedication=book.parent_message,
        preview=book.generation.get("line") == "magic" or bool(book.generation.get("template_id")),
        progress=dict(book.generation.get("progress") or {}),
        pages=[PageOut(beat=p.index, text=p.text, image=bool(p.preview_image_key)) for p in pages],
    )


async def _my_book(db: SessionDep, user: CurrentUser, book_id: uuid.UUID) -> Book:
    book = await db.get(Book, book_id)
    if book is None or book.created_by_user_id != user.id:
        raise ApiError("not_found", 404)
    return book


def custom_brief(body: BookIn) -> dict[str, Any] | None:
    """«حكاية خاصة» (Magic only): the brief's lengths, then the instant screen (links, phone numbers, plainly
    unsafe words). The worker runs the AI safety review on it before any story is written."""
    if body.custom is None:
        if body.theme == CUSTOM_THEME:
            raise ApiError("custom_story_invalid", 422, {"fields": ["custom"]})
        return None
    if body.line != "magic":
        raise ApiError("custom_story_magic_only", 422)
    if body.theme != CUSTOM_THEME:
        raise ApiError("custom_story_invalid", 422, {"fields": ["theme"]})
    try:
        brief = CustomBrief.model_validate(body.custom)
    except ValidationError as e:
        fields = sorted({str(err["loc"][0]) for err in e.errors() if err["loc"]})
        raise ApiError("custom_story_invalid", 422, {"fields": fields}) from e
    unsafe = screen_brief(brief)
    if unsafe:
        raise ApiError("custom_story_unsafe", 422, {"fields": unsafe})
    return brief.model_dump()


async def _book_extras(
    db: SessionDep, child: Child, body: BookIn
) -> tuple[uuid.UUID | None, dict[str, Any] | None]:
    """The book's optional extras: the child's chosen companion and the custom story brief."""
    companion_id = None
    if body.companion_id is not None:
        comp = await db.get(Companion, body.companion_id)
        if comp is None or comp.child_id != child.id:
            raise ApiError("not_found", 404)
        if comp.status != CompanionStatus.approved or not comp.sheet_key:
            raise ApiError("companion_not_approved", 409)
        companion_id = comp.id
    return companion_id, custom_brief(body)


@router.post("/books", status_code=201)
async def start_book(
    body: BookIn, user: CurrentUser, db: SessionDep, settings: SettingsDep, queue: QueueDep
) -> BookOut:
    child = await _my_child(db, user, body.child_id)
    character = await _my_character(db, user, body.character_id)
    if character.child_id != child.id or character.approved_at is None:
        raise ApiError("character_not_approved", 409)
    companion_id, custom = await _book_extras(db, child, body)
    row = (
        await db.execute(select(ThemeRow).where(ThemeRow.slug == body.theme, ThemeRow.active))
    ).scalar_one_or_none()
    if row is None or not Theme.model_validate(row.definition).available:
        raise ApiError("not_found", 404)
    magic = body.line == "magic"
    # Classic (Addendum 4 §1A) needs a live template for this story, style and the child's look
    template = None if magic else await live_template(db, row.id, character.art_style, child)
    if not magic and template is None:
        raise ApiError("classic_unavailable", 409)
    since = datetime.now(UTC) - timedelta(days=1)
    previews = (
        await db.execute(
            select(func.count())
            .select_from(Book)
            .where(Book.created_by_user_id == user.id, Book.created_at >= since, Book.is_sample.is_(False))
        )
    ).scalar_one()
    if previews >= PREVIEWS_PER_DAY:  # every preview costs real money, Classic ones too
        raise ApiError("too_many_previews", 429)
    values = (await runtime_settings.current(db, settings)).values
    classic = {"template_id": str(template.id), "budget_pinned": True} if template else {}
    if custom:
        classic["custom"] = custom  # the worker writes the story and its pictures from the brief
    book = Book(
        child_id=child.id,
        character_id=character.id,
        companion_id=companion_id,
        theme_id=row.id,
        theme_version=row.version,
        created_by_user_id=user.id,
        language=Locale(body.language),
        art_style=character.art_style,
        status=BookStatus.generating,
        parent_message=" ".join(body.dedication.split()) if body.dedication else None,
        budget_usd=Decimal(str(values["book_budget_usd"])) if magic else classic_budget_usd(values),
        generation={"line": body.line, "offline": False, "requested_by": str(user.id), **classic},
    )
    db.add(book)
    await db.commit()
    job = "qamra_worker.jobs.books.generate_book" if magic else CLASSIC_JOB
    enqueue(queue, job, str(book.id), "preview")  # the cover and the first pages, watermarked
    return await _book_out(db, book)


@router.get("/books/{book_id}")
async def book_status(
    book_id: uuid.UUID, user: CurrentUser, db: SessionDep, settings: SettingsDep, queue: QueueDep
) -> BookOut:
    book = await _my_book(db, user, book_id)
    values = (await runtime_settings.current(db, settings)).values
    if await resume_classic_draft(db, book, values):  # a Classic draft from before its template went live
        enqueue(queue, CLASSIC_JOB, str(book.id), "preview")
    return await _book_out(db, book)


@router.get("/books/{book_id}/pages/{beat}/image")
async def preview_image(
    book_id: uuid.UUID, beat: int, user: CurrentUser, db: SessionDep, storage: StorageDep
) -> Response:
    book = await _my_book(db, user, book_id)
    page = (
        await db.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == beat))
    ).scalar_one_or_none()
    if page is None or not page.preview_image_key:
        raise ApiError("not_found", 404)
    return Response(
        storage.get(page.preview_image_key),
        media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store"},
    )


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=280)


TEXT_LOCKED = (BookStatus.in_review, BookStatus.approved, BookStatus.ordered, BookStatus.printed)


@router.patch("/books/{book_id}/pages/{beat}")
async def edit_text(
    book_id: uuid.UUID, beat: int, body: TextIn, user: CurrentUser, db: SessionDep
) -> BookOut:
    """Step 8 of the design: the parent may reword a page before the final drawing. Once the final files are
    being made or wait for our review, the words are staff's to check (`text_locked`)."""
    book = await _my_book(db, user, book_id)
    if book.status in TEXT_LOCKED or (
        book.status == BookStatus.generating and book.generation.get("mode") == "final"
    ):
        raise ApiError("text_locked", 409)
    page = (
        await db.execute(select(BookPage).where(BookPage.book_id == book.id, BookPage.index == beat))
    ).scalar_one_or_none()
    if page is None or beat == 0:
        raise ApiError("not_found", 404)
    page.text = " ".join(body.text.split())
    page.flags = sorted({*(page.flags or []), "parent_edited"})  # the safety review looks again before print
    await db.commit()
    return await _book_out(db, book)


class ToCartIn(BaseModel):
    sku: str = Field(max_length=64)
    addons: list[AddOnIn] = Field(default_factory=list, max_length=20)
    item_id: uuid.UUID | None = None  # the line added in one tap on the story page, which this book fills


@router.post("/books/{book_id}/cart", status_code=201)
async def add_to_cart(
    book_id: uuid.UUID,
    body: ToCartIn,
    request: Request,
    response: Response,
    user: CurrentUser,
    db: SessionDep,
    settings: SettingsDep,
) -> CartOut:
    book = await _my_book(db, user, book_id)
    child = await db.get(Child, book.child_id)
    theme = await db.get(ThemeRow, book.theme_id)
    if child is None or theme is None:
        raise ApiError("not_found", 404)
    catalog = await load_catalog(db)
    variant = catalog.variants.get(body.sku)
    line = str(book.generation.get("line", "magic"))
    if variant is None or catalog.product_of(variant).slug not in LINE_PRODUCTS[line]:
        raise ApiError("unknown_product", 404)
    if (catalog.product_of(variant).slug == CUSTOM_PRODUCT) != bool(book.generation.get("custom")):
        raise ApiError("unknown_product", 404)  # a custom story is sold as magic-custom-story, and only it is
    addons = [a.model_dump() for a in body.addons]
    if book.parent_message and line == "classic" and all(a["slug"] != "dedication-page" for a in addons):
        addons.append({"slug": "dedication-page", "qty": 1})  # written on the story step; free in Magic
    companion_addon = catalog.addons.get("drawing-companion")
    if (
        book.companion_id
        and line == "classic"
        and companion_addon is not None
        and line in companion_addon.lines  # withdrawn from Classic until its templates draw the companion
        and all(a["slug"] != "drawing-companion" for a in addons)
    ):
        addons.append({"slug": "drawing-companion", "qty": 1})  # chosen on the companion step; free in Magic
    check_item(catalog, variant, book.art_style, addons)
    personalization = clean_personalization(
        {
            "child_name": child.first_name,
            "gender": child.gender.value,
            "age": max(2, min(12, date.today().year - child.birth_year)),
            "hijab": child.wears_hijab,
            "glasses": child.wears_glasses,
            "dedication": book.parent_message,
        }
    )
    same: CartItem | None
    if body.item_id is not None:  # «أكملوا بيانات الطفل»: the story page's line gets this book
        cart, held = await _own_item(db, request, user, body.item_id)  # 404 unless in the caller's cart
        sold = next((v for v in catalog.variants.values() if v.id == held.variant_id), None)
        if sold is None or catalog.product_of(sold).slug not in LINE_PRODUCTS[line]:
            raise ApiError("item_mismatch", 409)
        held.child_id, held.book_id, held.personalization = child.id, book.id, personalization
        held.style_slug, held.theme_slug = book.art_style, theme.slug
        same = held
    else:
        cart = await ensure_cart(db, request, response, user, settings)
        same = (
            (
                await db.execute(
                    select(CartItem).where(CartItem.cart_id == cart.id, CartItem.book_id == book.id)
                )
            )
            .scalars()
            .first()
        )
    if same is not None:  # Addendum 9: back from the add-ons step to the format, still one line per book
        chosen = {a["slug"] for a in addons}
        kept = [  # the add-ons chosen after the preview that still fit the (maybe new) format
            a
            for a in same.addons
            if a["slug"] not in chosen
            and a["slug"] in catalog.addons
            and fits(catalog, variant, catalog.addons[a["slug"]])
        ]
        if kept and not addon_problems(catalog, variant, [*addons, *kept]):
            addons = [*addons, *kept]
        same.variant_id, same.addons = variant.id, addons
        await db.commit()
        return await cart_out(db, cart)
    db.add(
        CartItem(
            cart_id=cart.id,
            variant_id=variant.id,
            style_slug=book.art_style,
            theme_slug=theme.slug,
            qty=1,
            addons=addons,
            personalization=personalization,
            child_id=child.id,
            book_id=book.id,
        )
    )
    await db.commit()
    return await cart_out(db, cart)
