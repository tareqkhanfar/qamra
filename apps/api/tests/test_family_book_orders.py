"""«مغامراتي مع عائلتي» in the store: confirming an order with a family book starts its print files (the
worker draws them from the plan with the child's approved character), and the family details the parent
gives with the book (the family's name, city and members) are checked and kept on the item for the book."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from api_helpers import make_admin, register
from fastapi import FastAPI
from httpx import AsyncClient
from rq import Queue
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_core.db.models import (
    Character,
    Child,
    Currency,
    Gender,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
)
from qamra_core.db.store import CartItem, CatalogProduct, Variant

FAMILY_JOB = "qamra_worker.jobs.family_book.render_order_family_items"


async def _order(adb: AsyncSession, parent_id: str, code: str, line: str) -> Order:
    order = Order(
        code=code,
        user_id=uuid.UUID(parent_id),
        status=OrderStatus.new,
        payment_method=PaymentMethod.cod,
        currency=Currency.ILS,
        subtotal=Decimal("89"),
        total=Decimal("89"),
        shipping={"name": "أم ليان", "city": "البيرة", "phone": "0591234567", "address": "حي الجنان"},
        phone="0591234567",
    )
    adb.add(order)
    await adb.flush()
    adb.add(
        OrderItem(
            order_id=order.id,
            sku=f"{line}-book",
            line=line,
            title={"name_ar": "مغامراتي مع عائلتي", "options": {"format": "spiral", "size": "21x28"}},
            personalization={"child_name": "ليان"},
            quantity=1,
            unit_price=Decimal("89"),
        )
    )
    await adb.commit()
    return order


async def test_confirming_a_family_book_order_starts_its_print_files(
    client: AsyncClient, adb: AsyncSession, app: FastAPI
) -> None:
    await seed_store(adb)
    parent = await register(client)
    family = await _order(adb, parent["id"], "QM-FAMBOOK", "family")
    story = await _order(adb, parent["id"], "QM-STORYBK", "magic")
    await make_admin(client, adb)
    queue = Queue("generation", connection=app.state.rq_redis)
    for order in (family, story):
        r = await client.post(f"/api/admin/orders/{order.id}/status", json={"to": "confirmed"})
        assert r.status_code == 200, r.text
    jobs = [(j.func_name, tuple(j.args)) for j in queue.jobs]
    assert (FAMILY_JOB, (str(family.id),)) in jobs
    assert all(args != (str(story.id),) for name, args in jobs if name == FAMILY_JOB)  # only family orders


async def _sell_family(adb: AsyncSession, parent_id: str) -> Child:
    """The seed ships the family book switched off; the test server sells it. A child with a character."""
    product = (
        await adb.execute(select(CatalogProduct).where(CatalogProduct.slug == "family-adventures"))
    ).scalar_one()
    product.active = True
    await adb.execute(update(Variant).where(Variant.product_id == product.id).values(active=True))
    child = Child(guardian_user_id=uuid.UUID(parent_id), first_name="ليان", gender=Gender.f, birth_year=2021)
    adb.add(child)
    await adb.flush()
    adb.add(Character(child_id=child.id, art_style="watercolor", approved_at=datetime.now(UTC)))
    await adb.commit()
    return child


async def test_the_family_details_come_with_the_book(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    parent = await register(client, email="mom@example.com")
    child = await _sell_family(adb, parent["id"])
    family = {
        "name": "الخطيب",
        "city": "رام الله",
        "members": [
            {"relation": "grandmother", "name": "  أم   خليل ", "scarf": True},
            {"relation": "brother", "name": "كرم"},
            {"relation": "other", "adult": False},
        ],
    }
    body = {"sku": "family-wireo", "child_id": str(child.id), "family": family}
    r = await client.post("/api/shop/workbooks/cart", json=body)
    assert r.status_code == 201, r.text
    item = (await adb.execute(select(CartItem).where(CartItem.child_id == child.id))).scalar_one()
    kept = item.personalization["family"]
    assert (kept["name"], kept["city"]) == ("الخطيب", "رام الله")
    assert [(m["role"], m["name"], m["adult"]) for m in kept["members"]] == [
        ("ستّي", "أم خليل", True),
        ("أخي", "كرم", False),
        ("من العائلة", "", False),
    ]
    assert kept["members"][0]["scarf"] is True and "photo" not in str(kept)

    for bad in (
        {**family, "name": "www.example.com"},  # no links
        {**family, "members": [{"relation": "mother", "name": "0599 123 456"}]},  # no numbers
        {**family, "members": [{"relation": "mother", "name": "{child}"}]},  # nothing like a template
        {**family, "members": [{"relation": "mother"}] * 7},  # at most six
        {**family, "members": [{"relation": "neighbour"}]},  # a relation from the list
        {**family, "members": [{"relation": "mother", "name": "ن" * 21}]},  # a first name
    ):
        r = await client.post("/api/shop/workbooks/cart", json={**body, "family": bad})
        assert r.status_code == 422, bad
    r = await client.post("/api/shop/workbooks/cart", json={"sku": "family-wireo", "child_id": str(child.id)})
    assert r.status_code == 201  # the details are optional: the book then has one neutral grown-up
