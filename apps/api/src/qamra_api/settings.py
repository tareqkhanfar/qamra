"""API settings: core infrastructure + auth, cookies, observability."""

from decimal import Decimal
from functools import lru_cache

from pydantic import SecretStr, model_validator
from qamra_core.settings import CoreSettings

DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me-0123456789"


class ApiSettings(CoreSettings):
    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cookie_secure: bool = False  # must be true in prod (HTTPS only)
    cookie_domain: str | None = None
    web_base_url: str = "http://localhost:3000"

    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None

    login_max_attempts: int = 10  # per email + IP, per window
    login_ip_max_attempts: int = 50  # per IP, per window (credential spraying)
    login_window_seconds: int = 900

    # Prices (ILS). Unset → the site says "coming soon" instead of showing a made-up number.
    price_digital_ils: Decimal | None = None
    price_softcover_ils: Decimal | None = None
    price_hardcover_ils: Decimal | None = None

    leads_per_ip_per_hour: int = 5

    sentry_dsn: SecretStr | None = None
    log_level: str = "INFO"
    log_json: bool = True

    @model_validator(mode="after")
    def _prod_safety(self) -> "ApiSettings":
        if self.env == "prod":
            secret = self.jwt_secret.get_secret_value()
            if secret == DEV_JWT_SECRET or len(secret) < 32:
                raise ValueError("JWT_SECRET must be set to a random value of ≥ 32 chars in prod")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in prod")
        return self

    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


@lru_cache
def get_settings() -> ApiSettings:
    return ApiSettings()
