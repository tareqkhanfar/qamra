"""API settings: core infrastructure + auth, cookies, observability."""

from functools import lru_cache

from pydantic import SecretStr, model_validator

from qamra_core.settings import CoreSettings

DEV_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me-0123456789"  # nosec B105  (prod refuses it)


class ApiSettings(CoreSettings):
    jwt_secret: SecretStr = SecretStr(DEV_JWT_SECRET)
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cookie_secure: bool = False  # must be true in prod (HTTPS only)
    cookie_domain: str | None = None
    web_base_url: str = "http://localhost:3000"

    login_max_attempts: int = 10  # per email + IP, per window
    login_ip_max_attempts: int = 50  # per IP, per window (credential spraying)
    login_window_seconds: int = 900

    settings_cache_seconds: int = 10  # admin-managed settings (prices, keys…) cache per API process

    leads_per_ip_per_hour: int = 5
    register_ip_max_per_hour: int = 10

    # Addendum 9 E2E tests: /api/e2e/* creates preview books with placeholder art (no AI). Never in prod.
    e2e_fixtures: bool = False

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
            if self.e2e_fixtures:
                raise ValueError("E2E_FIXTURES must be off in prod")
        return self


@lru_cache
def get_settings() -> ApiSettings:
    return ApiSettings()
