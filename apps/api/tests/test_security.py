import uuid

import pytest
from qamra_api.security import (
    TokenInvalid,
    create_access_token,
    decode_access_token,
    hash_password,
    read_state,
    sign_state,
    verify_password,
)
from qamra_api.settings import ApiSettings

SECRET = "x" * 40


def test_password_hash_roundtrip() -> None:
    h = hash_password("moonlight-2026")
    assert h.startswith("$argon2id$")
    assert verify_password("moonlight-2026", h) and not verify_password("wrong", h)
    assert not verify_password("anything", None)


def test_access_token_roundtrip() -> None:
    uid = uuid.uuid4()
    claims = decode_access_token(create_access_token(uid, "parent", SECRET, 15), SECRET)
    assert claims.user_id == uid and claims.role == "parent"


def test_oauth_state_is_not_an_access_token() -> None:
    blob = sign_state({"state": "s"}, SECRET)
    assert read_state(blob, SECRET) == {"state": "s"}
    with pytest.raises(TokenInvalid):
        decode_access_token(blob, SECRET)


def test_prod_requires_real_secret_and_secure_cookies() -> None:
    with pytest.raises(ValueError):
        ApiSettings(_env_file=None, env="prod", cookie_secure=True)  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        ApiSettings(_env_file=None, env="prod", jwt_secret="y" * 40, cookie_secure=False)  # type: ignore[call-arg]
    ok = ApiSettings(_env_file=None, env="prod", jwt_secret="y" * 40, cookie_secure=True)  # type: ignore[call-arg]
    assert ok.env == "prod"
