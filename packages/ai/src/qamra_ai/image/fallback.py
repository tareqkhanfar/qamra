"""Primary → fallback image provider (Addendum 3 §1).

The primary gets `switch_after` attempts (default 2, exponential backoff between them). Only then does the
request go to the fallback, and the switch is logged and recorded in the image params so the book shows
it. Transient errors on the fallback are retried too. Content blocks are not retried on the same provider
(a new seed from the page loop is the better retry), but they do count as a failed primary attempt: a
false positive on one provider's filter must not leave a child's page empty. Our own QA safety check
still runs on whatever comes back.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import replace

import structlog

from qamra_ai.errors import ContentBlocked, InvalidOutput, ProviderConfigError, ProviderError
from qamra_ai.image.base import GeneratedImage, ImageProvider, ImageRequest

log = structlog.get_logger("qamra.ai.image")

Sleep = Callable[[float], Awaitable[None]]
_PRIMARY_FAILURES = (ProviderError, ProviderConfigError, ContentBlocked, InvalidOutput)


def backoff(attempt: int, base: float = 2.0, cap: float = 30.0) -> float:
    """Exponential backoff with jitter: ~2s, ~4s, ~8s …"""
    delay: float = min(cap, base * 2 ** (attempt - 1))
    return delay * random.uniform(0.8, 1.2)  # nosec B311 (jitter, not security)


class FallbackImageProvider:
    def __init__(
        self,
        primary: ImageProvider,
        fallback: ImageProvider | None = None,
        *,
        switch_after: int = 2,
        fallback_attempts: int = 2,
        base_delay: float = 2.0,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self.primary, self.fallback = primary, fallback
        self.name, self.model = primary.name, primary.model
        self.switch_after = max(1, switch_after)
        self.fallback_attempts = max(1, fallback_attempts)
        self._base = base_delay
        self._sleep = sleep
        self.switches = 0  # requests that ended up on the fallback (reported per book)

    async def generate(self, req: ImageRequest) -> GeneratedImage:
        errors: list[str] = []
        last: Exception = ProviderError("no attempt made")
        for attempt in range(1, self.switch_after + 1):
            try:
                return await self.primary.generate(req)
            except _PRIMARY_FAILURES as e:
                errors.append(f"{type(e).__name__}: {e}")
                log.warning(
                    "image.primary_failed",
                    step=req.step,
                    model=self.primary.model,
                    attempt=attempt,
                    error=type(e).__name__,
                    detail=str(e)[:200],
                )
                if self.fallback is None and not isinstance(e, ProviderError):
                    raise
                if attempt < self.switch_after and not isinstance(e, ContentBlocked):
                    await self._sleep(backoff(attempt, self._base))
                last = e
        if self.fallback is None:
            raise last
        self.switches += 1
        log.warning(
            "image.fallback_switch",
            step=req.step,
            primary=self.primary.model,
            fallback=self.fallback.model,
            primary_errors=errors,
        )
        for attempt in range(1, self.fallback_attempts + 1):
            try:
                result = await self.fallback.generate(req)
            except ProviderError as e:
                errors.append(f"fallback {type(e).__name__}: {e}")
                if attempt == self.fallback_attempts:
                    raise
                await self._sleep(backoff(attempt, self._base))
                continue
            return replace(
                result,
                params={**result.params, "fallback_from": self.primary.model, "primary_errors": errors},
            )
        raise ProviderError("fallback exhausted")  # pragma: no cover (loop always returns or raises)
