from api_helpers import make_admin, register
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_core.db.models import AppSetting, AuditLog


async def _make_admin(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)


async def test_admin_settings_forbidden_for_parents_and_anonymous(client: AsyncClient) -> None:
    assert (await client.get("/api/admin/settings")).status_code == 401
    await register(client)
    assert (await client.get("/api/admin/settings")).status_code == 403
    assert (
        await client.put("/api/admin/settings", json={"values": {"price_digital_ils": "1"}})
    ).status_code == 403


async def test_admin_reads_grouped_settings_with_examples(client: AsyncClient, adb: AsyncSession) -> None:
    await _make_admin(client, adb)
    view = (await client.get("/api/admin/settings")).json()
    groups = {g["id"]: g for g in view["groups"]}
    assert list(groups) == [
        "pricing",
        "contact",
        "site",
        "ai_keys",
        "ai_models",
        "quality",
        "print",
        "notifications",
        "privacy",
        "security",
    ]
    models = {s["key"]: s for s in groups["ai_models"]["settings"]}
    assert (
        models["image_provider"]["value"] == "fal"
        and models["fal_image_model"]["value"] == "fal-ai/nano-banana-2"
    )
    assert models["fal_fallback_model"]["label"] == "نموذج fal الاحتياطي"  # renamed from "FLUX model"
    assert models["text_model"]["value"] == "claude-sonnet-5"
    assert models["text_model_fast"]["value"] == "claude-haiku-4-5-20251001"
    quality = {s["key"]: s["value"] for s in groups["quality"]["settings"]}
    assert quality["book_budget_usd"] == "3.00" and quality["qa_threshold"] == 75
    hard = next(s for s in groups["pricing"]["settings"] if s["key"] == "price_hardcover_ils")
    assert hard["value"] == "119" and hard["is_example"] and not hard["configured"]
    key = next(s for s in groups["ai_keys"]["settings"] if s["key"] == "anthropic_api_key")
    assert key["kind"] == "secret" and key["value"] == "" and not key["configured"]


async def test_secret_is_encrypted_masked_and_never_logged(client: AsyncClient, adb: AsyncSession) -> None:
    await _make_admin(client, adb)
    secret = "sk-ant-api03-THIS-IS-A-TEST-KEY-9f3a"
    r = await client.put(
        "/api/admin/settings",
        json={"values": {"anthropic_api_key": secret, "support_whatsapp": "+970 59 123 4567"}},
    )
    assert r.status_code == 200, r.text
    key = next(s for g in r.json()["groups"] for s in g["settings"] if s["key"] == "anthropic_api_key")
    assert key["configured"] and key["value"] == "•••• 9f3a" and secret not in r.text
    row = await adb.get(AppSetting, "anthropic_api_key")
    assert (
        row is not None
        and row.value is None
        and row.secret_ciphertext
        and secret not in row.secret_ciphertext
    )
    audit = (
        await adb.execute(select(AuditLog).where(AuditLog.action == "admin.settings_updated"))
    ).scalar_one()
    assert audit.data == {"keys": ["anthropic_api_key", "support_whatsapp"]} and secret not in str(audit.data)
    public = (await client.get("/api/settings/public")).json()
    assert "anthropic_api_key" not in public and public["support_whatsapp"] == "+970591234567"
    # clearing a secret
    r = await client.put("/api/admin/settings", json={"values": {"anthropic_api_key": None}})
    key = next(s for g in r.json()["groups"] for s in g["settings"] if s["key"] == "anthropic_api_key")
    assert not key["configured"]


async def test_invalid_values_rejected_atomically(client: AsyncClient, adb: AsyncSession) -> None:
    await _make_admin(client, adb)
    for bad in (
        {"support_whatsapp": "call me"},
        {"instagram_url": "javascript:alert(1)"},
        {"photo_retention_hours": 48},
        {"price_digital_ils": "-3"},
        {"image_provider": "midjourney"},
        {"music_enabled": "yes"},
        {"not_a_setting": 1},
    ):
        r = await client.put("/api/admin/settings", json={"values": {"price_softcover_ils": "70", **bad}})
        assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_setting", bad
    assert await adb.get(AppSetting, "price_softcover_ils") is None  # nothing half-applied


async def test_public_settings_have_no_secrets(client: AsyncClient) -> None:
    public = (await client.get("/api/settings/public")).json()
    assert public["music_enabled"] is True and public["price_hardcover_ils"] == "119"
    assert not any(k.endswith(("_key", "_secret", "_password", "_token")) for k in public)


async def test_registration_can_be_closed(client: AsyncClient, adb: AsyncSession) -> None:
    await _make_admin(client, adb)
    await client.put("/api/admin/settings", json={"values": {"registration_open": False}})
    await client.post("/api/auth/logout")
    r = await client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "moonlight-2026", "full_name": "N"},
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "registration_closed"
