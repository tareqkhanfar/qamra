"""/api/auth — register, login, refresh, logout, me, Google sign-in."""

import secrets
from datetime import UTC, datetime

import httpx
import jwt
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from qamra_api import ratelimit, runtime_settings
from qamra_api.auth import google
from qamra_api.auth import service as auth
from qamra_api.auth.schemas import LoginIn, PasswordChangeIn, RegisterIn, UserOut
from qamra_api.deps import (
    ACCESS_COOKIE,
    OAUTH_COOKIE,
    REFRESH_COOKIE,
    CurrentUser,
    RedisDep,
    SessionDep,
    SettingsDep,
)
from qamra_api.errors import ApiError
from qamra_api.security import TokenInvalid, read_state, sign_state
from qamra_api.settings import ApiSettings
from qamra_core.db.models import Locale, User, UserRole

router = APIRouter(prefix="/api/auth", tags=["auth"])
REFRESH_PATH = "/api/auth"
GOOGLE_PATH = "/api/auth/google"


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
) -> UserOut:
    per_email, per_ip = ratelimit.login_keys(client_ip(request), body.email)
    window = settings.login_window_seconds
    if (
        await ratelimit.hit(redis, per_ip, window) > settings.login_ip_max_attempts
        or await ratelimit.hit(redis, per_email, window) > settings.login_max_attempts
    ):
        raise ApiError("too_many_attempts", 429)
    user = await auth.authenticate(db, body.email, body.password)
    await ratelimit.reset(redis, per_email)
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
    return UserOut.of(session.user)


@router.post("/logout", status_code=204)
async def logout(request: Request, db: SessionDep, settings: SettingsDep) -> Response:
    await auth.logout(db, request.cookies.get(REFRESH_COOKIE))
    response = Response(status_code=204)
    clear_session_cookies(response, settings)
    return response


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.of(user)


@router.post("/password")
async def change_password(
    body: PasswordChangeIn,
    request: Request,
    response: Response,
    user: CurrentUser,
    db: SessionDep,
    redis: RedisDep,
    settings: SettingsDep,
) -> UserOut:
    """Change password; signs out every other session (all refresh tokens revoked, new one issued)."""
    key = f"rl:password:{user.id}"
    if await ratelimit.hit(redis, key, settings.login_window_seconds) > settings.login_max_attempts:
        raise ApiError("too_many_attempts", 429)
    await auth.change_password(db, user, body.current_password, body.new_password)
    await ratelimit.reset(redis, key)
    session = await auth.start_session(
        db, user, settings, request.headers.get("user-agent"), "password_change"
    )
    set_session_cookies(response, session, settings)
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
