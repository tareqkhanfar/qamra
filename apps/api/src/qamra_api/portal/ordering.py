"""Class orders (CLAUDE.md §8, Addendum 4 §5): wholesale prices from the school's price list, one order and
one invoice per class, delivered to the school.

The store does the work: `pricing.quote` (price-list tiers by the order's total quantity, shipping), the
order snapshot (`unit_costs`, the quote breakdown) and `issue_invoice`. This module only turns a class into
the engine's inputs: one item per approved copy, so every child's book is its own order line.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.errors import ApiError
from qamra_api.store.catalog import Catalog, item_input, load_catalog, unit_costs, zone_rule
from qamra_core.db.models import Book, BookStatus, Child, Currency, Organization
from qamra_core.db.portal import ClassBook
from qamra_core.db.store import CatalogProduct, PriceList, PriceListItem, ShippingZone, Variant
from qamra_core.pricing import Quote, quote

PRODUCTS = {"classic": "classic-class-book", "magic": "magic-class-book"}
APPROVED = (BookStatus.in_review, BookStatus.approved)  # approved by the school (then by our reviewers)


def currency_of(org: Organization) -> Currency:
    return Currency.JOD if org.country == "JO" else Currency.ILS


async def price_list_for(db: AsyncSession, org: Organization, currency: Currency) -> PriceList | None:
    """The school's own active list, else the default list for kindergartens (`organization_id` NULL)."""
    now = datetime.now(UTC)
    rows = (
        await db.execute(
            select(PriceList)
            .where(
                PriceList.active,
                PriceList.currency == currency,
                or_(PriceList.organization_id == org.id, PriceList.organization_id.is_(None)),
            )
            .order_by(PriceList.created_at.desc())
        )
    ).scalars()
    live = [
        p
        for p in rows
        if (p.valid_from is None or p.valid_from <= now) and (p.valid_to is None or now < p.valid_to)
    ]
    own = [p for p in live if p.organization_id == org.id]
    default = [p for p in live if p.organization_id is None]
    return own[0] if own else default[0] if default else None


async def tiers_for(
    db: AsyncSession, price_list: PriceList | None, variant: Variant
) -> tuple[tuple[int, Decimal], ...]:
    if price_list is None:
        return ()
    item = (
        await db.execute(
            select(PriceListItem).where(
                PriceListItem.price_list_id == price_list.id, PriceListItem.variant_id == variant.id
            )
        )
    ).scalar_one_or_none()
    if item is None:
        return ()
    return tuple(sorted((int(t["min_qty"]), Decimal(str(t["unit_price"]))) for t in item.tiers))


def zone_for(catalog: Catalog, org: Organization) -> ShippingZone | None:
    """The delivery zone of the school's city (or the first zone of its country)."""
    zones = sorted(catalog.zones.values(), key=lambda z: z.sort)
    city = (org.city or "").strip()
    return next((z for z in zones if city and city in z.cities), None) or next(
        (z for z in zones if z.country == org.country and not z.cities), None
    )


@dataclass
class ClassQuote:
    catalog: Catalog
    product: CatalogProduct
    variant: Variant
    currency: Currency
    price_list: PriceList | None
    tiers: tuple[tuple[int, Decimal], ...]
    copies: list[tuple[Book, Child]]
    zone: ShippingZone | None
    quote: Quote


async def approved_copies(db: AsyncSession, cb: ClassBook) -> list[tuple[Book, Child]]:
    rows = (
        await db.execute(
            select(Book, Child)
            .join(Child, Child.id == Book.child_id)
            .where(
                Book.generation["class_book_id"].astext == str(cb.id),
                Book.status.in_(APPROVED),
                Child.classroom_id == cb.classroom_id,  # a child who left the class isn't ordered
            )
            .order_by(Child.first_name)
        )
    ).all()
    return [(b, c) for b, c in rows]


async def class_quote(db: AsyncSession, org: Organization, cb: ClassBook) -> ClassQuote:
    catalog = await load_catalog(db, include_b2b=True)
    product = next((p for p in catalog.products.values() if p.slug == PRODUCTS.get(cb.line, "")), None)
    variant = next(
        (v for v in catalog.variants.values() if product is not None and v.product_id == product.id), None
    )
    if product is None or variant is None:
        raise ApiError("unknown_product", 404)
    currency = currency_of(org)
    price_list = await price_list_for(db, org, currency)
    tiers = await tiers_for(db, price_list, variant)
    if not tiers and catalog.price(variant, currency) is None:
        raise ApiError("no_price_list", 409)
    copies = await approved_copies(db, cb)
    zone = zone_for(catalog, org)
    try:
        inputs = [
            item_input(
                catalog,
                key=str(book.id),
                variant=variant,
                currency=currency,
                qty=1,
                style=cb.art_style,
                addons=[],
                child_key=str(child.id),
                tiers=tiers,
            )
            for book, child in copies
        ]
    except ValueError as e:
        raise ApiError("no_price_list", 409) from e
    q = quote(inputs, zone=zone_rule(zone, currency), cash_on_delivery=True)
    return ClassQuote(catalog, product, variant, currency, price_list, tiers, copies, zone, q)


def item_costs(cq: ClassQuote, usd_ils: Decimal) -> dict[str, Any]:
    return unit_costs(cq.catalog, cq.variant, [], usd_ils)
