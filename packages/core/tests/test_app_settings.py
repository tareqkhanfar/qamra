import pytest

from qamra_core.app_settings import REGISTRY, SettingError, mask, validate


@pytest.mark.parametrize(
    ("key", "raw", "expected"),
    [
        ("price_digital_ils", "49", "49"),
        ("price_digital_ils", 49.5, "49.5"),
        ("support_whatsapp", "+970 (59) 123-4567", "+970591234567"),
        ("instagram_url", "https://instagram.com/qamra", "https://instagram.com/qamra"),
        ("instagram_url", "", ""),
        ("music_volume", 30, 30),
        ("image_provider", "fal", "fal"),
        ("print_spine_mm", "7.25", "7.2"),
        ("book_budget_usd", "3.5", "3.5"),
        ("admin_ip_allowlist", " 203.0.113.7 , 10.0.0.0/8 ", "203.0.113.7/32, 10.0.0.0/8"),
        ("final_mode", "2k_upscale", "2k_upscale"),
        ("anthropic_api_key", "  sk-ant-123  ", "sk-ant-123"),
    ],
)
def test_valid(key: str, raw: object, expected: object) -> None:
    assert validate(REGISTRY[key], raw) == expected


@pytest.mark.parametrize(
    ("key", "raw"),
    [
        ("price_digital_ils", "abc"),
        ("price_digital_ils", "-1"),
        ("price_digital_ils", "NaN"),
        ("support_whatsapp", "12"),
        ("support_email", "not-an-email"),
        ("instagram_url", "http://insecure.example"),
        ("instagram_url", "javascript:alert(1)"),
        ("music_volume", 101),
        ("music_volume", True),
        ("photo_retention_hours", 25),
        ("draft_retention_days", 31),
        ("image_provider", "other"),
        ("image_provider", "flux"),  # the FLUX adapter became the generic fal provider (fallback model)
        ("admin_ip_allowlist", "not-an-ip"),
        ("book_budget_usd", "0.1"),
        ("qa_threshold", 20),
        ("page_max_regenerations", 5),
        ("company_name", "x\x07y"),
        ("anthropic_api_key", "multi\nline"),
        ("registration_open", "true"),
    ],
)
def test_invalid(key: str, raw: object) -> None:
    with pytest.raises(SettingError):
        validate(REGISTRY[key], raw)


def test_addendum_3_defaults() -> None:
    d = {k: REGISTRY[k].default for k in REGISTRY}
    assert d["image_provider"] == "fal" and d["fal_image_model"] == "fal-ai/nano-banana-2"
    assert d["fal_fallback_model"] == "fal-ai/flux-2-pro/edit" and "flux_image_model" not in d
    assert d["text_model"] == "claude-sonnet-5" and d["text_model_fast"] == "claude-haiku-4-5-20251001"
    assert d["page_max_regenerations"] == 2 and d["book_budget_usd"] == "3.00" and d["image_concurrency"] == 4
    assert d["preview_resolution"] == "0.5K" and d["final_mode"] == "1k_upscale"


def test_privacy_bounds_never_exceed_the_rules() -> None:
    assert REGISTRY["photo_retention_hours"].max == 24 and REGISTRY["draft_retention_days"].max == 30


def test_secrets_are_never_public() -> None:
    assert not [d.key for d in REGISTRY.values() if d.kind == "secret" and d.public]


def test_mask() -> None:
    assert mask("") == "" and mask("short") == "•••• " and mask("sk-ant-abcdefgh1234") == "•••• 1234"
