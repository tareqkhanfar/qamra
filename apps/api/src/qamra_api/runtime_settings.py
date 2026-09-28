"""Admin-managed settings for request handlers, with a short in-process cache (cleared on admin save)."""

import time

from sqlalchemy.ext.asyncio import AsyncSession

from qamra_api.settings import ApiSettings
from qamra_core import settings_store
from qamra_core.crypto import cipher_for
from qamra_core.settings_store import Resolved

_cache: tuple[float, Resolved] | None = None


async def current(db: AsyncSession, settings: ApiSettings) -> Resolved:
    global _cache
    now = time.monotonic()
    if (
        _cache is not None
        and settings.settings_cache_seconds > 0
        and now - _cache[0] < settings.settings_cache_seconds
    ):
        return _cache[1]
    resolved = await settings_store.load(db, cipher_for(settings))
    _cache = (now, resolved)
    return resolved


def invalidate() -> None:
    global _cache
    _cache = None
