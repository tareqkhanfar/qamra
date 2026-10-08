"""Storefront API (Addendum 4 §5): the catalog, the cart with its live quote, checkout and order tracking."""

import secrets
import uuid
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select

from qamra_api import notify, ratelimit, runtime_settings
from qamra_api.auth.router import client_ip
from qamra_api.deps import OptionalUser, RedisDep, SessionDep, SettingsDep
from qamra_api.errors import ApiError
from qamra_api.store import gift_cards
from qamra_api.store.addons import available
from qamra_api.store.cart import (
    COOKIE,
    cart_items,
    clean_personalization,
    coupon_rule,
    ensure_cart,
    find_cart,
    needs_details,
    same_phone,
)
from qamra_api.store.catalog import (
    BULK_MIN_QTY,
    BULK_SETTINGS,
    Catalog,
    addon_lines,
    addon_problems,
    automatic_addons,
    bulk_blocked,
    bulk_tiers,
    item_input,
    load_catalog,
    unit_costs,
    zone_rule,
)
from qamra_api.store.payments import provider_for
from qamra_api.store.workbooks import FamilyIn, family_personalization, line_gaps, orderable
from qamra_api.validation import PHONE
from qamra_core import settings_store
from qamra_core.db.models import AuditLog, Book, Currency, Order, OrderItem, OrderStatus
from qamra_core.db.store import (
    Cart,
    CartItem,
    CartStatus,
    CatalogProduct,
    CouponRedemption,
    OrderEvent,
    Variant,
)
from qamra_core.pricing import ItemInput, Quote, addon_amount, quote

router = APIRouter(prefix="/api/store", tags=["store"])
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I on a phone call
CHECKOUTS_PER_IP_PER_HOUR = 20
TRACKS_PER_IP_PER_HOUR = 60


# ---- the catalog ------------------------------------------------------------------------------------------


class VariantOut(BaseModel):
    sku: str
    options: dict[str, str]
    price: Decimal | None


class ProductOut(BaseModel):
    slug: str
    line: str
    name_ar: str
    name_en: str
    description_ar: str
    description_en: str
    option_names: list[str]
    features: dict[str, Any]
    min_qty: int
    variants: list[VariantOut]
    from_price: Decimal | None


class StyleOut(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    lines: list[str]
    price_modifier: Decimal
    sample_images: list[str]


class AddOnOut(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    description_ar: str
    description_en: str
    image: str | None
    price: Decimal | None
    percent: Decimal | None
    lines: list[str]
    included_lines: list[str]
    requires: dict[str, list[str]]
    excludes: list[str]
    max_qty: int
    step: str


class ZoneOut(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    country: str
    currency: str
    cities: list[str]
    fee: Decimal
    free_over: Decimal | None
    cod_fee: Decimal
    eta_days: list[int]


class CatalogOut(BaseModel):
    currency: str
    products: list[ProductOut]
    styles: list[StyleOut]
    addons: list[AddOnOut]
    zones: list[ZoneOut]


def _catalog_out(c: Catalog, currency: Currency) -> CatalogOut:
    products = []
    for p in sorted(c.products.values(), key=lambda x: x.sort):
        variants = [
            VariantOut(sku=v.sku, options=v.options, price=c.price(v, currency))
            for v in c.variants.values()
            if v.product_id == p.id
        ]
        priced = [v.price for v in variants if v.price is not None]
        products.append(
            ProductOut(
                slug=p.slug,
                line=p.line.value,
                name_ar=p.name_ar,
                name_en=p.name_en,
                description_ar=p.description_ar,
                description_en=p.description_en,
                option_names=p.option_names,
                features=p.features,
                min_qty=p.min_qty,
                variants=variants,
                from_price=min(priced) if priced else None,
            )
        )
    return CatalogOut(
        currency=currency.value,
        products=products,
        styles=[
            StyleOut(
                slug=s.slug,
                name_ar=s.name_ar,
                name_en=s.name_en,
                lines=s.lines,
                price_modifier=c.style_modifier(s.slug, currency),
                sample_images=s.sample_images,
            )
            for s in sorted(c.styles.values(), key=lambda x: x.sort)
        ],
        addons=[
            AddOnOut(
                slug=a.slug,
                name_ar=a.name_ar,
                name_en=a.name_en,
                description_ar=a.description_ar,
                description_en=a.description_en,
                image=a.image,
                price=c.addon_prices.get((a.id, currency)),
                percent=a.percent,
                lines=a.lines,
                included_lines=a.included_lines,
                requires=a.requires,
                excludes=a.excludes,
                max_qty=a.max_qty,
                step=a.step,
            )
            for a in sorted(c.addons.values(), key=lambda x: x.sort)
        ],
        zones=[
            ZoneOut(
                slug=z.slug,
                name_ar=z.name_ar,
                name_en=z.name_en,
                country=z.country,
                currency=z.currency.value,
                cities=z.cities,
                fee=z.fee,
                free_over=z.free_over,
                cod_fee=z.cod_fee,
                eta_days=[z.eta_days_min, z.eta_days_max],
            )
            for z in sorted(c.zones.values(), key=lambda x: x.sort)
        ],
    )


@router.get("/catalog")
async def catalog(db: SessionDep, currency: Literal["ILS", "JOD"] = "ILS") -> CatalogOut:
    return _catalog_out(await load_catalog(db), Currency(currency))


# ---- the cart ---------------------------------------------------------------------------------------------


class AddOnIn(BaseModel):
    slug: str = Field(max_length=64)
    qty: int = Field(default=1, ge=1, le=10)


class ItemIn(BaseModel):
    sku: str = Field(max_length=64)
    qty: int = Field(default=1, ge=1, le=50)
    style: str | None = Field(default=None, max_length=40)
    theme: str | None = Field(default=None, max_length=64)
    addons: list[AddOnIn] = Field(default_factory=list, max_length=20)
    personalization: dict[str, Any] = Field(default_factory=dict)
    family: FamilyIn | None = None  # «مغامراتي مع عائلتي»: the family the product page asks for (optional)


class ItemPatch(BaseModel):
    qty: int | None = Field(default=None, ge=1, le=50)
    style: str | None = Field(default=None, max_length=40)
    addons: list[AddOnIn] | None = Field(default=None, max_length=20)
    personalization: dict[str, Any] | None = None


class CartAddOnOut(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    qty: int
    included: bool
    amount: Decimal = Decimal("0")  # Addendum 9: the add-on line's price on this item (0 when free)


class CartItemOut(BaseModel):
    id: uuid.UUID
    sku: str
    product: str
    line: str
    name_ar: str
    name_en: str
    options: dict[str, str]
    style: str | None
    theme: str | None
    qty: int
    addons: list[CartAddOnOut]
    child_name: str | None
    child_gender: Literal["m", "f"] | None  # the gift card's sample wording agrees with the child
    unit_price: Decimal
    base: Decimal
    addons_total: Decimal
    discount: Decimal
    total: Decimal
    # Addendum 9 (cart design): the book behind the line, and its price before the cart's discounts
    subtotal: Decimal = Decimal("0")
    book_id: uuid.UUID | None = None
    child_id: uuid.UUID | None = None
    book_title: str | None = None
    book_status: str | None = None
    needs_details: bool = False  # added in one tap: the child (and a story's book) come from the create flow
    # docs/plans/order-flows.md (chunk 8), for the cart's owner: what an activity line prints for the child
    missing: list[str] = Field(default_factory=list)  # still lacks "name_en" | "name" (workbooks.line_gaps)
    child_name_en: str | None = None  # the child's name in English letters (the English name page)
    family: dict[str, Any] | None = None  # the family book's {name, city, members: [{relation, role, name…}]}
    character_id: uuid.UUID | None = None  # the approved character the book is drawn with


class CartOut(BaseModel):
    currency: str
    count: int
    items: list[CartItemOut]
    unavailable: list[str]
    subtotal: Decimal
    sale_discount: Decimal
    bundle: str | None
    bundle_discount: Decimal
    coupon: str | None
    coupon_code: str | None
    coupon_problem: str | None
    coupon_discount: Decimal
    zone: str | None
    shipping: Decimal
    cod_fee: Decimal
    total: Decimal
    notes: list[str]
    # Addendum 9: the bundle's admin name, the gift order and its card message, the gift card
    bundle_name_ar: str | None = None
    bundle_name_en: str | None = None
    bundle_pct: Decimal | None = None
    gift: bool = False
    gift_message: str | None = None
    gift_card: str | None = None  # masked
    gift_card_amount: Decimal = Decimal("0")
    gift_card_problem: str | None = None


EMPTY_CART = CartOut(
    currency="ILS",
    count=0,
    items=[],
    unavailable=[],
    subtotal=Decimal("0"),
    sale_discount=Decimal("0"),
    bundle=None,
    bundle_discount=Decimal("0"),
    coupon=None,
    coupon_code=None,
    coupon_problem=None,
    coupon_discount=Decimal("0"),
    zone=None,
    shipping=Decimal("0"),
    cod_fee=Decimal("0"),
    total=Decimal("0"),
    notes=[],
)


async def _priced(
    db: SessionDep, c: Catalog, cart: Cart, *, phone: str | None = None
) -> tuple[list[tuple[CartItem, Variant]], list[str], Quote, Any]:
    """The cart's items with their variants, the unavailable ones, the quote and the coupon row."""
    by_id = {v.id: v for v in c.variants.values()}
    rows, missing = [], []
    for item in await cart_items(db, cart):
        variant = by_id.get(item.variant_id)
        if variant is None or c.price(variant, cart.currency) is None:
            missing.append(str(item.id))
            continue
        rows.append((item, variant))
    copies = Counter[uuid.UUID]()
    for item, variant in rows:
        copies[variant.id] += item.qty
    bulk = [
        v for v in {v.id: v for _, v in rows}.values() if copies[v.id] >= BULK_MIN_QTY and v.print_cost_tiers
    ]
    values = await settings_store.plain(db, *BULK_SETTINGS) if bulk else {}
    tiers = {v.id: bulk_tiers(c, v, cart.currency, values) for v in bulk}
    inputs = [_input(c, item, variant, cart.currency, tiers.get(variant.id, ())) for item, variant in rows]
    rule = coupon = problem = None
    if cart.coupon_code:
        rule, coupon, problem = await coupon_rule(
            db, cart.coupon_code, cart.currency, user_id=cart.user_id, phone=phone
        )
    card = card_problem = None  # Addendum 9: a gift card pays after every discount
    if cart.gift_card_code:
        card, _, card_problem = await gift_cards.card_rule(db, cart.gift_card_code, cart.currency)
    zone = next((z for z in c.zones.values() if z.id == cart.zone_id), None)
    q = quote(
        inputs,
        sales=c.sale_rules(),
        bundles=c.bundle_rules(),
        coupon=rule,
        zone=zone_rule(zone, cart.currency),
        gift_card=card,
    )
    if problem:
        q.coupon_problem = problem
    q.gift_card_problem = card_problem
    return rows, missing, q, coupon


def _gender(raw: object) -> Literal["m", "f"] | None:
    return "m" if raw == "m" else "f" if raw == "f" else None


def _uuid(raw: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(raw)) if raw else None
    except ValueError:
        return None


def _gaps(c: Catalog, item: CartItem, variant: Variant) -> list[str]:
    """What a line that has its child still lacks for its book (an activity book's English name, a name the
    tracing pages can write): the cart asks to complete it, and checkout waits like for a missing child."""
    if item.child_id is None:
        return []
    return line_gaps(c.product_of(variant).line.value, variant.options, item.personalization)


# What the server writes on a line when the child fills it (`POST /api/shop/workbooks/cart`): a cart edit that
# sends `personalization` keeps them (they are not the storefront's to change).
SERVER_HELD = ("character_id", "name_en", "family")


def _input(
    c: Catalog,
    item: CartItem,
    variant: Variant,
    currency: Currency,
    tiers: tuple[tuple[int, Decimal], ...] = (),
) -> ItemInput:
    addons = [*item.addons, *[{"slug": s, "qty": 1} for s in automatic_addons(c, variant)]]
    child = item.personalization.get("child_name")
    return item_input(
        c,
        key=str(item.id),
        variant=variant,
        currency=currency,
        qty=item.qty,
        style=item.style_slug,
        addons=addons,
        child_key=str(item.child_id or child or item.id),
        tiers=tiers,  # from 10 copies, the printer's tiers (Addendum 7 §8)
    )


async def check_copies(
    db: SessionDep, cart: Cart, variant: Variant, copies: int, skip: uuid.UUID | None = None
) -> None:
    """10+ copies of a tiered book (the family book) wait for the printer's real prices (2026-09-28)."""
    if not variant.print_cost_tiers:
        return
    others = sum(i.qty for i in await cart_items(db, cart) if i.variant_id == variant.id and i.id != skip)
    if bulk_blocked(variant, others + copies, cart.currency):
        raise ApiError("bulk_price_pending", 409, details={"min_qty": BULK_MIN_QTY})


async def cart_out(db: SessionDep, cart: Cart | None) -> CartOut:
    if cart is None:
        return EMPTY_CART
    c = await load_catalog(db)
    rows, missing, q, _ = await _priced(db, c, cart)
    prices = {p.key: p for p in q.items}
    books = await _books(db, [item.book_id for item, _ in rows if item.book_id])
    items = []
    for item, variant in rows:
        product = c.product_of(variant)
        p = prices[str(item.id)]
        addons = [*item.addons, *[{"slug": s, "qty": 1} for s in automatic_addons(c, variant)]]
        lines = addon_lines(c, variant, cart.currency, addons)
        amounts = {a.slug: addon_amount(a, p.unit_price) for a in lines}
        book = books.get(item.book_id) if item.book_id else None
        held = item.personalization
        missing = _gaps(c, item, variant)
        items.append(
            CartItemOut(
                id=item.id,
                sku=variant.sku,
                product=product.slug,
                line=product.line.value,
                name_ar=product.name_ar,
                name_en=product.name_en,
                options=variant.options,
                style=item.style_slug,
                theme=item.theme_slug,
                qty=item.qty,
                addons=[
                    CartAddOnOut(
                        slug=a["slug"],
                        name_ar=c.addons[a["slug"]].name_ar,
                        name_en=c.addons[a["slug"]].name_en,
                        qty=int(a.get("qty", 1)),
                        included=product.line.value in c.addons[a["slug"]].included_lines,
                        amount=amounts.get(a["slug"], Decimal("0")),
                    )
                    for a in addons
                    if a["slug"] in c.addons
                ],
                child_name=item.personalization.get("child_name"),
                child_gender=_gender(item.personalization.get("gender")),
                unit_price=p.unit_price,
                base=p.base,
                addons_total=p.addons,
                discount=p.sale_discount + p.bundle_discount + p.coupon_discount,
                total=p.total,
                subtotal=p.base + p.addons,
                book_id=item.book_id,
                child_id=item.child_id,
                book_title=book.title if book else None,
                book_status=book.status.value if book else None,
                needs_details=needs_details(product.line.value, item) or bool(missing),
                missing=missing,
                child_name_en=held.get("name_en") or None,
                family=held.get("family") or None,
                character_id=_uuid(held.get("character_id")),
            )
        )
    zone = next((z.slug for z in c.zones.values() if z.id == cart.zone_id), None)
    bundle = next((b for b in c.bundles if b.slug == q.bundle), None)
    return CartOut(
        currency=cart.currency.value,
        count=sum(i.qty for i in items),
        items=items,
        unavailable=missing,
        subtotal=q.subtotal,
        sale_discount=q.sale_discount,
        bundle=q.bundle,
        bundle_discount=q.bundle_discount,
        coupon=q.coupon,
        coupon_code=cart.coupon_code,
        coupon_problem=q.coupon_problem,
        coupon_discount=q.coupon_discount,
        zone=zone,
        shipping=q.shipping,
        cod_fee=q.cod_fee,
        total=q.total,
        notes=q.notes,
        bundle_name_ar=bundle.name_ar if bundle else None,
        bundle_name_en=bundle.name_en if bundle else None,
        bundle_pct=bundle.discount_pct if bundle else None,
        gift=cart.gift,
        gift_message=cart.gift_message if cart.gift else None,
        gift_card=gift_cards.masked(cart.gift_card_code) if cart.gift_card_code else None,
        gift_card_amount=q.gift_card_amount,
        gift_card_problem=q.gift_card_problem,
    )


async def _books(db: SessionDep, ids: list[uuid.UUID]) -> dict[uuid.UUID, Book]:
    """The books behind cart lines (Addendum 9: the cart shows each one's title and preview state)."""
    if not ids:
        return {}
    return {b.id: b for b in (await db.execute(select(Book).where(Book.id.in_(ids)))).scalars()}


def check_item(
    c: Catalog, variant: Variant | None, style: str | None, addons: list[dict[str, Any]]
) -> Variant:
    if variant is None:
        raise ApiError("unknown_product", 404)
    product = c.product_of(variant)
    if not orderable(product):  # closed by the admin (store/workbooks.py)
        raise ApiError("not_orderable", 409)
    if style is not None and (style not in c.styles or product.line.value not in c.styles[style].lines):
        raise ApiError("invalid_style", 422)
    problems = addon_problems(c, variant, addons)
    if problems:
        raise ApiError("invalid_addons", 422, details={"problems": problems})
    return variant


@router.get("/cart")
async def get_cart(request: Request, db: SessionDep, user: OptionalUser) -> CartOut:
    cart = await find_cart(db, request, user)
    out = await cart_out(db, cart)
    await db.commit()  # a signed-in parent may just have adopted their guest cart
    return out


@router.post("/cart/items", status_code=201)
async def add_item(
    body: ItemIn,
    request: Request,
    response: Response,
    db: SessionDep,
    user: OptionalUser,
    settings: SettingsDep,
) -> CartOut:
    c = await load_catalog(db)
    addons = [a.model_dump() for a in body.addons]
    variant = check_item(c, c.variants.get(body.sku), body.style, addons)
    try:
        personalization = clean_personalization(body.personalization)
    except (ValueError, TypeError) as e:
        raise ApiError("invalid_input", 422, details={"field": str(e)}) from e
    if body.family is not None and c.product_of(variant).line.value == "family":
        personalization["family"] = family_personalization(body.family)
    cart = await ensure_cart(db, request, response, user, settings)
    await check_copies(db, cart, variant, body.qty)
    db.add(
        CartItem(
            cart_id=cart.id,
            variant_id=variant.id,
            style_slug=body.style,
            theme_slug=body.theme,
            qty=body.qty,
            addons=addons,
            personalization=personalization,
        )
    )
    cart.updated_at = datetime.now(UTC)
    await db.commit()
    return await cart_out(db, cart)


async def _own_item(
    db: SessionDep, request: Request, user: OptionalUser, item_id: uuid.UUID
) -> tuple[Cart, CartItem]:
    cart = await find_cart(db, request, user)
    item = await db.get(CartItem, item_id)
    if cart is None or item is None or item.cart_id != cart.id:
        raise ApiError("not_found", 404)
    return cart, item


@router.patch("/cart/items/{item_id}")
async def update_item(
    item_id: uuid.UUID, body: ItemPatch, request: Request, db: SessionDep, user: OptionalUser
) -> CartOut:
    cart, item = await _own_item(db, request, user, item_id)
    c = await load_catalog(db)
    variant = next((v for v in c.variants.values() if v.id == item.variant_id), None)
    style = body.style if body.style is not None else item.style_slug
    addons = [a.model_dump() for a in body.addons] if body.addons is not None else available(c, item.addons)
    check_item(c, variant, style, addons)
    if body.qty is not None and variant is not None:
        await check_copies(db, cart, variant, body.qty, skip=item.id)
    if body.personalization is not None:
        try:
            cleaned = clean_personalization(body.personalization)
        except (ValueError, TypeError) as e:
            raise ApiError("invalid_input", 422, details={"field": str(e)}) from e
        kept = {k: item.personalization[k] for k in SERVER_HELD if k in item.personalization}
        item.personalization = {**cleaned, **kept}
    item.style_slug, item.addons = style, addons
    if body.qty is not None:
        item.qty = body.qty
    cart.updated_at = datetime.now(UTC)
    await db.commit()
    return await cart_out(db, cart)


@router.delete("/cart/items/{item_id}")
async def remove_item(item_id: uuid.UUID, request: Request, db: SessionDep, user: OptionalUser) -> CartOut:
    cart, item = await _own_item(db, request, user, item_id)
    await db.delete(item)
    await db.commit()
    return await cart_out(db, cart)


class CouponIn(BaseModel):
    code: str = Field(min_length=2, max_length=32)


@router.put("/cart/coupon")
async def set_coupon(
    body: CouponIn, request: Request, db: SessionDep, user: OptionalUser, redis: RedisDep
) -> CartOut:
    if await ratelimit.hit(redis, f"rl:coupon:{client_ip(request)}", 3600) > 30:
        raise ApiError("too_many_attempts", 429)  # coupon codes can't be guessed by brute force
    cart = await find_cart(db, request, user)
    if cart is None:
        raise ApiError("cart_empty", 409)
    cart.coupon_code = body.code.strip().upper()
    await db.commit()
    return await cart_out(db, cart)


@router.delete("/cart/coupon")
async def clear_coupon(request: Request, db: SessionDep, user: OptionalUser) -> CartOut:
    cart = await find_cart(db, request, user)
    if cart is not None:
        cart.coupon_code = None
        await db.commit()
    return await cart_out(db, cart)


class ZoneIn(BaseModel):
    zone: str = Field(max_length=64)


@router.put("/cart/zone")
async def set_zone(body: ZoneIn, request: Request, db: SessionDep, user: OptionalUser) -> CartOut:
    cart = await find_cart(db, request, user)
    if cart is None:
        raise ApiError("cart_empty", 409)
    c = await load_catalog(db)
    zone = c.zones.get(body.zone)
    if zone is None:
        raise ApiError("unknown_zone", 404)
    cart.zone_id, cart.currency = zone.id, zone.currency  # Jordan pays in JOD
    await db.commit()
    return await cart_out(db, cart)


# ---- checkout ---------------------------------------------------------------------------------------------


class CheckoutIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    phone: str = Field(max_length=32)
    zone: str = Field(max_length=64)
    city: str = Field(min_length=2, max_length=60)
    address: str = Field(min_length=5, max_length=300)
    notes: str | None = Field(default=None, max_length=500)
    payment: Literal["cod", "card"] = "cod"  # card: a disabled gateway stub for now (store.payments)
    accept_terms: bool

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        v = v.strip()
        if not PHONE.match(v):
            raise ValueError("invalid phone")
        return v

    @field_validator("name", "city", "address")
    @classmethod
    def _squash(cls, v: str) -> str:
        return " ".join(v.split())


class PlacedOut(BaseModel):
    code: str
    status: str
    currency: str
    total: Decimal
    eta_days: list[int]


async def _new_code(db: SessionDep) -> str:
    for _ in range(10):
        code = "QM-" + "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        taken = (
            await db.execute(select(func.count()).select_from(Order).where(Order.code == code))
        ).scalar_one()
        if not taken:
            return code
    raise ApiError("try_again", 503)


async def _express_left(db: SessionDep, c: Catalog) -> int | None:
    addon = c.addons.get("express")
    if addon is None or addon.daily_capacity is None:
        return None
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    used = (
        await db.execute(
            select(func.count())
            .select_from(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.created_at >= today, OrderItem.addons.contains([{"slug": "express"}]))
        )
    ).scalar_one()
    return max(0, addon.daily_capacity - int(used))


@router.post("/checkout", status_code=201)
async def checkout(
    body: CheckoutIn,
    request: Request,
    response: Response,
    db: SessionDep,
    user: OptionalUser,
    redis: RedisDep,
    settings: SettingsDep,
) -> PlacedOut:
    if not body.accept_terms:
        raise ApiError("terms_required", 422)
    payer = provider_for(body.payment)  # cash on delivery; the card stub is refused here
    if await ratelimit.hit(redis, f"rl:checkout:{client_ip(request)}", 3600) > CHECKOUTS_PER_IP_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    cart = await find_cart(db, request, user)
    if cart is None:
        raise ApiError("cart_empty", 409)
    c = await load_catalog(db)
    zone = c.zones.get(body.zone)
    if zone is None:
        raise ApiError("unknown_zone", 404)
    if zone.cities and body.city not in zone.cities:
        raise ApiError("unknown_city", 422)
    cart.zone_id, cart.currency = zone.id, zone.currency
    rows, missing, q, coupon = await _priced(db, c, cart, phone=body.phone)
    if not rows:
        raise ApiError("cart_empty", 409)
    if missing:
        raise ApiError("items_unavailable", 409, details={"items": missing})
    waiting = [
        (item, c.product_of(variant), _gaps(c, item, variant))
        for item, variant in rows
        if needs_details(c.product_of(variant).line.value, item) or _gaps(c, item, variant)
    ]
    if waiting:  # «أكملوا بيانات الطفل» in the cart: nothing can be made without the child
        items = [
            {"id": str(i.id), "name_ar": p.name_ar, "name_en": p.name_en, **({"missing": g} if g else {})}
            for i, p, g in waiting
        ]
        raise ApiError("details_missing", 409, details={"items": items})
    per_product: dict[uuid.UUID, int] = {}
    copies = Counter[uuid.UUID]()
    for item, variant in rows:
        item.addons = available(c, item.addons)  # an add-on switched off since then is dropped, not refused
        check_item(c, variant, item.style_slug, item.addons)
        per_product[variant.product_id] = per_product.get(variant.product_id, 0) + item.qty
        copies[variant.id] += item.qty
    if any(bulk_blocked(v, copies[v.id], cart.currency) for _, v in rows):  # e.g. added before the zone
        raise ApiError("bulk_price_pending", 409, details={"min_qty": BULK_MIN_QTY})
    short = [c.products[p].slug for p, n in per_product.items() if n < c.products[p].min_qty]
    if short:
        raise ApiError("below_minimum", 422, details={"products": short})
    wants_express = sum(1 for item, _ in rows if any(a["slug"] == "express" for a in item.addons))
    left = await _express_left(db, c) if wants_express else None
    if left is not None and wants_express > left:
        raise ApiError("express_full", 409)
    if cart.coupon_code and q.coupon is None:
        raise ApiError("coupon_invalid", 422, details={"problem": q.coupon_problem})
    if cart.gift_card_code and q.gift_card_problem:
        raise ApiError("gift_card_invalid", 422, details={"problem": q.gift_card_problem})
    redemption = None  # Addendum 9: the card's balance goes down first, atomically, or nothing is written
    if q.gift_card_amount > 0 and cart.gift_card_code:
        card = await gift_cards.find(db, cart.gift_card_code)
        if card is None:
            raise ApiError("gift_card_changed", 409)
        redemption = await gift_cards.redeem(db, card.id, q.gift_card_amount)

    values = (await runtime_settings.current(db, settings)).values
    usd_ils = Decimal(str(values.get("usd_ils") or "3.70"))
    physical = any(
        variant.options.get("format") in ("softcover", "hardcover", "spiral") for _, variant in rows
    )
    order = Order(
        code=await _new_code(db),
        user_id=user.id if user is not None else None,
        status=OrderStatus.new,
        payment_method=payer.method,
        currency=cart.currency,
        subtotal=q.subtotal,
        discount=q.discount,
        delivery_fee=q.shipping + q.cod_fee,
        total=q.total,
        shipping={
            "name": body.name,
            "phone": body.phone,
            "city": body.city,
            "address": body.address,
            "notes": body.notes,
        },
        phone=body.phone,
        zone_id=zone.id,
        coupon_id=coupon.id if coupon is not None and q.coupon else None,
        pricing=_quote_json(q),
        source="web",
        gift=cart.gift,
        gift_message=cart.gift_message if cart.gift else None,
    )
    db.add(order)
    await db.flush()
    if redemption is not None:
        redemption.order_id = order.id
    prices = {p.key: p for p in q.items}
    cost_total = Decimal("0")
    for item, variant in rows:
        product = c.product_of(variant)
        p = prices[str(item.id)]
        addons = [*item.addons, *[{"slug": s, "qty": 1} for s in automatic_addons(c, variant)]]
        costs = unit_costs(c, variant, addons, usd_ils)
        cost_total += Decimal(costs["total"]) * item.qty
        db.add(
            OrderItem(
                order_id=order.id,
                book_id=item.book_id,
                variant_id=variant.id,
                sku=variant.sku,
                line=product.line.value,
                title={"name_ar": product.name_ar, "name_en": product.name_en, "options": variant.options},
                style_slug=item.style_slug,
                theme_slug=item.theme_slug,
                child_id=item.child_id,
                personalization=item.personalization,
                addons=addon_snapshot(c, product.line.value, addons, p.unit_price, order.currency),
                quantity=item.qty,
                unit_price=p.unit_price,
                discount=p.sale_discount + p.bundle_discount + p.coupon_discount,
                costs=costs,
            )
        )
    if physical:
        cost_total += zone.cost_ils + Decimal(str(values.get("cod_cost_ils") or "0"))
    order.cost_ils = cost_total.quantize(Decimal("0.01"))
    if coupon is not None and q.coupon:
        coupon.uses += 1
        db.add(
            CouponRedemption(
                coupon_id=coupon.id,
                order_id=order.id,
                user_id=order.user_id,
                phone=body.phone,
                amount=q.coupon_discount,
            )
        )
    db.add(
        OrderEvent(order_id=order.id, kind="status", to_status=OrderStatus.new, note="placed on the website")
    )
    db.add(
        AuditLog(
            actor_user_id=order.user_id, action="order.placed", entity_type="order", entity_id=str(order.id)
        )
    )
    cart.status = CartStatus.ordered
    order.payment_status = payer.start(order).status
    await db.commit()
    notify.order_placed(request.app.state.rq_redis, order.id)  # "we've received your order" email
    response.delete_cookie(COOKIE, path="/", domain=settings.cookie_domain)
    return PlacedOut(
        code=order.code,
        status=order.status.value,
        currency=order.currency.value,
        total=order.total,
        eta_days=[zone.eta_days_min, zone.eta_days_max],
    )


def addon_snapshot(
    c: Catalog, line: str, addons: list[dict[str, Any]], unit_price: Decimal, currency: Currency
) -> list[dict[str, Any]]:
    """Each add-on as sold: name and unit price frozen on the order line (invoices list them)."""
    out = []
    for a in addons:
        addon = c.addons.get(str(a["slug"]))
        if addon is None:
            continue
        included = line in addon.included_lines
        if included:
            price = Decimal("0")
        elif addon.percent is not None and addon.pricing.value == "percent_of_item":
            price = (unit_price * addon.percent / 100).quantize(Decimal("0.01"))
        else:
            price = c.addon_prices.get((addon.id, currency), Decimal("0"))
        out.append(
            {
                "slug": addon.slug,
                "qty": int(a.get("qty", 1)),
                "included": included,
                "unit_price": str(price.quantize(Decimal("0.01"))),
                "name_ar": addon.name_ar,
                "name_en": addon.name_en,
            }
        )
    return out


def _quote_json(q: Quote) -> dict[str, Any]:
    return {
        "subtotal": str(q.subtotal),
        "sale_discount": str(q.sale_discount),
        "bundle": q.bundle,
        "bundle_discount": str(q.bundle_discount),
        "coupon": q.coupon,
        "coupon_discount": str(q.coupon_discount),
        "shipping": str(q.shipping),
        "cod_fee": str(q.cod_fee),
        "total": str(q.total),
        "gift_card": q.gift_card,  # masked; the redemption row links the card itself
        "gift_card_amount": str(q.gift_card_amount),
        "items": {
            p.key: {
                "unit_price": str(p.unit_price),
                "addons": str(p.addons),
                "sale": str(p.sale_discount),
                "bundle": str(p.bundle_discount),
                "coupon": str(p.coupon_discount),
                "total": str(p.total),
            }
            for p in q.items
        },
    }


# ---- tracking ---------------------------------------------------------------------------------------------


class TrackAddOn(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    qty: int


class TrackItem(BaseModel):
    name_ar: str
    name_en: str
    qty: int
    child_name: str | None
    # docs/plans/order-flows.md §c.9: the same detail line as the cart (frozen on the order line)
    line: str | None = None
    product: str | None = None
    sku: str | None = None
    options: dict[str, str] = Field(default_factory=dict)
    theme: str | None = None
    style: str | None = None
    book_title: str | None = None
    child_name_en: str | None = None
    family: dict[str, Any] | None = None
    addons: list[TrackAddOn] = Field(default_factory=list)


class TrackEvent(BaseModel):
    status: str
    at: datetime


class TrackOut(BaseModel):
    code: str
    status: str
    currency: str
    total: Decimal
    placed_at: datetime
    items: list[TrackItem]
    events: list[TrackEvent]
    city: str | None


@router.get("/orders/{code}")
async def track(code: str, phone: str, request: Request, db: SessionDep, redis: RedisDep) -> TrackOut:
    """An order's progress, for whoever has both the order code and the phone it was placed with."""
    if await ratelimit.hit(redis, f"rl:track:{client_ip(request)}", 3600) > TRACKS_PER_IP_PER_HOUR:
        raise ApiError("too_many_attempts", 429)
    order = (await db.execute(select(Order).where(Order.code == code.strip().upper()))).scalar_one_or_none()
    if order is None or not order.phone or not same_phone(order.phone, phone):
        raise ApiError("not_found", 404)  # same answer for a wrong code and a wrong phone
    items = list((await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars())
    books = await _books(db, [i.book_id for i in items if i.book_id])
    variants = [i.variant_id for i in items if i.variant_id]
    products = (
        dict(
            (
                await db.execute(
                    select(Variant.id, CatalogProduct.slug)
                    .join(CatalogProduct, CatalogProduct.id == Variant.product_id)
                    .where(Variant.id.in_(variants))
                )
            ).all()
        )
        if variants
        else {}
    )
    events = (
        await db.execute(
            select(OrderEvent)
            .where(OrderEvent.order_id == order.id, OrderEvent.kind == "status")
            .order_by(OrderEvent.created_at)
        )
    ).scalars()
    return TrackOut(
        code=order.code,
        status=order.status.value,
        currency=order.currency.value,
        total=order.total,
        placed_at=order.created_at,
        items=[
            TrackItem(
                name_ar=str(i.title.get("name_ar", "")),
                name_en=str(i.title.get("name_en", "")),
                qty=i.quantity,
                child_name=i.personalization.get("child_name"),
                line=i.line,
                product=products.get(i.variant_id) if i.variant_id else None,
                sku=i.sku,
                options={str(k): str(v) for k, v in (i.title.get("options") or {}).items()},
                theme=i.theme_slug,
                style=i.style_slug,
                book_title=books[i.book_id].title if i.book_id and i.book_id in books else None,
                child_name_en=i.personalization.get("name_en") or None,
                family=i.personalization.get("family") or None,
                addons=[
                    TrackAddOn(
                        slug=str(a.get("slug")),
                        name_ar=str(a.get("name_ar", "")),
                        name_en=str(a.get("name_en", "")),
                        qty=int(a.get("qty", 1)),
                    )
                    for a in (i.addons or [])
                    if a.get("slug")
                ],
            )
            for i in items
        ],
        events=[
            TrackEvent(status=e.to_status.value, at=e.created_at) for e in events if e.to_status is not None
        ],
        city=order.shipping.get("city"),
    )
