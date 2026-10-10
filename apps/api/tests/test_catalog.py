from decimal import Decimal
from pathlib import Path

import yaml
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_ai.pipeline.theme import CONTENT_DIR
from qamra_api.seed import upsert_themes


async def test_theme_list_sorted_with_status(client: AsyncClient, adb: AsyncSession) -> None:
    await upsert_themes(adb)
    r = await client.get("/api/themes", params={"lang": "ar"})
    assert r.status_code == 200
    cards = r.json()
    slugs = [c["slug"] for c in cards]
    assert slugs[:3] == ["first-day", "graduation", "new-sibling"]
    assert {c["status"] for c in cards[:3]} == {"available"}
    # every story is written and on sale (owner, 2026-10-09), olive season among them
    assert {c["status"] for c in cards} == {"available"} and len(cards) == 8
    olive = next(c for c in cards if c["slug"] == "olive-season")
    assert olive["name"] == "موسم الزيتون" and 16 < olive["pages"] <= 28 and olive["classic"] == {}
    first = cards[0]
    assert first["name"] == "أوّل يوم في الروضة" and first["pages"] == 24 and first["art"]["scene"] == "garden"
    en = (await client.get("/api/themes", params={"lang": "en"})).json()
    assert en[0]["name"] == "First Day at Kindergarten"


async def test_theme_detail_peek_uses_real_story_text(client: AsyncClient, adb: AsyncSession) -> None:
    await upsert_themes(adb)
    d = (await client.get("/api/themes/graduation")).json()
    assert d["tag"] == "kindergarten" and d["values"][0] == "الاعتزاز بالنفس"
    kinds = [p["kind"] for p in d["peek"]]
    assert kinds == ["art", "text", "art", "art"]
    text = d["peek"][1]["text"]
    assert "ليان" in text and "{" not in text and "[" not in text
    assert d["sample_name"] == "ليان"
    assert [p["index"] for p in d["samples"]] == [1, 6, 11, 17]  # beginning, middle, end
    assert all("{" not in p["text"] and p["art"]["scene"] for p in d["samples"])
    olive = (await client.get("/api/themes/olive-season")).json()
    assert olive["status"] == "available" and olive["sample_name"] and olive["values"][0] == "حبّ الأرض"
    assert len(olive["samples"]) == 4 and all("{" not in p["text"] for p in olive["samples"])


async def test_a_story_still_being_written_is_listed_as_coming_soon(
    client: AsyncClient, adb: AsyncSession, tmp_path: Path
) -> None:
    """A stub (catalog only, no pages) loads as coming soon: no samples, no sample child."""
    stub = tmp_path / "themes" / "next-story"
    stub.mkdir(parents=True)
    data = yaml.safe_load((CONTENT_DIR / "themes/olive-season/theme.yaml").read_text(encoding="utf-8"))
    data = {k: v for k, v in data.items() if k not in ("pages", "cover", "for_parents", "cast")}
    data["slug"], data["catalog"]["status"] = "next-story", "coming_soon"
    data["catalog"].pop("sample_child", None)
    (stub / "theme.yaml").write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    await upsert_themes(adb, tmp_path)
    soon = (await client.get("/api/themes/next-story")).json()
    assert soon["status"] == "coming_soon" and soon["samples"] == [] and soon["sample_name"] is None


async def test_unknown_theme_404(client: AsyncClient, adb: AsyncSession) -> None:
    await upsert_themes(adb)
    r = await client.get("/api/themes/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


async def test_seed_is_idempotent(adb: AsyncSession) -> None:
    first = await upsert_themes(adb)
    again = await upsert_themes(adb)
    assert all(s.startswith("+") for s in first) and all(s.startswith("~") for s in again)


async def test_pricing_comes_from_the_catalog(client: AsyncClient, adb: AsyncSession) -> None:
    from sqlalchemy import select

    from qamra_api.seed_store import seed_store
    from qamra_core.db.models import Currency
    from qamra_core.db.store import Variant, VariantPrice

    await seed_store(adb)
    prices = (await client.get("/api/pricing")).json()
    assert [p["product"] for p in prices] == ["digital", "softcover", "hardcover"]
    assert [Decimal(p["amount"]) for p in prices] == [Decimal("19"), Decimal("69"), Decimal("99")]
    hard = (await adb.execute(select(Variant).where(Variant.sku == "classic-hard-21"))).scalar_one()
    row = await adb.get(VariantPrice, (hard.id, Currency.ILS))
    assert row is not None
    row.amount = Decimal("125.50")  # an admin edit shows up at once
    await adb.commit()
    hard_price = (await client.get("/api/pricing")).json()[2]
    assert Decimal(hard_price["amount"]) == Decimal("125.5") and hard_price["currency"] == "ILS"
    jod = (await client.get("/api/pricing", params={"currency": "JOD"})).json()
    assert jod[0]["currency"] == "JOD" and Decimal(jod[0]["amount"]) == Decimal("4")
