from httpx import AsyncClient


async def register(
    client: AsyncClient,
    email: str = "salma.mom@example.com",
    password: str = "moonlight-2026",
    name: str = "أم سلمى",
) -> dict:  # type: ignore[type-arg]
    r = await client.post(
        "/api/auth/register", json={"email": email, "password": password, "full_name": name}
    )
    assert r.status_code == 201, r.text
    return r.json()  # type: ignore[no-any-return]


async def make_admin(
    client: AsyncClient, adb, email: str = "admin@example.com", password: str = "moonlight-2026"
) -> str:  # type: ignore[no-untyped-def]
    """Admin with 2FA on, signed in through password + TOTP. Returns the TOTP secret."""
    import uuid
    from datetime import UTC, datetime

    import pyotp

    from qamra_core.crypto import DEV_KEY, _cipher, encrypt
    from qamra_core.db.models import User, UserRole

    me = await register(client, email=email, password=password)
    user = await adb.get(User, uuid.UUID(me["id"]))
    assert user is not None
    secret = pyotp.random_base32()
    user.role = UserRole.admin
    user.totp_secret_ciphertext = encrypt(_cipher(DEV_KEY), secret)
    user.totp_enabled_at = datetime.now(UTC)
    await adb.commit()
    await client.post("/api/auth/logout")
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200 and r.json() == {"mfa_required": True}, r.text
    r = await client.post("/api/auth/mfa/verify", json={"code": pyotp.TOTP(secret).now()})
    assert r.status_code == 200 and r.json()["mfa_verified"], r.text
    return secret
