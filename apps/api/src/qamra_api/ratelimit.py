"""Fixed-window counters in Redis (login brute-force protection)."""

import hashlib

from redis.asyncio import Redis


async def hit(redis: Redis, key: str, window_seconds: int) -> int:
    """Increment the counter for `key` and return the count within the current window."""
    async with redis.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, window_seconds, nx=True)
        count, _ = await pipe.execute()
    return int(count)


async def reset(redis: Redis, key: str) -> None:
    await redis.delete(key)


def login_keys(ip: str, email: str) -> tuple[str, str]:
    """Emails are hashed so Redis never holds them in clear text."""
    email_hash = hashlib.sha256(email.lower().encode()).hexdigest()[:24]
    return f"rl:login:{ip}:{email_hash}", f"rl:login-ip:{ip}"
