from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_core.db.models import Currency, Order, OrderItem, OrderStatus
from qamra_core.db.store import AddOn, Coupon, CouponKind, CouponRedemption, OrderEvent

CHECKOUT = {
    "name": "أم ليان",
    "phone": "+970 59 123 4567",
    "zone": "west-bank",
    "city": "البيرة",
    "address": "حي الجنان، قرب المسجد",
    "accept_terms": True,
}


@pytest.fixture(autouse=True)
async def _catalog(adb: AsyncSession) -> None:
    await seed_store(adb)


async def _add(client: AsyncClient, sku: str, **extra: object) -> dict:  # type: ignore[type-arg]
    r = await client.post("/api/store/cart/items", json={"sku": sku, **extra})
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


async def test_catalog_lists_public_products_with_prices(client: AsyncClient) -> None:
    ils = (await client.get("/api/store/catalog")).json()
    slugs = [p["slug"] for p in ils["products"]]
    assert "classic-book" in slugs and "learning-journey" in slugs
    assert "classic-class-book" not in slugs  # B2B products are sold through price lists
    classic = next(p for p in ils["products"] if p["slug"] == "classic-book")
    assert Decimal(classic["from_price"]) == 19
    jod = (await client.get("/api/store/catalog", params={"currency": "JOD"})).json()
    assert Decimal(next(p for p in jod["products"] if p["slug"] == "classic-book")["from_price"]) == 4
    assert {s["slug"] for s in ils["styles"]} == {"watercolor", "cartoon", "3d", "semi-realistic", "coloring"}


async def test_guest_cart_prices_add_ons_bundles_and_shipping(client: AsyncClient) -> None:
    cart = await _add(
        client,
        "classic-soft-21",
        style="watercolor",
        theme="graduation",
        addons=[{"slug": "gift-box"}],
        personalization={"child_name": "ليان", "gender": "f", "age": 6, "hijab": True},
    )
    assert "qamra_cart" in client.cookies  # guests keep their cart in a cookie
    item = cart["items"][0]
    assert item["child_name"] == "ليان" and Decimal(item["unit_price"]) == 69
    assert {a["slug"] for a in item["addons"]} == {"gift-box", "digital-copy"}  # the free digital copy
    assert Decimal(cart["total"]) == 84
    cart = await _add(client, "magic-hard-21", personalization={"child_name": "كرم", "gender": "m", "age": 4})
    assert cart["bundle"] == "siblings" and Decimal(cart["bundle_discount"]) == Decimal("41.60")
    cart = (await client.put("/api/store/cart/zone", json={"zone": "west-bank"})).json()
    assert Decimal(cart["shipping"]) == 20 and Decimal(cart["total"]) == Decimal("201.40")  # 181.40 + 20
    first = cart["items"][0]["id"]
    r = await client.patch(
        f"/api/store/cart/items/{first}", json={"addons": [{"slug": "gift-box"}, {"slug": "cover-poster"}]}
    )
    cart = r.json()
    assert Decimal(cart["shipping"]) == 0 and Decimal(cart["total"]) == Decimal("206.40")  # over 200 ₪: free


async def test_add_on_rules_are_enforced(client: AsyncClient) -> None:
    r = await client.post(
        "/api/store/cart/items", json={"sku": "classic-hard-21", "addons": [{"slug": "hardcover-upgrade"}]}
    )
    assert (
        r.status_code == 422
        and "hardcover-upgrade: needs format softcover" in r.json()["error"]["details"]["problems"]
    )
    r = await client.post(
        "/api/store/cart/items",
        json={"sku": "classic-soft-21", "addons": [{"slug": "extra-character", "qty": 4}]},
    )
    assert r.status_code == 422
    r = await client.post("/api/store/cart/items", json={"sku": "class-classic-soft-21"})
    assert r.status_code == 404  # B2B products aren't in the public store
    r = await client.post("/api/store/cart/items", json={"sku": "classic-soft-21", "style": "3d"})
    assert r.status_code == 422  # 3D is sold in Magic only, until Classic templates exist


async def test_checkout_freezes_prices_and_costs(client: AsyncClient, adb: AsyncSession) -> None:
    adb.add(Coupon(code="EID10", kind=CouponKind.percent, value=Decimal("10"), first_order_only=True))
    await adb.commit()
    await _add(client, "classic-soft-21", personalization={"child_name": "ليان"})
    cart = (await client.put("/api/store/cart/coupon", json={"code": "eid10"})).json()
    assert cart["coupon"] == "EID10" and Decimal(cart["coupon_discount"]) == Decimal("6.90")
    r = await client.post("/api/store/checkout", json=CHECKOUT)
    assert r.status_code == 201, r.text
    placed = r.json()
    assert placed["code"].startswith("QM-") and Decimal(placed["total"]) == Decimal("62.10") + 20
    assert "qamra_cart" not in client.cookies  # the cart is done
    order = (await adb.execute(select(Order).where(Order.code == placed["code"]))).scalar_one()
    assert (
        order.status == OrderStatus.new
        and order.currency == Currency.ILS
        and order.phone == CHECKOUT["phone"]
    )
    assert order.pricing["coupon"] == "EID10" and order.cost_ils > 0
    line = (await adb.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalar_one()
    assert line.sku == "classic-soft-21" and line.unit_price == 69 and line.discount == Decimal("6.90")
    assert line.costs["print"] == "14.00" and line.title["name_ar"] == "قمرة كلاسيك"
    digital = next(a for a in line.addons if a["slug"] == "digital-copy")
    assert digital["unit_price"] == "0.00" and digital["name_ar"]  # names and prices frozen for invoices
    assert (await adb.execute(select(CouponRedemption))).scalar_one().phone == CHECKOUT["phone"]
    assert (await adb.execute(select(OrderEvent))).scalar_one().to_status == OrderStatus.new

    # the same phone can't use a first-order coupon twice
    await _add(client, "classic-soft-21")
    cart = (await client.put("/api/store/cart/coupon", json={"code": "EID10"})).json()
    r = await client.post("/api/store/checkout", json=CHECKOUT)
    assert r.status_code == 422 and r.json()["error"]["details"]["problem"] == "first_order_only"


async def test_tracking_needs_the_code_and_the_phone(client: AsyncClient) -> None:
    await _add(client, "classic-soft-21", personalization={"child_name": "ليان"})
    code = (await client.post("/api/store/checkout", json=CHECKOUT)).json()["code"]
    ok = await client.get(f"/api/store/orders/{code}", params={"phone": "0591234567"})
    assert (
        ok.status_code == 200
        and ok.json()["status"] == "new"
        and ok.json()["items"][0]["child_name"] == "ليان"
    )
    wrong = await client.get(f"/api/store/orders/{code}", params={"phone": "0599999999"})
    assert wrong.status_code == 404


async def test_express_production_is_capacity_limited(client: AsyncClient, adb: AsyncSession) -> None:
    express = (await adb.execute(select(AddOn).where(AddOn.slug == "express"))).scalar_one()
    express.daily_capacity = 0
    await adb.commit()
    await _add(client, "classic-soft-21", addons=[{"slug": "express"}])
    r = await client.post("/api/store/checkout", json=CHECKOUT)
    assert r.status_code == 409 and r.json()["error"]["code"] == "express_full"


async def test_jordan_pays_in_dinars(client: AsyncClient) -> None:
    await _add(client, "classic-soft-21")
    cart = (await client.put("/api/store/cart/zone", json={"zone": "amman"})).json()
    assert cart["currency"] == "JOD" and Decimal(cart["items"][0]["unit_price"]) == 13
    assert Decimal(cart["shipping"]) == 3
