"""Orquestra a leitura pública da PTAX sem acesso ao PostgreSQL."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
from loguru import logger
from pydantic import ValidationError

from .cache import CacheEntry, PtaxCache
from .ptax import BcbPtaxClient, PtaxResponse, public_response, SAO_PAULO


class PtaxService:
    def __init__(self, cache: PtaxCache, client: BcbPtaxClient, ttl_seconds: int = 900) -> None:
        self.cache = cache
        self.client = client
        self.ttl_seconds = max(60, min(ttl_seconds, 43200))

    async def get(self, now: datetime | None = None) -> PtaxResponse:
        now = now or datetime.now(timezone.utc)
        shared = await self.cache.redis_ready()
        fresh = await self.cache.get_fresh(shared)
        if fresh:
            return public_response(fresh.quote, now, fresh.synced_at, "NORMAL")
        last = await self._valid_last(shared, now)
        if not shared and not self.cache.single_worker_fallback:
            return public_response(last.quote if last else None, now, last.synced_at if last else None, "FONTE_INDISPONIVEL" if last else "INDISPONIVEL")
        token = await self.cache.acquire(shared)
        if token is None:
            return await self._wait_or_fallback(shared, last, now)
        try:
            fresh = await self.cache.get_fresh(shared)
            if fresh:
                return public_response(fresh.quote, now, fresh.synced_at, "NORMAL")
            try:
                quote = await self.client.fetch(now)
                if quote is None:
                    return self._fallback(last, now)
                entry = CacheEntry(quote=quote, synced_at=datetime.now(timezone.utc))
                ttl = self._ttl(now, quote.dataHoraBoletimIso)
                await self.cache.save(entry, ttl, shared)
                return public_response(entry.quote, now, entry.synced_at, "NORMAL")
            except (httpx.HTTPError, ValueError, ValidationError, TimeoutError, OSError) as exc:
                logger.warning("PTAX upstream/cache indisponível", error_type=type(exc).__name__)
                return self._fallback(last, now)
        finally:
            await self.cache.release(token, shared)

    async def _valid_last(self, shared: bool, now: datetime) -> CacheEntry | None:
        entry = await self.cache.get_last(shared)
        if not entry:
            return None
        age = (now.astimezone(SAO_PAULO).date() - entry.quote.dataHoraBoletimIso.astimezone(SAO_PAULO).date()).days
        return entry if 0 <= age <= 7 else None

    async def _wait_or_fallback(self, shared: bool, last: CacheEntry | None, now: datetime) -> PtaxResponse:
        for _ in range(5):
            if last:
                break
            await asyncio.sleep(0.3)
            fresh = await self.cache.get_fresh(shared)
            if fresh:
                return public_response(fresh.quote, now, fresh.synced_at, "NORMAL")
        return self._fallback(last, now)

    @staticmethod
    def _fallback(last: CacheEntry | None, now: datetime) -> PtaxResponse:
        return public_response(last.quote if last else None, now, last.synced_at if last else None, "FONTE_INDISPONIVEL" if last else "INDISPONIVEL")

    def _ttl(self, now: datetime, bulletin: datetime) -> int:
        local = now.astimezone(SAO_PAULO)
        if local.weekday() >= 5:
            return min(self.ttl_seconds * 4, 21600)
        if bulletin.astimezone(SAO_PAULO).date() < local.date():
            return min(self.ttl_seconds, 900)
        return min(self.ttl_seconds * 2, 3600)
