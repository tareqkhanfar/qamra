"""One tap adds any product to the cart, for guests too (Tareq, 2026-10-02). The line then waits for the
child: the create flow fills it (`item_id`), checkout refuses it until then, and signing in brings the guest
cart's lines into the parent's cart. A signed-out browser never reads a parent's cart through the cookie."""

import uuid
from typing import Any

import pytest
from api_helpers import register
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_api.settings import ApiSettings
from qamra_core.db.models import Order, OrderItem
from qamra_core.db.store import Cart, CartItem, CartStatus

CHECKOUT = {
    "name": "أم ليان",
    "phone": "+970 59 765 4321",
    "zone": "west-bank",
    "city": "البيرة",
    "address": "البالوع، قرب المسجد",
    "accept_terms": True,
}
FAMILY = {"name": "الخطيب", "city": "نابلس", "members": [{"relation": "mother", "name": "سارة"}]}


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings(
        _env_file=None,
        env="test",
        cookie_secure=False,
        log_json=False,  # type: ignore[call-arg]
        web_base_url="http://testserver",
        login_max_attempts=5,
        login_ip_max_attempts=20,
        settings_cache_seconds=0,
        e2e_fixtures=True,  # the children, characters and preview books come from the E2E fixtures
    )


@pytest.fixture(autouse=True)
async def _data(adb: AsyncSession) -> None:
    await upsert_themes(adb)
    await seed_store(adb)


async def _add(client: AsyncClient, sku: str, **extra: Any) -> dict[str, Any]:
    r = await client.post("/api/store/cart/items", json={"sku": sku, **extra})
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


async def _preview(client: AsyncClient, **body: Any) -> dict[str, Any]:
    r = await client.post("/api/e2e/books", json=body)
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


async def test_a_story_added_in_one_tap_gets_its_book_then_checks_out(
    client: AsyncClient, adb: AsyncSession
) -> None:
    cart = await _add(client, "classic-soft-21", theme="olive-season", style="watercolor")  # a guest
    line = cart["items"][0]
    assert line["needs_details"] and line["child_id"] is None and line["theme"] == "olive-season"
    r = await client.post("/api/store/checkout", json=CHECKOUT)
    assert r.status_code == 409 and r.json()["error"]["code"] == "details_missing"
    assert r.json()["error"]["details"]["items"] == [
        {"id": line["id"], "name_ar": "قمرة كلاسيك", "name_en": "Qamra Classic"}
    ]

    await register(client)  # «أكملوا بيانات الطفل» asks to sign in first; the guest cart comes along
    book = await _preview(client, line="classic", theme="olive-season")
    r = await client.post(
        f"/api/create/books/{book['book_id']}/cart",
        json={"sku": "classic-hard-21", "item_id": line["id"]},  # the parent picked another format
    )
    assert r.status_code == 201, r.text
    cart = r.json()
    assert [i["id"] for i in cart["items"]] == [line["id"]]  # filled, not a second line
    filled = cart["items"][0]
    assert filled["book_id"] == book["book_id"] and filled["child_id"] == book["child_id"]
    assert (
        filled["sku"] == "classic-hard-21" and filled["child_name"] == "ليان" and not filled["needs_details"]
    )

    r = await client.post("/api/store/checkout", json=CHECKOUT)
    assert r.status_code == 201, r.text
    order = (await adb.execute(select(Order).where(Order.code == r.json()["code"]))).scalar_one()
    item = (await adb.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalar_one()
    assert str(item.book_id) == book["book_id"] and str(item.child_id) == book["child_id"]
    assert item.theme_slug == "olive-season"


async def test_an_activity_book_added_in_one_tap_gets_the_child_and_keeps_the_family(
    client: AsyncClient, adb: AsyncSession
) -> None:
    cart = await _add(client, "family-wireo", family=FAMILY)
    line = cart["items"][0]
    assert line["needs_details"]
    other = (await _add(client, "journey-s1-spiral"))["items"][1]
    await register(client)
    child = (await _preview(client, name="كرم", gender="m"))["child_id"]

    wrong = await client.post(
        "/api/shop/workbooks/cart", json={"sku": "family-wireo", "child_id": child, "item_id": other["id"]}
    )
    assert wrong.status_code == 409 and wrong.json()["error"]["code"] == "item_mismatch"
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": "family-wireo", "child_id": child, "item_id": line["id"]}
    )
    assert r.status_code == 201, r.text
    cart = r.json()
    assert [i["id"] for i in cart["items"]] == [line["id"], other["id"]]
    assert cart["items"][0]["child_id"] == child and not cart["items"][0]["needs_details"]
    assert cart["items"][1]["needs_details"]  # still waiting: checkout names it
    row = await adb.get(CartItem, uuid.UUID(line["id"]))
    assert row is not None
    await adb.refresh(row)
    assert row.personalization["child_name"] == "كرم" and row.personalization["family"]["name"] == "الخطيب"
    assert row.personalization["family"]["members"][0]["role"] == "ماما"  # given on the product page

    r = await client.post("/api/store/checkout", json=CHECKOUT)
    assert r.status_code == 409 and [i["id"] for i in r.json()["error"]["details"]["items"]] == [other["id"]]
    await client.delete(f"/api/store/cart/items/{other['id']}")
    assert (await client.post("/api/store/checkout", json=CHECKOUT)).status_code == 201


async def test_only_the_owner_can_fill_a_line(client: AsyncClient, adb: AsyncSession, app: FastAPI) -> None:
    await register(client)
    line = (await _add(client, "journey-s1-spiral"))["items"][0]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", headers={"X-Qamra-Client": "test"}
    ) as stranger:
        await register(stranger, email="other.mom@example.com")
        child = (await _preview(stranger))["child_id"]
        book = (await _preview(stranger, child_id=child))["book_id"]
        r = await stranger.post(
            "/api/shop/workbooks/cart",
            json={"sku": "journey-s1-spiral", "child_id": child, "item_id": line["id"]},
        )
        assert r.status_code == 404
        r = await stranger.post(
            f"/api/create/books/{book}/cart", json={"sku": "classic-soft-21", "item_id": line["id"]}
        )
        assert r.status_code == 404
    row = await adb.get(CartItem, uuid.UUID(line["id"]))
    assert row is not None
    await adb.refresh(row)
    assert row.child_id is None and row.book_id is None


async def test_signing_in_brings_the_guest_lines_and_signing_out_hides_the_cart(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await register(client)
    mine = (await _add(client, "journey-s1-spiral"))["items"][0]["id"]
    await client.post("/api/auth/logout")

    # the cookie still points at the parent's cart: a signed-out browser must not read or change it
    assert (await client.get("/api/store/cart")).json()["count"] == 0
    assert (await client.delete(f"/api/store/cart/items/{mine}")).status_code == 404
    assert (await client.patch(f"/api/store/cart/items/{mine}", json={"qty": 2})).status_code == 404

    guest = await _add(client, "classic-soft-21", theme="moon-trip")
    guest = await _add(client, "wb-kg2-set-color-spiral")
    assert [i["sku"] for i in guest["items"]] == ["classic-soft-21", "wb-kg2-set-color-spiral"]
    guest_cart = (await adb.execute(select(Cart).where(Cart.user_id.is_(None)))).scalar_one()

    r = await client.post(
        "/api/auth/login", json={"email": "salma.mom@example.com", "password": "moonlight-2026"}
    )
    assert r.status_code == 200, r.text
    workbook = guest["items"][1]["id"]  # the first request after signing in brings the guest lines along
    r = await client.patch(f"/api/store/cart/items/{workbook}", json={"qty": 2})
    assert r.status_code == 200, r.text
    cart = (await client.get("/api/store/cart")).json()
    assert [i["sku"] for i in cart["items"]] == [
        "journey-s1-spiral",
        "classic-soft-21",
        "wb-kg2-set-color-spiral",
    ]
    assert cart["items"][0]["id"] == mine and cart["count"] == 4  # in the order they were added
    await adb.refresh(guest_cart)
    assert guest_cart.status == CartStatus.abandoned

    await client.post("/api/auth/logout")
    assert (await client.get("/api/store/cart")).json()["count"] == 0
