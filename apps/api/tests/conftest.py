from collections.abc import AsyncIterator
from dataclasses import replace

import pytest
from fakeredis import FakeAsyncRedis, FakeRedis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.app import create_app
from qamra_api.deps import get_session
from qamra_api.settings import ApiSettings
from qamra_core.app_settings import REGISTRY
from qamra_core.storage import ObjectStorage


@pytest.fixture(autouse=True)
def prices_shown_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Customers see no prices by default (`show_prices` off, Tareq 2026-10-16). The store tests check the
    prices, so the suite runs with the switch on; test_price_visibility.py stores the setting to test off."""
    monkeypatch.setitem(REGISTRY, "show_prices", replace(REGISTRY["show_prices"], default=True))


@pytest.fixture
def settings() -> ApiSettings:
    return ApiSettings(
        _env_file=None,
        env="test",
        cookie_secure=False,
        log_json=False,  # type: ignore[call-arg]
        web_base_url="http://testserver",
        login_max_attempts=5,
        login_ip_max_attempts=20,
        settings_cache_seconds=0,
    )


@pytest.fixture
async def app(settings: ApiSettings, adb: AsyncSession, storage: ObjectStorage) -> AsyncIterator[FastAPI]:
    app = create_app(settings, manage_resources=False)
    app.state.redis = FakeAsyncRedis(decode_responses=True)
    app.state.rq_redis = FakeRedis()
    app.state.storage = storage

    async def _session() -> AsyncIterator[AsyncSession]:
        yield adb

    app.dependency_overrides[get_session] = _session
    yield app
    await app.state.redis.aclose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver", headers={"X-Qamra-Client": "test"}
    ) as c:
        yield c
