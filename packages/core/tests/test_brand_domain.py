"""BRAND_DOMAIN is what every printed QR code names (`https://{brand_domain}/a/…`, `/v/…`): a bare domain,
and in production the public one, never an address or a port (a printed code lives for years)."""

import pytest
from pydantic import ValidationError

from qamra_core.settings import CoreSettings


def settings(**values: object) -> CoreSettings:
    return CoreSettings(_env_file=None, **values)  # type: ignore[arg-type]


@pytest.mark.parametrize("typed", ["qamra.app", "https://qamra.app", "http://Qamra.app/", " qamra.app/ "])
def test_the_domain_is_kept_bare(typed: str) -> None:
    assert settings(brand_domain=typed).brand_domain == "qamra.app"


def test_a_url_with_a_path_is_refused() -> None:
    with pytest.raises(ValidationError):
        settings(brand_domain="https://qamra.app/ar")


@pytest.mark.parametrize("host", ["203.0.113.7", "[2001:db8::1]", "qamra.app:8443", "localhost"])
def test_production_never_prints_an_address_or_a_port(host: str) -> None:
    with pytest.raises(ValidationError, match="BRAND_DOMAIN"):
        settings(env="prod", settings_encryption_keys="k", brand_domain=host)
    assert settings(brand_domain=host).brand_domain == host  # a dev stack may point anywhere


def test_production_prints_the_public_domain() -> None:
    assert settings(env="prod", settings_encryption_keys="k").brand_domain == "qamra.app"
