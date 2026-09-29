"""Test-only fixtures for the end-to-end tests (tests/e2e): mounted only when `E2E_FIXTURES=true` and never
in prod (the settings refuse it). They create what the paid steps would have made, with placeholder art and
no AI call: a child with the guardian's consent, an approved character, and a book waiting at its preview.
Everything belongs to the signed-in parent, so the real create, cart and checkout APIs run unchanged.
"""

import io
import secrets
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field
from sqlalchemy import select

from qamra_api.deps import CurrentUser, SessionDep, StorageDep
from qamra_api.errors import ApiError
from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.store import gift_cards
from qamra_core.db.models import (
    Book,
    BookPage,
    BookStatus,
    Character,
    CharacterStatus,
    Child,
    Consent,
    Currency,
    Gender,
    Locale,
    Order,
    OrderItem,
    PageStatus,
    Theme,
)
from qamra_core.db.store import Coupon, CouponKind, GiftCard

router = APIRouter(prefix="/api/e2e", tags=["e2e"])
PREVIEW_BEATS = (0, 1, 2, 3)  # the cover and three pages, like a real preview


def _placeholder(color: tuple[int, int, int], fmt: str, side: int = 512) -> bytes:
    """A night sky with a moon: clearly not a real drawing."""
    img = Image.new("RGB", (side, side), color)
    draw = ImageDraw.Draw(img)
    draw.ellipse((side * 0.55, side * 0.12, side * 0.85, side * 0.42), fill=(242, 179, 61))
    draw.rectangle((0, side * 0.72, side, side), fill=(62, 107, 77))
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


class BookIn(BaseModel):
    child_id: uuid.UUID | None = None  # another book for a child made before (reuses its character)
    name: str = Field(default="ليان", min_length=1, max_length=40)
    gender: Literal["m", "f"] = "f"
    age: int = Field(default=6, ge=2, le=10)
    hijab: bool = False
    line: Literal["classic", "magic"] = "classic"
    theme: str = Field(default="olive-season", max_length=64)
    style: str = Field(default="watercolor", max_length=40)


class BookOut(BaseModel):
    child_id: uuid.UUID
    character_id: uuid.UUID
    book_id: uuid.UUID
    theme: str
    line: str
    characters: int  # how many characters the child has (a second book must not add one)


@router.post("/books", status_code=201)
async def preview_book(body: BookIn, user: CurrentUser, db: SessionDep, storage: StorageDep) -> BookOut:
    theme = (await db.execute(select(Theme).where(Theme.slug == body.theme))).scalar_one_or_none()
    if theme is None:
        raise ApiError("not_found", 404)
    if body.child_id is not None:
        child = await db.get(Child, body.child_id)
        if child is None or child.guardian_user_id != user.id:
            raise ApiError("not_found", 404)
    else:
        child = Child(
            guardian_user_id=user.id,
            first_name=body.name,
            gender=Gender(body.gender),
            birth_year=date.today().year - body.age,
            wears_hijab=body.hijab and body.gender == "f",
        )
        db.add(child)
        await db.flush()
        db.add(Consent(child_id=child.id, guardian_user_id=user.id, consent_text_version=CONSENT_VERSION))
    character = (
        (
            await db.execute(
                select(Character)
                .where(Character.child_id == child.id, Character.approved_at.is_not(None))
                .order_by(Character.approved_at.desc())
            )
        )
        .scalars()
        .first()
    )
    if character is None:
        character = Character(
            child_id=child.id,
            art_style=body.style,
            status=CharacterStatus.approved,
            approved_at=datetime.now(UTC),
            provider="e2e",
            model="placeholder",
        )
        db.add(character)
        await db.flush()
        character.sheet_image_key = f"children/{child.id}/characters/{character.id}.png"
        storage.put(character.sheet_image_key, _placeholder((34, 48, 106), "PNG"), "image/png")
    book = Book(
        child_id=child.id,
        character_id=character.id,
        theme_id=theme.id,
        theme_version=theme.version,
        created_by_user_id=user.id,
        language=Locale.ar,
        art_style=character.art_style,
        status=BookStatus.preview,
        title=theme.title_ar.replace("{name}", child.first_name),
        budget_usd=Decimal("0"),
        generation={"line": body.line, "offline": "sketch", "e2e": True},
    )
    db.add(book)
    await db.flush()
    for beat in PREVIEW_BEATS:
        key = f"children/{child.id}/books/{book.id}/preview/{beat:02d}.jpg"
        storage.put(key, _placeholder((22, 32, 74), "JPEG"), "image/jpeg")
        db.add(
            BookPage(book_id=book.id, index=beat, status=PageStatus.ok, preview_image_key=key, layout="full")
        )
    await db.commit()
    count = len(
        (await db.execute(select(Character.id).where(Character.child_id == child.id))).scalars().all()
    )
    return BookOut(
        child_id=child.id,
        character_id=character.id,
        book_id=book.id,
        theme=theme.slug,
        line=body.line,
        characters=count,
    )


class CodeOut(BaseModel):
    code: str


class CouponIn(BaseModel):
    kind: Literal["percent", "fixed"] = "percent"
    value: Decimal = Field(default=Decimal("10"), gt=0, le=90)


@router.post("/coupons", status_code=201)
async def coupon(body: CouponIn, user: CurrentUser, db: SessionDep) -> CodeOut:
    code = "E2E" + secrets.token_hex(4).upper()
    currency = Currency.ILS if body.kind == "fixed" else None
    db.add(
        Coupon(code=code, kind=CouponKind(body.kind), value=body.value, currency=currency, per_customer=None)
    )
    await db.commit()
    return CodeOut(code=code)


class CardIn(BaseModel):
    amount: Decimal = Field(default=Decimal("50"), gt=0, le=500)


@router.post("/gift-cards", status_code=201)
async def gift_card(body: CardIn, user: CurrentUser, db: SessionDep) -> CodeOut:
    code = gift_cards.new_code()
    db.add(GiftCard(code=code, currency=Currency.ILS, amount=body.amount, balance=body.amount, note="e2e"))
    await db.commit()
    return CodeOut(code=gift_cards.pretty(code))


class OrderOut(BaseModel):
    code: str
    gift: bool
    gift_message: str | None
    total: Decimal
    discount: Decimal
    pricing: dict[str, object]
    skus: list[str]
    addons: list[list[str]]


@router.get("/orders/{code}")
async def order(code: str, user: CurrentUser, db: SessionDep) -> OrderOut:
    """What the test needs to check after checkout, for the signed-in parent's own orders only."""
    row = (await db.execute(select(Order).where(Order.code == code))).scalar_one_or_none()
    if row is None or row.user_id != user.id:
        raise ApiError("not_found", 404)
    items = (await db.execute(select(OrderItem).where(OrderItem.order_id == row.id))).scalars().all()
    return OrderOut(
        code=row.code,
        gift=row.gift,
        gift_message=row.gift_message,
        total=row.total,
        discount=row.discount,
        pricing=row.pricing,
        skus=[str(i.sku) for i in items],
        addons=[[str(a.get("slug")) for a in i.addons] for i in items],
    )
