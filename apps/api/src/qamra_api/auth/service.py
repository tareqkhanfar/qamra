"""Auth use-cases. Refresh tokens rotate on every use; re-use of a rotated token revokes the family."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.errors import ApiError
from qamra_api.security import (
    MIN_PASSWORD_LENGTH,
    create_access_token,
    hash_password,
    hash_refresh_token,
    is_common_password,
    new_refresh_token,
    verify_password,
)
from qamra_api.settings import ApiSettings
from qamra_core.db.models import AuditLog, Locale, RefreshToken, User, UserRole


@dataclass(frozen=True)
class Session:
    user: User
    access_token: str
    refresh_token: str  # raw, only ever sent as an httpOnly cookie
    mfa: bool = False


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def find_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == normalize_email(email)))
    return result.scalar_one_or_none()


def audit(
    db: AsyncSession, action: str, user_id: uuid.UUID | None, entity_id: object = None, **data: object
) -> None:
    db.add(
        AuditLog(
            actor_user_id=user_id,
            action=action,
            entity_type="user",
            entity_id=str(entity_id or user_id) if (entity_id or user_id) else None,
            data=data,
        )
    )


def check_password_strength(password: str, email: str = "") -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ApiError("weak_password", 422)
    if is_common_password(password) or (email and password.lower() == email.lower().split("@")[0]):
        raise ApiError("common_password", 422)


async def register(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    locale: Locale,
    role: UserRole = UserRole.parent,
) -> User:
    check_password_strength(password, email)
    if await find_user_by_email(db, email) is not None:
        raise ApiError("email_taken", 409)
    user = User(
        email=normalize_email(email),
        password_hash=hash_password(password),
        full_name=full_name,
        locale=locale,
        role=role,
    )
    db.add(user)
    await db.flush()
    audit(db, "user.registered", user.id, method="password")
    return user


async def change_password(db: AsyncSession, user: User, current: str, new: str) -> None:
    if user.password_hash is None or not verify_password(current, user.password_hash):
        raise ApiError("wrong_password", 403)
    check_password_strength(new, user.email)
    user.password_hash = hash_password(new)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revoked_reason="password_change")
    )
    audit(db, "user.password_changed", user.id)
    await db.flush()


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await find_user_by_email(db, email)
    if not verify_password(password, user.password_hash if user else None) or user is None:
        raise ApiError("invalid_credentials", 401)
    if not user.is_active:
        raise ApiError("account_disabled", 403)
    return user


async def _issue(
    db: AsyncSession,
    user: User,
    settings: ApiSettings,
    family_id: uuid.UUID,
    user_agent: str | None,
    mfa: bool = False,
) -> Session:
    raw, digest = new_refresh_token()
    now = datetime.now(UTC)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=digest,
            family_id=family_id,
            expires_at=now + timedelta(days=settings.refresh_token_days),
            user_agent=(user_agent or "")[:300] or None,
            mfa=mfa,
        )
    )
    access = create_access_token(
        user.id,
        user.role.value,
        settings.jwt_secret.get_secret_value(),
        settings.access_token_minutes,
        mfa=mfa,
    )
    return Session(user=user, access_token=access, refresh_token=raw, mfa=mfa)


async def start_session(
    db: AsyncSession,
    user: User,
    settings: ApiSettings,
    user_agent: str | None,
    method: str,
    mfa: bool = False,
) -> Session:
    user.last_login_at = datetime.now(UTC)
    session = await _issue(db, user, settings, uuid.uuid4(), user_agent, mfa=mfa)
    audit(db, "user.login", user.id, method=method, mfa=mfa)
    await db.commit()
    return session


async def revoke_all_sessions(db: AsyncSession, user: User, reason: str) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revoked_reason=reason[:16])
    )


ROTATION_GRACE = timedelta(seconds=30)  # two tabs refreshing at once must not look like theft


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID, reason: str) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC), revoked_reason=reason)
    )


async def rotate(db: AsyncSession, raw: str | None, settings: ApiSettings, user_agent: str | None) -> Session:
    if not raw:
        raise ApiError("not_authenticated", 401)
    token = (
        await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)).with_for_update()
        )
    ).scalar_one_or_none()
    if token is None:
        raise ApiError("not_authenticated", 401)
    now = datetime.now(UTC)
    in_grace = (
        token.revoked_reason == "rotated"
        and token.revoked_at is not None
        and now - token.revoked_at < ROTATION_GRACE
    )
    if token.revoked_at is not None and not in_grace:
        # a rotated or logged-out token came back: assume theft, end the whole login
        await _revoke_family(db, token.family_id, "reuse")
        audit(db, "user.refresh_reuse_detected", token.user_id)
        await db.commit()
        raise ApiError("not_authenticated", 401)
    if token.expires_at <= now:
        raise ApiError("token_expired", 401)
    user = await db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise ApiError("not_authenticated", 401)
    if token.revoked_at is None:
        token.revoked_at, token.revoked_reason = now, "rotated"
    session = await _issue(db, user, settings, token.family_id, user_agent, mfa=token.mfa)
    await db.commit()
    return session


async def logout(db: AsyncSession, raw: str | None) -> None:
    if not raw:
        return
    token = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)))
    ).scalar_one_or_none()
    if token is not None:
        await _revoke_family(db, token.family_id, "logout")
        audit(db, "user.logout", token.user_id)
        await db.commit()
