"""Rate limit específico do cadastro gratuito, sem consultar o banco comercial."""

from __future__ import annotations

import asyncio
import hashlib
import time

from core.config import settings


class FreeRegistrationRateLimiter:
    """Janela fixa por IP, com Redis e fallback conservador em memória."""

    _attempts: dict[str, tuple[int, float]] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def consume(cls, ip_address: str | None) -> tuple[bool, int]:
        identity = hashlib.sha256((ip_address or "unknown").encode()).hexdigest()
        key = f"identity:register-free:{identity}"
        try:
            import redis.asyncio as redis

            client = redis.from_url(
                settings.redis_url,
                socket_connect_timeout=0.15,
                socket_timeout=0.15,
                decode_responses=True,
            )
            try:
                count = await client.incr(key)
                if count == 1:
                    await client.expire(key, settings.free_registration_window_seconds)
                ttl = max(1, await client.ttl(key))
                return count <= settings.free_registration_max_attempts, ttl
            finally:
                await client.aclose()
        except Exception:
            return await cls._consume_memory(identity)

    @classmethod
    async def _consume_memory(cls, identity: str) -> tuple[bool, int]:
        now = time.monotonic()
        window = settings.free_registration_window_seconds
        async with cls._lock:
            count, expires_at = cls._attempts.get(identity, (0, now + window))
            if expires_at <= now:
                count, expires_at = 0, now + window
            count += 1
            cls._attempts[identity] = (count, expires_at)
            return count <= settings.free_registration_max_attempts, max(1, int(expires_at - now))

    @classmethod
    async def reset_for_tests(cls) -> None:
        async with cls._lock:
            cls._attempts.clear()
