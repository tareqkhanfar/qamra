"""The order path of Addendum 9 (§1.4–§1.6, designs AddOns and Cart): the add-ons step after the preview, the
gift order with its card message, one field for a discount code or a gift card, and the cross-sell that reuses
the child's approved character («شخصية ليان جاهزة»). Every amount comes from the pricing engine (`cart_out`).
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from qamra_api import ratelimit
from qamra_api.auth.router import client_ip
from qamra_api.deps import OptionalUser, RedisDep, SessionDep
from qamra_api.errors import ApiError
from qamra_api.store import gift_cards
from qamra_api.store.addons import merge, offers
from qamra_api.store.cart import find_cart
from qamra_api.store.catalog import PRINTED_FORMATS, Catalog, load_catalog
from qamra_api.store.router import AddOnIn, CartItemOut, CartOut, _own_item, cart_out, check_item
from qamra_core.db.models import Character, Child, Currency
from qamra_core.db.store import Cart, CartItem, Coupon

router = APIRouter(prefix="/api/store", tags=["store"])
CODE_TRIES_PER_IP_PER_HOUR = 30  # shared with the coupon field: codes can't be guessed by brute force
GIFT_MESSAGE_MAX = 200
GIFT_MESSAGE_LINES = 6
STORY_PRODUCTS = {"classic": "classic-book", "magic": "magic-book"}


# ---- the add-ons step (design AddOns) ---------------------------------------------------------------------


class AddOnOfferOut(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    description_ar: str
    description_en: str
    badge_ar: str | None
    badge_en: str | None
    featured: bool  # in the open list; the rest are under «إضافات أخرى»
    price: Decimal  # one of it on this book
    percent: Decimal | None
    included: bool
    on: bool
    qty: int
    max_qty: int
    needs: list[str]
    excludes: list[str]
    locked: str | None  # needs | excludes
    blockers: list[str]


class AddOnsOut(BaseModel):
    currency: str
    item: CartItemOut
    addons: list[AddOnOfferOut]


class AddOnsIn(BaseModel):
    addons: list[AddOnIn] = Field(default_factory=list, max_length=20)


async def _step(db: SessionDep, cart: Cart, item: CartItem) -> AddOnsOut:
    c = await load_catalog(db)
    variant = next((v for v in c.variants.values() if v.id == item.variant_id), None)
    shown = next((i for i in (await cart_out(db, cart)).items if i.id == item.id), None)
    if variant is None or shown is None:
        raise ApiError("items_unavailable", 409, details={"items": [str(item.id)]})
    return AddOnsOut(
        currency=cart.currency.value,
        item=shown,
        addons=[
            AddOnOfferOut(
                slug=o.addon.slug,
                name_ar=o.addon.name_ar,
                name_en=o.addon.name_en,
                description_ar=o.addon.description_ar,
                description_en=o.addon.description_en,
                badge_ar=o.addon.badge_ar,
                badge_en=o.addon.badge_en,
                featured=o.addon.featured,
                price=o.price,
                percent=o.addon.percent,
                included=o.included,
                on=o.on,
                qty=o.qty,
                max_qty=o.addon.max_qty,
                needs=list(o.addon.needs),
                excludes=list(o.addon.excludes),
                locked=o.locked,
                blockers=o.blockers,
            )
            for o in offers(c, variant, cart.currency, shown.unit_price, item.addons)
        ],
    )


@router.get("/cart/items/{item_id}/addons")
async def item_addons(item_id: uuid.UUID, request: Request, db: SessionDep, user: OptionalUser) -> AddOnsOut:
    cart, item = await _own_item(db, request, user, item_id)
    return await _step(db, cart, item)


@router.put("/cart/items/{item_id}/addons")
async def set_item_addons(
    item_id: uuid.UUID, body: AddOnsIn, request: Request, db: SessionDep, user: OptionalUser
) -> AddOnsOut:
    """Sets the add-ons this step offers; the item's other add-ons (dedication, companion…) stay."""
    cart, item = await _own_item(db, request, user, item_id)
    c = await load_catalog(db)
    variant = next((v for v in c.variants.values() if v.id == item.variant_id), None)
    if variant is None:
        raise ApiError("items_unavailable", 409, details={"items": [str(item.id)]})
    addons = merge(c, variant, item.addons, [a.model_dump() for a in body.addons])
    check_item(c, variant, item.style_slug, addons)  # lines, formats, exclusions and dependencies
    item.addons = addons
    await db.commit()
    return await _step(db, cart, item)


# ---- a gift, and its card message --------------------------------------------------------------------------


class GiftIn(BaseModel):
    gift: bool
    message: str | None = Field(default=None, max_length=400)  # checked again after tidying (≤ 200)


def tidy_message(text: str | None) -> str | None:
    """Trimmed lines, at most a few of them; 200 characters or fewer (the card's space)."""
    lines = [" ".join(line.split()) for line in (text or "").splitlines()]
    kept: list[str] = []
    for line in lines:
        if line or (kept and kept[-1]):
            kept.append(line)
    out = "\n".join(kept[:GIFT_MESSAGE_LINES]).strip()
    if len(out) > GIFT_MESSAGE_MAX:
        raise ApiError("invalid_input", 422, details={"fields": ["message"], "max": GIFT_MESSAGE_MAX})
    return out or None


@router.put("/cart/gift")
async def set_gift(body: GiftIn, request: Request, db: SessionDep, user: OptionalUser) -> CartOut:
    cart = await find_cart(db, request, user)
    if cart is None:
        raise ApiError("cart_empty", 409)
    message = tidy_message(body.message)
    cart.gift = body.gift
    if body.message is not None:
        cart.gift_message = message  # kept while the toggle is off, in case it goes back on
    await db.commit()
    return await cart_out(db, cart)


# ---- one field: a discount code or a gift card -------------------------------------------------------------


class CodeIn(BaseModel):
    code: str = Field(min_length=2, max_length=40)


@router.put("/cart/code")
async def apply_code(
    body: CodeIn, request: Request, db: SessionDep, user: OptionalUser, redis: RedisDep
) -> CartOut:
    if await ratelimit.hit(redis, f"rl:coupon:{client_ip(request)}", 3600) > CODE_TRIES_PER_IP_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    cart = await find_cart(db, request, user)
    if cart is None:
        raise ApiError("cart_empty", 409)
    if gift_cards.looks_like_card(body.code):
        card = await gift_cards.find(db, body.code)
        if card is None:
            raise ApiError("code_unknown", 422)
        cart.gift_card_code = card.code  # problems (expired, currency…) show in the cart
    else:
        code = body.code.strip().upper()
        if (await db.execute(select(Coupon.id).where(Coupon.code == code))).scalar_one_or_none() is None:
            raise ApiError("code_unknown", 422)
        cart.coupon_code = code
    await db.commit()
    return await cart_out(db, cart)


@router.delete("/cart/gift-card")
async def clear_gift_card(request: Request, db: SessionDep, user: OptionalUser) -> CartOut:
    cart = await find_cart(db, request, user)
    if cart is not None:
        cart.gift_card_code = None
        await db.commit()
    return await cart_out(db, cart)


# ---- «شخصية ليان جاهزة»: another book with the character the child already has ---------------------------


class CrossSellOut(BaseModel):
    child_id: uuid.UUID
    child_name: str
    gender: str
    character_id: uuid.UUID
    style: str
    line: str
    product: str
    name_ar: str
    name_en: str
    from_price: Decimal | None
    currency: str


def _from_price(c: Catalog, product: str, currency: Currency) -> Decimal | None:
    """The cheapest printed copy of a product (the design's «+ 89 ₪»)."""
    prices = [
        price
        for v in c.variants.values()
        if c.product_of(v).slug == product
        and v.options.get("format") in PRINTED_FORMATS
        and (price := c.price(v, currency)) is not None
    ]
    return min(prices) if prices else None


@router.get("/cart/cross-sell")
async def cross_sell(request: Request, db: SessionDep, user: OptionalUser) -> list[CrossSellOut]:
    """For each of the parent's children in the cart with an approved character: another story drawn with
    that same character (Addendum 9 §6: reused as is, never redrawn, no new AI cost for the character).
    Nothing for guests or for children without an approved character."""
    cart = await find_cart(db, request, user)
    if cart is None or user is None:
        return []
    c = await load_catalog(db)
    lines: dict[uuid.UUID, str] = {}
    for item in (await db.execute(select(CartItem).where(CartItem.cart_id == cart.id))).scalars():
        variant = next((v for v in c.variants.values() if v.id == item.variant_id), None)
        if item.child_id and variant is not None:
            lines.setdefault(item.child_id, c.product_of(variant).line.value)
    out: list[CrossSellOut] = []
    for child_id, line in lines.items():
        child = await db.get(Child, child_id)
        if child is None or child.guardian_user_id != user.id:
            continue
        character = (
            (
                await db.execute(
                    select(Character)
                    .where(
                        Character.child_id == child.id,
                        Character.approved_at.is_not(None),
                        Character.sheet_image_key.is_not(None),
                    )
                    .order_by(Character.approved_at.desc())
                )
            )
            .scalars()
            .first()
        )
        if character is None:
            continue
        style = c.styles.get(character.art_style)
        order = dict.fromkeys((line, *STORY_PRODUCTS))  # the cart line's own line first, else the other one
        fitting = [x for x in order if x in STORY_PRODUCTS and style is not None and x in style.lines]
        if not fitting:
            continue
        slug = STORY_PRODUCTS[fitting[0]]
        product = next((p for p in c.products.values() if p.slug == slug), None)
        if product is None:
            continue
        out.append(
            CrossSellOut(
                child_id=child.id,
                child_name=child.first_name,
                gender=child.gender.value,
                character_id=character.id,
                style=character.art_style,
                line=fitting[0],
                product=product.slug,
                name_ar=product.name_ar,
                name_en=product.name_en,
                from_price=_from_price(c, product.slug, cart.currency),
                currency=cart.currency.value,
            )
        )
    return out
