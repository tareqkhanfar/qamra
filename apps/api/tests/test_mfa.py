import time
import uuid
from datetime import UTC, datetime

import pyotp
from api_helpers import make_admin, register
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.auth import mfa
from qamra_api.deps import ip_allowed
from qamra_api.security import create_access_token
from qamra_api.settings import DEV_JWT_SECRET
from qamra_core.db.models import AppSetting, AuditLog, User, UserRole
from qamra_core.db.store import StaffRole, UserStaffRole

PASSWORD = "moonlight-2026"


async def _enroll(client: AsyncClient) -> tuple[str, list[str]]:
    r = await client.post("/api/auth/mfa/setup", json={"password": PASSWORD})
    assert r.status_code == 200, r.text
    secret = r.json()["secret"]
    assert r.json()["uri"].startswith("otpauth://totp/")
    qr = await client.get("/api/auth/mfa/qr.png")
    assert qr.status_code == 200 and qr.headers["content-type"] == "image/png"
    r = await client.post("/api/auth/mfa/enable", json={"code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200, r.text
    return secret, r.json()["recovery_codes"]


def test_totp_step_matching_and_replay() -> None:
    secret = pyotp.random_base32()
    now = time.time()
    code = pyotp.TOTP(secret).at(now)
    step = mfa.match_step(secret, code, None, now)
    assert step is not None
    assert mfa.match_step(secret, code, step, now) is None  # the same code never works twice
    assert mfa.match_step(secret, "000000" if code != "000000" else "111111", None, now) is None
    assert mfa.match_step(secret, pyotp.TOTP(secret).at(now - 30), None, now) is not None  # one step of drift


def test_recovery_codes_are_single_use() -> None:
    codes, hashes = mfa.new_recovery_codes()
    assert len(codes) == 10 and len(set(codes)) == 10 and all(len(c) == 11 for c in codes)
    remaining = mfa.consume_recovery(hashes, codes[3].upper())
    assert remaining is not None and len(remaining) == 9
    assert mfa.consume_recovery(remaining, codes[3]) is None


async def test_enrollment_then_login_needs_the_second_factor(client: AsyncClient, adb: AsyncSession) -> None:
    me = await register(client, password=PASSWORD)
    secret, recovery = await _enroll(client)
    user = await adb.get(User, uuid.UUID(me["id"]))
    assert user is not None and user.totp_enabled_at and secret not in (user.totp_secret_ciphertext or "")
    assert len(user.recovery_codes) == 10 and recovery[0] not in user.recovery_codes  # hashes only
    assert (await client.get("/api/auth/me")).json()["mfa_verified"] is True

    await client.post("/api/auth/logout")
    r = await client.post("/api/auth/login", json={"email": me["email"], "password": PASSWORD})
    assert r.json() == {"mfa_required": True}
    assert (await client.get("/api/auth/me")).status_code == 401  # no session before the code
    assert (await client.post("/api/auth/mfa/verify", json={"code": "123456"})).status_code in (401, 429)
    # a code already used during enrollment can't be replayed; a recovery code works once
    r = await client.post("/api/auth/mfa/verify", json={"code": recovery[0]})
    assert r.status_code == 200 and r.json()["mfa_verified"]
    audit = (
        await adb.execute(select(AuditLog).where(AuditLog.action == "user.mfa_recovery_used"))
    ).scalar_one()
    assert audit.data == {"left": 9}


async def test_verify_without_challenge_is_rejected(client: AsyncClient) -> None:
    assert (await client.post("/api/auth/mfa/verify", json={"code": "123456"})).status_code == 401


async def test_setup_needs_the_password(client: AsyncClient) -> None:
    await register(client, password=PASSWORD)
    assert (await client.post("/api/auth/mfa/setup", json={"password": "wrong-one"})).status_code == 403


async def test_verify_is_rate_limited(client: AsyncClient) -> None:
    me = await register(client, password=PASSWORD)
    await _enroll(client)
    await client.post("/api/auth/logout")
    await client.post("/api/auth/login", json={"email": me["email"], "password": PASSWORD})
    codes = [
        (await client.post("/api/auth/mfa/verify", json={"code": "000001"})).status_code for _ in range(7)
    ]
    assert codes[-1] == 429


async def test_admin_area_requires_2fa(client: AsyncClient, adb: AsyncSession) -> None:
    me = await register(client, email="boss@example.com", password=PASSWORD)
    user = await adb.get(User, uuid.UUID(me["id"]))
    assert user is not None
    user.role = UserRole.admin
    adb.add(UserStaffRole(user_id=user.id, role=StaffRole.owner, granted_at=datetime.now(UTC)))
    await adb.commit()
    r = await client.get("/api/admin/settings")
    assert r.status_code == 403 and r.json()["error"]["code"] == "mfa_setup_required"
    await _enroll(client)  # enabling 2FA upgrades the current session
    assert (await client.get("/api/admin/settings")).status_code == 200
    assert (await client.post("/api/auth/mfa/disable", json={"code": "123456"})).json()["error"]["code"] == (
        "admin_requires_2fa"
    )


async def test_admin_session_without_second_factor_is_refused(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    user = (await adb.execute(select(User).where(User.email == "admin@example.com"))).scalar_one()
    # a password-only session (e.g. from before 2FA was switched on) can't open the admin area
    token = create_access_token(user.id, "admin", DEV_JWT_SECRET, 15, mfa=False)
    client.cookies.set("qamra_at", token)
    r = await client.get("/api/admin/settings")
    assert r.status_code == 403 and r.json()["error"]["code"] == "mfa_required"


async def test_admin_ip_allowlist(client: AsyncClient, adb: AsyncSession) -> None:
    await make_admin(client, adb)
    adb.add(AppSetting(key="admin_ip_allowlist", value="203.0.113.7"))
    await adb.commit()
    r = await client.get("/api/admin/settings")
    assert r.status_code == 403 and r.json()["error"]["code"] == "ip_not_allowed"
    assert ip_allowed("10.1.2.3", "10.0.0.0/8, 203.0.113.7/32") and not ip_allowed(
        "10.1.2.3", "192.168.0.0/16"
    )
    assert ip_allowed("anything", "")
