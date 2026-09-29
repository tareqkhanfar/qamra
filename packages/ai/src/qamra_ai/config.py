"""Runtime settings for the AI pipeline.

Scripts read them from env/.env. The worker builds them from the admin settings (`qamra_core` registry),
which are the source of truth in the running system.
"""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ImageProviderName = Literal["fal", "gemini", "openai", "self_hosted", "fake", "sketch"]
TextProviderName = Literal["anthropic", "fake"]
ResolutionName = Literal["0.5K", "1K", "2K", "4K"]
FinalMode = Literal["1k_upscale", "2k_upscale"]
EffortName = Literal["low", "medium", "high"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Brand (Addendum 1: a rename must never touch code)
    brand_name_ar: str = "قمرة"
    brand_name_en: str = "Qamra"
    brand_domain: str = "qamra.app"
    brand_tagline_ar: str = "حكاية طفلك… تحت ضوء القمر"
    brand_tagline_en: str = "Your child's story, by moonlight."

    # Keys
    anthropic_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    fal_key: SecretStr | None = None

    # Text (Addendum 3: Sonnet writes, Haiku checks; Opus stays selectable but is not the default)
    text_provider: TextProviderName = "anthropic"
    text_model: str = "claude-sonnet-5"  # story adaptation + vowelization
    text_model_fast: str = "claude-haiku-4-5-20251001"  # safety review, page QA, drawing checks
    story_effort: EffortName = "medium"
    text_server_fallbacks: bool = True  # only sent to models that support server-side fallbacks

    # Images (Addendum 3: fal Nano Banana 2 → FLUX.2 pro edit fallback)
    image_provider: ImageProviderName = "fal"
    fal_image_model: str = "fal-ai/nano-banana-2"  # /edit is used automatically with references
    fal_fallback_model: str = "fal-ai/flux-2-pro/edit"
    fal_upscale_model: str = "fal-ai/seedvr/upscale/image"
    fallback_after_failures: int = 2
    gemini_image_model: str = "gemini-3.1-flash-image"
    gemini_image_size: Literal["1K", "2K", "4K"] = "2K"
    openai_image_model: str = "gpt-image-2.5-sunburst"
    openai_image_quality: Literal["low", "medium", "high", "xhigh", "max", "auto"] = "high"

    # Self-hosted GPU (Addendum 4 §8): our ComfyUI server, for Classic template edits only; off by default
    classic_image_provider: Literal["fal", "self_hosted"] = "fal"
    # Classic hero edits (Addendum 4 §1A): FLUX.2 [klein] 4B, Apache 2.0; also the fal fallback of self_hosted
    classic_fal_model: str = "fal-ai/flux-2/klein/4b/edit"
    self_hosted_url: str = ""
    self_hosted_token: SecretStr | None = None
    self_hosted_workflow: str = ""  # a file in qamra_ai/image/comfy_workflows/, approved in docs/licenses.md

    # Resolution tiers (Addendum 3 §2.1)
    preview_resolution: ResolutionName = "0.5K"
    final_mode: FinalMode = "1k_upscale"
    preview_pages: int = 4  # cover + first 3 story pages

    # Quality + cost controls
    image_concurrency: int = 4
    page_max_regenerations: int = 2  # automatic redraws per page before a human looks at it
    qa_threshold: float = 0.75
    book_budget_usd: float = 3.00

    # Print
    print_dpi: int = 300
    print_trim_mm: float = 210.0
    print_bleed_mm: float = 3.0
    print_safe_mm: float = 10.0
    print_signature: int = 4
    print_spine_mm: float = 8.0

    @property
    def final_resolution(self) -> ResolutionName:
        return "2K" if self.final_mode == "2k_upscale" else "1K"


@lru_cache
def get_settings() -> Settings:
    return Settings()
