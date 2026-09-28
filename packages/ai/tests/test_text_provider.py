import pytest
from tests_helpers import png

from qamra_ai.errors import ProviderConfigError
from qamra_ai.text.anthropic_provider import AnthropicTextProvider, supports_effort, supports_fallbacks
from qamra_ai.text.base import CACHE, ImagePart, SystemPart


@pytest.fixture
def provider() -> AnthropicTextProvider:
    return AnthropicTextProvider("sk-test-not-used", server_fallbacks=True)


def test_cache_breakpoints_are_placed(provider: AnthropicTextProvider) -> None:
    kw = provider.request(
        model="claude-haiku-4-5-20251001",
        system=[SystemPart("rules", cache=True), SystemPart("volatile")],
        user=[ImagePart(png(), "image/png"), "label", CACHE, ImagePart(png(), "image/png"), "brief"],
        max_tokens=1500,
        effort="medium",
    )
    system = kw["system"]
    assert system[0]["cache_control"] == {"type": "ephemeral"} and "cache_control" not in system[1]
    content = kw["messages"][0]["content"]
    assert [b["type"] for b in content] == ["image", "text", "image", "text"]
    assert content[1]["cache_control"] == {"type": "ephemeral"} and "cache_control" not in content[3]
    assert "output_config" not in kw  # no effort for Haiku 4.5


def test_effort_only_where_supported(provider: AnthropicTextProvider) -> None:
    kw = provider.request(model="claude-sonnet-5", system="s", user=["u"], max_tokens=100, effort="medium")
    assert kw["output_config"] == {"effort": "medium"} and kw["system"] == "s"
    assert supports_effort("claude-opus-5") and not supports_effort("claude-haiku-4-5-20251001")


def test_server_fallbacks_only_for_models_that_have_them() -> None:
    assert supports_fallbacks("claude-opus-5") and supports_fallbacks("claude-fable-5-1")
    assert not supports_fallbacks("claude-sonnet-5") and not supports_fallbacks("claude-haiku-4-5-20251001")


def test_too_many_breakpoints_rejected(provider: AnthropicTextProvider) -> None:
    with pytest.raises(ProviderConfigError):
        provider.request(
            model="claude-sonnet-5",
            system=[SystemPart("a", cache=True), SystemPart("b", cache=True)],
            user=["x", CACHE, "y", CACHE, "z", CACHE],
            max_tokens=10,
            effort=None,
        )


def test_missing_key() -> None:
    with pytest.raises(ProviderConfigError):
        AnthropicTextProvider(None)
