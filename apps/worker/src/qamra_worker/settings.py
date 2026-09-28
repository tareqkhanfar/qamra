from functools import lru_cache

from pydantic import SecretStr

from qamra_core.settings import CoreSettings


class WorkerSettings(CoreSettings):
    sentry_dsn: SecretStr | None = None
    log_level: str = "INFO"
    log_json: bool = True


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
