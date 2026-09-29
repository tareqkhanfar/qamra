"""Activity books (Addendum 9): who can order what, and the order item for one of the parent's children."""

import uuid
from datetime import UTC, datetime

from api_helpers import make_admin, register
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_api.store.workbooks import orderable
from qamra_core.db.models import AuditLog, Character, Child, Gender
from qamra_core.db.store import CartItem, CatalogProduct, ProductLine, Variant


async def _open_family(adb: AsyncSession) -> None:
    """The seed ships the family book switched off; the test server sells it."""
    product = (
        await adb.execute(select(CatalogProduct).where(CatalogProduct.slug == "family-adventures"))
    ).scalar_one()
    product.active = True
    await adb.execute(update(Variant).where(Variant.product_id == product.id).values(active=True))
    await adb.commit()


async def _child(adb: AsyncSession, user_id: str, *, approved: bool = True) -> Child:
    child = Child(
        guardian_user_id=uuid.UUID(user_id),
        first_name="ليان",
        gender=Gender.f,
        birth_year=2021,
        wears_hijab=True,
    )
    adb.add(child)
    await adb.flush()
    adb.add(
        Character(
            child_id=child.id,
            art_style="watercolor",
            approved_at=datetime.now(UTC) if approved else None,
        )
    )
    await adb.commit()
    return child


def test_the_educational_lines_wait_unless_switched_on() -> None:
    workbook = CatalogProduct(slug="x", line=ProductLine.workbook, features={})
    family = CatalogProduct(slug="y", line=ProductLine.family, features={})
    assert not orderable(workbook) and orderable(family)
    assert orderable(CatalogProduct(slug="z", line=ProductLine.journey, features={"orderable": True}))
    assert not orderable(CatalogProduct(slug="w", line=ProductLine.family, features={"orderable": False}))


async def test_the_cart_refuses_what_is_not_orderable(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    for sku in ("wb-kg2-v1-color-spiral", "journey-s1-spiral"):
        r = await client.post("/api/store/cart/items", json={"sku": sku})
        assert r.status_code == 409 and r.json()["error"]["code"] == "not_orderable"
    flags = (await client.get("/api/shop/summary")).json()["orderable"]
    assert flags["foundation-workbook"] is False and flags["classic-book"] is True

    await make_admin(client, adb)
    r = await client.put("/api/admin/shop/products/foundation-workbook/orderable", json={"orderable": True})
    assert r.status_code == 200 and r.json() == {"slug": "foundation-workbook", "orderable": True}
    audit = (
        await adb.execute(select(AuditLog).where(AuditLog.action == "admin.product_orderable"))
    ).scalar_one()
    assert audit.entity_id == "foundation-workbook" and audit.data == {"before": False, "after": True}
    assert (await client.get("/api/admin/shop/orderable")).json()["foundation-workbook"] is True
    r = await client.post("/api/store/cart/items", json={"sku": "wb-kg2-v1-color-spiral"})
    assert r.status_code == 201
    assert (
        await client.put("/api/admin/shop/products/nope/orderable", json={"orderable": True})
    ).status_code == 404


async def test_only_catalog_staff_open_products(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    await make_admin(client, adb, email="support@example.com", roles=("support",))
    r = await client.put("/api/admin/shop/products/learning-journey/orderable", json={"orderable": True})
    assert r.status_code == 403


async def test_a_workbook_for_my_child_with_the_approved_character(
    client: AsyncClient, adb: AsyncSession
) -> None:
    await seed_store(adb)
    await _open_family(adb)
    body = {"sku": "family-wireo", "child_id": str(uuid.uuid4())}
    assert (await client.post("/api/shop/workbooks/cart", json=body)).status_code == 401

    me = await register(client, email="mom@example.com")
    mine = await _child(adb, me["id"])
    r = await client.post("/api/shop/workbooks/cart", json={**body, "child_id": str(mine.id)})
    assert r.status_code == 201, r.text
    assert r.json()["count"] == 1
    item = (await adb.execute(select(CartItem).where(CartItem.child_id == mine.id))).scalar_one()
    character = (await adb.execute(select(Character).where(Character.child_id == mine.id))).scalar_one()
    assert item.personalization["child_name"] == "ليان" and item.personalization["hijab"] is True
    assert item.personalization["character_id"] == str(character.id)

    r = await client.post("/api/shop/workbooks/cart", json={**body, "child_id": str(mine.id), "qty": 10})
    assert r.status_code == 409 and r.json()["error"]["code"] == "bulk_price_pending"
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": "classic-soft-21", "child_id": str(mine.id)}
    )
    assert r.status_code == 404  # stories go through the create flow, not here
    r = await client.post(
        "/api/shop/workbooks/cart", json={"sku": "journey-s1-spiral", "child_id": str(mine.id)}
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "not_orderable"

    drafting = await _child(adb, me["id"], approved=False)
    r = await client.post("/api/shop/workbooks/cart", json={**body, "child_id": str(drafting.id)})
    assert r.status_code == 409 and r.json()["error"]["code"] == "character_not_approved"

    await client.post("/api/auth/logout")
    other = await register(client, email="other@example.com")
    assert other["id"] != me["id"]
    r = await client.post("/api/shop/workbooks/cart", json={**body, "child_id": str(mine.id)})
    assert r.status_code == 404  # another family's child
