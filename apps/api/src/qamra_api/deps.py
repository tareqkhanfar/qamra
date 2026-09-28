"""FastAPI dependencies: settings, db session, redis, storage, current user, roles, CSRF header."""

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from qamra_core.db.models import User, UserRole
from qamra_core.storage import ObjectStorage
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.errors import ApiError
from qamra_api.security import TokenExpired, TokenInvalid, decode_access_token
from qamra_api.settings import ApiSettings

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


async def current_user(request: Request, session: SessionDep, settings: SettingsDep) -> User:
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
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_role(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    async def _check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ApiError("forbidden", 403)
        return user

    return _check
