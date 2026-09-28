"""Google sign-in (OpenID Connect, authorization-code flow). Enabled when GOOGLE_CLIENT_ID/SECRET are set."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"  # nosec B105  (public endpoint, not a secret)
JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = ("https://accounts.google.com", "accounts.google.com")

_jwks = jwt.PyJWKClient(JWKS_URL, cache_keys=True)


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    email_verified: bool
    name: str


def authorize_url(client_id: str, redirect_uri: str, state: str, nonce: str) -> str:
    return (
        AUTH_URL
        + "?"
        + urlencode(
            {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "nonce": nonce,
                "prompt": "select_account",
            }
        )
    )


async def exchange_code(code: str, client_id: str, client_secret: str, redirect_uri: str) -> str:
    """→ raw id_token."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
    resp.raise_for_status()
    id_token = resp.json().get("id_token")
    if not id_token:
        raise ValueError("no id_token in Google response")
    return str(id_token)


def verify_id_token(id_token: str, client_id: str, nonce: str) -> GoogleIdentity:
    key = _jwks.get_signing_key_from_jwt(id_token)
    claims: dict[str, Any] = jwt.decode(
        id_token, key.key, algorithms=["RS256"], audience=client_id, issuer=ISSUERS, leeway=30
    )
    if claims.get("nonce") != nonce:
        raise ValueError("nonce mismatch")
    if claims.get("exp", 0) < datetime.now(UTC).timestamp() - 30:
        raise ValueError("expired id_token")
    return GoogleIdentity(
        sub=str(claims["sub"]),
        email=str(claims.get("email", "")).lower(),
        email_verified=bool(claims.get("email_verified")),
        name=str(claims.get("name") or claims.get("email", "")),
    )
