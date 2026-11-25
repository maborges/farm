"""Rate limit específico para solicitação pública de demonstração na landing page."""

from __future__ import annotations

import asyncio
import hashlib
import time

from core.config import settings

DEMO_REQUEST_MAX_ATTEMPTS = 5
DEMO_REQUEST_WINDOW_SECONDS = 900


class DemoRequestRateLimiter:
    """Janela fixa por IP, com Redis e fallback conservador em memória."""

    _attempts: dict[str, tuple[int, float]] = {}
    _lock = asyncio.Lock()

    @classmethod
    async def consume(cls, ip_address: str | None) -> tuple[bool, int]:
        """
        Consome uma tentativa de solicitação de demonstração para o IP informado.

        Args:
            ip_address: Endereço IP de origem da requisição ou None.

        Return:
            Tupla `(permitido, retry_after_segundos)`.

        Raises:
            Nenhuma exceção é propagada; falhas de Redis recorrem ao fallback em memória.
        """
        identity = hashlib.sha256((ip_address or "unknown").encode()).hexdigest()
        key = f"identity:demo-request:{identity}"
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
                    await client.expire(key, DEMO_REQUEST_WINDOW_SECONDS)
                ttl = max(1, await client.ttl(key))
                return count <= DEMO_REQUEST_MAX_ATTEMPTS, ttl
            finally:
                await client.aclose()
        except Exception:
            return await cls._consume_memory(identity)

    @classmethod
    async def _consume_memory(cls, identity: str) -> tuple[bool, int]:
        now = time.monotonic()
        async with cls._lock:
            count, expires_at = cls._attempts.get(identity, (0, now + DEMO_REQUEST_WINDOW_SECONDS))
            if expires_at <= now:
                count, expires_at = 0, now + DEMO_REQUEST_WINDOW_SECONDS
            count += 1
            cls._attempts[identity] = (count, expires_at)
            return count <= DEMO_REQUEST_MAX_ATTEMPTS, max(1, int(expires_at - now))

    @classmethod
    async def reset_for_tests(cls) -> None:
        """
        Limpa o estado em memória do rate limiter entre execuções de teste.

        Args:
            Nenhum.

        Return:
            None.

        Raises:
            Nenhuma exceção é lançada.
        """
        async with cls._lock:
            cls._attempts.clear()
