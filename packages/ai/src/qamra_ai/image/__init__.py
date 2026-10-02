"""Image providers, upscalers + factories (provider/model choice comes from admin settings)."""

import structlog

from qamra_ai.config import ImageProviderName, Settings
from qamra_ai.errors import ProviderConfigError
from qamra_ai.image.base import GeneratedImage, ImageProvider, ImageRequest, RefImage
from qamra_ai.image.fallback import FallbackImageProvider
from qamra_ai.image.upscale import LocalUpscaler, Upscaler

log = structlog.get_logger("qamra.ai.image")


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
    if name == "self_hosted":
        from qamra_ai.image.comfy import ComfyImageProvider

        return ComfyImageProvider(
            settings.self_hosted_url, _secret(settings.self_hosted_token), settings.self_hosted_workflow
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


def make_cover_image_provider(settings: Settings) -> FallbackImageProvider | None:
    """The cover's own model (Addendum 11 §6.4: covers may use a higher-quality model), on fal only, with
    the page model as its fallback. None when unset, equal to the page model, or offline: the cover then
    uses the page provider."""
    model = settings.cover_image_model.strip()
    if settings.image_provider != "fal" or not model or model == settings.fal_image_model:
        return None
    from qamra_ai.image.fal import FalImageProvider

    key = _secret(settings.fal_key)
    return FallbackImageProvider(
        FalImageProvider(key, model),
        FalImageProvider(key, settings.fal_image_model),
        switch_after=settings.fallback_after_failures,
    )


def make_classic_image_provider(settings: Settings) -> FallbackImageProvider:
    """The Classic hero-edit provider (Addendum 4 §1A, §8), through the same factory and fallback.

    `classic_image_provider` picks fal (the klein model in `classic_fal_model`) or our self-hosted GPU; the
    fal fallback is the same klein model, so an edit never silently moves to a pricier model. Offline runs
    (fake, sketch) stay offline. A self-hosted workflow without an approved license, or without a server
    address, is a configuration error: fal draws instead, and the switch is logged.
    """
    if settings.image_provider in ("fake", "sketch"):
        return make_image_provider(settings)
    model = settings.classic_fal_model
    klein = settings.model_copy(update={"fal_image_model": model, "fal_fallback_model": model})
    if settings.classic_image_provider == "self_hosted":
        try:
            return make_image_provider(klein, "self_hosted")
        except ProviderConfigError as e:
            log.warning("classic.self_hosted_unavailable", error=str(e)[:200])
    return make_image_provider(klein, "fal")


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
    "make_classic_image_provider",
    "make_cover_image_provider",
    "make_image_provider",
    "make_upscaler",
]
