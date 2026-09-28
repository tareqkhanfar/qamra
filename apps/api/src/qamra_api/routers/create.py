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
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from qamra_ai.pipeline.theme import Theme
from qamra_api import ratelimit, runtime_settings
from qamra_api.deps import CurrentUser, RedisDep, SessionDep, SettingsDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.jobs import QueueDep, enqueue
from qamra_api.store.cart import clean_personalization, ensure_cart
from qamra_api.store.catalog import load_catalog
from qamra_api.store.router import AddOnIn, CartOut, cart_out, check_item
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
    Consent,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PhotoStatus,
)
from qamra_core.db.models import Theme as ThemeRow
from qamra_core.db.store import CartItem, OrderEvent
from qamra_core.storage import child_prefix

router = APIRouter(prefix="/api/create", tags=["create"])
CONSENT_VERSION = "parent-2026-09"  # the consent text shown on step 2 (messages: create.consent)
MAX_CHARACTERS = 4  # the first drawing and 3 free redraws per child
PREVIEWS_PER_DAY = 3  # Magic previews cost real money: per parent, per day
UPLOADS_PER_HOUR = 20
LINE_PRODUCTS = {"classic": ("classic-book",), "magic": ("magic-book", "magic-custom-story")}


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


def _character_out(c: Character) -> CharacterOut:
    return CharacterOut(id=c.id, status=c.status.value, style=c.art_style, approved=c.approved_at is not None)


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
        characters=[_character_out(c) for c in characters],
        redraws_left=max(0, MAX_CHARACTERS - sum(c.status != CharacterStatus.failed for c in characters)),
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


@router.get("/children")
async def my_children(user: CurrentUser, db: SessionDep) -> list[ChildOut]:
    rows = (
        (await db.execute(select(Child).where(Child.guardian_user_id == user.id).order_by(Child.created_at)))
        .scalars()
        .all()
    )
    return [await _child_out(db, c) for c in rows]


# The personal fields an order or cart line may carry; the rest (format, add-ons, prices) stays for the books.
PERSONAL = ("child_name", "gender", "age", "hijab", "glasses", "dedication")
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
    db.add(
        Consent(
            child_id=child.id,
            guardian_user_id=user.id,
            consent_text_version=CONSENT_VERSION,
            scope="photo_processing",
            ip=request.client.host if request.client else None,
            user_agent=(request.headers.get("user-agent") or "")[:300] or None,
        )
    )
    db.add(
        AuditLog(actor_user_id=user.id, action="consent.given", entity_type="child", entity_id=str(child.id))
    )
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


@router.post("/children/{child_id}/characters", status_code=202)
async def draw_character(
    child_id: uuid.UUID, body: CharacterIn, user: CurrentUser, db: SessionDep, queue: QueueDep
) -> CharacterOut:
    child = await _my_child(db, user, child_id)
    catalog = await load_catalog(db)
    if body.style not in catalog.styles:
        raise ApiError("invalid_style", 422)
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
    character = Character(
        child_id=child.id,
        art_style=body.style,
        status=CharacterStatus.generating,
        params={"attempt": drawn + 1, "fixes": sorted(set(body.fixes))},  # what didn't look like the child
    )
    db.add(character)
    await db.commit()
    enqueue(queue, "qamra_worker.jobs.create.generate_character", str(character.id))
    return _character_out(character)


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
    character.status, character.approved_at = CharacterStatus.approved, character.approved_at or now
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


async def _book_out(db: SessionDep, book: Book) -> BookOut:
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
        preview=book.generation.get("line") == "magic",
        progress=dict(book.generation.get("progress") or {}),
        pages=[PageOut(beat=p.index, text=p.text, image=bool(p.preview_image_key)) for p in pages],
    )


async def _my_book(db: SessionDep, user: CurrentUser, book_id: uuid.UUID) -> Book:
    book = await db.get(Book, book_id)
    if book is None or book.created_by_user_id != user.id:
        raise ApiError("not_found", 404)
    return book


@router.post("/books", status_code=201)
async def start_book(
    body: BookIn, user: CurrentUser, db: SessionDep, settings: SettingsDep, queue: QueueDep
) -> BookOut:
    child = await _my_child(db, user, body.child_id)
    character = await _my_character(db, user, body.character_id)
    if character.child_id != child.id or character.approved_at is None:
        raise ApiError("character_not_approved", 409)
    row = (
        await db.execute(select(ThemeRow).where(ThemeRow.slug == body.theme, ThemeRow.active))
    ).scalar_one_or_none()
    if row is None or not Theme.model_validate(row.definition).available:
        raise ApiError("not_found", 404)
    magic = body.line == "magic"
    if magic:
        since = datetime.now(UTC) - timedelta(days=1)
        previews = (
            await db.execute(
                select(func.count())
                .select_from(Book)
                .where(
                    Book.created_by_user_id == user.id, Book.created_at >= since, Book.is_sample.is_(False)
                )
            )
        ).scalar_one()
        if previews >= PREVIEWS_PER_DAY:
            raise ApiError("too_many_previews", 429)
    values = (await runtime_settings.current(db, settings)).values
    book = Book(
        child_id=child.id,
        character_id=character.id,
        theme_id=row.id,
        theme_version=row.version,
        created_by_user_id=user.id,
        language=Locale(body.language),
        art_style=character.art_style,
        status=BookStatus.generating if magic else BookStatus.draft,
        parent_message=" ".join(body.dedication.split()) if body.dedication else None,
        budget_usd=Decimal(str(values["book_budget_usd"])),
        generation={"line": body.line, "offline": False, "requested_by": str(user.id)},
    )
    db.add(book)
    await db.commit()
    if magic:
        enqueue(queue, "qamra_worker.jobs.books.generate_book", str(book.id), "preview")
    return await _book_out(db, book)


@router.get("/books/{book_id}")
async def book_status(book_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> BookOut:
    return await _book_out(db, await _my_book(db, user, book_id))


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


@router.patch("/books/{book_id}/pages/{beat}")
async def edit_text(
    book_id: uuid.UUID, beat: int, body: TextIn, user: CurrentUser, db: SessionDep
) -> BookOut:
    """Step 8 of the design: the parent may reword a page before the final drawing."""
    book = await _my_book(db, user, book_id)
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
    addons = [a.model_dump() for a in body.addons]
    if book.parent_message and line == "classic" and all(a["slug"] != "dedication-page" for a in addons):
        addons.append({"slug": "dedication-page", "qty": 1})  # written on the story step; free in Magic
    check_item(catalog, variant, book.art_style, addons)
    cart = await ensure_cart(db, request, response, user, settings)
    db.add(
        CartItem(
            cart_id=cart.id,
            variant_id=variant.id,
            style_slug=book.art_style,
            theme_slug=theme.slug,
            qty=1,
            addons=addons,
            personalization=clean_personalization(
                {
                    "child_name": child.first_name,
                    "gender": child.gender.value,
                    "age": date.today().year - child.birth_year,
                    "hijab": child.wears_hijab,
                    "glasses": child.wears_glasses,
                    "dedication": book.parent_message,
                }
            ),
            child_id=child.id,
            book_id=book.id,
        )
    )
    await db.commit()
    return await cart_out(db, cart)
