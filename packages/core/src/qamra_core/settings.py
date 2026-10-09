"""Infrastructure settings shared by the api and the worker (env / .env)."""

import ipaddress
from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MAX_SIGNED_URL_SECONDS = 900  # hard cap from the privacy rules (≤ 15 minutes)


class CoreSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["dev", "test", "prod"] = "dev"

    # Brand (Addendum 1: never hardcode)
    brand_name_ar: str = "قمرة"
    brand_name_en: str = "Qamra"
    brand_domain: str = "qamra.app"  # the bare host every printed QR code and link names (https://{it}/…)

    database_url: str = "postgresql+psycopg://qamra:qamra@localhost:5432/qamra"
    db_pool_size: int = 5
    redis_url: str = "redis://localhost:6379/0"

    # S3-compatible object storage: MinIO locally, Cloudflare R2 in production
    s3_endpoint_url: str | None = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "qamra-private"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_sse: Literal["AES256", "none"] = "AES256"  # R2 encrypts at rest by itself → "none"
    s3_signed_url_seconds: int = 600

    # Encrypts secrets stored in the database (admin-managed API keys, SMTP password…).
    # Comma-separated Fernet keys; the first encrypts, all decrypt (rotation). Generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    settings_encryption_keys: SecretStr | None = None

    # Privacy retention (CLAUDE.md §3, Addendum 1 §1)
    photo_retention_hours: int = 24  # after character approval
    drawing_retention_hours: int = 24  # original drawing, after companion approval
    draft_retention_days: int = 30

    @model_validator(mode="after")
    def _prod_needs_encryption_key(self) -> "CoreSettings":
        if self.env == "prod" and self.settings_encryption_keys is None:
            raise ValueError("SETTINGS_ENCRYPTION_KEYS must be set in prod")
        return self

    @field_validator("brand_domain")
    @classmethod
    def _bare_domain(cls, v: str) -> str:
        """`https://qamra.app/` → `qamra.app`: the QR codes print `https://{brand_domain}/…`."""
        host = v.strip().lower().removeprefix("https://").removeprefix("http://").rstrip("/")
        if not host or "/" in host:
            raise ValueError("BRAND_DOMAIN is a domain such as qamra.app, not a URL with a path")
        return host

    @model_validator(mode="after")
    def _prod_prints_the_public_domain(self) -> "CoreSettings":
        """A printed QR code lives for years: in prod it names the public domain, never an address or port."""
        if self.env == "prod" and (
            ":" in self.brand_domain or _is_ip(self.brand_domain) or "." not in self.brand_domain
        ):
            raise ValueError(
                "BRAND_DOMAIN must be the public domain in prod (e.g. qamra.app), not an IP or a port"
            )
        return self

    @field_validator("s3_signed_url_seconds")
    @classmethod
    def _cap_signed_urls(cls, v: int) -> int:
        if not 0 < v <= MAX_SIGNED_URL_SECONDS:
            raise ValueError(f"signed URLs must expire within {MAX_SIGNED_URL_SECONDS}s")
        return v


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return True


@lru_cache
def get_core_settings() -> CoreSettings:
    return CoreSettings()
