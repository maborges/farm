"""Cache isolado para indicadores macroeconômicos do BCB."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from redis.asyncio import Redis

from .sgs import IndicadoresMacroPayload

FRESH_KEY = "agro:macro:v1:fresh"
LAST_KEY = "agro:macro:v1:last"
LOCK_KEY = "agro:macro:v1:lock"
RATE_PREFIX = "agro:macro:v1:rate:"


class MacroCacheEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: IndicadoresMacroPayload
    synced_at: datetime


class MacroCache:
    def __init__(self, redis_url: str, single_worker_fallback: bool = False) -> None:
        self.redis = Redis.from_url(redis_url, socket_connect_timeout=0.25, socket_timeout=0.25)
        self.single_worker_fallback = single_worker_fallback
        self.local_fresh: tuple[MacroCacheEntry, float] | None = None
        self.local_last: MacroCacheEntry | None = None
        self.local_lock = asyncio.Lock()
        self.local_rate: dict[str, tuple[int, float]] = {}

    async def close(self) -> None:
        await self.redis.aclose()

    async def redis_ready(self) -> bool:
        try:
            return bool(await self.redis.ping())
        except Exception:
            return False

    async def get_fresh(self, shared: bool) -> MacroCacheEntry | None:
        if shared:
            try:
                raw = await self.redis.get(FRESH_KEY)
                return MacroCacheEntry.model_validate_json(raw) if raw else None
            except Exception:
                return None
        if self.single_worker_fallback and self.local_fresh and self.local_fresh[1] > time.monotonic():
            return self.local_fresh[0]
        return None

    async def get_last(self, shared: bool) -> MacroCacheEntry | None:
        if shared:
            try:
                raw = await self.redis.get(LAST_KEY)
                entry = MacroCacheEntry.model_validate_json(raw) if raw else None
                if entry:
                    self.local_last = entry
                return entry
            except Exception:
                return self.local_last
        return self.local_last

    async def save(self, entry: MacroCacheEntry, ttl: int, shared: bool) -> None:
        self.local_last = entry
        if shared:
            try:
                await self.redis.set(FRESH_KEY, entry.model_dump_json(), ex=ttl)
                await self.redis.set(LAST_KEY, entry.model_dump_json(), ex=30 * 86400)
            except Exception:
                pass
        elif self.single_worker_fallback:
            self.local_fresh = (entry, time.monotonic() + ttl)

    async def acquire(self, shared: bool) -> str | None:
        if shared:
            token = uuid4().hex
            try:
                return token if await self.redis.set(LOCK_KEY, token, nx=True, px=16000) else None
            except Exception:
                return None
        if self.single_worker_fallback and not self.local_lock.locked():
            await self.local_lock.acquire()
            return "local"
        return None

    async def release(self, token: str, shared: bool) -> None:
        if shared:
            script = "if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('DEL',KEYS[1]) else return 0 end"
            try:
                await self.redis.eval(script, 1, LOCK_KEY, token)
            except Exception:
                pass
        elif token == "local" and self.local_lock.locked():
            self.local_lock.release()

    async def allow_request(self, key: str, shared: bool) -> bool:
        if shared:
            script = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n"
            try:
                return int(await self.redis.eval(script, 1, RATE_PREFIX + key)) <= 60
            except Exception:
                return False
        if not self.single_worker_fallback:
            return False
        now = time.monotonic()
        count, start = self.local_rate.get(key, (0, now))
        if now - start >= 60:
            count, start = 0, now
        self.local_rate[key] = (count + 1, start)
        if len(self.local_rate) > 10000:
            self.local_rate = {k: v for k, v in self.local_rate.items() if now - v[1] < 60}
        return count < 60
