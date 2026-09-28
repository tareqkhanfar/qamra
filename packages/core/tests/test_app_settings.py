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
        ("image_provider", "flux", "flux"),
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
        ("company_name", "x\x07y"),
        ("anthropic_api_key", "multi\nline"),
        ("registration_open", "true"),
    ],
)
def test_invalid(key: str, raw: object) -> None:
    with pytest.raises(SettingError):
        validate(REGISTRY[key], raw)


def test_privacy_bounds_never_exceed_the_rules() -> None:
    assert REGISTRY["photo_retention_hours"].max == 24 and REGISTRY["draft_retention_days"].max == 30


def test_secrets_are_never_public() -> None:
    assert not [d.key for d in REGISTRY.values() if d.kind == "secret" and d.public]


def test_mask() -> None:
    assert mask("") == "" and mask("short") == "•••• " and mask("sk-ant-abcdefgh1234") == "•••• 1234"
