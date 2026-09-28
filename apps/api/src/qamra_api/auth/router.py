"""/api/auth — register, login, refresh, logout, me, Google sign-in."""

import io
import secrets
import uuid
from datetime import UTC, datetime

import httpx
import jwt
import qrcode
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from qamra_api import ratelimit, runtime_settings
from qamra_api.auth import google, mfa
from qamra_api.auth import service as auth
from qamra_api.auth.schemas import (
    LoginIn,
    MfaChallengeOut,
    MfaCodeIn,
    MfaSetupIn,
    MfaSetupOut,
    PasswordChangeIn,
    RecoveryCodesOut,
    RegisterIn,
    UserOut,
)
from qamra_api.deps import (
    ACCESS_COOKIE,
    OAUTH_COOKIE,
    REFRESH_COOKIE,
    CurrentAuth,
    RedisDep,
    SessionDep,
    SettingsDep,
)
from qamra_api.errors import ApiError
from qamra_api.security import TokenInvalid, read_blob, read_state, sign_blob, sign_state, verify_password
from qamra_api.settings import ApiSettings
from qamra_core.crypto import cipher_for, decrypt, encrypt
from qamra_core.db.models import Locale, User, UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])
REFRESH_PATH = "/api/auth"
GOOGLE_PATH = "/api/auth/google"
MFA_PATH = "/api/auth/mfa"
MFA_COOKIE = "qamra_mfa"
MFA_MINUTES = 5
MFA_MAX_ATTEMPTS = 5  # per login challenge window


def _set_cookie(
    response: Response, name: str, value: str, max_age: int, path: str, settings: ApiSettings
) -> None:
    response.set_cookie(
        name,
        value,
        max_age=max_age,
        path=path,
        domain=settings.cookie_domain,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


def set_session_cookies(response: Response, session: auth.Session, settings: ApiSettings) -> None:
    _set_cookie(
        response, ACCESS_COOKIE, session.access_token, settings.access_token_minutes * 60, "/", settings
    )
    _set_cookie(
        response,
        REFRESH_COOKIE,
        session.refresh_token,
        settings.refresh_token_days * 86400,
        REFRESH_PATH,
        settings,
    )


def clear_session_cookies(response: Response, settings: ApiSettings) -> None:
    for name, path in ((ACCESS_COOKIE, "/"), (REFRESH_COOKIE, REFRESH_PATH)):
        response.delete_cookie(
            name,
            path=path,
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            httponly=True,
            samesite="lax",
        )


def client_ip(request: Request) -> str:
    # Behind Nginx/Cloudflare: uvicorn runs with --proxy-headers and trusted forwarded IPs.
    return request.client.host if request.client else "unknown"


@router.post("/register", status_code=201)
async def register(
    redis: RedisDep,
    body: RegisterIn,
    request: Request,
    response: Response,
    db: SessionDep,
    settings: SettingsDep,
) -> UserOut:
    if not (await runtime_settings.current(db, settings)).values.get("registration_open", True):
        raise ApiError("registration_closed", 403)
    # account-creation spam: 10 per IP per hour
    if (
        await ratelimit.hit(redis, f"rl:register:{client_ip(request)}", 3600)
        > settings.register_ip_max_per_hour
    ):
        raise ApiError("too_many_attempts", 429)
    user = await auth.register(
        db, email=body.email, password=body.password, full_name=body.full_name, locale=body.locale
    )
    session = await auth.start_session(db, user, settings, request.headers.get("user-agent"), "register")
    set_session_cookies(response, session, settings)
    return UserOut.of(user)


@router.post("/login")
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
) -> UserOut | MfaChallengeOut:
    per_email, per_ip = ratelimit.login_keys(client_ip(request), body.email)
    window = settings.login_window_seconds
    if (
        await ratelimit.hit(redis, per_ip, window) > settings.login_ip_max_attempts
        or await ratelimit.hit(redis, per_email, window) > settings.login_max_attempts
    ):
        raise ApiError("too_many_attempts", 429)
    user = await auth.authenticate(db, body.email, body.password)
    await ratelimit.reset(redis, per_email)
    if user.totp_enabled_at is not None:
        # password OK; the session starts only after the second factor (POST /api/auth/mfa/verify)
        blob = sign_blob({"uid": str(user.id)}, settings.jwt_secret.get_secret_value(), "mfa", MFA_MINUTES)
        _set_cookie(response, MFA_COOKIE, blob, MFA_MINUTES * 60, MFA_PATH, settings)
        return MfaChallengeOut()
    session = await auth.start_session(db, user, settings, request.headers.get("user-agent"), "password")
    set_session_cookies(response, session, settings)
    return UserOut.of(user)


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: SessionDep, settings: SettingsDep) -> UserOut:
    try:
        session = await auth.rotate(
            db, request.cookies.get(REFRESH_COOKIE), settings, request.headers.get("user-agent")
        )
    except ApiError:
        clear_session_cookies(response, settings)
        raise
    set_session_cookies(response, session, settings)
    return UserOut.of(session.user, mfa_verified=session.mfa)


@router.post("/logout", status_code=204)
async def logout(request: Request, db: SessionDep, settings: SettingsDep) -> Response:
    await auth.logout(db, request.cookies.get(REFRESH_COOKIE))
    response = Response(status_code=204)
    clear_session_cookies(response, settings)
    return response


@router.get("/me")
async def me(current: CurrentAuth) -> UserOut:
    return UserOut.of(current.user, mfa_verified=current.claims.mfa)


@router.post("/password")
async def change_password(
    body: PasswordChangeIn,
    request: Request,
    response: Response,
    current: CurrentAuth,
    db: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
) -> UserOut:
    """Change password; signs out every other session (all refresh tokens revoked, new one issued)."""
    user = current.user
    key = f"rl:password:{user.id}"
    if await ratelimit.hit(redis, key, settings.login_window_seconds) > settings.login_max_attempts:
        raise ApiError("too_many_attempts", 429)
    await auth.change_password(db, user, body.current_password, body.new_password)
    await ratelimit.reset(redis, key)
    session = await auth.start_session(
        db, user, settings, request.headers.get("user-agent"), "password_change", mfa=current.claims.mfa
    )
    set_session_cookies(response, session, settings)
    return UserOut.of(user, mfa_verified=session.mfa)


# ---- two-step verification (TOTP) ---------------------------------------------------------------


def _clear_mfa_cookie(response: Response, settings: ApiSettings) -> None:
    response.delete_cookie(
        MFA_COOKIE, path=MFA_PATH, domain=settings.cookie_domain, secure=settings.cookie_secure, httponly=True
    )


async def _check_code(
    db: SessionDep, user: User, code: str, settings: ApiSettings, *, pending: bool = False
) -> str:
    """'totp' or 'recovery' when `code` is valid for `user`, else ApiError. Updates replay/recovery state."""
    if not user.totp_secret_ciphertext:
        raise ApiError("mfa_not_pending", 409)
    secret = decrypt(cipher_for(settings), user.totp_secret_ciphertext)
    step = mfa.match_step(secret, code, user.totp_last_step)
    if step is not None:
        user.totp_last_step = step
        return "totp"
    if not pending and user.recovery_codes:
        remaining = mfa.consume_recovery(list(user.recovery_codes), code)
        if remaining is not None:
            user.recovery_codes = remaining
            auth.audit(db, "user.mfa_recovery_used", user.id, left=len(remaining))
            return "recovery"
    raise ApiError("invalid_code", 401)


@router.post("/mfa/verify")
async def mfa_verify(
    body: MfaCodeIn,
    request: Request,
    response: Response,
    db: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
) -> UserOut:
    """Second step of a login: the challenge cookie from /login + a TOTP or recovery code."""
    try:
        blob = read_blob(request.cookies.get(MFA_COOKIE, ""), settings.jwt_secret.get_secret_value(), "mfa")
        user_id = uuid.UUID(blob["uid"])
    except (TokenInvalid, KeyError, ValueError) as e:
        raise ApiError("token_expired", 401) from e
    ip = client_ip(request)
    if (
        await ratelimit.hit(redis, f"rl:mfa:{user_id}", settings.login_window_seconds) > MFA_MAX_ATTEMPTS
        or await ratelimit.hit(redis, f"rl:mfa-ip:{ip}", settings.login_window_seconds)
        > settings.login_ip_max_attempts
    ):
        raise ApiError("too_many_attempts", 429)
    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.totp_enabled_at is None:
        raise ApiError("not_authenticated", 401)
    method = await _check_code(db, user, body.code, settings)
    await ratelimit.reset(redis, f"rl:mfa:{user_id}")
    session = await auth.start_session(
        db, user, settings, request.headers.get("user-agent"), f"password+{method}", mfa=True
    )
    _clear_mfa_cookie(response, settings)
    set_session_cookies(response, session, settings)
    return UserOut.of(user, mfa_verified=True)


@router.post("/mfa/setup")
async def mfa_setup(
    body: MfaSetupIn, current: CurrentAuth, db: SessionDep, settings: SettingsDep
) -> MfaSetupOut:
    """Start enrollment: a new secret, stored encrypted and pending until a first code confirms it."""
    user = current.user
    if user.totp_enabled_at is not None:
        raise ApiError("mfa_already_enabled", 409)
    if user.password_hash is not None and not verify_password(body.password or "", user.password_hash):
        raise ApiError("wrong_password", 403)
    secret = mfa.new_secret()
    user.totp_secret_ciphertext = encrypt(cipher_for(settings), secret)
    user.totp_last_step = None
    auth.audit(db, "user.mfa_setup_started", user.id)
    await db.commit()
    return MfaSetupOut(secret=secret, uri=mfa.provisioning_uri(secret, user.email, settings.brand_name_en))


@router.get("/mfa/qr.png")
async def mfa_qr(current: CurrentAuth, settings: SettingsDep) -> Response:
    """QR of the pending secret for authenticator apps (only while enrollment is pending)."""
    user = current.user
    if user.totp_enabled_at is not None or not user.totp_secret_ciphertext:
        raise ApiError("mfa_not_pending", 409)
    secret = decrypt(cipher_for(settings), user.totp_secret_ciphertext)
    img = qrcode.make(mfa.provisioning_uri(secret, user.email, settings.brand_name_en), box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/mfa/enable")
async def mfa_enable(
    body: MfaCodeIn,
    request: Request,
    response: Response,
    current: CurrentAuth,
    db: SessionDep,
    settings: SettingsDep,
) -> RecoveryCodesOut:
    """Confirm the first code: 2FA is on, recovery codes are shown once, other sessions are signed out."""
    user = current.user
    if user.totp_enabled_at is not None:
        raise ApiError("mfa_already_enabled", 409)
    await _check_code(db, user, body.code, settings, pending=True)
    codes, hashes = mfa.new_recovery_codes()
    user.totp_enabled_at = datetime.now(UTC)
    user.recovery_codes = hashes
    await auth.revoke_all_sessions(db, user, "mfa_enabled")
    auth.audit(db, "user.mfa_enabled", user.id)
    session = await auth.start_session(
        db, user, settings, request.headers.get("user-agent"), "mfa_enable", mfa=True
    )
    set_session_cookies(response, session, settings)
    return RecoveryCodesOut(recovery_codes=codes)


@router.post("/mfa/recovery-codes")
async def mfa_new_recovery_codes(
    body: MfaCodeIn, current: CurrentAuth, db: SessionDep, settings: SettingsDep
) -> RecoveryCodesOut:
    user = current.user
    if user.totp_enabled_at is None:
        raise ApiError("mfa_not_pending", 409)
    await _check_code(db, user, body.code, settings)
    codes, hashes = mfa.new_recovery_codes()
    user.recovery_codes = hashes
    auth.audit(db, "user.mfa_recovery_regenerated", user.id)
    await db.commit()
    return RecoveryCodesOut(recovery_codes=codes)


@router.post("/mfa/disable")
async def mfa_disable(
    body: MfaCodeIn, current: CurrentAuth, db: SessionDep, settings: SettingsDep
) -> UserOut:
    user = current.user
    if user.role == UserRole.admin:
        raise ApiError("admin_requires_2fa", 403)
    if user.totp_enabled_at is None:
        return UserOut.of(user)
    await _check_code(db, user, body.code, settings)
    user.totp_enabled_at = None
    user.totp_secret_ciphertext = None
    user.totp_last_step = None
    user.recovery_codes = []
    auth.audit(db, "user.mfa_disabled", user.id)
    await db.commit()
    return UserOut.of(user)


# ---- Google ------------------------------------------------------------------------------------


def _safe_next(path: str | None) -> str:
    """Only same-site relative paths (no open redirects)."""
    if not path or not path.startswith("/") or path.startswith("//") or "\\" in path:
        return "/"
    return path


def _redirect_uri(settings: ApiSettings) -> str:
    return f"{settings.web_base_url.rstrip('/')}{GOOGLE_PATH}/callback"


async def _google_config(db: SessionDep, settings: ApiSettings) -> tuple[str, str] | None:
    """(client_id, client_secret) when Google sign-in is enabled and configured in the admin."""
    values = (await runtime_settings.current(db, settings)).values
    cid, secret = values.get("google_client_id") or "", values.get("google_client_secret") or ""
    return (cid, secret) if values.get("google_login_enabled") and cid and secret else None


@router.get("/google/start")
async def google_start(db: SessionDep, settings: SettingsDep, next: str | None = None) -> RedirectResponse:
    cfg = await _google_config(db, settings)
    if cfg is None:
        raise ApiError("google_disabled", 404)
    client_id, _ = cfg
    state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    blob = sign_state(
        {"state": state, "nonce": nonce, "next": _safe_next(next)}, settings.jwt_secret.get_secret_value()
    )
    response = RedirectResponse(
        google.authorize_url(client_id, _redirect_uri(settings), state, nonce),
        status_code=302,
    )
    response.set_cookie(
        OAUTH_COOKIE,
        blob,
        max_age=600,
        path=GOOGLE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        domain=settings.cookie_domain,
    )
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request, db: SessionDep, settings: SettingsDep, code: str | None = None, state: str | None = None
) -> RedirectResponse:
    web = settings.web_base_url.rstrip("/")
    failed = RedirectResponse(f"{web}/ar/login?error=google_failed", status_code=302)
    failed.delete_cookie(OAUTH_COOKIE, path=GOOGLE_PATH, domain=settings.cookie_domain)
    cfg = await _google_config(db, settings)
    if cfg is None or not code or not state:
        return failed
    client_id, client_secret = cfg
    try:
        saved = read_state(request.cookies.get(OAUTH_COOKIE, ""), settings.jwt_secret.get_secret_value())
        if not secrets.compare_digest(saved.get("state", ""), state):
            return failed
        id_token = await google.exchange_code(code, client_id, client_secret, _redirect_uri(settings))
        identity = google.verify_id_token(id_token, client_id, saved["nonce"])
    except (TokenInvalid, ValueError, KeyError, httpx.HTTPError, jwt.PyJWTError):
        return failed
    if not identity.email_verified or not identity.email:
        return failed
    user = await _user_for_google(db, identity)
    if not user.is_active:
        return failed
    session = await auth.start_session(db, user, settings, request.headers.get("user-agent"), "google")
    response = RedirectResponse(f"{web}{_safe_next(saved.get('next'))}", status_code=302)
    response.delete_cookie(OAUTH_COOKIE, path=GOOGLE_PATH, domain=settings.cookie_domain)
    set_session_cookies(response, session, settings)
    return response


async def _user_for_google(db: SessionDep, identity: google.GoogleIdentity) -> User:
    user = (await db.execute(select(User).where(User.google_sub == identity.sub))).scalar_one_or_none()
    if user is not None:
        return user
    user = await auth.find_user_by_email(db, identity.email)
    if user is not None:  # verified Google email → link to the existing account
        user.google_sub = identity.sub
        user.email_verified_at = user.email_verified_at or datetime.now(UTC)
        auth.audit(db, "user.google_linked", user.id)
        return user
    user = User(
        email=identity.email,
        password_hash=None,
        full_name=identity.name[:120] or identity.email,
        google_sub=identity.sub,
        email_verified_at=datetime.now(UTC),
        role=UserRole.parent,
        locale=Locale.ar,
    )
    db.add(user)
    await db.flush()
    auth.audit(db, "user.registered", user.id, method="google")
    return user
