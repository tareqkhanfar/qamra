"""Payments: cash on delivery unchanged, the card gateway a disabled stub. Emails: checkout and the order's
status changes enqueue one email job each, on the worker's default queue; a Redis outage never breaks them."""

from api_helpers import complete_cart, make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_api.store.payments import CardGatewayStub, CashOnDelivery, provider_for
from qamra_core.db.models import Order, PaymentMethod, PaymentStatus

CHECKOUT = {
    "name": "أم ليان",
    "phone": "0591234567",
    "zone": "west-bank",
    "city": "البيرة",
    "address": "حي الجنان، قرب المسجد",
    "accept_terms": True,
}
EMAIL = "qamra_worker.jobs.notify.send_order_email"


async def _place(client: AsyncClient, adb: AsyncSession, **extra: object) -> AsyncClient:
    r = await client.post(
        "/api/store/cart/items", json={"sku": "classic-soft-21", "personalization": {"child_name": "ليان"}}
    )
    assert r.status_code == 201, r.text
    await complete_cart(adb)
    return await client.post("/api/store/checkout", json={**CHECKOUT, **extra})  # type: ignore[return-value]


def _emails(app: FastAPI) -> list[tuple[str, ...]]:
    return [
        tuple(j.args) for j in Queue("default", connection=app.state.rq_redis).jobs if j.func_name == EMAIL
    ]


async def test_only_cash_on_delivery_is_offered(client: AsyncClient) -> None:
    r = await client.get("/api/store/payment-methods")
    assert r.status_code == 200
    assert r.json() == [
        {"method": "cod", "enabled": True, "label_ar": "الدفع عند الاستلام", "label_en": "Cash on delivery"},
    ]  # the card gateway's seat is never listed
    assert isinstance(provider_for("cod"), CashOnDelivery) and CardGatewayStub.enabled is False


async def test_cash_on_delivery_is_unchanged_and_emails_the_customer(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await seed_store(adb)
    me = await register(client)
    r = await _place(client, adb)  # no `payment` field, exactly as the checkout form sends it today
    assert r.status_code == 201, r.text
    order = (await adb.execute(select(Order).where(Order.code == r.json()["code"]))).scalar_one()
    assert order.payment_method == PaymentMethod.cod and order.payment_status == PaymentStatus.unpaid
    assert order.user_id is not None and str(order.user_id) == me["id"]
    assert _emails(app) == [(str(order.id), "placed")]
    r = await _place(client, adb, payment="cod")
    assert r.status_code == 201 and len(_emails(app)) == 2


async def test_the_card_stub_is_refused_before_any_order(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await seed_store(adb)
    r = await _place(client, adb, payment="card")
    assert r.status_code == 409 and r.json()["error"]["code"] == "payment_unavailable"
    assert "البطاقة" in r.json()["error"]["message"]["ar"]
    assert (await adb.execute(select(func.count()).select_from(Order))).scalar_one() == 0 and _emails(
        app
    ) == []
    assert (await _place(client, adb, payment="bitcoin")).status_code == 422


async def test_status_changes_enqueue_the_customer_emails(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await seed_store(adb)
    await register(client, email="lian.mom@example.com")
    code = (await _place(client, adb)).json()["code"]
    order = (await adb.execute(select(Order).where(Order.code == code))).scalar_one()
    await make_admin(client, adb)
    for step in ("confirmed", "generating", "review", "printing", "shipped", "delivered"):
        r = await client.post(f"/api/admin/orders/{order.id}/status", json={"to": step})
        assert r.status_code == 200, r.text
    assert [e for _, e in _emails(app)] == ["placed", "confirmed", "printing", "shipped", "delivered"]


async def test_a_queue_outage_never_breaks_checkout(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await seed_store(adb)

    class Down:
        def __getattr__(self, name: str) -> object:
            raise ConnectionError("redis is down")

    app.state.rq_redis = Down()
    r = await _place(client, adb)
    assert r.status_code == 201, r.text
