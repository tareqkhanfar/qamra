from decimal import Decimal

from api_helpers import make_admin
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store

CHECKOUT = {
    "name": "أم ليان",
    "phone": "+970 59 123 4567",
    "zone": "west-bank",
    "city": "البيرة",
    "address": "حي الجنان",
    "accept_terms": True,
}


async def test_reports_count_the_period_and_export_csv(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    item = {
        "sku": "classic-soft-21",
        "addons": [{"slug": "gift-box"}],
        "personalization": {"child_name": "ليان"},
    }
    assert (await client.post("/api/store/cart/items", json=item)).status_code == 201
    assert (await client.post("/api/store/checkout", json=CHECKOUT)).status_code == 201
    await make_admin(client, adb)
    r = (await client.get("/api/admin/reports", params={"days": 30})).json()
    assert r["orders"] == 1 and Decimal(r["revenue_ils"]) == 69 + 15 + 20
    assert r["by_addon"][0]["key"] == "gift-box" and Decimal(r["attach_rate_pct"]) == 100
    csv = await client.get("/api/admin/reports/orders.csv", params={"days": 30})
    assert csv.status_code == 200 and csv.text.startswith("﻿order,") and "البيرة" in csv.text
    items = await client.get("/api/admin/reports/items.csv")
    assert "classic-soft-21" in items.text and "علبة هدية" in items.text


async def test_only_report_staff_see_the_numbers(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb, email="edit@example.com", roles=("editor",))
    assert (await client.get("/api/admin/reports")).status_code == 403
