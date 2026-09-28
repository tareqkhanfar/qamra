from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.seed import upsert_themes
from qamra_api.settings import ApiSettings


async def test_theme_list_sorted_with_status(client: AsyncClient, adb: AsyncSession) -> None:
    await upsert_themes(adb)
    r = await client.get("/api/themes", params={"lang": "ar"})
    assert r.status_code == 200
    cards = r.json()
    slugs = [c["slug"] for c in cards]
    assert slugs[:3] == ["first-day", "graduation", "new-sibling"]
    assert {c["status"] for c in cards[:3]} == {"available"}
    soon = [c for c in cards if c["status"] == "coming_soon"]
    assert len(soon) == 5 and all(c["pages"] > 0 for c in soon)
    first = cards[0]
    assert first["name"] == "أوّل يوم في الروضة" and first["pages"] == 12 and first["art"]["scene"] == "garden"
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
    assert [p["index"] for p in d["samples"]] == [1, 4, 8, 12]
    assert all("{" not in p["text"] and p["art"]["scene"] for p in d["samples"])
    soon = (await client.get("/api/themes/moon-trip")).json()
    assert soon["status"] == "coming_soon" and soon["samples"] == [] and soon["sample_name"] is None


async def test_unknown_theme_404(client: AsyncClient, adb: AsyncSession) -> None:
    await upsert_themes(adb)
    r = await client.get("/api/themes/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


async def test_seed_is_idempotent(adb: AsyncSession) -> None:
    first = await upsert_themes(adb)
    again = await upsert_themes(adb)
    assert all(s.startswith("+") for s in first) and all(s.startswith("~") for s in again)


async def test_pricing_examples_then_admin_values(
    client: AsyncClient, adb: AsyncSession, settings: ApiSettings
) -> None:
    from qamra_core import settings_store
    from qamra_core.crypto import cipher_for

    prices = (await client.get("/api/pricing")).json()
    assert [p["product"] for p in prices] == ["digital", "softcover", "hardcover"]
    assert [Decimal(p["amount"]) for p in prices] == [
        Decimal("49"),
        Decimal("89"),
        Decimal("119"),
    ]  # examples
    await settings_store.save(adb, cipher_for(settings), {"price_hardcover_ils": "125.50"}, None)
    hard = (await client.get("/api/pricing")).json()[2]
    assert Decimal(hard["amount"]) == Decimal("125.5") and hard["currency"] == "ILS"
    jod = (await client.get("/api/pricing", params={"currency": "JOD"})).json()
    assert jod[0]["currency"] == "JOD" and Decimal(jod[0]["amount"]) == Decimal("9")
