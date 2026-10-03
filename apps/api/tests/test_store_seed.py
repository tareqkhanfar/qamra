from decimal import Decimal
from pathlib import Path
from typing import Any

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
    # classic, magic, custom story, coloring, 2 class books, workbook (2 levels × 12), journey, family, and
    # «قلبي يعرف الله» (6 books printed and as PDFs, 3 printed sets)
    assert variants == 3 + 1 + 1 + 1 + 1 + 1 + 24 + 7 + 2 + 15
    assert addons == 20
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
    assert styles["watercolor"].lines[:2] == ["magic", "classic"] and not styles["crayon"].active
    assert "family" in styles["3d"].lines  # 3D for the activity books too (Tareq, 2026-10-02)
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


async def test_the_family_book_is_sold_with_its_print_tiers_marked_estimated(adb: AsyncSession) -> None:
    from qamra_core.db.store import CatalogProduct

    await seed_store(adb)
    family = (
        await adb.execute(select(CatalogProduct).where(CatalogProduct.slug == "family-adventures"))
    ).scalar_one()
    assert (
        family.active is True
    )  # the book is designed and reviewed (Tareq, 2026-09-30); the tiers stay ⚠ estimates
    wireo = (await adb.execute(select(Variant).where(Variant.sku == "family-wireo"))).scalar_one()
    assert [t["min_qty"] for t in wireo.print_cost_tiers] == [1, 10, 50, 100, 500]
    assert wireo.print_cost_tiers[2] == {"min_qty": 50, "unit_ils": "30.00", "estimated": True}  # ⚠
    gift = (await adb.execute(select(AddOn).where(AddOn.slug == "gift-box"))).scalar_one()
    assert "family" in gift.lines


async def test_the_language_pass_reaches_existing_rows_but_not_admin_edits(adb: AsyncSession) -> None:
    """Migration 3f7ceee7a4df: the seed is insert-only, so the corrected text is written onto old rows."""
    import importlib.util

    import yaml

    from qamra_api.seed_store import CATALOG
    from qamra_api.store.quiz import QUIZ_KEY, seed_rules
    from qamra_core import migrations
    from qamra_core.db.models import AppSetting
    from qamra_core.db.store import CatalogProduct

    path = next((Path(migrations.__file__).parent / "versions").glob("*_3f7ceee7a4df_*.py"))
    spec = importlib.util.spec_from_file_location("language_pass", path)
    assert spec is not None and spec.loader is not None
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)

    # the new text is exactly what the catalog seeds today
    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    by_slug = {e["slug"]: e for e in catalog["products"] + catalog["addons"]}
    for slug, column, _old, new in mig.PRODUCTS + mig.ADDONS:
        assert by_slug[slug][column] == new, (slug, column)

    await seed_store(adb)
    models: dict[str, Any] = {"products": CatalogProduct, "addons": AddOn}

    async def row(table: str, slug: str) -> Any:
        model = models[table]
        return (await adb.execute(select(model).where(model.slug == slug))).scalar_one()

    # a database seeded before the language pass, where an admin has since rewritten one description
    changes = [("products", *c) for c in mig.PRODUCTS] + [("addons", *c) for c in mig.ADDONS]
    for table, slug, column, old, _new in changes:
        setattr(await row(table, slug), column, old)
    poster = await row("addons", "cover-poster")
    poster.description_ar = "بوستر بحجم A3"
    quiz = await adb.get(AppSetting, QUIZ_KEY)
    assert quiz is not None
    old_quiz = seed_rules().model_dump(mode="json")
    mig.rewrite_quiz(old_quiz, forward=False)
    quiz.value = old_quiz
    await adb.commit()

    async def run(forward: bool) -> None:
        await adb.run_sync(lambda s: mig.apply(s.connection(), forward=forward))
        adb.expire_all()

    await run(forward=True)
    for table, slug, column, _old, new in changes:
        if slug != "cover-poster":
            assert getattr(await row(table, slug), column) == new, (slug, column)
    assert (await row("addons", "cover-poster")).description_ar == "بوستر بحجم A3"  # the admin's edit stays
    quiz = await adb.get(AppSetting, QUIZ_KEY)
    assert quiz is not None and quiz.value == seed_rules().model_dump(mode="json")

    await run(forward=False)
    for table, slug, column, old, _new in changes:
        if slug != "cover-poster":
            assert getattr(await row(table, slug), column) == old, (slug, column)
    quiz = await adb.get(AppSetting, QUIZ_KEY)
    assert quiz is not None and quiz.value == old_quiz
