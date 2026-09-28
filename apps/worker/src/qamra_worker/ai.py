"""Admin settings (database, the source of truth) → the AI pipeline's settings.

Keys are decrypted here, inside the worker process, and only handed to the provider clients. They are never
logged or returned. Offline runs (placeholder art, no AI cost) switch to the sketch and fake providers.
"""

from decimal import Decimal

from pydantic import SecretStr

from qamra_ai.config import Settings as AISettings
from qamra_ai.image import make_image_provider, make_upscaler
from qamra_ai.pipeline.runtime import Runtime
from qamra_ai.text import make_text_provider
from qamra_core.settings import CoreSettings
from qamra_core.settings_store import Resolved


def _secret(value: object) -> SecretStr | None:
    return SecretStr(str(value)) if value else None


def ai_settings(resolved: Resolved, core: CoreSettings, *, offline: bool | str = False) -> AISettings:
    """`offline`: False → the configured providers; True/"sketch" → placeholder art; "fake" → tests."""
    v = resolved.values
    settings = AISettings(
        _env_file=None,  # type: ignore[call-arg]
        brand_name_ar=core.brand_name_ar,
        brand_name_en=core.brand_name_en,
        brand_domain=core.brand_domain,
        anthropic_api_key=_secret(v["anthropic_api_key"]),
        gemini_api_key=_secret(v["gemini_api_key"]),
        openai_api_key=_secret(v["openai_api_key"]),
        fal_key=_secret(v["fal_key"]),
        text_model=v["text_model"],
        text_model_fast=v["text_model_fast"],
        story_effort=v["story_effort"],
        image_provider=v["image_provider"],
        fal_image_model=v["fal_image_model"],
        fal_fallback_model=v["fal_fallback_model"],
        fal_upscale_model=v["fal_upscale_model"],
        fallback_after_failures=int(v["fallback_after_failures"]),
        gemini_image_model=v["gemini_image_model"],
        openai_image_model=v["openai_image_model"],
        openai_image_quality=v["openai_image_quality"],
        classic_image_provider=v["classic_image_provider"],
        self_hosted_url=v["self_hosted_url"],
        self_hosted_token=_secret(v["self_hosted_token"]),
        self_hosted_workflow=v["self_hosted_workflow"],
        preview_resolution=v["preview_resolution"],
        final_mode=v["final_mode"],
        preview_pages=int(v["preview_pages"]),
        image_concurrency=int(v["image_concurrency"]),
        page_max_regenerations=int(v["page_max_regenerations"]),
        qa_threshold=int(v["qa_threshold"]) / 100,
        book_budget_usd=float(Decimal(str(v["book_budget_usd"]))),
        print_spine_mm=float(Decimal(str(v["print_spine_mm"]))),
        print_signature=int(v["print_signature"]),
    )
    if offline:
        provider = "fake" if offline == "fake" else "sketch"
        settings = settings.model_copy(update={"image_provider": provider, "text_provider": "fake"})
    return settings


def make_runtime(settings: AISettings) -> Runtime:
    return Runtime(
        settings=settings,
        text=make_text_provider(settings),
        image=make_image_provider(settings),
        upscaler=make_upscaler(settings),
    )
