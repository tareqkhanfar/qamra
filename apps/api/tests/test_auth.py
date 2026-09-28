import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from api_helpers import register
from httpx import AsyncClient
from qamra_api.deps import ACCESS_COOKIE, REFRESH_COOKIE
from qamra_api.security import JWT_ALG
from qamra_api.settings import ApiSettings
from qamra_core.db.models import AuditLog, RefreshToken, User
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


async def test_register_sets_cookies_and_me(client: AsyncClient) -> None:
    user = await register(client, email="  Salma.Mom@Example.com ")
    assert user["email"] == "salma.mom@example.com"
    assert user["role"] == "parent" and user["locale"] == "ar" and user["has_password"]
    assert client.cookies.get(ACCESS_COOKIE) and client.cookies.get(REFRESH_COOKIE)
    me = await client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["id"] == user["id"]


async def test_cookies_are_httponly_and_scoped(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/register", json={"email": "a@example.com", "password": "moonlight-2026", "full_name": "A"}
    )
    set_cookies = r.headers.get_list("set-cookie")
    access = next(c for c in set_cookies if c.startswith(ACCESS_COOKIE))
    refresh = next(c for c in set_cookies if c.startswith(REFRESH_COOKIE))
    assert "HttpOnly" in access and "SameSite=lax" in access and "Path=/" in access
    assert "HttpOnly" in refresh and "Path=/api/auth" in refresh


async def test_duplicate_email_is_friendly(client: AsyncClient) -> None:
    await register(client)
    r = await client.post(
        "/api/auth/register",
        json={"email": "SALMA.MOM@example.com", "password": "moonlight-2026", "full_name": "x"},
    )
    assert r.status_code == 409
    err = r.json()["error"]
    assert err["code"] == "email_taken" and "مسجَّل" in err["message"]["ar"] and err["message"]["en"]


@pytest.mark.parametrize(
    ("body", "code", "status"),
    [
        ({"email": "b@example.com", "password": "short", "full_name": "B"}, "weak_password", 422),
        ({"email": "not-an-email", "password": "moonlight-2026", "full_name": "B"}, "invalid_input", 422),
        ({"email": "b@example.com", "password": "moonlight-2026", "full_name": "   "}, "invalid_input", 422),
    ],
)
async def test_register_validation(client: AsyncClient, body: dict, code: str, status: int) -> None:  # type: ignore[type-arg]
    r = await client.post("/api/auth/register", json=body)
    assert r.status_code == status and r.json()["error"]["code"] == code


async def test_login_logout_flow(client: AsyncClient, adb: AsyncSession) -> None:
    await register(client)
    await client.post("/api/auth/logout")
    assert (await client.get("/api/auth/me")).status_code == 401

    r = await client.post(
        "/api/auth/login", json={"email": "salma.mom@example.com", "password": "moonlight-2026"}
    )
    assert r.status_code == 200 and r.json()["full_name"] == "أم سلمى"
    assert (await client.get("/api/auth/me")).status_code == 200

    r = await client.post("/api/auth/logout")
    assert r.status_code == 204
    assert (await client.get("/api/auth/me")).json()["error"]["code"] == "not_authenticated"
    actions = (await adb.execute(select(AuditLog.action))).scalars().all()
    assert {"user.registered", "user.login", "user.logout"} <= set(actions)


async def test_wrong_password_and_unknown_email_look_the_same(client: AsyncClient) -> None:
    await register(client)
    wrong = await client.post(
        "/api/auth/login", json={"email": "salma.mom@example.com", "password": "nope-nope-nope"}
    )
    unknown = await client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": "nope-nope-nope"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["error"]["message"]["ar"] == "البريد الإلكتروني أو كلمة المرور غير صحيحة."


async def test_login_rate_limited(client: AsyncClient, settings: ApiSettings) -> None:
    await register(client)
    body = {"email": "salma.mom@example.com", "password": "wrong-wrong-wrong"}
    for _ in range(settings.login_max_attempts):
        assert (await client.post("/api/auth/login", json=body)).status_code == 401
    r = await client.post("/api/auth/login", json={**body, "password": "moonlight-2026"})
    assert r.status_code == 429 and r.json()["error"]["code"] == "too_many_attempts"


async def test_unsafe_request_without_client_header_is_rejected(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/login",
        json={"email": "a@example.com", "password": "x" * 8},
        headers={"X-Qamra-Client": ""},
    )
    assert r.status_code == 403 and r.json()["error"]["code"] == "bad_request"


async def test_expired_access_token(client: AsyncClient, settings: ApiSettings) -> None:
    user = await register(client)
    past = datetime.now(UTC) - timedelta(hours=1)
    token = jwt.encode(
        {
            "sub": user["id"],
            "role": "parent",
            "typ": "access",
            "iat": past,
            "exp": past + timedelta(minutes=15),
        },
        settings.jwt_secret.get_secret_value(),
        JWT_ALG,
    )
    client.cookies.set(ACCESS_COOKIE, token)
    r = await client.get("/api/auth/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "token_expired"


async def test_forged_token_rejected(client: AsyncClient) -> None:
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "typ": "access",
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "not-our-secret" * 4,
        JWT_ALG,
    )
    client.cookies.set(ACCESS_COOKIE, token)
    assert (await client.get("/api/auth/me")).json()["error"]["code"] == "not_authenticated"


async def test_refresh_rotates_and_detects_reuse(client: AsyncClient, adb: AsyncSession) -> None:
    await register(client)
    first = client.cookies.get(REFRESH_COOKIE, path="/api/auth")
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 200
    second = client.cookies.get(REFRESH_COOKIE, path="/api/auth")
    assert second and second != first
    # age the rotated token past the grace window
    await adb.execute(
        update(RefreshToken)
        .where(RefreshToken.revoked_reason == "rotated")
        .values(revoked_at=datetime.now(UTC) - timedelta(minutes=5))
    )
    await adb.commit()

    # replaying the first (rotated) token revokes the whole family, including the second token
    client.cookies.delete(REFRESH_COOKIE)
    client.cookies.set(REFRESH_COOKIE, first, path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 401
    client.cookies.delete(REFRESH_COOKIE)
    client.cookies.set(REFRESH_COOKIE, second, path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 401
    live = (await adb.execute(select(RefreshToken).where(RefreshToken.revoked_at.is_(None)))).scalars().all()
    assert live == []


async def test_concurrent_refresh_within_grace_window(client: AsyncClient) -> None:
    """Two tabs refreshing with the same token at once must both stay signed in."""
    await register(client)
    token = client.cookies.get(REFRESH_COOKIE, path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 200
    client.cookies.delete(REFRESH_COOKIE)
    client.cookies.set(REFRESH_COOKIE, token, path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 200
    assert (await client.get("/api/auth/me")).status_code == 200


async def test_refresh_after_logout_fails(client: AsyncClient) -> None:
    await register(client)
    token = client.cookies.get(REFRESH_COOKIE, path="/api/auth")
    await client.post("/api/auth/logout")
    client.cookies.set(REFRESH_COOKIE, token, path="/api/auth")
    assert (await client.post("/api/auth/refresh")).status_code == 401


async def test_disabled_account(client: AsyncClient, adb: AsyncSession) -> None:
    user = await register(client)
    row = await adb.get(User, uuid.UUID(user["id"]))
    assert row is not None
    row.is_active = False
    await adb.commit()
    assert (await client.get("/api/auth/me")).json()["error"]["code"] == "account_disabled"
    r = await client.post(
        "/api/auth/login", json={"email": "salma.mom@example.com", "password": "moonlight-2026"}
    )
    assert r.status_code == 403
