"""Catalog admin (Addendum 4 §6, step 5): prices, costs and margins for everything the store sells.

Every product, variant, add-on and delivery zone shows what it costs us and its margin in ₪ and %, in red
when it is under the margin floor. Edits are audited (who, what, before and after). The price simulator
runs the store's own pricing engine on a basket and shows its cost and margin.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select

from qamra_api import runtime_settings
from qamra_api.deps import AdminUser, SessionDep, SettingsDep, require_permission
from qamra_api.errors import ApiError
from qamra_api.store.catalog import Catalog, load_catalog, tiers_estimated
from qamra_core.db.models import AuditLog, Currency, Organization
from qamra_core.db.store import (
    AddOn,
    AddOnPrice,
    AddOnPricing,
    Bundle,
    Coupon,
    PriceList,
    PriceListItem,
    Sale,
    ShippingZone,
    Variant,
    VariantPrice,
)

router = APIRouter(prefix="/api/admin/catalog", tags=["admin"])
CENT = Decimal("0.01")
Money = Field(default=None, ge=0, le=100_000, max_digits=9, decimal_places=2)


def margin(price_ils: Decimal | None, cost_ils: Decimal) -> tuple[Decimal | None, Decimal | None]:
    """(margin in ₪, margin in %) of one unit at its list price; None without a price."""
    if price_ils is None:
        return None, None
    amount = (price_ils - cost_ils).quantize(CENT)
    pct = (amount / price_ils * 100).quantize(Decimal("0.1")) if price_ils else Decimal("0")
    return amount, pct


class Rates(BaseModel):
    usd_ils: Decimal
    jod_ils: Decimal
    margin_floor_pct: Decimal


class VariantRow(BaseModel):
    sku: str
    product: str
    product_ar: str
    product_en: str
    line: str
    audience: str
    options: dict[str, str]
    active: bool
    product_active: bool
    price_ils: Decimal | None
    price_jod: Decimal | None
    cost_print_ils: Decimal
    cost_packaging_ils: Decimal
    cost_handling_ils: Decimal
    cost_ai_usd: Decimal
    unit_cost_ils: Decimal  # printing, packaging, handling and AI for one copy (delivery is per order)
    margin_ils: Decimal | None
    margin_pct: Decimal | None  # at the ₪ price
    margin_pct_jod: Decimal | None  # at the JD price, converted to ₪
    below_floor: bool
    printer_tiers: bool
    printer_estimated: bool


class AddOnRow(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    pricing: str
    percent: Decimal | None
    price_ils: Decimal | None
    price_jod: Decimal | None
    cost_ils: Decimal
    cost_ai_usd: Decimal
    unit_cost_ils: Decimal
    margin_ils: Decimal | None
    margin_pct: Decimal | None
    below_floor: bool
    lines: list[str]
    included_lines: list[str]
    active: bool


class ZoneRow(BaseModel):
    slug: str
    name_ar: str
    name_en: str
    currency: str
    fee: Decimal
    free_over: Decimal | None
    cod_fee: Decimal
    cost_ils: Decimal
    fee_margin_ils: Decimal  # what the delivery fee leaves after the parcel's cost (can be negative)
    active: bool


class CouponRow(BaseModel):
    code: str
    kind: str
    value: Decimal
    currency: str | None
    min_subtotal: Decimal | None
    max_uses: int | None
    uses: int
    per_customer: int | None
    first_order_only: bool
    lines: list[str]
    starts_at: datetime | None
    ends_at: datetime | None
    active: bool


class OfferRow(BaseModel):
    """A bundle or a seasonal sale."""

    id: str
    kind: str  # bundle kind, or "sale"
    name_ar: str
    name_en: str
    discount_pct: Decimal
    lines: list[str]
    starts_at: datetime | None
    ends_at: datetime | None
    active: bool


class CatalogAdminOut(BaseModel):
    rates: Rates
    variants: list[VariantRow]
    addons: list[AddOnRow]
    zones: list[ZoneRow]
    coupons: list[CouponRow]
    bundles: list[OfferRow]
    sales: list[OfferRow]


async def _rates(db: SessionDep, settings: SettingsDep) -> Rates:
    v = (await runtime_settings.current(db, settings)).values
    return Rates(
        usd_ils=Decimal(str(v["usd_ils"])),
        jod_ils=Decimal(str(v["jod_ils"])),
        margin_floor_pct=Decimal(str(v["margin_floor_pct"])),
    )


def _variant_row(c: Catalog, v: Variant, r: Rates) -> VariantRow:
    product = c.product_of(v)
    cost = (
        v.cost_print_ils + v.cost_packaging_ils + v.cost_handling_ils + (v.cost_ai_usd * r.usd_ils)
    ).quantize(CENT)
    ils, jod = c.price(v, Currency.ILS), c.price(v, Currency.JOD)
    amount, pct = margin(ils, cost)
    _, pct_jod = margin((jod * r.jod_ils).quantize(CENT) if jod is not None else None, cost)
    return VariantRow(
        sku=v.sku,
        product=product.slug,
        product_ar=product.name_ar,
        product_en=product.name_en,
        line=product.line.value,
        audience=product.audience.value,
        options=v.options,
        active=v.active,
        product_active=product.active,
        price_ils=ils,
        price_jod=jod,
        cost_print_ils=v.cost_print_ils,
        cost_packaging_ils=v.cost_packaging_ils,
        cost_handling_ils=v.cost_handling_ils,
        cost_ai_usd=v.cost_ai_usd,
        unit_cost_ils=cost,
        margin_ils=amount,
        margin_pct=pct,
        margin_pct_jod=pct_jod,
        below_floor=any(p is not None and p < r.margin_floor_pct for p in (pct, pct_jod)),
        printer_tiers=bool(v.print_cost_tiers),
        printer_estimated=tiers_estimated(v),
    )


def _addon_row(c: Catalog, a: AddOn, r: Rates) -> AddOnRow:
    ils = c.addon_prices.get((a.id, Currency.ILS))
    jod = c.addon_prices.get((a.id, Currency.JOD))
    cost = (a.cost_ils + a.cost_ai_usd * r.usd_ils).quantize(CENT)
    fixed = a.pricing == AddOnPricing.fixed
    amount, pct = margin(ils, cost) if fixed and ils else (None, None)
    return AddOnRow(
        slug=a.slug,
        name_ar=a.name_ar,
        name_en=a.name_en,
        pricing=a.pricing.value,
        percent=a.percent,
        price_ils=ils,
        price_jod=jod,
        cost_ils=a.cost_ils,
        cost_ai_usd=a.cost_ai_usd,
        unit_cost_ils=cost,
        margin_ils=amount,
        margin_pct=pct,
        below_floor=pct is not None and pct < r.margin_floor_pct,
        lines=list(a.lines),
        included_lines=list(a.included_lines),
        active=a.active,
    )


def _zone_row(z: ShippingZone, r: Rates) -> ZoneRow:
    fee_ils = z.fee * (r.jod_ils if z.currency == Currency.JOD else 1)
    return ZoneRow(
        slug=z.slug,
        name_ar=z.name_ar,
        name_en=z.name_en,
        currency=z.currency.value,
        fee=z.fee,
        free_over=z.free_over,
        cod_fee=z.cod_fee,
        cost_ils=z.cost_ils,
        fee_margin_ils=(fee_ils - z.cost_ils).quantize(CENT),
        active=z.active,
    )


def _coupon_row(c: Coupon) -> CouponRow:
    return CouponRow(
        code=c.code,
        kind=c.kind.value,
        value=c.value,
        currency=c.currency.value if c.currency else None,
        min_subtotal=c.min_subtotal,
        max_uses=c.max_uses,
        uses=c.uses,
        per_customer=c.per_customer,
        first_order_only=c.first_order_only,
        lines=list(c.lines),
        starts_at=c.starts_at,
        ends_at=c.ends_at,
        active=c.active,
    )


def _bundle_row(b: Bundle) -> OfferRow:
    return OfferRow(
        id=b.slug,
        kind=b.kind.value,
        name_ar=b.name_ar,
        name_en=b.name_en,
        discount_pct=b.discount_pct,
        lines=list(b.lines),
        starts_at=b.starts_at,
        ends_at=b.ends_at,
        active=b.active,
    )


def _sale_row(s: Sale) -> OfferRow:
    return OfferRow(
        id=str(s.id),
        kind="sale",
        name_ar=s.name_ar,
        name_en=s.name_en,
        discount_pct=s.discount_pct,
        lines=list(s.lines),
        starts_at=s.starts_at,
        ends_at=s.ends_at,
        active=s.active,
    )


@router.get("", dependencies=[Depends(require_permission("catalog"))])
async def catalog_admin(db: SessionDep, settings: SettingsDep) -> CatalogAdminOut:
    r = await _rates(db, settings)
    c = await load_catalog(db, include_b2b=True, include_inactive=True)
    addons = (await db.execute(select(AddOn).order_by(AddOn.sort, AddOn.slug))).scalars().all()
    zones = (await db.execute(select(ShippingZone).order_by(ShippingZone.sort))).scalars().all()
    coupons = (await db.execute(select(Coupon).order_by(Coupon.created_at.desc()))).scalars().all()
    bundles = (await db.execute(select(Bundle).order_by(Bundle.slug))).scalars().all()
    sales = (await db.execute(select(Sale).order_by(Sale.starts_at.desc()))).scalars().all()
    return CatalogAdminOut(
        rates=r,
        variants=[_variant_row(c, v, r) for v in c.variants.values()],
        addons=[_addon_row(c, a, r) for a in addons],
        zones=[_zone_row(z, r) for z in zones],
        coupons=[_coupon_row(x) for x in coupons],
        bundles=[_bundle_row(b) for b in bundles],
        sales=[_sale_row(s) for s in sales],
    )


def _audit(db: SessionDep, admin: AdminUser, what: str, entity: str, before: Any, after: Any) -> None:
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action=f"catalog.{what}.updated",
            entity_type=what,
            entity_id=entity,
            data={"before": before, "after": after},
        )
    )


def _plain(row: Any, fields: list[str]) -> dict[str, Any]:
    """The audited fields of a row, JSON-ready."""
    out = {}
    for f in fields:
        value = getattr(row, f)
        out[f] = str(value) if isinstance(value, Decimal | datetime | uuid.UUID) else value
    return out


# ---- edits -------------------------------------------------------------------------------------------------


class VariantPatch(BaseModel):
    price_ils: Decimal | None = Money
    price_jod: Decimal | None = Money
    cost_print_ils: Decimal | None = Money
    cost_packaging_ils: Decimal | None = Money
    cost_handling_ils: Decimal | None = Money
    cost_ai_usd: Decimal | None = Field(default=None, ge=0, le=1000, max_digits=9, decimal_places=4)
    active: bool | None = None


VARIANT_FIELDS = ["cost_print_ils", "cost_packaging_ils", "cost_handling_ils", "cost_ai_usd", "active"]


async def _set_price(db: SessionDep, variant: Variant, currency: Currency, amount: Decimal) -> None:
    row = await db.get(VariantPrice, (variant.id, currency))
    if row is None:
        db.add(VariantPrice(variant_id=variant.id, currency=currency, amount=amount))
    else:
        row.amount = amount


@router.patch("/variants/{sku}", dependencies=[Depends(require_permission("prices"))])
async def edit_variant(
    sku: str, body: VariantPatch, admin: AdminUser, db: SessionDep, settings: SettingsDep
) -> VariantRow:
    variant = (await db.execute(select(Variant).where(Variant.sku == sku))).scalar_one_or_none()
    if variant is None:
        raise ApiError("not_found", 404)
    old_prices = {
        p.currency.value: str(p.amount)
        for p in (
            await db.execute(select(VariantPrice).where(VariantPrice.variant_id == variant.id))
        ).scalars()
    }
    before = _plain(variant, VARIANT_FIELDS) | {"prices": old_prices}
    changes = body.model_dump(exclude_none=True)
    for field in VARIANT_FIELDS:
        if field in changes:
            setattr(variant, field, changes[field])
    if body.price_ils is not None:
        await _set_price(db, variant, Currency.ILS, body.price_ils)
    if body.price_jod is not None:
        await _set_price(db, variant, Currency.JOD, body.price_jod)
    await db.flush()
    _audit(db, admin, "variant", sku, before, {k: str(v) for k, v in changes.items()})
    await db.commit()
    c = await load_catalog(db, include_b2b=True, include_inactive=True)
    return _variant_row(c, c.variants[sku], await _rates(db, settings))


class ProductPatch(BaseModel):
    active: bool


@router.patch("/products/{slug}", dependencies=[Depends(require_permission("catalog"))])
async def edit_product(slug: str, body: ProductPatch, admin: AdminUser, db: SessionDep) -> dict[str, Any]:
    from qamra_core.db.store import CatalogProduct

    product = (
        await db.execute(select(CatalogProduct).where(CatalogProduct.slug == slug))
    ).scalar_one_or_none()
    if product is None:
        raise ApiError("not_found", 404)
    _audit(db, admin, "product", slug, {"active": product.active}, {"active": body.active})
    product.active = body.active
    await db.commit()
    return {"slug": slug, "active": product.active}


class AddOnPatch(BaseModel):
    price_ils: Decimal | None = Money
    price_jod: Decimal | None = Money
    cost_ils: Decimal | None = Money
    cost_ai_usd: Decimal | None = Field(default=None, ge=0, le=1000, max_digits=9, decimal_places=4)
    active: bool | None = None


@router.patch("/addons/{slug}", dependencies=[Depends(require_permission("prices"))])
async def edit_addon(
    slug: str, body: AddOnPatch, admin: AdminUser, db: SessionDep, settings: SettingsDep
) -> AddOnRow:
    addon = (await db.execute(select(AddOn).where(AddOn.slug == slug))).scalar_one_or_none()
    if addon is None:
        raise ApiError("not_found", 404)
    before = _plain(addon, ["cost_ils", "cost_ai_usd", "active"])
    changes = body.model_dump(exclude_none=True)
    for field in ("cost_ils", "cost_ai_usd", "active"):
        if field in changes:
            setattr(addon, field, changes[field])
    for currency, amount in ((Currency.ILS, body.price_ils), (Currency.JOD, body.price_jod)):
        if amount is None:
            continue
        if addon.pricing != AddOnPricing.fixed:
            raise ApiError("invalid_input", 422, {"fields": ["price_ils", "price_jod"]})  # priced by percent
        row = await db.get(AddOnPrice, (addon.id, currency))
        if row is None:
            db.add(AddOnPrice(addon_id=addon.id, currency=currency, amount=amount))
        else:
            row.amount = amount
    await db.flush()
    _audit(db, admin, "addon", slug, before, {k: str(v) for k, v in changes.items()})
    await db.commit()
    c = await load_catalog(db, include_b2b=True, include_inactive=True)
    await db.refresh(addon)
    return _addon_row(c, addon, await _rates(db, settings))


class ZonePatch(BaseModel):
    fee: Decimal | None = Money
    free_over: Decimal | None = Money
    clear_free_over: bool = False  # no free-delivery threshold
    cod_fee: Decimal | None = Money
    cost_ils: Decimal | None = Money
    active: bool | None = None


@router.patch("/zones/{slug}", dependencies=[Depends(require_permission("prices"))])
async def edit_zone(
    slug: str, body: ZonePatch, admin: AdminUser, db: SessionDep, settings: SettingsDep
) -> ZoneRow:
    zone = (await db.execute(select(ShippingZone).where(ShippingZone.slug == slug))).scalar_one_or_none()
    if zone is None:
        raise ApiError("not_found", 404)
    fields = ["fee", "free_over", "cod_fee", "cost_ils", "active"]
    before = _plain(zone, fields)
    changes = body.model_dump(exclude_none=True, exclude={"clear_free_over"})
    for field in fields:
        if field in changes:
            setattr(zone, field, changes[field])
    if body.clear_free_over:
        zone.free_over = None
    _audit(db, admin, "zone", slug, before, _plain(zone, fields))
    await db.commit()
    return _zone_row(zone, await _rates(db, settings))


class CouponIn(BaseModel):
    code: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    kind: str = Field(pattern=r"^(percent|fixed)$")
    value: Decimal = Field(gt=0, le=100_000, max_digits=9, decimal_places=2)
    currency: Currency | None = None  # required for a fixed amount
    min_subtotal: Decimal | None = Money
    max_uses: int | None = Field(default=None, ge=1, le=1_000_000)
    per_customer: int | None = Field(default=1, ge=1, le=100)
    first_order_only: bool = False
    lines: list[str] = Field(default_factory=list, max_length=10)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


@router.post("/coupons", status_code=201, dependencies=[Depends(require_permission("prices"))])
async def add_coupon(body: CouponIn, admin: AdminUser, db: SessionDep) -> CouponRow:
    from qamra_core.db.store import CouponKind

    code = body.code.upper()
    if body.kind == "percent" and body.value > 90:
        raise ApiError("invalid_input", 422, {"fields": ["value"]})
    if body.kind == "fixed" and body.currency is None:
        raise ApiError("invalid_input", 422, {"fields": ["currency"]})
    if (await db.execute(select(Coupon).where(Coupon.code == code))).scalar_one_or_none():
        raise ApiError("coupon_exists", 409)
    coupon = Coupon(
        code=code,
        kind=CouponKind(body.kind),
        value=body.value,
        currency=body.currency,
        min_subtotal=body.min_subtotal,
        max_uses=body.max_uses,
        per_customer=body.per_customer,
        first_order_only=body.first_order_only,
        lines=body.lines,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    db.add(coupon)
    _audit(db, admin, "coupon", code, None, body.model_dump(mode="json"))
    await db.commit()
    return _coupon_row(coupon)


class ActivePatch(BaseModel):
    active: bool | None = None
    ends_at: datetime | None = None
    discount_pct: Decimal | None = Field(default=None, gt=0, le=90, max_digits=5, decimal_places=2)


@router.patch("/coupons/{code}", dependencies=[Depends(require_permission("prices"))])
async def edit_coupon(code: str, body: ActivePatch, admin: AdminUser, db: SessionDep) -> CouponRow:
    coupon = (await db.execute(select(Coupon).where(Coupon.code == code.upper()))).scalar_one_or_none()
    if coupon is None:
        raise ApiError("not_found", 404)
    before = _plain(coupon, ["active", "ends_at"])
    if body.active is not None:
        coupon.active = body.active
    if body.ends_at is not None:
        coupon.ends_at = body.ends_at
    _audit(db, admin, "coupon", coupon.code, before, _plain(coupon, ["active", "ends_at"]))
    await db.commit()
    return _coupon_row(coupon)


class SaleIn(BaseModel):
    name_ar: str = Field(min_length=2, max_length=120)
    name_en: str = Field(min_length=2, max_length=120)
    discount_pct: Decimal = Field(gt=0, le=90, max_digits=5, decimal_places=2)
    lines: list[str] = Field(default_factory=list, max_length=10)
    products: list[str] = Field(default_factory=list, max_length=50)
    starts_at: datetime
    ends_at: datetime


@router.post("/sales", status_code=201, dependencies=[Depends(require_permission("prices"))])
async def add_sale(body: SaleIn, admin: AdminUser, db: SessionDep) -> OfferRow:
    if body.ends_at <= body.starts_at:
        raise ApiError("invalid_input", 422, {"fields": ["ends_at"]})
    sale = Sale(**body.model_dump())
    db.add(sale)
    await db.flush()
    _audit(db, admin, "sale", str(sale.id), None, body.model_dump(mode="json"))
    await db.commit()
    return _sale_row(sale)


@router.patch("/sales/{sale_id}", dependencies=[Depends(require_permission("prices"))])
async def edit_sale(sale_id: uuid.UUID, body: ActivePatch, admin: AdminUser, db: SessionDep) -> OfferRow:
    sale = await db.get(Sale, sale_id)
    if sale is None:
        raise ApiError("not_found", 404)
    fields = ["active", "ends_at", "discount_pct"]
    before = _plain(sale, fields)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(sale, field, value)
    _audit(db, admin, "sale", str(sale.id), before, _plain(sale, fields))
    await db.commit()
    return _sale_row(sale)


@router.patch("/bundles/{slug}", dependencies=[Depends(require_permission("prices"))])
async def edit_bundle(slug: str, body: ActivePatch, admin: AdminUser, db: SessionDep) -> OfferRow:
    bundle = (await db.execute(select(Bundle).where(Bundle.slug == slug))).scalar_one_or_none()
    if bundle is None:
        raise ApiError("not_found", 404)
    fields = ["active", "ends_at", "discount_pct"]
    before = _plain(bundle, fields)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(bundle, field, value)
    _audit(db, admin, "bundle", slug, before, _plain(bundle, fields))
    await db.commit()
    return _bundle_row(bundle)


# ---- the price simulator ------------------------------------------------------------------------------


class SimItem(BaseModel):
    sku: str = Field(max_length=64)
    qty: int = Field(default=1, ge=1, le=500)
    style: str | None = Field(default=None, max_length=40)
    addons: list[dict[str, Any]] = Field(default_factory=list, max_length=20)


class SimIn(BaseModel):
    currency: Currency = Currency.ILS
    zone: str | None = Field(default=None, max_length=64)
    coupon: str | None = Field(default=None, max_length=32)
    items: list[SimItem] = Field(min_length=1, max_length=30)


class SimLine(BaseModel):
    sku: str
    qty: int
    unit_price: Decimal
    total: Decimal
    cost_ils: Decimal


class SimOut(BaseModel):
    currency: str
    lines: list[SimLine]
    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    cod_fee: Decimal
    total: Decimal
    total_ils: Decimal
    cost_ils: Decimal
    margin_ils: Decimal
    margin_pct: Decimal | None
    below_floor: bool
    notes: list[str]


@router.post("/simulate", dependencies=[Depends(require_permission("prices"))])
async def simulate(body: SimIn, db: SessionDep, settings: SettingsDep) -> SimOut:
    """What a basket would cost the customer and us, through the store's own pricing engine."""
    from qamra_api.store.cart import coupon_rule
    from qamra_api.store.catalog import BULK_SETTINGS, bulk_tiers, item_input, unit_costs, zone_rule
    from qamra_api.store.router import check_item
    from qamra_core import settings_store
    from qamra_core.pricing import quote

    r = await _rates(db, settings)
    c = await load_catalog(db, include_b2b=True, include_inactive=True)
    values = await settings_store.plain(db, *BULK_SETTINGS)
    inputs, costs = [], []
    copies: dict[str, int] = {}
    for item in body.items:
        copies[item.sku] = copies.get(item.sku, 0) + item.qty
    for i, item in enumerate(body.items):
        variant = check_item(c, c.variants.get(item.sku), item.style, item.addons)
        if c.price(variant, body.currency) is None:
            raise ApiError("unknown_product", 404)
        tiers = bulk_tiers(c, variant, body.currency, values) if copies[item.sku] >= 10 else ()
        inputs.append(
            item_input(
                c,
                key=str(i),
                variant=variant,
                currency=body.currency,
                qty=item.qty,
                style=item.style,
                addons=item.addons,
                child_key=str(i),
                tiers=tiers,
            )
        )
        unit = unit_costs(c, variant, item.addons, r.usd_ils)
        costs.append(sum((Decimal(v) for v in unit.values()), Decimal("0")) * item.qty)
    zone = c.zones.get(body.zone) if body.zone else None
    rule, problem = None, None
    if body.coupon:
        rule, _, problem = await coupon_rule(db, body.coupon, body.currency, user_id=None, phone=None)
    q = quote(
        inputs,
        sales=c.sale_rules(),
        bundles=c.bundle_rules(),
        coupon=rule,
        zone=zone_rule(zone, body.currency),
    )
    rate = r.jod_ils if body.currency == Currency.JOD else Decimal("1")
    total_ils = (q.total * rate).quantize(CENT)
    cost = (sum(costs, Decimal("0")) + (zone.cost_ils if zone else Decimal("0"))).quantize(CENT)
    amount, pct = margin(total_ils, cost) if total_ils else (total_ils - cost, None)
    by_key = {p.key: p for p in q.items}
    return SimOut(
        currency=body.currency.value,
        lines=[
            SimLine(
                sku=item.sku,
                qty=item.qty,
                unit_price=by_key[str(i)].unit_price,
                total=by_key[str(i)].total,
                cost_ils=costs[i].quantize(CENT),
            )
            for i, item in enumerate(body.items)
        ],
        subtotal=q.subtotal,
        discount=q.discount,
        shipping=q.shipping,
        cod_fee=q.cod_fee,
        total=q.total,
        total_ils=total_ils,
        cost_ils=cost,
        margin_ils=(amount or Decimal("0")),
        margin_pct=pct,
        below_floor=pct is not None and pct < r.margin_floor_pct,
        notes=[*q.notes, *([f"coupon: {problem}"] if problem else [])],
    )


# ---- B2B price lists (Addendum 4 §5): wholesale tiers per variant, per organization ------------------------


class TierIn(BaseModel):
    min_qty: int = Field(ge=1, le=10_000)
    unit_price: Decimal = Field(gt=0, le=100_000, max_digits=9, decimal_places=2)


class PriceListItemRow(BaseModel):
    sku: str
    product_ar: str
    product_en: str
    tiers: list[TierIn]
    retail: Decimal | None  # the variant's own price in the list's currency
    unit_cost_ils: Decimal
    margin_pct: list[Decimal | None]  # per tier, in ₪ (JD lists converted)
    below_floor: bool


class PriceListRow(BaseModel):
    id: uuid.UUID
    name: str
    currency: str
    organization_id: uuid.UUID | None  # None = the default list for every kindergarten
    organization: str | None
    active: bool
    valid_from: datetime | None
    valid_to: datetime | None
    items: list[PriceListItemRow]


class PriceListsOut(BaseModel):
    lists: list[PriceListRow]
    variants: list[VariantRow]  # the B2B variants a list can price
    organizations: list[dict[str, str]]  # id, name: kindergartens a list can belong to


async def _price_list_row(db: SessionDep, c: Catalog, pl: PriceList, r: Rates) -> PriceListRow:
    org = await db.get(Organization, pl.organization_id) if pl.organization_id else None
    by_id = {v.id: v for v in c.variants.values()}
    items = []
    for item in (
        await db.execute(select(PriceListItem).where(PriceListItem.price_list_id == pl.id))
    ).scalars():
        variant = by_id.get(item.variant_id)
        if variant is None:
            continue
        row = _variant_row(c, variant, r)
        tiers = sorted((TierIn.model_validate(t) for t in item.tiers), key=lambda t: t.min_qty)
        rate = Decimal("1") if pl.currency == Currency.ILS else r.jod_ils
        pcts = [margin((t.unit_price * rate).quantize(CENT), row.unit_cost_ils)[1] for t in tiers]
        items.append(
            PriceListItemRow(
                sku=variant.sku,
                product_ar=row.product_ar,
                product_en=row.product_en,
                tiers=tiers,
                retail=c.price(variant, pl.currency),
                unit_cost_ils=row.unit_cost_ils,
                margin_pct=pcts,
                below_floor=any(p is not None and p < r.margin_floor_pct for p in pcts),
            )
        )
    return PriceListRow(
        id=pl.id,
        name=pl.name,
        currency=pl.currency.value,
        organization_id=pl.organization_id,
        organization=org.name if org else None,
        active=pl.active,
        valid_from=pl.valid_from,
        valid_to=pl.valid_to,
        items=sorted(items, key=lambda i: i.sku),
    )


@router.get("/price-lists", dependencies=[Depends(require_permission("prices"))])
async def price_lists(db: SessionDep, settings: SettingsDep) -> PriceListsOut:
    r = await _rates(db, settings)
    c = await load_catalog(db, include_b2b=True, include_inactive=True)
    lists = (
        await db.execute(select(PriceList).order_by(PriceList.organization_id.nulls_first(), PriceList.name))
    ).scalars()
    orgs = (await db.execute(select(Organization).order_by(Organization.name))).scalars()
    return PriceListsOut(
        lists=[await _price_list_row(db, c, pl, r) for pl in lists],
        variants=[
            _variant_row(c, v, r) for v in c.variants.values() if c.product_of(v).audience.value == "b2b"
        ],
        organizations=[{"id": str(o.id), "name": o.name} for o in orgs],
    )


class PriceListIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    currency: Currency = Currency.ILS
    organization_id: uuid.UUID | None = None
    copy_from: uuid.UUID | None = None  # start from another list's tiers (usually the default one)


async def _list_out(db: SessionDep, settings: SettingsDep, pl: PriceList) -> PriceListRow:
    c = await load_catalog(db, include_b2b=True, include_inactive=True)
    return await _price_list_row(db, c, pl, await _rates(db, settings))


@router.post("/price-lists", status_code=201, dependencies=[Depends(require_permission("prices"))])
async def add_price_list(
    body: PriceListIn, admin: AdminUser, db: SessionDep, settings: SettingsDep
) -> PriceListRow:
    if body.organization_id is not None and await db.get(Organization, body.organization_id) is None:
        raise ApiError("not_found", 404)
    pl = PriceList(
        name=" ".join(body.name.split()), currency=body.currency, organization_id=body.organization_id
    )
    db.add(pl)
    await db.flush()
    if body.copy_from is not None:
        for item in (
            await db.execute(select(PriceListItem).where(PriceListItem.price_list_id == body.copy_from))
        ).scalars():
            db.add(PriceListItem(price_list_id=pl.id, variant_id=item.variant_id, tiers=list(item.tiers)))
    _audit(
        db,
        admin,
        "price_list",
        str(pl.id),
        None,
        {"name": pl.name, "organization_id": str(body.organization_id)},
    )
    await db.commit()
    return await _list_out(db, settings, pl)


class PriceListPatch(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    active: bool | None = None
    organization_id: uuid.UUID | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None


async def _price_list(db: SessionDep, list_id: uuid.UUID) -> PriceList:
    pl = await db.get(PriceList, list_id)
    if pl is None:
        raise ApiError("not_found", 404)
    return pl


@router.patch("/price-lists/{list_id}", dependencies=[Depends(require_permission("prices"))])
async def edit_price_list(
    list_id: uuid.UUID, body: PriceListPatch, admin: AdminUser, db: SessionDep, settings: SettingsDep
) -> PriceListRow:
    pl = await _price_list(db, list_id)
    fields = ["name", "active", "organization_id", "valid_from", "valid_to"]
    before = _plain(pl, fields)
    changes = body.model_dump(exclude_unset=True)
    if (
        changes.get("organization_id") is not None
        and await db.get(Organization, changes["organization_id"]) is None
    ):
        raise ApiError("not_found", 404)
    for field, value in changes.items():
        setattr(pl, field, " ".join(value.split()) if field == "name" and value else value)
    _audit(db, admin, "price_list", str(pl.id), before, _plain(pl, fields))
    await db.commit()
    return await _list_out(db, settings, pl)


class TiersIn(BaseModel):
    tiers: list[TierIn] = Field(min_length=1, max_length=10)


@router.put("/price-lists/{list_id}/items/{sku}", dependencies=[Depends(require_permission("prices"))])
async def set_tiers(
    list_id: uuid.UUID, sku: str, body: TiersIn, admin: AdminUser, db: SessionDep, settings: SettingsDep
) -> PriceListRow:
    """A variant's wholesale tiers in this list: the unit price from each minimum quantity up."""
    pl = await _price_list(db, list_id)
    variant = (await db.execute(select(Variant).where(Variant.sku == sku))).scalar_one_or_none()
    if variant is None:
        raise ApiError("unknown_product", 404)
    quantities = [t.min_qty for t in body.tiers]
    if len(set(quantities)) != len(quantities):
        raise ApiError("invalid_tiers", 422)
    tiers = [
        {"min_qty": t.min_qty, "unit_price": str(t.unit_price.quantize(CENT))}
        for t in sorted(body.tiers, key=lambda t: t.min_qty)
    ]
    item = (
        await db.execute(
            select(PriceListItem).where(
                PriceListItem.price_list_id == pl.id, PriceListItem.variant_id == variant.id
            )
        )
    ).scalar_one_or_none()
    before = list(item.tiers) if item else None
    if item is None:
        db.add(PriceListItem(price_list_id=pl.id, variant_id=variant.id, tiers=tiers))
    else:
        item.tiers = tiers
    _audit(db, admin, "price_list", str(pl.id), {"sku": sku, "tiers": before}, {"sku": sku, "tiers": tiers})
    await db.commit()
    return await _list_out(db, settings, pl)


@router.delete("/price-lists/{list_id}/items/{sku}", dependencies=[Depends(require_permission("prices"))])
async def remove_tiers(
    list_id: uuid.UUID, sku: str, admin: AdminUser, db: SessionDep, settings: SettingsDep
) -> PriceListRow:
    pl = await _price_list(db, list_id)
    variant = (await db.execute(select(Variant).where(Variant.sku == sku))).scalar_one_or_none()
    item = (
        (
            await db.execute(
                select(PriceListItem).where(
                    PriceListItem.price_list_id == pl.id, PriceListItem.variant_id == variant.id
                )
            )
        ).scalar_one_or_none()
        if variant
        else None
    )
    if item is None:
        raise ApiError("not_found", 404)
    _audit(
        db,
        admin,
        "price_list",
        str(pl.id),
        {"sku": sku, "tiers": list(item.tiers)},
        {"sku": sku, "tiers": None},
    )
    await db.delete(item)
    await db.commit()
    return await _list_out(db, settings, pl)
