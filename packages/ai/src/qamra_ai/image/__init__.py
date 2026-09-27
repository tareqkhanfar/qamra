"""Image providers + factory."""

from qamra_ai.config import ImageProviderName, Settings
from qamra_ai.image.base import GeneratedImage, ImageProvider, ImageRequest, RefImage


def _secret(v: object) -> str | None:
    return v.get_secret_value() if v is not None else None  # type: ignore[attr-defined]


def make_image_provider(settings: Settings, name: ImageProviderName | None = None) -> ImageProvider:
    name = name or settings.image_provider
    if name == "gemini":
        from qamra_ai.image.gemini import GeminiImageProvider

        return GeminiImageProvider(
            _secret(settings.gemini_api_key),
            settings.gemini_image_model,
            settings.gemini_image_size,
        )
    if name == "flux":
        from qamra_ai.image.flux import FluxImageProvider

        return FluxImageProvider(_secret(settings.fal_key), settings.flux_image_model, settings.flux_image_px)
    if name == "openai":
        from qamra_ai.image.openai_image import OpenAIImageProvider

        return OpenAIImageProvider(
            _secret(settings.openai_api_key),
            settings.openai_image_model,
            settings.openai_image_quality,
            settings.openai_image_px,
        )
    from qamra_ai.image.fake import FakeImageProvider

    return FakeImageProvider()


__all__ = ["GeneratedImage", "ImageProvider", "ImageRequest", "RefImage", "make_image_provider"]
