"""Addendum 9 order path through the API: the add-ons step, a cart of two books with add-ons priced by the DB
rules, the gift order and its packing slip, gift cards with a coupon, the cross-sell and character reuse.
Preview books come from the test-only fixtures (`/api/e2e/*`, placeholder art, no AI)."""

import asyncio
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from api_helpers import make_admin, open_jordan, register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from qamra_api.errors import ApiError
from qamra_api.print_batches import Candidate, build_manifest
from qamra_api.routers.create import CONSENT_VERSION
from qamra_api.seed import upsert_themes
from qamra_api.seed_store import seed_store
from qamra_api.settings import ApiSettings
from qamra_api.store import gift_cards
from qamra_core.db.models import AuditLog, Character, CharacterStatus, Currency, Order, OrderItem
from qamra_core.db.store import Coupon, CouponKind, GiftCard, GiftCardRedemption
from qamra_core.storage import ObjectStorage

FACE = Path(__file__).resolve().parents[3] / "packages/ai/tests/fixtures/face-astronaut-public-domain.png"
CHECKOUT = {
    "name": "أم ليان",
    "phone": "+970 59 765 4321",
    "zone": "west-bank",
    "city": "البيرة",
    "address": "البالوع، قرب المسجد",
    "accept_terms": True,
}
D = Decimal


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
        e2e_fixtures=True,  # this module creates its preview books through the E2E fixtures
    )


@pytest.fixture(autouse=True)
async def _data(adb: AsyncSession) -> None:
    await upsert_themes(adb)
    await seed_store(adb)


async def _book(client: AsyncClient, **body: Any) -> dict[str, Any]:
    r = await client.post("/api/e2e/books", json=body)
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


async def _to_cart(
    client: AsyncClient, book_id: str, sku: str, addons: list[str] | None = None
) -> dict[str, Any]:
    r = await client.post(
        f"/api/create/books/{book_id}/cart", json={"sku": sku, "addons": [{"slug": a} for a in addons or []]}
    )
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


def _line(cart: dict[str, Any], book_id: str) -> dict[str, Any]:
    return next(i for i in cart["items"] if i["book_id"] == book_id)


async def test_two_books_with_add_ons_match_the_db_rules(client: AsyncClient, adb: AsyncSession) -> None:
    await open_jordan(adb)  # the JD path, kept while Jordan is switched off
    await register(client)
    olive = await _book(client, name="ليان", line="classic", theme="olive-season", hijab=True)
    moon = await _book(client, child_id=olive["child_id"], line="magic", theme="moon-trip")
    assert moon["character_id"] == olive["character_id"] and moon["characters"] == 1  # reused, not redrawn

    cart = await _to_cart(client, olive["book_id"], "classic-soft-21")
    item = _line(cart, olive["book_id"])
    assert item["book_title"] == "ليان في موسم الزيتون" and item["book_status"] == "preview"
    step = (await client.get(f"/api/store/cart/items/{item['id']}/addons")).json()
    offered = {a["slug"]: a for a in step["addons"]}
    assert [s for s, a in offered.items() if a["featured"]] == [
        "hardcover-upgrade",
        "gift-box",
        "extra-copy",
        "coloring-version",
    ]
    assert {"family-voice", "cover-poster", "express"} <= {s for s, a in offered.items() if not a["featured"]}
    assert "dedication-page" not in offered and "digital-copy" not in offered  # other steps / automatic
    assert D(offered["extra-copy"]["price"]) == D("34.50") and offered["hardcover-upgrade"]["badge_ar"]

    r = await client.put(
        f"/api/store/cart/items/{item['id']}/addons",
        json={"addons": [{"slug": "gift-box"}, {"slug": "extra-copy"}]},
    )
    assert r.status_code == 200, r.text
    item = r.json()["item"]
    assert D(item["subtotal"]) == D("118.50")  # 69 + 15 + 34.50, computed by the server
    amounts = {a["slug"]: D(a["amount"]) for a in item["addons"]}
    assert amounts == {"gift-box": D("15"), "extra-copy": D("34.50"), "digital-copy": D("0")}

    cart = await _to_cart(client, moon["book_id"], "magic-hard-21")
    assert D(cart["subtotal"]) == D("257.50") and cart["count"] == 2
    assert cart["bundle"] == "two-books" and cart["bundle_name_ar"] == "الكتاب الثاني −15%"
    assert D(_line(cart, olive["book_id"])["discount"]) == D("10.35")  # the cheaper book, not its add-ons
    assert D(_line(cart, moon["book_id"])["discount"]) == 0
    assert D(cart["total"]) == D("247.15")

    # back to the format step: still one line for the book, and the add-ons that fit stay
    cart = await _to_cart(client, olive["book_id"], "classic-hard-21")
    item = _line(cart, olive["book_id"])
    assert cart["count"] == 2 and item["sku"] == "classic-hard-21"
    assert {a["slug"] for a in item["addons"]} >= {"gift-box", "extra-copy"}
    jod = (await client.put("/api/store/cart/zone", json={"zone": "amman"})).json()
    assert (
        jod["currency"] == "JOD" and D(jod["subtotal"]) == D("19") + 3 + D("9.50") + 27
    )  # the same rules in JD
    assert D(jod["bundle_discount"]) == D("2.85")  # 15% of 19 JD


async def test_add_on_dependencies_come_from_the_admin(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    r = await client.patch("/api/admin/catalog/addons/express", json={"needs": ["gift-box"]})
    assert r.status_code == 200 and r.json()["needs"] == ["gift-box"]
    bad = await client.patch("/api/admin/catalog/addons/express", json={"needs": ["express"]})
    assert bad.status_code == 422  # never itself, only add-ons that exist
    await client.patch("/api/admin/catalog/addons/family-voice", json={"needs": ["gift-box"]})
    await client.post("/api/auth/logout")

    await register(client, email="dep.mom@example.com")
    book = await _book(client)
    item = _line(await _to_cart(client, book["book_id"], "classic-soft-21"), book["book_id"])
    url = f"/api/store/cart/items/{item['id']}/addons"
    alone = await client.put(url, json={"addons": [{"slug": "express"}]})
    assert (
        alone.status_code == 422 and "express: needs gift-box" in alone.json()["error"]["details"]["problems"]
    )
    both = await client.put(url, json={"addons": [{"slug": "express"}, {"slug": "gift-box"}]})
    assert both.status_code == 200
    express = next(a for a in both.json()["addons"] if a["slug"] == "express")
    assert express["on"] and express["needs"] == ["gift-box"] and express["locked"] is None

    digital = await _book(client, child_id=book["child_id"], theme="first-day")
    line = _line(await _to_cart(client, digital["book_id"], "classic-digital"), digital["book_id"])
    offered = {
        a["slug"]: a
        for a in (await client.get(f"/api/store/cart/items/{line['id']}/addons")).json()["addons"]
    }
    assert "gift-box" not in offered  # a digital book has no box…
    assert offered["family-voice"]["locked"] == "needs" and offered["family-voice"]["blockers"] == [
        "gift-box"
    ]


async def test_a_gift_order_hides_prices_and_prints_the_message(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await register(client, email="gift.mom@example.com")
    book = await _book(client)
    await _to_cart(client, book["book_id"], "classic-soft-21", ["gift-box"])
    note = "  كل عام وأنتِ بطلة حكايتنا   يا ليان…  \n\n\n  من ماما  "
    cart = (await client.put("/api/store/cart/gift", json={"gift": True, "message": note})).json()
    assert cart["gift"] is True and cart["gift_message"] == "كل عام وأنتِ بطلة حكايتنا يا ليان…\n\nمن ماما"
    long = await client.put("/api/store/cart/gift", json={"gift": True, "message": "م" * 201})
    assert long.status_code == 422  # the card holds 200 characters
    off = (await client.put("/api/store/cart/gift", json={"gift": False})).json()
    assert off["gift"] is False and off["gift_message"] is None
    back = (await client.put("/api/store/cart/gift", json={"gift": True})).json()
    assert back["gift_message"] == cart["gift_message"]  # kept while it was off
    r = await client.post("/api/store/checkout", json=CHECKOUT)
    assert r.status_code == 201, r.text
    order = (await adb.execute(select(Order).where(Order.code == r.json()["code"]))).scalar_one()
    assert order.gift and order.gift_message == cart["gift_message"]

    items = list((await adb.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars())
    manifest = build_manifest([Candidate(order, items=items)], sends=1)
    assert manifest["items"][0]["gift"] is True and manifest["items"][0]["gift_message"] == order.gift_message

    await make_admin(client, adb)
    slip = (await client.get(f"/api/admin/orders/{order.id}/packing-slip")).json()
    assert slip["gift"] and slip["prices_hidden"] and slip["gift_message"] == order.gift_message
    assert slip["total"] is None and slip["subtotal"] is None and slip["payment_method"] is None
    assert all(i["unit_price"] is None and i["total"] is None for i in slip["items"])
    assert slip["items"][0]["book_title"] == "ليان في موسم الزيتون" and slip["recipient"]["name"] == "أم ليان"
    detail = (await client.get(f"/api/admin/orders/{order.id}")).json()
    assert detail["gift"] is True and detail["gift_message"] == order.gift_message

    order.gift = False  # the same order packed as a normal parcel shows its prices
    await adb.commit()
    plain = (await client.get(f"/api/admin/orders/{order.id}/packing-slip")).json()
    assert D(plain["total"]) == order.total and D(plain["items"][0]["unit_price"]) == 69


async def test_gift_cards_are_issued_by_staff_and_pay_after_the_coupon(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await open_jordan(adb)  # a JD cart refuses a ₪ card
    await make_admin(client, adb)
    issued = await client.post("/api/admin/gift-cards", json={"amount": "50", "note": "لعائلة ليان"})
    assert issued.status_code == 201, issued.text
    card = issued.json()
    assert card["code"].startswith("QG-") and len(card["code"]) == 17 and card["status"] == "active"
    listed = (await client.get("/api/admin/gift-cards")).json()
    assert [c["code"] for c in listed] == [card["code"]]
    log = (await adb.execute(select(AuditLog).where(AuditLog.action == "gift_card.issued"))).scalar_one()
    assert card["code"] not in str(log.data)  # never the spendable code in the log
    adb.add(Coupon(code="EID10", kind=CouponKind.percent, value=D("10"), per_customer=None))
    await adb.commit()
    await client.post("/api/auth/logout")

    await register(client, email="card.mom@example.com")
    book = await _book(client)
    await _to_cart(client, book["book_id"], "classic-soft-21")
    assert (await client.put("/api/store/cart/code", json={"code": "NOPE-1"})).status_code == 422
    assert (await client.put("/api/store/cart/code", json={"code": "QG-AAAA-BBBB-CCCC"})).status_code == 422
    cart = (await client.put("/api/store/cart/code", json={"code": "eid10"})).json()
    assert cart["coupon"] == "EID10" and D(cart["coupon_discount"]) == D("6.90")
    typed = card["code"].lower().replace("-", " ")  # dashes and spaces don't matter
    cart = (await client.put("/api/store/cart/code", json={"code": typed})).json()
    assert cart["gift_card"].endswith(card["code"][-4:]) and card["code"] not in str(cart)  # masked
    assert D(cart["gift_card_amount"]) == 50 and D(cart["total"]) == D("12.10")  # 62.10 − 50
    cart = (await client.put("/api/store/cart/zone", json={"zone": "amman"})).json()
    assert cart["gift_card_problem"] == "currency" and D(cart["gift_card_amount"]) == 0  # a ₪ card, a JD cart
    cart = (await client.put("/api/store/cart/zone", json={"zone": "west-bank"})).json()
    assert D(cart["total"]) == D("32.10")  # 62.10 + 20 delivery − 50

    placed = await client.post("/api/store/checkout", json=CHECKOUT)
    assert placed.status_code == 201, placed.text
    assert D(placed.json()["total"]) == D("32.10")
    row = await gift_cards.find(adb, card["code"])
    assert row is not None and row.balance == 0
    redemption = (await adb.execute(select(GiftCardRedemption))).scalar_one()
    order = (await adb.execute(select(Order).where(Order.code == placed.json()["code"]))).scalar_one()
    assert redemption.order_id == order.id and redemption.amount == 50
    assert order.pricing["gift_card_amount"] == "50.00" and order.discount == D("6.90")

    await _to_cart(client, book["book_id"], "classic-soft-21")  # a new cart: the card is spent
    cart = (await client.put("/api/store/cart/code", json={"code": card["code"]})).json()
    assert cart["gift_card_problem"] == "empty" and D(cart["total"]) == 69
    r = await client.post("/api/store/checkout", json=CHECKOUT)
    assert r.status_code == 422 and r.json()["error"]["code"] == "gift_card_invalid"
    await client.delete("/api/store/cart/gift-card")
    assert (await client.post("/api/store/checkout", json=CHECKOUT)).status_code == 201


async def test_a_card_can_be_switched_off(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    card = (await client.post("/api/admin/gift-cards", json={"amount": "30", "currency": "JOD"})).json()
    off = await client.patch(f"/api/admin/gift-cards/{card['id']}", json={"active": False})
    assert off.status_code == 200 and off.json()["status"] == "disabled"
    rule, _, problem = await gift_cards.card_rule(adb, card["code"], Currency.JOD)
    assert rule is None and problem == "disabled"


async def test_two_orders_can_never_spend_the_same_balance(migrated: str) -> None:
    """The conditional UPDATE under two real, concurrent transactions: one wins, the other is refused."""
    engine = create_async_engine(migrated, poolclass=NullPool)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    code = gift_cards.new_code()
    async with sessions() as db:
        card = GiftCard(code=code, currency=Currency.ILS, amount=D("50"), balance=D("50"), active=True)
        db.add(card)
        await db.commit()

    async def spend(delay: float) -> str:
        await asyncio.sleep(delay)
        async with sessions() as db:
            try:
                await gift_cards.redeem(db, card.id, D("50"))
            except ApiError as e:
                return e.code
            await asyncio.sleep(0.3)  # hold the row while the other one tries
            await db.commit()
            return "ok"

    try:
        results = await asyncio.gather(spend(0), spend(0.1))
        assert sorted(results) == ["gift_card_changed", "ok"]
        async with sessions() as db:
            left = (await db.execute(select(GiftCard.balance).where(GiftCard.id == card.id))).scalar_one()
            spent = (
                await db.execute(select(GiftCardRedemption).where(GiftCardRedemption.gift_card_id == card.id))
            ).all()
            assert left == 0 and len(spent) == 1
    finally:
        async with sessions() as db:
            await db.execute(delete(GiftCard).where(GiftCard.id == card.id))  # redemptions cascade
            await db.commit()
        await engine.dispose()


async def test_cross_sell_only_for_a_child_with_an_approved_character(
    client: AsyncClient, adb: AsyncSession
) -> None:
    assert (await client.get("/api/store/cart/cross-sell")).json() == []  # guests: nothing
    await register(client, email="cross.mom@example.com")
    book = await _book(client, name="ليان")
    await _to_cart(client, book["book_id"], "classic-soft-21")
    [offer] = (await client.get("/api/store/cart/cross-sell")).json()
    assert offer["child_name"] == "ليان" and offer["character_id"] == book["character_id"]
    assert offer["line"] == "classic" and offer["product"] == "classic-book" and D(offer["from_price"]) == 69
    character = await adb.get(Character, uuid.UUID(book["character_id"]))
    assert character is not None
    character.approved_at, character.status = None, CharacterStatus.ready
    await adb.commit()
    assert (await client.get("/api/store/cart/cross-sell")).json() == []


async def test_a_second_story_reuses_the_approved_character(
    client: AsyncClient, adb: AsyncSession, app: FastAPI, storage: ObjectStorage
) -> None:
    """Addendum 9 §6 through the real create API: the character is drawn once, then every book reuses it."""
    await register(client, email="reuse.mom@example.com")
    child = (await client.post("/api/create/children", json={"name": "كرم", "gender": "m", "age": 5})).json()
    await client.post(
        f"/api/create/children/{child['id']}/consent", json={"accept": True, "version": CONSENT_VERSION}
    )
    photo = await client.post(
        f"/api/create/children/{child['id']}/photos",
        files=[("photos", ("kid.png", FACE.read_bytes(), "image/png"))],
    )
    assert photo.status_code == 200, photo.text
    queue = Queue("generation", connection=app.state.rq_redis)
    first = (
        await client.post(f"/api/create/children/{child['id']}/characters", json={"style": "watercolor"})
    ).json()
    character = await adb.get(Character, uuid.UUID(first["id"]))
    assert character is not None
    character.sheet_image_key = f"children/{child['id']}/characters/{first['id']}.png"
    character.status = CharacterStatus.ready
    storage.put(character.sheet_image_key, FACE.read_bytes(), "image/png")
    await adb.commit()
    await client.post(f"/api/create/characters/{first['id']}/approve")
    drawn = [j.func_name for j in queue.jobs].count("qamra_worker.jobs.create.generate_character")

    again = await client.post(f"/api/create/children/{child['id']}/characters", json={"style": "watercolor"})
    assert again.json()["id"] == first["id"] and again.json()["approved"] is True  # the same one, as it is
    for theme in ("graduation", "first-day"):  # a first and a second story
        r = await client.post(
            "/api/create/books",
            json={"child_id": child["id"], "character_id": first["id"], "theme": theme, "line": "magic"},
        )
        assert r.status_code == 201, r.text
    jobs = [j.func_name for j in queue.jobs]
    assert jobs.count("qamra_worker.jobs.create.generate_character") == drawn  # never drawn again
    assert jobs.count("qamra_worker.jobs.books.generate_book") == 2
    count = (
        await adb.execute(select(Character.id).where(Character.child_id == uuid.UUID(child["id"])))
    ).all()
    assert len(count) == 1
