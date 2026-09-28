"""The printer's prices per copy by run length (Addendum 7 §3.9 and §8), entered from the printer's quote.

Until staff save the real quote, the seeded tiers are estimates: the admin shows them with ⚠, and orders of
10+ copies wait (Tareq, 2026-09-28). Saving the quote clears the flag, and the cart then prices 10+ copies
from these tiers and the margin settings.
"""

from decimal import Decimal
from itertools import pairwise

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from qamra_api.deps import AdminUser, SessionDep, require_permission
from qamra_api.errors import ApiError
from qamra_api.store.catalog import (
    BULK_MIN_QTY,
    BULK_SETTINGS,
    Catalog,
    load_catalog,
    other_unit_cost,
    quantity_table,
    tiers_estimated,
)
from qamra_core import settings_store
from qamra_core.db.models import AuditLog, Currency
from qamra_core.db.store import Variant

router = APIRouter(
    prefix="/api/admin/store/print-costs",
    tags=["admin"],
    dependencies=[Depends(require_permission("prices"))],
)
QUANTITIES = (1, 10, 50, 100, 500)


class TierIn(BaseModel):
    min_qty: int = Field(ge=1, le=100_000)
    unit_ils: Decimal = Field(gt=0, le=10_000, max_digits=8, decimal_places=2)


class TiersIn(BaseModel):
    tiers: list[TierIn] = Field(min_length=1, max_length=12)

    @field_validator("tiers")
    @classmethod
    def _sane(cls, tiers: list[TierIn]) -> list[TierIn]:
        tiers = sorted(tiers, key=lambda t: t.min_qty)
        if tiers[0].min_qty != 1:
            raise ValueError("the first tier is for 1 copy")
        if len({t.min_qty for t in tiers}) != len(tiers):
            raise ValueError("each minimum quantity once")
        if any(b.unit_ils > a.unit_ils for a, b in pairwise(tiers)):
            raise ValueError("a longer run never costs more per copy")
        return tiers


class TierOut(BaseModel):
    min_qty: int
    unit_ils: Decimal


class RowOut(BaseModel):
    qty: int
    printer_ils: Decimal
    cost_ils: Decimal
    price_ils: Decimal
    total_ils: Decimal
    margin_pct: Decimal


class PrintCostsOut(BaseModel):
    sku: str
    product_ar: str
    product_en: str
    retail_ils: Decimal | None
    other_cost_ils: Decimal  # packaging, handling and the AI drawing, per copy
    estimated: bool  # ⚠ the seed's estimates, not the printer's quote
    bulk_from: int
    tiers: list[TierOut]
    table: list[RowOut]


def _out(c: Catalog, v: Variant, values: dict[str, object]) -> PrintCostsOut:
    product = c.product_of(v)
    other = other_unit_cost(v, Decimal(str(values["usd_ils"])))
    table = [
        RowOut(
            qty=r.qty,
            printer_ils=r.unit_cost - other,
            cost_ils=r.unit_cost,
            price_ils=r.unit_price,
            total_ils=r.total,
            margin_pct=r.margin_pct,
        )
        for r in quantity_table(c, v, dict(values), QUANTITIES)
    ]
    return PrintCostsOut(
        sku=v.sku,
        product_ar=product.name_ar,
        product_en=product.name_en,
        retail_ils=c.price(v, Currency.ILS),
        other_cost_ils=other,
        estimated=tiers_estimated(v),
        bulk_from=BULK_MIN_QTY,
        tiers=[
            TierOut(min_qty=int(t["min_qty"]), unit_ils=Decimal(str(t["unit_ils"])))
            for t in v.print_cost_tiers
        ],
        table=table,
    )


@router.get("")
async def list_print_costs(db: SessionDep) -> list[PrintCostsOut]:
    """Every variant priced by the printer's tiers (the family book today)."""
    c = await load_catalog(db, include_b2b=True, include_inactive=True)
    values = await settings_store.plain(db, *BULK_SETTINGS)
    return [_out(c, v, values) for v in c.variants.values() if v.print_cost_tiers]


@router.put("/{sku}")
async def save_print_costs(sku: str, body: TiersIn, admin: AdminUser, db: SessionDep) -> PrintCostsOut:
    variant = (await db.execute(select(Variant).where(Variant.sku == sku))).scalar_one_or_none()
    if variant is None or not variant.print_cost_tiers:
        raise ApiError("not_found", 404)
    before = [dict(t) for t in variant.print_cost_tiers]
    variant.print_cost_tiers = [{"min_qty": t.min_qty, "unit_ils": str(t.unit_ils)} for t in body.tiers]
    variant.cost_print_ils = body.tiers[0].unit_ils  # one copy's print cost, frozen on single-copy orders
    db.add(
        AuditLog(
            actor_user_id=admin.id,
            action="print_costs.saved",
            entity_type="variant",
            entity_id=sku,
            data={"before": before, "after": variant.print_cost_tiers},
        )
    )
    await db.commit()
    c = await load_catalog(db, include_b2b=True, include_inactive=True)
    return _out(c, c.variants[sku], await settings_store.plain(db, *BULK_SETTINGS))
