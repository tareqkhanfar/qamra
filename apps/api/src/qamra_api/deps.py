"""FastAPI dependencies: settings, db session, redis, storage, current user, roles, CSRF header."""

import ipaddress
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api import runtime_settings
from qamra_api.errors import ApiError
from qamra_api.security import AccessClaims, TokenExpired, TokenInvalid, decode_access_token
from qamra_api.settings import ApiSettings
from qamra_core.db.models import User, UserRole
from qamra_core.db.store import UserStaffRole
from qamra_core.permissions import allowed
from qamra_core.storage import ObjectStorage

ACCESS_COOKIE = "qamra_at"
REFRESH_COOKIE = "qamra_rt"
OAUTH_COOKIE = "qamra_oauth"
CLIENT_HEADER = "x-qamra-client"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def get_settings_dep(request: Request) -> ApiSettings:
    settings: ApiSettings = request.app.state.settings
    return settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


def get_redis(request: Request) -> Redis:
    redis: Redis = request.app.state.redis
    return redis


def get_storage(request: Request) -> ObjectStorage:
    storage: ObjectStorage = request.app.state.storage
    return storage


SettingsDep = Annotated[ApiSettings, Depends(get_settings_dep)]
SessionDep = Annotated[AsyncSession, Depends(get_session)]
RedisDep = Annotated[Redis, Depends(get_redis)]
StorageDep = Annotated[ObjectStorage, Depends(get_storage)]


async def require_client_header(request: Request) -> None:
    """CSRF defence: browsers can't add custom headers cross-site without a CORS preflight,
    and the API allows no cross-origin requests. Combined with SameSite=Lax cookies."""
    if request.method in UNSAFE_METHODS and not request.headers.get(CLIENT_HEADER):
        raise ApiError("bad_request", 403)


@dataclass(frozen=True)
class Auth:
    user: User
    claims: AccessClaims


async def current_auth(request: Request, session: SessionDep, settings: SettingsDep) -> Auth:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise ApiError("not_authenticated", 401)
    try:
        claims = decode_access_token(token, settings.jwt_secret.get_secret_value())
    except TokenExpired as e:
        raise ApiError("token_expired", 401) from e
    except TokenInvalid as e:
        raise ApiError("not_authenticated", 401) from e
    user = await session.get(User, claims.user_id)
    if user is None:
        raise ApiError("not_authenticated", 401)
    if not user.is_active:
        raise ApiError("account_disabled", 403)
    return Auth(user, claims)


CurrentAuth = Annotated[Auth, Depends(current_auth)]


async def optional_user(request: Request, session: SessionDep, settings: SettingsDep) -> User | None:
    """The signed-in user, or None for guests: the store works without an account (Addendum 4 §5)."""
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        return None
    try:
        claims = decode_access_token(token, settings.jwt_secret.get_secret_value())
    except (TokenExpired, TokenInvalid):
        return None
    user = await session.get(User, claims.user_id)
    return user if user is not None and user.is_active else None


OptionalUser = Annotated[User | None, Depends(optional_user)]


async def current_user(auth: CurrentAuth) -> User:
    return auth.user


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    async def _check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ApiError("forbidden", 403)
        return user

    return _check


def ip_allowed(ip: str, allowlist: str) -> bool:
    """Empty allowlist = no limit. Otherwise the client IP must fall inside one of the networks."""
    if not allowlist.strip():
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    nets = [ipaddress.ip_network(n.strip(), strict=False) for n in allowlist.split(",") if n.strip()]
    return any(addr in net for net in nets)


async def require_admin(
    request: Request, auth: CurrentAuth, session: SessionDep, settings: SettingsDep
) -> User:
    """Admin endpoints (Addendum 3 §6): admin role, a 2FA-verified session, the optional IP allowlist."""
    if auth.user.role != UserRole.admin:
        raise ApiError("forbidden", 403)
    values = (await runtime_settings.current(session, settings)).values
    client = request.client.host if request.client else ""
    if not ip_allowed(client, str(values.get("admin_ip_allowlist") or "")):
        raise ApiError("ip_not_allowed", 403)
    if auth.user.totp_enabled_at is None:
        raise ApiError("mfa_setup_required", 403)
    if not auth.claims.mfa:
        raise ApiError("mfa_required", 403)
    return auth.user


AdminUser = Annotated[User, Depends(require_admin)]


def require_permission(permission: str) -> Callable[..., Awaitable[User]]:
    """A 2FA-verified staff member whose roles grant `permission` (qamra_core.permissions)."""

    async def _check(user: AdminUser, session: SessionDep) -> User:
        roles = (
            await session.execute(select(UserStaffRole.role).where(UserStaffRole.user_id == user.id))
        ).scalars()
        if not allowed(roles, permission):
            raise ApiError("forbidden", 403)
        return user

    return _check
