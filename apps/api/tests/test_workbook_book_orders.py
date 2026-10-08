"""«دوسية التأسيس» in the admin (order flows §d chunk 10): confirming an order with a workbook item starts its
print files (the worker draws each volume from its plan with the child's name and character, no AI cost), and
the admin's retry of a workbook book runs the workbook job again for its order item."""

import uuid
from decimal import Decimal

from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_core.db.models import (
    Book,
    BookStatus,
    Child,
    Currency,
    Gender,
    Locale,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Theme,
    User,
)

ORDER_JOB = "qamra_worker.jobs.workbook_book.render_order_workbook_items"
ITEM_JOB = "qamra_worker.jobs.workbook_book.render_workbook_item"


async def _order(adb: AsyncSession, parent_id: str, code: str, line: str, sku: str) -> Order:
    order = Order(
        code=code,
        user_id=uuid.UUID(parent_id),
        status=OrderStatus.new,
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("69"),
        total=Decimal("69"),
        shipping={"name": "أم رؤى", "city": "البيرة", "phone": "0591234567", "address": "حي الجنان"},
        phone="0591234567",
    )
    adb.add(order)
    await adb.flush()
    adb.add(
        OrderItem(
            order_id=order.id,
            sku=sku,
            line=line,
            title={
                "name_ar": "دوسية التأسيس",
                "options": {"level": "kg2", "volume": "1", "interior": "color", "format": "spiral"},
            },
            personalization={"child_name": "رؤى", "name_en": "Roua"},
            quantity=1,
            unit_price=Decimal("69"),
        )
    )
    await adb.commit()
    return order


async def test_confirming_a_workbook_order_starts_its_volumes(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await seed_store(adb)
    parent = await register(client)
    workbook = await _order(adb, parent["id"], "QM-WBOOK1", "workbook", "wb-kg2-v1-color-spiral")
    journey = await _order(adb, parent["id"], "QM-JRNY01", "journey", "journey-s1-spiral")
    await make_admin(client, adb)
    for order in (workbook, journey):
        r = await client.post(f"/api/admin/orders/{order.id}/status", json={"to": "confirmed"})
        assert r.status_code == 200, r.text
    jobs = [(j.func_name, tuple(j.args)) for j in Queue("generation", connection=app.state.rq_redis).jobs]
    assert (ORDER_JOB, (str(workbook.id),)) in jobs
    assert all(args != (str(journey.id),) for name, args in jobs if name == ORDER_JOB)  # workbook orders only


async def test_the_admin_retry_runs_the_workbook_job_and_shows_the_variant(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await make_admin(client, adb)
    owner = (await adb.execute(select(User).where(User.email == "admin@example.com"))).scalar_one()
    child = Child(guardian_user_id=owner.id, first_name="رؤى", gender=Gender.f, birth_year=2021)
    adb.add(child)
    theme = Theme(
        slug="foundation-workbook",
        title_ar="دوسية التأسيس",
        title_en="x",
        age_min=4,
        age_max=6,
        definition={},
    )
    adb.add(theme)
    await adb.flush()
    item_id = str(uuid.uuid4())
    book = Book(
        child_id=child.id,
        theme_id=theme.id,
        theme_version=1,
        language=Locale.ar,
        art_style="3d",
        status=BookStatus.failed,
        title="دوسية رؤى — KG2 — الجزء الأول",
        generation={
            "line": "workbook",
            "order_item_id": item_id,
            "level": "kg2",
            "volume": 1,
            "name_en": "Roua",
        },
        flags=["name_en_guessed"],
    )
    adb.add(book)
    await adb.commit()
    detail = (await client.get(f"/api/admin/books/{book.id}")).json()
    assert detail["generation"]["level"] == "kg2" and detail["generation"]["volume"] == 1
    assert detail["generation"]["name_en"] == "Roua" and detail["flags"] == ["name_en_guessed"]
    r = await client.post(f"/api/admin/books/{book.id}/generate", json={"mode": "final"})
    assert r.status_code == 202, r.text
    jobs = [(j.func_name, tuple(j.args)) for j in Queue("generation", connection=app.state.rq_redis).jobs]
    assert jobs[-1] == (ITEM_JOB, (item_id,))
