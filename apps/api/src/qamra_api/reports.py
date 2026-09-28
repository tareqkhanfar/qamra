"""Sales reports (Addendum 4 §6, step 5): pure calculations over order rows, in ₪.

The admin endpoint loads the rows; everything here is plain data in, plain data out, so each figure is
unit-tested without a database. JD amounts are converted at the settings' JD rate. Cancelled orders are
left out by the caller.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

CENT = Decimal("0.01")


@dataclass(frozen=True)
class ItemRow:
    sku: str
    line: str
    product: str  # the product's name as sold
    theme: str | None
    style: str | None
    qty: int
    unit_price: Decimal
    discount: Decimal
    addons: list[dict[str, Any]] = field(default_factory=list)  # the order line's add-on snapshot
    book_id: str | None = None


@dataclass(frozen=True)
class OrderRow:
    code: str
    day: date
    currency: str  # ILS | JOD
    total: Decimal
    cost_ils: Decimal
    b2b: bool
    items: list[ItemRow]


@dataclass(frozen=True)
class BookRow:
    """A book made through the create flow: its line, and whether an order bought it."""

    line: str
    bought: bool


def _pct(part: Decimal, whole: Decimal) -> Decimal | None:
    return (part / whole * 100).quantize(Decimal("0.1")) if whole else None


def _paid(addon: dict[str, Any]) -> bool:
    return not addon.get("included") and Decimal(str(addon.get("unit_price", "0"))) > 0


def summarize(
    orders: list[OrderRow],
    books: list[BookRow],
    ai_cost: dict[date, Decimal],
    *,
    jod_ils: Decimal,
    floor_pct: Decimal,
) -> dict[str, Any]:
    rate = {"ILS": Decimal("1"), "JOD": jod_ils}
    revenue = sum((o.total * rate[o.currency] for o in orders), Decimal("0")).quantize(CENT)
    cost = sum((o.cost_ils for o in orders), Decimal("0")).quantize(CENT)
    below = 0
    for o in orders:
        pct = _pct(o.total * rate[o.currency] - o.cost_ils, o.total * rate[o.currency])
        if pct is not None and pct < floor_pct:
            below += 1

    lines: dict[str, list[Decimal]] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    products: dict[str, list[Decimal]] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    themes: dict[str, list[Decimal]] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    styles: Counter[str] = Counter()
    addons: dict[str, list[Decimal]] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    names: dict[str, str] = {}
    with_addon = items = 0
    for o in orders:
        for i in o.items:
            sold = (i.unit_price * i.qty - i.discount) * rate[o.currency]
            for bucket, key in ((lines, i.line), (products, i.product), (themes, i.theme)):
                if key:
                    bucket[key][0] += i.qty
                    bucket[key][1] += sold
            if i.style:
                styles[i.style] += i.qty
            items += 1
            paid = [a for a in i.addons if _paid(a)]
            with_addon += bool(paid)
            for a in paid:
                slug = str(a["slug"])
                names[slug] = str(a.get("name_ar") or slug)
                qty = int(a.get("qty", 1))
                addons[slug][0] += qty
                addons[slug][1] += Decimal(str(a["unit_price"])) * qty * rate[o.currency]

    def table(d: dict[str, list[Decimal]]) -> list[dict[str, Any]]:
        rows = [{"key": k, "qty": int(v[0]), "revenue_ils": v[1].quantize(CENT)} for k, v in d.items()]
        return sorted(rows, key=lambda r: (-r["revenue_ils"], r["key"]))

    funnel: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for b in books:
        funnel[b.line][0] += 1
        funnel[b.line][1] += b.bought
    b2b = [o for o in orders if o.b2b]
    b2c = [o for o in orders if not o.b2b]
    return {
        "orders": len(orders),
        "revenue_ils": revenue,
        "aov_ils": (revenue / len(orders)).quantize(CENT) if orders else Decimal("0"),
        "cost_ils": cost,
        "margin_ils": revenue - cost,
        "margin_pct": _pct(revenue - cost, revenue),
        "orders_below_floor": below,
        "by_line": table(lines),
        "by_product": table(products),
        "by_theme": table(themes),
        "by_style": [{"key": k, "qty": n} for k, n in styles.most_common()],
        "by_addon": [{**row, "name_ar": names.get(row["key"], row["key"])} for row in table(addons)],
        "attach_rate_pct": _pct(Decimal(with_addon), Decimal(items)),
        "preview_to_purchase": [
            {"line": line, "books": n, "bought": b, "rate_pct": _pct(Decimal(b), Decimal(n))}
            for line, (n, b) in sorted(funnel.items())
        ],
        "ai_cost": [{"day": d.isoformat(), "usd": v.quantize(CENT)} for d, v in sorted(ai_cost.items())],
        "b2b": {
            "orders": len(b2b),
            "revenue_ils": sum((o.total * rate[o.currency] for o in b2b), Decimal("0")).quantize(CENT),
        },
        "b2c": {
            "orders": len(b2c),
            "revenue_ils": sum((o.total * rate[o.currency] for o in b2c), Decimal("0")).quantize(CENT),
        },
    }
