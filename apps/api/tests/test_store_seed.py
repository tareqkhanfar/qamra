from decimal import Decimal

from api_helpers import make_admin
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed_store import seed_store
from qamra_core.db.models import Currency
from qamra_core.db.store import AddOn, ArtStyle, PriceListItem, Variant, VariantPrice


async def _count(adb: AsyncSession, model: type) -> int:
    return int((await adb.execute(select(func.count()).select_from(model))).scalar_one())


async def test_seed_builds_the_catalog_once(adb: AsyncSession) -> None:
    added = await seed_store(adb)
    assert "+product:classic-book" in added and "+variant:wb-kg2-set-color-spiral" in added
    variants, addons = await _count(adb, Variant), await _count(adb, AddOn)
    # classic, magic, custom story, coloring, 2 class books, workbook (2 levels × 12), journey, family
    assert variants == 3 + 1 + 1 + 1 + 1 + 1 + 24 + 7 + 2
    assert addons == 19
    assert await seed_store(adb) == []  # insert-only: a second run changes nothing
    assert await _count(adb, Variant) == variants

    soft = (await adb.execute(select(Variant).where(Variant.sku == "classic-soft-21"))).scalar_one()
    prices = {
        p.currency: p.amount
        for p in (await adb.execute(select(VariantPrice).where(VariantPrice.variant_id == soft.id))).scalars()
    }
    assert prices == {Currency.ILS: Decimal("69.00"), Currency.JOD: Decimal("13.00")}

    styles = {s.slug: s for s in (await adb.execute(select(ArtStyle))).scalars()}
    assert {"watercolor", "cartoon", "3d", "semi-realistic", "coloring"} <= set(styles)
    assert styles["watercolor"].lines == ["magic", "classic"] and not styles["crayon"].active
    for style in styles.values():  # never a studio or artist name (Addendum 4 §2)
        assert not any(name in style.prompt.lower() for name in ("pixar", "disney", "ghibli", "dreamworks"))

    tiers = (await adb.execute(select(PriceListItem))).scalars().all()
    assert len(tiers) == 11 and any(t.tiers[-1] == {"min_qty": 100, "unit_price": "35.00"} for t in tiers)


async def test_edits_in_the_admin_survive_a_deploy(adb: AsyncSession) -> None:
    await seed_store(adb)
    soft = (await adb.execute(select(Variant).where(Variant.sku == "classic-soft-21"))).scalar_one()
    soft.cost_print_ils = Decimal("12.50")
    await adb.commit()
    await seed_store(adb)
    await adb.refresh(soft)
    assert soft.cost_print_ils == Decimal("12.50")


async def test_staff_roles_limit_the_admin(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb, email="support@example.com", roles=("support",))
    assert (await client.get("/api/admin/books")).status_code == 200  # support may view books
    assert (await client.get("/api/admin/settings")).status_code == 403  # but not settings
    assert (await client.get("/api/admin/metrics")).status_code == 403
    assert (
        await client.post("/api/admin/books/00000000-0000-0000-0000-000000000000/approve")
    ).status_code == 403


async def test_the_family_book_waits_for_approval_with_its_print_tiers(adb: AsyncSession) -> None:
    from qamra_core.db.store import CatalogProduct

    await seed_store(adb)
    family = (
        await adb.execute(select(CatalogProduct).where(CatalogProduct.slug == "family-adventures"))
    ).scalar_one()
    assert family.active is False  # on sale once the book is designed and the printer's prices are in
    wireo = (await adb.execute(select(Variant).where(Variant.sku == "family-wireo"))).scalar_one()
    assert [t["min_qty"] for t in wireo.print_cost_tiers] == [1, 10, 50, 100, 500]
    assert wireo.print_cost_tiers[2] == {"min_qty": 50, "unit_ils": "30.00", "estimated": True}  # ⚠
    gift = (await adb.execute(select(AddOn).where(AddOn.slug == "gift-box"))).scalar_one()
    assert "family" in gift.lines
