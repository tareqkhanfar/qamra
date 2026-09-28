"""Sales reports and CSV exports for the admin (Addendum 4 §6, step 5).

The figures come from `qamra_api.reports.summarize` over the period's orders (cancelled ones left out),
the books made through the create flow, and the AI cost log. The CSV files open in Excel with Arabic intact
(UTF-8 with a byte-order mark).
"""

import csv
import io
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select

from qamra_api import runtime_settings
from qamra_api.deps import SessionDep, SettingsDep, require_permission
from qamra_api.reports import BookRow, ItemRow, OrderRow, summarize
from qamra_core.db.models import Book, GenerationCost, Order, OrderItem, OrderStatus

router = APIRouter(
    prefix="/api/admin/reports", tags=["admin"], dependencies=[Depends(require_permission("reports"))]
)
Days = Query(default=30, ge=1, le=730)


async def _orders(db: SessionDep, since: datetime) -> list[tuple[Order, list[OrderItem]]]:
    orders = (
        (
            await db.execute(
                select(Order)
                .where(Order.created_at >= since, Order.status != OrderStatus.cancelled)
                .order_by(Order.created_at)
            )
        )
        .scalars()
        .all()
    )
    items = (
        (await db.execute(select(OrderItem).where(OrderItem.order_id.in_([o.id for o in orders]))))
        .scalars()
        .all()
    )
    by_order: dict[Any, list[OrderItem]] = {}
    for i in items:
        by_order.setdefault(i.order_id, []).append(i)
    return [(o, by_order.get(o.id, [])) for o in orders]


def _item_row(i: OrderItem) -> ItemRow:
    return ItemRow(
        sku=i.sku or (i.product.value if i.product else ""),
        line=i.line or "",
        product=str(i.title.get("name_ar") or i.sku or ""),
        theme=i.theme_slug,
        style=i.style_slug,
        qty=i.quantity,
        unit_price=i.unit_price,
        discount=i.discount,
        addons=list(i.addons or []),
        book_id=str(i.book_id) if i.book_id else None,
    )


def _b2b(o: Order) -> bool:
    return o.organization_id is not None or o.source == "portal"


@router.get("")
async def report(db: SessionDep, settings: SettingsDep, days: int = Days) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=days)
    values = (await runtime_settings.current(db, settings)).values
    rows = await _orders(db, since)
    orders = [
        OrderRow(
            o.code,
            o.created_at.date(),
            o.currency.value,
            o.total,
            o.cost_ils,
            _b2b(o),
            [_item_row(i) for i in items],
        )
        for o, items in rows
    ]
    made = (
        await db.execute(
            select(Book.id, Book.generation["line"].astext).where(
                Book.created_at >= since,
                Book.is_sample.is_(False),
                Book.generation["line"].astext.is_not(None),
            )
        )
    ).all()
    bought = {
        b
        for (b,) in (
            await db.execute(
                select(OrderItem.book_id)
                .join(Order, Order.id == OrderItem.order_id)
                .where(OrderItem.book_id.in_([m[0] for m in made]), Order.status != OrderStatus.cancelled)
            )
        ).all()
    }
    day = func.date(GenerationCost.created_at)
    ai = {
        d if isinstance(d, date) else date.fromisoformat(str(d)): Decimal(str(usd))
        for d, usd in (
            await db.execute(
                select(day, func.sum(GenerationCost.usd))
                .where(GenerationCost.created_at >= since)
                .group_by(day)
            )
        ).all()
    }
    summary = summarize(
        orders,
        [BookRow(str(line), book_id in bought) for book_id, line in made],
        ai,
        jod_ils=Decimal(str(values["jod_ils"])),
        floor_pct=Decimal(str(values["margin_floor_pct"])),
    )
    return {"days": days, "since": since.date().isoformat(), **summary}


def _csv(name: str, header: list[str], rows: list[list[Any]]) -> Response:
    buf = io.StringIO()
    buf.write("﻿")  # Excel reads the Arabic as UTF-8
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/orders.csv")
async def orders_csv(db: SessionDep, settings: SettingsDep, days: int = Days) -> Response:
    since = datetime.now(UTC) - timedelta(days=days)
    rate = Decimal(str((await runtime_settings.current(db, settings)).values["jod_ils"]))
    out = []
    for o, items in await _orders(db, since):
        total_ils = (o.total * (rate if o.currency.value == "JOD" else 1)).quantize(Decimal("0.01"))
        margin = total_ils - o.cost_ils
        pct = (margin / total_ils * 100).quantize(Decimal("0.1")) if total_ils else ""
        out.append(
            [
                o.code, o.created_at.isoformat(timespec="minutes"), o.status.value,
                "B2B" if _b2b(o) else "B2C", o.shipping.get("city", ""), o.currency.value,
                o.subtotal, o.discount, o.delivery_fee, o.total,
                total_ils, o.cost_ils, margin, pct, sum(i.quantity for i in items),
                (o.pricing or {}).get("coupon") or "",
            ]
        )  # fmt: skip
    header = [
        "order", "date", "status", "customer", "city", "currency", "subtotal", "discount", "delivery",
        "total", "total_ils", "cost_ils", "margin_ils", "margin_pct", "copies", "coupon",
    ]  # fmt: skip
    return _csv(f"qamra-orders-{days}d.csv", header, out)


@router.get("/items.csv")
async def items_csv(db: SessionDep, settings: SettingsDep, days: int = Days) -> Response:
    since = datetime.now(UTC) - timedelta(days=days)
    rate = Decimal(str((await runtime_settings.current(db, settings)).values["jod_ils"]))
    out = []
    for o, items in await _orders(db, since):
        r = rate if o.currency.value == "JOD" else Decimal("1")
        for i in items:
            row = _item_row(i)
            paid = [a for a in row.addons if not a.get("included")]
            out.append(
                [
                    o.code, o.created_at.date().isoformat(), row.sku, row.line, row.product, row.theme or "",
                    row.style or "", row.qty, row.unit_price, row.discount, o.currency.value,
                    "، ".join(str(a.get("name_ar") or a.get("slug")) for a in paid),
                    ((row.unit_price * row.qty - row.discount) * r).quantize(Decimal("0.01")),
                ]
            )  # fmt: skip
    header = [
        "order", "date", "sku", "line", "product", "theme", "style", "qty", "unit_price", "discount",
        "currency", "extras", "revenue_ils",
    ]  # fmt: skip
    return _csv(f"qamra-items-{days}d.csv", header, out)
