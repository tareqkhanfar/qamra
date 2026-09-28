from decimal import Decimal

from api_helpers import make_admin
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_core.db.models import AuditLog
from qamra_core.db.store import CatalogProduct, Variant

QUOTE = {
    "tiers": [
        {"min_qty": 1, "unit_ils": "40"},
        {"min_qty": 10, "unit_ils": "34"},
        {"min_qty": 50, "unit_ils": "28"},
        {"min_qty": 100, "unit_ils": "25"},
        {"min_qty": 500, "unit_ils": "18.50"},
    ]
}


async def _on_sale(adb: AsyncSession) -> None:
    """The family book is seeded inactive until approval; these tests sell it."""
    await seed_store(adb)
    product = (
        await adb.execute(select(CatalogProduct).where(CatalogProduct.slug == "family-adventures"))
    ).scalar_one()
    product.active = True
    await adb.commit()


async def test_ten_copies_wait_for_the_printers_real_prices(client: AsyncClient, adb: AsyncSession) -> None:
    await _on_sale(adb)
    ten = await client.post("/api/store/cart/items", json={"sku": "family-wireo", "qty": 10})
    assert ten.status_code == 409 and ten.json()["error"]["code"] == "bulk_price_pending"
    nine = await client.post("/api/store/cart/items", json={"sku": "family-wireo", "qty": 9})
    assert nine.status_code == 201
    item = nine.json()["items"][0]
    assert Decimal(item["unit_price"]) == 89  # single copies sell at retail
    more = await client.patch(f"/api/store/cart/items/{item['id']}", json={"qty": 12})
    assert more.status_code == 409
    again = await client.post("/api/store/cart/items", json={"sku": "family-wireo", "qty": 1})
    assert again.status_code == 409  # 9 + 1 copies in two lines are still 10


async def test_saving_the_quote_clears_the_estimate_and_prices_ten_copies(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await _on_sale(adb)
    await make_admin(client, adb)
    listed = (await client.get("/api/admin/store/print-costs")).json()
    family = next(r for r in listed if r["sku"] == "family-wireo")
    assert family["estimated"] is True and [r["qty"] for r in family["table"]] == [1, 10, 50, 100, 500]

    bad = await client.put(
        "/api/admin/store/print-costs/family-wireo",
        json={"tiers": [{"min_qty": 1, "unit_ils": "30"}, {"min_qty": 10, "unit_ils": "35"}]},
    )
    assert bad.status_code == 422  # a longer run never costs more per copy
    saved = (await client.put("/api/admin/store/print-costs/family-wireo", json=QUOTE)).json()
    assert saved["estimated"] is False
    ten_row = next(r for r in saved["table"] if r["qty"] == 10)
    variant = (await adb.execute(select(Variant).where(Variant.sku == "family-wireo"))).scalar_one()
    await adb.refresh(variant)
    assert variant.cost_print_ils == 40
    log = (await adb.execute(select(AuditLog).where(AuditLog.action == "print_costs.saved"))).scalar_one()
    assert log.entity_id == "family-wireo"

    await client.post("/api/auth/logout")
    cart = await client.post("/api/store/cart/items", json={"sku": "family-wireo", "qty": 10})
    assert cart.status_code == 201, cart.text
    assert Decimal(cart.json()["items"][0]["unit_price"]) == Decimal(ten_row["price_ils"]) < 89


async def test_only_pricing_staff_enter_printer_prices(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    await make_admin(client, adb, email="help@example.com", roles=("support",))
    assert (await client.get("/api/admin/store/print-costs")).status_code == 403
