"""Encryption for secrets at rest (admin-managed API keys etc.). Fernet = AES-128-CBC + HMAC-SHA256."""

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from qamra_core.settings import CoreSettings

# Dev/test only. Production refuses to start without SETTINGS_ENCRYPTION_KEYS (see CoreSettings).
DEV_KEY = "ZGV2LW9ubHktcWFtcmEta2V5LW5vdC1mb3ItcHJvZCE="


class DecryptError(Exception):
    pass


@lru_cache(maxsize=4)
def _cipher(keys: str) -> MultiFernet:
    return MultiFernet([Fernet(k.strip().encode()) for k in keys.split(",") if k.strip()])


def cipher_for(settings: CoreSettings) -> MultiFernet:
    keys = (
        settings.settings_encryption_keys.get_secret_value() if settings.settings_encryption_keys else DEV_KEY
    )
    return _cipher(keys)


def encrypt(cipher: MultiFernet, plaintext: str) -> str:
    return cipher.encrypt(plaintext.encode()).decode()


def decrypt(cipher: MultiFernet, token: str) -> str:
    try:
        return cipher.decrypt(token.encode()).decode()
    except InvalidToken as e:
        raise DecryptError("secret could not be decrypted (wrong or rotated-out key)") from e
