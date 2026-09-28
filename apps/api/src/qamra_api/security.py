"""Passwords (argon2), access JWTs, opaque refresh tokens."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

_hasher = PasswordHash.recommended()  # argon2id
_DUMMY_HASH = _hasher.hash("timing-equalizer-not-a-real-password")
JWT_ALG = "HS256"
MIN_PASSWORD_LENGTH = 8


# The most common passwords seen in breach corpora (plus local favourites). Anything here is refused.
_COMMON = frozenset(
    [
        "123456",
        "1234567",
        "12345678",
        "123456789",
        "1234567890",
        "0123456789",
        "password",
        "password1",
        "password123",
        "qwerty",
        "qwerty123",
        "qwertyuiop",
        "abc123",
        "abcd1234",
        "111111",
        "11111111",
        "000000",
        "00000000",
        "123123",
        "123123123",
        "12341234",
        "1q2w3e4r",
        "1q2w3e4r5t",
        "iloveyou",
        "welcome",
        "admin",
        "admin123",
        "letmein",
        "monkey",
        "dragon",
        "sunshine",
        "princess",
        "football",
        "baseball",
        "superman",
        "trustno1",
        "passw0rd",
        "p@ssw0rd",
        "p@ssword",
        "987654321",
        "99999999",
        "88888888",
        "12344321",
        "147258369",
        "159753",
        "7777777",
        "palestine",
        "palestine1",
        "jordan123",
        "qamra",
        "qamra123",
        "moon1234",
        "moonlight",
    ]
)


def is_common_password(password: str) -> bool:
    p = password.lower()
    return p in _COMMON or len(set(p)) <= 2


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Always runs one argon2 verification so unknown emails cost the same time as known ones."""
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False
    return _hasher.verify(password, password_hash)


@dataclass(frozen=True)
class AccessClaims:
    user_id: uuid.UUID
    role: str
    expires_at: datetime


class TokenExpired(Exception):
    pass


class TokenInvalid(Exception):
    pass


def create_access_token(user_id: uuid.UUID, role: str, secret: str, minutes: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, secret, algorithm=JWT_ALG)


def decode_access_token(token: str, secret: str) -> AccessClaims:
    try:
        payload = jwt.decode(
            token, secret, algorithms=[JWT_ALG], leeway=10, options={"require": ["exp", "iat", "sub"]}
        )
    except jwt.ExpiredSignatureError as e:
        raise TokenExpired from e
    except jwt.PyJWTError as e:
        raise TokenInvalid from e
    if payload.get("typ") != "access":
        raise TokenInvalid
    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError as e:
        raise TokenInvalid from e
    return AccessClaims(user_id, str(payload.get("role", "")), datetime.fromtimestamp(payload["exp"], UTC))


def new_refresh_token() -> tuple[str, str]:
    """→ (raw token for the cookie, sha256 hex for the database)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_refresh_token(raw)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def sign_state(payload: dict[str, str], secret: str, minutes: int = 10) -> str:
    """Short-lived signed blob (OAuth state/nonce cookie)."""
    now = datetime.now(UTC)
    return jwt.encode(
        {**payload, "typ": "oauth", "iat": now, "exp": now + timedelta(minutes=minutes)},
        secret,
        algorithm=JWT_ALG,
    )


def read_state(token: str, secret: str) -> dict[str, str]:
    try:
        payload = jwt.decode(token, secret, algorithms=[JWT_ALG])
    except jwt.PyJWTError as e:
        raise TokenInvalid from e
    if payload.get("typ") != "oauth":
        raise TokenInvalid
    return {k: str(v) for k, v in payload.items() if k not in ("typ", "iat", "exp")}
