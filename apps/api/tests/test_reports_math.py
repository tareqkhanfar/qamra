from datetime import date
from decimal import Decimal

from qamra_api.reports import BookRow, ItemRow, OrderRow, summarize

GIFT = {"slug": "gift-box", "qty": 1, "included": False, "unit_price": "15.00", "name_ar": "علبة هدية"}
FREE = {"slug": "digital-copy", "qty": 1, "included": False, "unit_price": "0.00"}


def _item(sku: str, line: str, price: str, addons: list | None = None, qty: int = 1) -> ItemRow:  # type: ignore[type-arg]
    return ItemRow(
        sku=sku, line=line, product=sku.split("-")[0], theme="graduation", style="watercolor", qty=qty,
        unit_price=Decimal(price), discount=Decimal("0"), addons=addons or [],
    )  # fmt: skip


def test_revenue_margin_and_mix_in_shekels() -> None:
    orders = [
        OrderRow("QM-1", date(2026, 9, 1), "ILS", Decimal("104"), Decimal("30"), False,
                 [_item("classic-soft-21", "classic", "69", [GIFT, FREE])]),
        OrderRow("QM-2", date(2026, 9, 2), "JOD", Decimal("30"), Decimal("140"), True,
                 [_item("magic-hard-21", "magic", "27", qty=1)]),
    ]  # fmt: skip
    books = [BookRow("magic", True), BookRow("magic", False), BookRow("classic", False)]
    r = summarize(
        orders, books, {date(2026, 9, 1): Decimal("1.5")}, jod_ils=Decimal("5"), floor_pct=Decimal("35")
    )
    assert r["orders"] == 2 and r["revenue_ils"] == Decimal("254.00")  # 104 + 30 JD × 5
    assert r["aov_ils"] == Decimal("127.00") and r["cost_ils"] == Decimal("170.00")
    assert r["orders_below_floor"] == 1  # the JD order: (150 − 140) / 150 < 35%
    assert r["by_line"][0] == {"key": "magic", "qty": 1, "revenue_ils": Decimal("135.00")}
    assert r["by_addon"] == [
        {"key": "gift-box", "qty": 1, "revenue_ils": Decimal("15.00"), "name_ar": "علبة هدية"}
    ]
    assert r["attach_rate_pct"] == Decimal("50.0")  # a free add-on doesn't count
    assert r["preview_to_purchase"][1] == {
        "line": "magic",
        "books": 2,
        "bought": 1,
        "rate_pct": Decimal("50.0"),
    }
    assert r["b2b"]["orders"] == 1 and r["b2c"]["revenue_ils"] == Decimal("104.00")


def test_an_empty_period_has_no_divisions_by_zero() -> None:
    r = summarize([], [], {}, jod_ils=Decimal("5"), floor_pct=Decimal("35"))
    assert r["orders"] == 0 and r["aov_ils"] == 0 and r["margin_pct"] is None and r["attach_rate_pct"] is None
