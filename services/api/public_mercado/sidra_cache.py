"""Cache de 2 níveis (Redis + Local Memory) e proteção de concorrência para consultas SIDRA/IBGE."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict
from redis.asyncio import Redis

from .sidra import EstatisticasIbgeResponse, MunicipiosIbgeResponse

FRESH_PREFIX = "agro:sidra:v1:fresh:"
LAST_PREFIX = "agro:sidra:v1:last:"
LOCK_PREFIX = "agro:sidra:v1:lock:"
RATE_PREFIX = "agro:sidra:v1:rate:"
MUN_PREFIX = "agro:sidra:v1:mun:"


class SidraCacheEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: EstatisticasIbgeResponse
    synced_at: datetime


class SidraMunicipiosEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: MunicipiosIbgeResponse
    synced_at: datetime


class SidraCache:
    """Cache resiliente para o subsistema IBGE/SIDRA."""

    def __init__(self, redis_url: str, single_worker_fallback: bool = False) -> None:
        self.redis = Redis.from_url(redis_url, socket_connect_timeout=0.25, socket_timeout=0.25)
        self.single_worker_fallback = single_worker_fallback
        self.local_fresh: dict[str, tuple[SidraCacheEntry, float]] = {}
        self.local_last: dict[str, SidraCacheEntry] = {}
        self.local_mun: dict[str, tuple[SidraMunicipiosEntry, float]] = {}
        self.local_locks: dict[str, asyncio.Lock] = {}
        self.local_rate: dict[str, tuple[int, float]] = {}

    async def close(self) -> None:
        await self.redis.aclose()

    async def redis_ready(self) -> bool:
        try:
            return bool(await self.redis.ping())
        except Exception:
            return False

    async def get_fresh(self, key: str, shared: bool) -> SidraCacheEntry | None:
        if shared:
            try:
                raw = await self.redis.get(FRESH_PREFIX + key)
                return SidraCacheEntry.model_validate_json(raw) if raw else None
            except Exception:
                return None
        if self.single_worker_fallback:
            cached = self.local_fresh.get(key)
            if cached and cached[1] > time.monotonic():
                return cached[0]
        return None

    async def get_last(self, key: str, shared: bool) -> SidraCacheEntry | None:
        if shared:
            try:
                raw = await self.redis.get(LAST_PREFIX + key)
                entry = SidraCacheEntry.model_validate_json(raw) if raw else None
                if entry:
                    self.local_last[key] = entry
                return entry
            except Exception:
                return self.local_last.get(key)
        return self.local_last.get(key)

    async def save(self, key: str, entry: SidraCacheEntry, ttl: int, shared: bool) -> None:
        self.local_last[key] = entry
        if shared:
            try:
                data = entry.model_dump_json()
                await self.redis.set(FRESH_PREFIX + key, data, ex=ttl)
                await self.redis.set(LAST_PREFIX + key, data, ex=30 * 86400)
            except Exception:
                pass
        elif self.single_worker_fallback:
            self.local_fresh[key] = (entry, time.monotonic() + ttl)
            if len(self.local_fresh) > 500:
                now_m = time.monotonic()
                self.local_fresh = {k: v for k, v in self.local_fresh.items() if v[1] > now_m}

    async def acquire(self, key: str, shared: bool) -> str | None:
        if shared:
            token = uuid4().hex
            try:
                lock_key = LOCK_PREFIX + key
                return token if await self.redis.set(lock_key, token, nx=True, px=15000) else None
            except Exception:
                return None
        if self.single_worker_fallback:
            lock = self.local_locks.setdefault(key, asyncio.Lock())
            if not lock.locked():
                await lock.acquire()
                return "local"
        return None

    async def release(self, key: str, token: str, shared: bool) -> None:
        if shared:
            script = "if redis.call('GET',KEYS[1]) == ARGV[1] then return redis.call('DEL',KEYS[1]) else return 0 end"
            try:
                await self.redis.eval(script, 1, LOCK_PREFIX + key, token)
            except Exception:
                pass
        elif token == "local":
            lock = self.local_locks.get(key)
            if lock and lock.locked():
                lock.release()

    async def allow_request(self, key: str, shared: bool, limit: int = 60) -> bool:
        if shared:
            script = "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],60) end; return n"
            try:
                return int(await self.redis.eval(script, 1, RATE_PREFIX + key)) <= limit
            except Exception:
                return False
        if not self.single_worker_fallback:
            return False
        now = time.monotonic()
        count, start = self.local_rate.get(key, (0, now))
        if now - start >= 60:
            count, start = 0, now
        self.local_rate[key] = (count + 1, start)
        if len(self.local_rate) > 5000:
            self.local_rate = {k: v for k, v in self.local_rate.items() if now - v[1] < 60}
        return count < limit

    async def get_municipios(self, uf: str, shared: bool) -> MunicipiosIbgeResponse | None:
        key = MUN_PREFIX + uf
        if shared:
            try:
                raw = await self.redis.get(key)
                return MunicipiosIbgeResponse.model_validate_json(raw) if raw else None
            except Exception:
                return None
        cached = self.local_mun.get(uf)
        if cached and cached[1] > time.monotonic():
            return cached[0].payload
        return None

    async def save_municipios(
        self, uf: str, resp: MunicipiosIbgeResponse, ttl: int, shared: bool
    ) -> None:
        entry = SidraMunicipiosEntry(payload=resp, synced_at=datetime.now())
        self.local_mun[uf] = (entry, time.monotonic() + ttl)
        if shared:
            try:
                await self.redis.set(MUN_PREFIX + uf, resp.model_dump_json(), ex=ttl)
            except Exception:
                pass
