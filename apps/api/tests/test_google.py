from urllib.parse import parse_qs, urlparse

import pytest
from api_helpers import register
from httpx import AsyncClient
from qamra_api.auth import google
from qamra_api.deps import ACCESS_COOKIE, OAUTH_COOKIE
from qamra_api.settings import ApiSettings
from qamra_core.db.models import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def google_on(settings: ApiSettings) -> ApiSettings:
    settings.google_client_id = "client-123.apps.googleusercontent.com"
    settings.google_client_secret = __import__("pydantic").SecretStr("s3cret")
    return settings


def fake_google(
    monkeypatch: pytest.MonkeyPatch,
    *,
    email: str = "parent@gmail.com",
    verified: bool = True,
    sub: str = "google-sub-1",
) -> None:
    async def exchange(code: str, *_: str) -> str:
        assert code == "the-code"
        return "id-token"

    def verify(token: str, client_id: str, nonce: str) -> google.GoogleIdentity:
        assert token == "id-token" and nonce
        return google.GoogleIdentity(sub=sub, email=email, email_verified=verified, name="Parent")

    monkeypatch.setattr(google, "exchange_code", exchange)
    monkeypatch.setattr(google, "verify_id_token", verify)


async def _start(client: AsyncClient, next_path: str = "/ar/account") -> str:
    r = await client.get("/api/auth/google/start", params={"next": next_path})
    assert r.status_code == 302
    url = urlparse(r.headers["location"])
    assert url.netloc == "accounts.google.com"
    q = parse_qs(url.query)
    assert q["redirect_uri"] == ["http://testserver/api/auth/google/callback"]
    assert client.cookies.get(OAUTH_COOKIE, path="/api/auth/google")
    return q["state"][0]


async def test_google_disabled(client: AsyncClient) -> None:
    r = await client.get("/api/auth/google/start")
    assert r.status_code == 404 and r.json()["error"]["code"] == "google_disabled"


async def test_google_creates_user(
    google_on: ApiSettings, client: AsyncClient, adb: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_google(monkeypatch)
    state = await _start(client)
    r = await client.get("/api/auth/google/callback", params={"code": "the-code", "state": state})
    assert r.status_code == 302 and r.headers["location"] == "http://testserver/ar/account"
    assert client.cookies.get(ACCESS_COOKIE)
    user = (await adb.execute(select(User).where(User.email == "parent@gmail.com"))).scalar_one()
    assert user.google_sub == "google-sub-1" and user.password_hash is None
    assert (await client.get("/api/auth/me")).json()["has_password"] is False


async def test_google_links_existing_account(
    google_on: ApiSettings, client: AsyncClient, adb: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await register(client, email="parent@gmail.com")
    await client.post("/api/auth/logout")
    fake_google(monkeypatch)
    state = await _start(client)
    await client.get("/api/auth/google/callback", params={"code": "the-code", "state": state})
    users = (await adb.execute(select(User).where(User.email == "parent@gmail.com"))).scalars().all()
    assert len(users) == 1 and users[0].google_sub == "google-sub-1"


@pytest.mark.parametrize("case", ["bad_state", "unverified", "no_cookie"])
async def test_google_failures_redirect_to_login(
    google_on: ApiSettings, client: AsyncClient, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    fake_google(monkeypatch, verified=case != "unverified")
    state = await _start(client)
    if case == "no_cookie":
        client.cookies.clear()
    r = await client.get(
        "/api/auth/google/callback",
        params={"code": "the-code", "state": "forged" if case == "bad_state" else state},
    )
    assert r.status_code == 302 and r.headers["location"].endswith("/ar/login?error=google_failed")
    assert not client.cookies.get(ACCESS_COOKIE)


async def test_open_redirect_blocked(
    google_on: ApiSettings, client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_google(monkeypatch)
    state = await _start(client, next_path="//evil.example.com/x")
    r = await client.get("/api/auth/google/callback", params={"code": "the-code", "state": state})
    assert r.headers["location"] == "http://testserver/"
