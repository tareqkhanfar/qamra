"""Two-factor sign-in with TOTP (RFC 6238, any authenticator app) and single-use recovery codes.

- The secret is stored encrypted with the same Fernet keys as admin secrets; the browser sees it only
  once, during setup.
- A code is accepted for the previous, current and next 30-second step, and never twice: the last used
  step is stored, which stops replay of an observed code.
- Recovery codes are stored as sha256 hashes and removed when used.
"""

import hashlib
import hmac
import secrets
import time
from datetime import UTC, datetime

import pyotp

RECOVERY_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no look-alikes (0/o, 1/l/i)
RECOVERY_COUNT = 10


def new_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, account: str, issuer: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=account, issuer_name=issuer)


def _digits(code: str) -> str:
    return "".join(ch for ch in code if ch.isdigit())


def match_step(secret: str, code: str, last_step: int | None, now: float | None = None) -> int | None:
    """The time step `code` belongs to (±1 step), or None. Steps at or before `last_step` never match."""
    code = _digits(code)
    if len(code) != 6:
        return None
    totp = pyotp.TOTP(secret)
    current = totp.timecode(datetime.fromtimestamp(now if now is not None else time.time(), UTC))
    for step in (current - 1, current, current + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(totp.generate_otp(step), code):
            return step
    return None


def hash_recovery(code: str) -> str:
    normalized = "".join(ch for ch in code.lower() if ch.isalnum())
    return hashlib.sha256(normalized.encode()).hexdigest()


def new_recovery_codes(n: int = RECOVERY_COUNT) -> tuple[list[str], list[str]]:
    """(codes to show once, hashes to store)."""
    codes = []
    for _ in range(n):
        raw = "".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(10))
        codes.append(f"{raw[:5]}-{raw[5:]}")
    return codes, [hash_recovery(c) for c in codes]


def consume_recovery(hashes: list[str], code: str) -> list[str] | None:
    """The remaining hashes when `code` matches one (it is used up), else None."""
    digest = hash_recovery(code)
    for h in hashes:
        if hmac.compare_digest(h, digest):
            return [x for x in hashes if x != h]
    return None
