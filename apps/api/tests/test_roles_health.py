from api_helpers import register
from fastapi import Depends, FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.deps import require_role
from qamra_core.db.models import User, UserRole


async def test_role_guard(app: FastAPI, client: AsyncClient, adb: AsyncSession) -> None:
    @app.get("/api/test/admin-only", dependencies=[Depends(require_role(UserRole.admin))])
    async def admin_only() -> dict[str, bool]:
        return {"ok": True}

    user = await register(client)
    r = await client.get("/api/test/admin-only")
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"

    row = await adb.get(User, __import__("uuid").UUID(user["id"]))
    assert row is not None
    row.role = UserRole.admin
    await adb.commit()
    assert (await client.get("/api/test/admin-only")).json() == {"ok": True}


async def test_health(client: AsyncClient) -> None:
    assert (await client.get("/api/health/live")).json() == {"status": "ok"}
    r = await client.get("/api/health")
    assert r.status_code == 200, r.text
    assert r.json() == {"status": "ok", "db": True, "redis": True, "storage": True}


async def test_unknown_route_is_friendly(client: AsyncClient) -> None:
    r = await client.get("/api/nope")
    assert r.status_code == 404 and r.json()["error"]["message"]["ar"]


async def test_request_id_header(client: AsyncClient) -> None:
    r = await client.get("/api/health/live", headers={"X-Request-ID": "abc123"})
    assert r.headers["x-request-id"] == "abc123"


async def test_security_headers_on_every_response(client: AsyncClient) -> None:
    r = await client.get("/api/health/live")
    h = r.headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert h["content-security-policy"].startswith("default-src 'none'")
    assert h["cross-origin-resource-policy"] == "same-origin" and "server" not in h
    me = await client.get("/api/auth/me")  # 401, but still personal-data route
    assert me.headers["cache-control"] == "no-store"
