from decimal import Decimal

from api_helpers import make_admin, sell_every_addon
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_core.db.models import AuditLog


def _row(catalog: dict, sku: str) -> dict:  # type: ignore[type-arg]
    return next(v for v in catalog["variants"] if v["sku"] == sku)


async def test_every_variant_shows_its_cost_and_margin(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    await make_admin(client, adb)
    catalog = (await client.get("/api/admin/catalog")).json()
    soft = _row(catalog, "classic-soft-21")
    cost = Decimal("14") + Decimal("3") + (Decimal("0.35") * Decimal("3.70")).quantize(Decimal("0.01"))
    assert Decimal(soft["price_ils"]) == 69 and Decimal(soft["unit_cost_ils"]) == cost
    assert Decimal(soft["margin_ils"]) == 69 - cost and soft["below_floor"] is False
    family = _row(catalog, "family-wireo")  # on sale since 2026-09-30; the printer quote is an estimate
    assert family["product_active"] is True and family["printer_estimated"] is True
    assert _row(catalog, "wb-kg1-v1-color-spiral")["active"] is True  # every volume renders (2026-10-01)
    assert any(a["slug"] == "gift-box" for a in catalog["addons"]) and catalog["zones"]


async def test_a_price_edit_reaches_the_store_and_is_audited(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    await make_admin(client, adb)
    r = await client.patch("/api/admin/catalog/variants/classic-soft-21", json={"price_ils": "79"})
    assert r.status_code == 200 and Decimal(r.json()["price_ils"]) == 79
    store = (await client.get("/api/store/catalog")).json()
    classic = next(p for p in store["products"] if p["slug"] == "classic-book")
    assert any(Decimal(v["price"]) == 79 for v in classic["variants"] if v["sku"] == "classic-soft-21")
    costly = await client.patch("/api/admin/catalog/variants/classic-soft-21", json={"cost_print_ils": "60"})
    assert costly.json()["below_floor"] is True  # (79 − 64.30) / 79 < 35%
    logs = (await adb.execute(select(AuditLog).where(AuditLog.action == "catalog.variant.updated"))).scalars()
    assert len(list(logs)) == 2
    zone = await client.patch(
        "/api/admin/catalog/zones/west-bank", json={"fee": "25", "clear_free_over": True}
    )
    assert Decimal(zone.json()["fee"]) == 25 and zone.json()["free_over"] is None


async def test_coupons_and_sales_are_created_and_switched_off(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    await make_admin(client, adb)
    coupon = {"code": "family10", "kind": "percent", "value": "10"}
    assert (await client.post("/api/admin/catalog/coupons", json=coupon)).status_code == 201
    again = await client.post("/api/admin/catalog/coupons", json=coupon)
    assert again.status_code == 409 and again.json()["error"]["code"] == "coupon_exists"
    off = await client.patch("/api/admin/catalog/coupons/FAMILY10", json={"active": False})
    assert off.json()["active"] is False
    fixed = await client.post(
        "/api/admin/catalog/coupons", json={"code": "TEN", "kind": "fixed", "value": "10"}
    )
    assert fixed.status_code == 422  # a fixed amount needs its currency
    sale = await client.post(
        "/api/admin/catalog/sales",
        json={
            "name_ar": "صيف العيلة",
            "name_en": "Family summer",
            "discount_pct": "15",
            "lines": ["family"],
            "starts_at": "2027-06-15T00:00:00Z",
            "ends_at": "2027-08-31T23:59:00Z",
        },
    )
    assert sale.status_code == 201 and sale.json()["kind"] == "sale"


async def test_the_simulator_runs_the_store_pricing_with_costs(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await seed_store(adb)
    await sell_every_addon(adb)  # the gift box is switched off in the seed (no stock)
    await make_admin(client, adb)
    r = await client.post(
        "/api/admin/catalog/simulate",
        json={"zone": "west-bank", "items": [{"sku": "classic-soft-21", "addons": [{"slug": "gift-box"}]}]},
    )
    assert r.status_code == 200, r.text
    sim = r.json()
    assert Decimal(sim["subtotal"]) == 69 + 15 and Decimal(sim["shipping"]) == 20
    assert Decimal(sim["cost_ils"]) > 0 and Decimal(sim["margin_ils"]) == Decimal(sim["total_ils"]) - Decimal(
        sim["cost_ils"]
    )


async def test_catalog_edits_need_the_right_role(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    await make_admin(client, adb, email="help@example.com", roles=("support",))
    assert (await client.get("/api/admin/catalog")).status_code == 403
    edit = await client.patch("/api/admin/catalog/variants/classic-soft-21", json={"price_ils": "1"})
    assert edit.status_code == 403
