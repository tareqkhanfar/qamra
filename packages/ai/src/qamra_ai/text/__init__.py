"""Text providers + factory."""

from qamra_ai.config import Settings, TextProviderName
from qamra_ai.text.base import ImagePart, StructuredResult, TextProvider, UserPart


def make_text_provider(settings: Settings, name: TextProviderName | None = None) -> TextProvider:
    name = name or settings.text_provider
    if name == "anthropic":
        from qamra_ai.text.anthropic_provider import AnthropicTextProvider

        key = settings.anthropic_api_key.get_secret_value() if settings.anthropic_api_key else None
        return AnthropicTextProvider(key, settings.text_server_fallbacks)
    from qamra_ai.pipeline.fakes import default_fake_text_provider

    return default_fake_text_provider()


__all__ = ["ImagePart", "StructuredResult", "TextProvider", "UserPart", "make_text_provider"]
