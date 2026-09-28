"""The active catalog, loaded per request, and the translation from store rows to pricing-engine inputs.

Everything the storefront sells comes from the database (Addendum 4 §5): products, variants and prices, art
styles, add-ons with their rules, bundles, sales and shipping zones. Add-on rules (lines, requirements,
exclusions, limits) are checked here so the cart and the checkout apply exactly the same ones.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core.db.models import Currency
from qamra_core.db.store import (
    AddOn,
    AddOnPrice,
    AddOnPricing,
    ArtStyle,
    Audience,
    Bundle,
    CatalogProduct,
    Sale,
    ShippingZone,
    Variant,
    VariantPrice,
)
from qamra_core.pricing import AddOnLine, BundleRule, ItemInput, SaleRule, ZoneRule

PRINTED_FORMATS = ("softcover", "hardcover", "spiral")


@dataclass
class Catalog:
    products: dict[uuid.UUID, CatalogProduct]
    variants: dict[str, Variant]  # by sku
    prices: dict[tuple[uuid.UUID, Currency], Decimal]
    styles: dict[str, ArtStyle]
    addons: dict[str, AddOn]
    addon_prices: dict[tuple[uuid.UUID, Currency], Decimal]
    zones: dict[str, ShippingZone]
    bundles: list[Bundle] = field(default_factory=list)
    sales: list[Sale] = field(default_factory=list)

    def product_of(self, variant: Variant) -> CatalogProduct:
        return self.products[variant.product_id]

    def price(self, variant: Variant, currency: Currency) -> Decimal | None:
        return self.prices.get((variant.id, currency))

    def style_modifier(self, slug: str | None, currency: Currency) -> Decimal:
        style = self.styles.get(slug or "")
        if style is None:
            return Decimal("0")
        return style.price_modifier_ils if currency == Currency.ILS else style.price_modifier_jod

    def sale_rules(self) -> list[SaleRule]:
        return [SaleRule(s.name_ar, s.discount_pct, tuple(s.lines), tuple(s.products)) for s in self.sales]

    def bundle_rules(self) -> list[BundleRule]:
        return [
            BundleRule(b.slug, b.kind.value, b.min_items, b.discount_pct, tuple(b.lines))
            for b in self.bundles
        ]


def _live(starts: datetime | None, ends: datetime | None, now: datetime) -> bool:
    return (starts is None or starts <= now) and (ends is None or now < ends)


async def load_catalog(db: AsyncSession, *, include_b2b: bool = False) -> Catalog:
    now = datetime.now(UTC)
    products = {
        p.id: p
        for p in (await db.execute(select(CatalogProduct).where(CatalogProduct.active))).scalars()
        if include_b2b or p.audience == Audience.b2c
    }
    variants = {
        v.sku: v
        for v in (await db.execute(select(Variant).where(Variant.active).order_by(Variant.sort))).scalars()
        if v.product_id in products
    }
    prices = {
        (p.variant_id, p.currency): p.amount for p in (await db.execute(select(VariantPrice))).scalars()
    }
    styles = {s.slug: s for s in (await db.execute(select(ArtStyle).where(ArtStyle.active))).scalars()}
    addons = {a.slug: a for a in (await db.execute(select(AddOn).where(AddOn.active))).scalars()}
    addon_prices = {
        (p.addon_id, p.currency): p.amount for p in (await db.execute(select(AddOnPrice))).scalars()
    }
    zones = {z.slug: z for z in (await db.execute(select(ShippingZone).where(ShippingZone.active))).scalars()}
    bundles = [
        b
        for b in (await db.execute(select(Bundle).where(Bundle.active))).scalars()
        if _live(b.starts_at, b.ends_at, now)
    ]
    sales = [
        s
        for s in (await db.execute(select(Sale).where(Sale.active))).scalars()
        if _live(s.starts_at, s.ends_at, now)
    ]
    return Catalog(products, variants, prices, styles, addons, addon_prices, zones, bundles, sales)


# ---- add-on rules ------------------------------------------------------------------------------------------


def addon_problems(catalog: Catalog, variant: Variant, chosen: list[dict[str, Any]]) -> list[str]:
    """Why these add-ons can't go on this variant (empty = fine)."""
    line = catalog.product_of(variant).line.value
    slugs = [str(a.get("slug")) for a in chosen]
    out = []
    for a in chosen:
        slug, qty = str(a.get("slug")), int(a.get("qty", 1))
        addon = catalog.addons.get(slug)
        if addon is None:
            out.append(f"{slug}: not available")
            continue
        if line not in addon.lines and line not in addon.included_lines:
            out.append(f"{slug}: not offered for this product")
        for option, allowed in addon.requires.items():
            if variant.options.get(option) not in allowed:
                out.append(f"{slug}: needs {option} {'/'.join(allowed)}")
        if not 1 <= qty <= addon.max_qty:
            out.append(f"{slug}: quantity 1–{addon.max_qty}")
        clash = [x for x in addon.excludes if x in slugs]
        if clash:
            out.append(f"{slug}: can't be combined with {', '.join(clash)}")
    if len(set(slugs)) != len(slugs):
        out.append("an add-on is listed twice")
    return out


def automatic_addons(catalog: Catalog, variant: Variant) -> list[str]:
    """Free add-ons every matching item gets without asking (the digital copy of a printed book)."""
    line = catalog.product_of(variant).line.value
    out = []
    for addon in catalog.addons.values():
        free = all(amount == 0 for (aid, _), amount in catalog.addon_prices.items() if aid == addon.id)
        fits = line in addon.lines and all(variant.options.get(k) in v for k, v in addon.requires.items())
        if free and fits and addon.pricing == AddOnPricing.fixed and addon.slug == "digital-copy":
            out.append(addon.slug)
    return out


def item_input(
    catalog: Catalog,
    *,
    key: str,
    variant: Variant,
    currency: Currency,
    qty: int,
    style: str | None,
    addons: list[dict[str, Any]],
    child_key: str | None,
    tiers: tuple[tuple[int, Decimal], ...] = (),
) -> ItemInput:
    product = catalog.product_of(variant)
    retail = catalog.price(variant, currency)
    if retail is None:
        raise ValueError(f"{variant.sku} has no {currency.value} price")
    lines = []
    for a in addons:
        addon = catalog.addons[str(a["slug"])]
        price = catalog.addon_prices.get((addon.id, currency), Decimal("0"))
        percent = addon.percent if addon.pricing == AddOnPricing.percent_of_item else None
        included = product.line.value in addon.included_lines
        lines.append(AddOnLine(addon.slug, int(a.get("qty", 1)), price, percent, included))
    return ItemInput(
        key=key,
        line=product.line.value,
        product=product.slug,
        sku=variant.sku,
        unit_price=retail,
        qty=qty,
        style_modifier=catalog.style_modifier(style, currency),
        addons=tuple(lines),
        child_key=child_key,
        physical=variant.options.get("format") in PRINTED_FORMATS,
        tiers=tiers,
    )


def zone_rule(zone: ShippingZone | None, currency: Currency) -> ZoneRule | None:
    if zone is None or zone.currency != currency:
        return None
    return ZoneRule(zone.slug, zone.fee, zone.free_over, zone.cod_fee)


def unit_costs(
    catalog: Catalog, variant: Variant, addons: list[dict[str, Any]], usd_ils: Decimal
) -> dict[str, str]:
    """What one item costs us, in ILS, frozen on the order line (Addendum 4 §6)."""
    ai = variant.cost_ai_usd * usd_ils
    addon_ils = sum(
        (
            catalog.addons[str(a["slug"])].cost_ils * int(a.get("qty", 1))
            for a in addons
            if str(a["slug"]) in catalog.addons
        ),
        Decimal("0"),
    )
    addon_ai = (
        sum(
            (
                catalog.addons[str(a["slug"])].cost_ai_usd * int(a.get("qty", 1))
                for a in addons
                if str(a["slug"]) in catalog.addons
            ),
            Decimal("0"),
        )
        * usd_ils
    )
    parts = {
        "print": variant.cost_print_ils,
        "packaging": variant.cost_packaging_ils,
        "handling": variant.cost_handling_ils,
        "ai_estimate": ai + addon_ai,
        "addons": addon_ils,
    }
    total = sum(parts.values(), Decimal("0"))
    return {k: str(v.quantize(Decimal("0.01"))) for k, v in {**parts, "total": total}.items()}
