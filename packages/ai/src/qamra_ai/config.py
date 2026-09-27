"""Runtime settings. Everything that may change (brand, models, keys) lives here, read from env/.env."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ImageProviderName = Literal["gemini", "flux", "openai", "fake"]
TextProviderName = Literal["anthropic", "fake"]


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

    # Text (Claude)
    text_provider: TextProviderName = "anthropic"
    text_model: str = "claude-opus-5"  # story adaptation + vowelization
    text_model_fast: str = "claude-opus-5"  # safety review + page judge
    text_server_fallbacks: bool = True  # server-side refusal fallback (beta)

    # Images
    image_provider: ImageProviderName = "gemini"
    gemini_image_model: str = "gemini-3.1-flash-image"
    gemini_image_size: Literal["1K", "2K", "4K"] = "2K"
    flux_image_model: str = "fal-ai/flux-2-pro/edit"
    flux_image_px: int = 2048
    openai_image_model: str = "gpt-image-2.5-sunburst"
    openai_image_quality: Literal["low", "medium", "high", "xhigh", "max", "auto"] = "high"
    openai_image_px: int = 2048

    image_concurrency: int = 4
    image_max_attempts: int = 3
    page_max_regenerations: int = 1  # automatic redraws when a page fails review

    # Print
    print_dpi: int = 300
    print_trim_mm: float = 210.0
    print_bleed_mm: float = 3.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
