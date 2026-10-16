"""«إخفاء الأسعار» (Tareq, 2026-10-16): while `show_prices` is off no customer response carries a price; the
admin keeps every price, and orders still record them from the price list."""

import json
from decimal import Decimal
from typing import Any
from urllib.parse import unquote

import pytest
from api_helpers import complete_cart, make_admin, sell_every_addon
from httpx import AsyncClient
from portal_helpers import approved_school
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.price_visibility import is_price_key, strip_prices
from qamra_api.routers.admin_orders import whatsapp_links
from qamra_api.seed_store import seed_store
from qamra_core.app_settings import _DEFS
from qamra_core.db.models import AppSetting, Order

CHECKOUT = {
    "name": "أم ليان",
    "phone": "+970 59 123 4567",
    "zone": "west-bank",
    "city": "البيرة",
    "address": "حي الجنان، قرب المسجد",
    "accept_terms": True,
}
# what a customer must never see while the prices are hidden (keys at any depth)
MONEY_KEYS = {
    "price",
    "from_price",
    "price_modifier",
    "currency",
    "fee",
    "cod_fee",
    "free_over",
    "unit_price",
    "base",
    "addons_total",
    "discount",
    "total",
    "subtotal",
    "sale_discount",
    "bundle_discount",
    "coupon_discount",
    "shipping",
    "gift_card_amount",
    "amount",
    "percent",
    "class_book_from",
    "price_softcover_ils",
    "delivery_fee_ils",
}


def keys(data: Any) -> set[str]:
    """Every key in a JSON document, at any depth."""
    if isinstance(data, dict):
        return set(data) | {k for v in data.values() for k in keys(v)}
    if isinstance(data, list):
        return {k for v in data for k in keys(v)}
    return set()


async def _show(adb: AsyncSession, on: bool) -> None:
    row = await adb.get(AppSetting, "show_prices") or AppSetting(key="show_prices")
    row.value = on
    adb.add(row)
    await adb.commit()


@pytest.fixture(autouse=True)
async def _catalog(adb: AsyncSession) -> None:
    await seed_store(adb)


async def _customer_journey(client: AsyncClient, adb: AsyncSession) -> dict[str, Any]:
    """The responses a customer meets from the catalog to tracking the order."""
    out: dict[str, Any] = {
        "settings": (await client.get("/api/settings/public")).json(),
        "catalog": (await client.get("/api/store/catalog")).json(),
        "pricing": (await client.get("/api/pricing")).json(),
        "summary": (await client.get("/api/shop/summary")).json(),
    }
    r = await client.post(
        "/api/store/cart/items", json={"sku": "classic-soft-21", "personalization": {"child_name": "ليان"}}
    )
    assert r.status_code == 201, r.text
    out["add"] = r.json()
    out["addons"] = (await client.get(f"/api/store/cart/items/{r.json()['items'][0]['id']}/addons")).json()
    out["zone"] = (await client.put("/api/store/cart/zone", json={"zone": "west-bank"})).json()
    await complete_cart(adb)
    out["cart"] = (await client.get("/api/store/cart")).json()
    placed = await client.post("/api/store/checkout", json=CHECKOUT)
    assert placed.status_code == 201, placed.text
    out["placed"] = placed.json()
    out["track"] = (
        await client.get(f"/api/store/orders/{placed.json()['code']}", params={"phone": "0591234567"})
    ).json()
    return out


def test_prices_are_hidden_until_the_admin_shows_them() -> None:
    show = next(d for d in _DEFS if d.key == "show_prices")
    assert show.default is False and show.public and show.group == "pricing"


async def test_while_hidden_no_customer_response_carries_a_price(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await _show(adb, False)
    seen = await _customer_journey(client, adb)
    for name, body in seen.items():
        leaked = keys(body) & MONEY_KEYS
        assert not leaked, f"{name}: {leaked}"
    assert seen["settings"]["show_prices"] is False and "support_whatsapp" in seen["settings"]
    assert not any(k.startswith(("price_", "delivery_fee_")) for k in seen["settings"])
    assert seen["pricing"] == []
    # the rest of each answer is intact: the products, the cart line, the order code and its progress
    classic = next(p for p in seen["catalog"]["products"] if p["slug"] == "classic-book")
    assert classic["variants"] and all("sku" in v for v in classic["variants"])
    assert seen["cart"]["count"] == 1 and seen["cart"]["items"][0]["child_name"] == "ليان"
    assert seen["placed"]["code"].startswith("QM-") and seen["track"]["status"] == "new"

    # the order still records the price from the price list, and the admin sees it
    order = (await adb.execute(select(Order).where(Order.code == seen["placed"]["code"]))).scalar_one()
    assert order.total == Decimal("69") + 20
    await make_admin(client, adb)
    detail = (await client.get(f"/api/admin/orders/{order.id}")).json()
    assert Decimal(detail["total"]) == order.total and detail["currency"] == "ILS"
    admin_settings = (await client.get("/api/admin/settings")).json()
    pricing = next(g for g in admin_settings["groups"] if g["id"] == "pricing")
    by_key = {s["key"]: s for s in pricing["settings"]}
    assert by_key["show_prices"]["value"] is False and Decimal(by_key["price_hardcover_ils"]["value"]) > 0

    # the packing slip goes in the box: no prices on it either; WhatsApp tells the parent to pay in cash
    slip = (await client.get(f"/api/admin/orders/{order.id}/packing-slip")).json()
    assert slip["prices_hidden"] and slip["total"] is None and slip["items"][0]["unit_price"] is None
    shipped = unquote(detail["messages"]["shipped"].split("text=", 1)[1])
    assert "₪" not in shipped and "المبلغ" not in shipped and "الدفع نقدًا عند الاستلام" in shipped


async def test_shown_again_every_price_comes_back(client: AsyncClient, adb: AsyncSession) -> None:
    await _show(adb, True)
    seen = await _customer_journey(client, adb)
    assert seen["settings"]["show_prices"] is True and Decimal(seen["settings"]["price_hardcover_ils"]) > 0
    classic = next(p for p in seen["catalog"]["products"] if p["slug"] == "classic-book")
    assert Decimal(classic["from_price"]) == 19 and seen["catalog"]["currency"] == "ILS"
    assert {p["product"] for p in seen["pricing"]} == {"digital", "softcover", "hardcover"}
    assert Decimal(seen["cart"]["total"]) == Decimal("69") + 20 and seen["cart"]["currency"] == "ILS"
    assert Decimal(seen["placed"]["total"]) == Decimal("89") and Decimal(seen["track"]["total"]) == Decimal(
        "89"
    )
    assert {"total", "subtotal", "unit_price"} <= keys(seen["cart"])


async def test_the_switch_takes_effect_without_a_deploy(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    r = await client.put("/api/admin/settings", json={"values": {"show_prices": True}})
    assert r.status_code == 200, r.text
    assert "from_price" in keys((await client.get("/api/store/catalog")).json())
    r = await client.put("/api/admin/settings", json={"values": {"show_prices": False}})
    assert r.status_code == 200, r.text
    assert not keys((await client.get("/api/store/catalog")).json()) & MONEY_KEYS
    # staff screens keep their prices whatever the switch says
    products = (await client.get("/api/admin/catalog")).json()
    assert "price" in str(products)


async def test_the_school_invoice_waits_while_prices_are_hidden(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await approved_school(client, adb)
    await _show(adb, False)
    r = await client.get("/api/portal/orders/QM-NOPE00/invoice.pdf")
    assert r.status_code == 404
    await _show(adb, True)
    r = await client.get("/api/portal/orders/QM-NOPE00/invoice.pdf")
    assert r.status_code == 404  # an unknown order: the route itself answers again


def test_only_money_is_stripped() -> None:
    quote = {
        "currency": "ILS",
        "product": "classic-class-book",
        "copies": 24,
        "tiers": [{"min_qty": 10, "unit_price": "35.00"}],
        "price_list": "روضات 2026",
        "unit_price": "35.00",
        "subtotal": "840.00",
        "discount": "0",
        "shipping": "0.00",
        "total": "840.00",
        "delivery": {"name": "روضة القمر", "city": "رام الله"},
        "notes": [],
    }
    assert strip_prices(quote) == {
        "product": "classic-class-book",
        "copies": 24,
        "tiers": [{"min_qty": 10}],
        "delivery": {"name": "روضة القمر", "city": "رام الله"},
        "notes": [],
    }
    # counts named like money stay: a voice invite's pages, a download's parts
    assert strip_prices({"total": 3, "parts_total": 2, "done": 1}) == {
        "total": 3,
        "parts_total": 2,
        "done": 1,
    }
    assert not is_price_key("show_prices", False) and not is_price_key("prices_hidden", True)
    assert is_price_key("amount", None) and is_price_key("percent", "10.00") and not is_price_key("amount", 2)


async def test_catalog_wording_about_price_is_swapped_while_hidden(
    client: AsyncClient, adb: AsyncSession
) -> None:
    """«نفس الكتاب بنص السعر تقريبًا», «نسخة رقمية مجانية مع المطبوع», the «توفير» badge: the catalog's own
    words give the price away: customers read content/store/no_price_wording.yaml while prices are hidden."""
    await sell_every_addon(adb)  # the seed keeps some switched off; every add-on's words are checked
    await _show(adb, False)
    addons = {a["slug"]: a for a in (await client.get("/api/store/catalog")).json()["addons"]}
    extra, digital = addons["extra-copy"], addons["digital-copy"]
    assert extra["description_ar"] == "نسخة أخرى من الكتاب نفسه، للإهداء أو للاحتفاظ بها" and extra["description_en"]
    assert digital["name_ar"] == "نسخة رقمية مع المطبوع" and "Free" not in digital["name_en"]
    words = json.dumps(addons, ensure_ascii=False)
    assert not any(w in words for w in ("السعر", "مجاني", "توفير", "price", "Free", "Save"))
    await _show(adb, True)
    addons = {a["slug"]: a for a in (await client.get("/api/store/catalog")).json()["addons"]}
    assert addons["extra-copy"]["description_ar"] == "نفس الكتاب بنص السعر تقريبًا"  # the admin's words again


def test_whatsapp_keeps_the_total_only_while_prices_are_shown() -> None:
    from qamra_core.db.models import Currency

    order = Order(code="QM-WA0001", phone="0591234567", currency=Currency.ILS, total=Decimal("89"))
    order.shipping = {"name": "أم ليان"}
    shown = unquote(whatsapp_links(order, show_prices=True)["shipped"].split("text=", 1)[1])
    hidden = unquote(whatsapp_links(order, show_prices=False)["shipped"].split("text=", 1)[1])
    assert "89 ₪" in shown and "₪" not in hidden and "89" not in hidden
    assert "QM-WA0001" in hidden
