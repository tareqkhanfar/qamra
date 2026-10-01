"""Activity books (Addendum 9): who can order what, and the order item for one of the parent's children."""

import uuid
from datetime import UTC, datetime

from api_helpers import make_admin, register
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import expand_variants, seed_store
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


def test_a_product_is_orderable_unless_the_admin_closes_it() -> None:
    for line in (ProductLine.workbook, ProductLine.journey, ProductLine.family):
        assert orderable(CatalogProduct(slug="x", line=line, features={}))
    assert orderable(CatalogProduct(slug="z", line=ProductLine.journey, features={"orderable": True}))
    assert not orderable(CatalogProduct(slug="w", line=ProductLine.family, features={"orderable": False}))


async def _hold_back(adb: AsyncSession, *slugs: str) -> None:
    """The seed sells everything (Tareq, 2026-09-30); this covers the admin switch that holds a product."""
    for slug in slugs:
        product = (await adb.execute(select(CatalogProduct).where(CatalogProduct.slug == slug))).scalar_one()
        product.features = {**product.features, "orderable": False}
    await adb.commit()


async def test_the_cart_refuses_what_is_not_orderable(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    await _hold_back(adb, "foundation-workbook", "learning-journey")
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


def test_the_matrix_marks_unrendered_volumes_inactive() -> None:
    rows = [
        {"volume": "1", "interior": "color", "format": "spiral", "price": {"ILS": 1}},
        {"volume": "2", "interior": "color", "format": "spiral", "price": {"ILS": 1}},
        {"volume": "3", "interior": "color", "format": "spiral", "price": {"ILS": 1}},
        {"volume": "set", "interior": "color", "format": "spiral", "price": {"ILS": 1}},
    ]
    matrix = {"levels": ["kg1", "kg2"], "rendered": {"kg1": [], "kg2": ["1", "2"]}, "rows": rows}
    got = {v["sku"]: v["active"] for v in expand_variants({"variant_matrix": matrix})}
    assert got["wb-kg2-v1-color-spiral"] and got["wb-kg2-v2-color-spiral"]
    assert not got["wb-kg2-v3-color-spiral"] and not got["wb-kg2-set-color-spiral"]
    assert not any(active for sku, active in got.items() if sku.startswith("wb-kg1-"))
    # without `rendered`, every row is inserted as before (active by default)
    plain = expand_variants({"variant_matrix": {"levels": ["kg1"], "rows": rows}})
    assert all("active" not in v for v in plain)


async def test_only_active_variants_are_listed_and_sold(client: AsyncClient, adb: AsyncSession) -> None:
    await seed_store(adb)
    products = {p["slug"]: p for p in (await client.get("/api/store/catalog")).json()["products"]}
    skus = {v["sku"] for v in products["foundation-workbook"]["variants"]}
    # every volume of both levels renders (2026-10-01), so both levels and their sets are sold
    assert {"wb-kg1-v1-color-spiral", "wb-kg2-v3-color-spiral", "wb-kg1-set-color-spiral"} <= skus
    journey = {v["sku"] for v in products["learning-journey"]["variants"]}
    assert {"journey-s2-spiral", "journey-s3-digital", "journey-set-spiral"} <= journey
    # a variant switched off (a volume that does not render) is neither listed nor sold
    await adb.execute(update(Variant).where(Variant.sku == "journey-s3-spiral").values(active=False))
    await adb.commit()
    products = {p["slug"]: p for p in (await client.get("/api/store/catalog")).json()["products"]}
    assert "journey-s3-spiral" not in {v["sku"] for v in products["learning-journey"]["variants"]}
    r = await client.post("/api/store/cart/items", json={"sku": "journey-s3-spiral"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "unknown_product"
    assert (await client.post("/api/store/cart/items", json={"sku": "journey-s2-spiral"})).status_code == 201


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
    await _hold_back(adb, "learning-journey")
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
