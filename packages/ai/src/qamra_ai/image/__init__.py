"""Image providers, upscalers + factories (provider/model choice comes from admin settings)."""

from qamra_ai.config import ImageProviderName, Settings
from qamra_ai.image.base import GeneratedImage, ImageProvider, ImageRequest, RefImage
from qamra_ai.image.fallback import FallbackImageProvider
from qamra_ai.image.upscale import LocalUpscaler, Upscaler


def _secret(v: object) -> str | None:
    return v.get_secret_value() if v is not None else None  # type: ignore[attr-defined]


def _single(settings: Settings, name: ImageProviderName) -> ImageProvider:
    if name == "fal":
        from qamra_ai.image.fal import FalImageProvider

        return FalImageProvider(_secret(settings.fal_key), settings.fal_image_model)
    if name == "gemini":
        from qamra_ai.image.gemini import GeminiImageProvider

        return GeminiImageProvider(
            _secret(settings.gemini_api_key), settings.gemini_image_model, settings.gemini_image_size
        )
    if name == "openai":
        from qamra_ai.image.openai_image import OpenAIImageProvider

        return OpenAIImageProvider(
            _secret(settings.openai_api_key), settings.openai_image_model, settings.openai_image_quality
        )
    if name == "sketch":
        from qamra_ai.image.sketch import SketchImageProvider

        return SketchImageProvider()
    from qamra_ai.image.fake import FakeImageProvider

    return FakeImageProvider()


def make_image_provider(settings: Settings, name: ImageProviderName | None = None) -> FallbackImageProvider:
    """Primary provider wrapped with the fal fallback (Addendum 3 §1).

    The fallback is the fal fallback model whenever a fal key is set, whatever the primary is; offline
    providers (fake, sketch) run without one.
    """
    name = name or settings.image_provider
    primary = _single(settings, name)
    fallback: ImageProvider | None = None
    if name not in ("fake", "sketch") and settings.fal_key and settings.fal_fallback_model:
        from qamra_ai.image.fal import FalImageProvider

        if not (name == "fal" and settings.fal_fallback_model == settings.fal_image_model):
            fallback = FalImageProvider(_secret(settings.fal_key), settings.fal_fallback_model)
    return FallbackImageProvider(primary, fallback, switch_after=settings.fallback_after_failures)


def make_upscaler(settings: Settings, name: ImageProviderName | None = None) -> Upscaler:
    name = name or settings.image_provider
    if name in ("fake", "sketch") or not settings.fal_key or not settings.fal_upscale_model:
        return LocalUpscaler()
    from qamra_ai.image.upscale import FalUpscaler

    return FalUpscaler(_secret(settings.fal_key), settings.fal_upscale_model)


__all__ = [
    "FallbackImageProvider",
    "GeneratedImage",
    "ImageProvider",
    "ImageRequest",
    "RefImage",
    "Upscaler",
    "make_image_provider",
    "make_upscaler",
]
