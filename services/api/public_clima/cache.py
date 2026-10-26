"""Infraestrutura de cache em dois níveis (Redis + Memória) para o clima público."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from uuid import uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict
from redis.asyncio import Redis

from .contracts import ClimaPrevisaoResponse

FRESH_PREFIX = "agro:clima:v1:fresh:"
LAST_PREFIX = "agro:clima:v1:last:"
LOCK_PREFIX = "agro:clima:v1:lock:"
RATE_PREFIX = "agro:clima:v1:rate:"
METRICS_PREFIX = "agro:clima:v1:metrics:"
MAX_COMBINED_CACHE_SECONDS = 60 * 60


class ClimaCacheEntry(BaseModel):
    """Envelope de cache com registro temporal de sincronização."""

    model_config = ConfigDict(extra="forbid")

    response: ClimaPrevisaoResponse
    synced_at: datetime


class ClimaCache:
    """Gerencia cache volátil em Redis com fallback em memória de processo."""

    def __init__(self, redis_url: str, single_worker_fallback: bool = True) -> None:
        self.redis = Redis.from_url(redis_url, socket_connect_timeout=0.25, socket_timeout=0.25)
        self.single_worker_fallback = single_worker_fallback
        self.local_fresh: dict[str, tuple[ClimaCacheEntry, float]] = {}
        self.local_last: dict[str, tuple[ClimaCacheEntry, float]] = {}
        self.local_locks: dict[str, asyncio.Lock] = {}
        self.local_rate: dict[str, tuple[int, float]] = {}
        self.local_metrics: dict[str, int] = {}

    async def close(self) -> None:
        """Encerra conexões ativas com o Redis."""
        try:
            await self.redis.aclose()
        except Exception as exc:
            logger.debug("Erro ao fechar conexão com Redis", error=str(exc))

    async def redis_ready(self) -> bool:
        """Verifica se o Redis compartilhado está pronto e responsivo."""
        try:
            return bool(await self.redis.ping())
        except Exception:
            return False

    async def get_fresh(self, key: str, shared: bool) -> ClimaCacheEntry | None:
        """Recupera dado recente do cache se ainda estiver dentro do TTL."""
        def within_retention(entry: ClimaCacheEntry | None) -> ClimaCacheEntry | None:
            if entry is None:
                return None
            synced_at = entry.synced_at
            if synced_at.tzinfo is None:
                synced_at = synced_at.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - synced_at).total_seconds()
            return entry if 0 <= age < MAX_COMBINED_CACHE_SECONDS else None

        if shared:
            try:
                raw = await self.redis.get(FRESH_PREFIX + key)
                entry = ClimaCacheEntry.model_validate_json(raw) if raw else None
                if entry and not within_retention(entry):
                    await self.redis.delete(FRESH_PREFIX + key)
                    return None
                return entry
            except Exception as exc:
                logger.debug("Falha na leitura de cache recente no Redis", key=key, error=str(exc))

        if self.single_worker_fallback and key in self.local_fresh:
            entry, expire_at = self.local_fresh[key]
            if expire_at > time.monotonic() and within_retention(entry):
                return entry
            self.local_fresh.pop(key, None)

        return None

    async def get_last(self, key: str, shared: bool) -> ClimaCacheEntry | None:
        """Recupera o último dado válido conhecido para contingência/stale."""
        def store_local(entry: ClimaCacheEntry) -> None:
            synced_at = entry.synced_at
            if synced_at.tzinfo is None:
                synced_at = synced_at.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - synced_at).total_seconds()
            if 0 <= age < MAX_COMBINED_CACHE_SECONDS:
                self.local_last[key] = (
                    entry,
                    time.monotonic() + MAX_COMBINED_CACHE_SECONDS - age,
                )

        def within_retention(entry: ClimaCacheEntry | None) -> ClimaCacheEntry | None:
            if entry is None:
                return None
            synced_at = entry.synced_at
            if synced_at.tzinfo is None:
                synced_at = synced_at.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - synced_at).total_seconds()
            if age < 0 or age >= MAX_COMBINED_CACHE_SECONDS:
                self.local_last.pop(key, None)
                return None
            return entry

        if shared:
            try:
                raw = await self.redis.get(LAST_PREFIX + key)
                entry = ClimaCacheEntry.model_validate_json(raw) if raw else None
                entry = within_retention(entry)
                if raw and entry is None:
                    await self.redis.delete(LAST_PREFIX + key)
                if entry:
                    store_local(entry)
                return entry
            except Exception as exc:
                logger.debug("Falha na leitura de último dado no Redis", key=key, error=str(exc))

        cached = self.local_last.get(key)
        if cached is None:
            return None
        entry, expire_at = cached
        if expire_at <= time.monotonic():
            self.local_last.pop(key, None)
            return None
        return within_retention(entry)

    async def save(self, key: str, entry: ClimaCacheEntry, ttl: int, shared: bool) -> None:
        """Persiste dado no cache recente e na área de contingência."""
        ttl = max(1, min(ttl, MAX_COMBINED_CACHE_SECONDS))
        synced_at = entry.synced_at
        if synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=timezone.utc)
        age = max(0.0, (datetime.now(timezone.utc) - synced_at).total_seconds())
        self.local_last[key] = (
            entry,
            time.monotonic() + max(0.0, MAX_COMBINED_CACHE_SECONDS - age),
        )
        if len(self.local_last) > 10000:
            now_mono = time.monotonic()
            self.local_last = {k: v for k, v in self.local_last.items() if v[1] > now_mono}
        if shared:
            try:
                raw = entry.model_dump_json()
                await self.redis.set(FRESH_PREFIX + key, raw, ex=ttl)
                await self.redis.set(LAST_PREFIX + key, raw, ex=MAX_COMBINED_CACHE_SECONDS)
                return
            except Exception as exc:
                logger.warning("Falha ao persistir no Redis compartilhado", key=key, error=str(exc))

        if self.single_worker_fallback:
            self.local_fresh[key] = (entry, time.monotonic() + ttl)

    async def acquire(self, key: str, shared: bool) -> str | None:
        """Adquire lock atômico por coordenada para evitar chamadas externas simultâneas."""
        if shared:
            lease_id = uuid4().hex
            try:
                ok = await self.redis.set(LOCK_PREFIX + key, lease_id, nx=True, px=15000)
                return lease_id if ok else None
            except Exception as exc:
                logger.debug("Falha ao adquirir lock no Redis", key=key, error=str(exc))

        if self.single_worker_fallback:
            if key not in self.local_locks:
                self.local_locks[key] = asyncio.Lock()
            lock = self.local_locks[key]
            if not lock.locked():
                await lock.acquire()
                return "local"

        return None

    async def release(self, key: str, lease_id: str, shared: bool) -> None:
        """Libera o lock atômico da coordenada."""
        if shared and lease_id != "local":
            script = (
                "if redis.call('GET',KEYS[1]) == ARGV[1] then "
                "return redis.call('DEL',KEYS[1]) else return 0 end"
            )
            try:
                await self.redis.eval(script, 1, LOCK_PREFIX + key, lease_id)
            except Exception as exc:
                logger.debug("Falha ao liberar lock no Redis", key=key, error=str(exc))
        elif lease_id == "local" and key in self.local_locks:
            lock = self.local_locks[key]
            if lock.locked():
                lock.release()

    async def allow_request(
        self, bucket: str, shared: bool, max_requests: int = 60, window_seconds: int = 60
    ) -> bool:
        """Limita requisições anônimas por bucket/IP para proteção contra abusos."""
        if shared:
            script = (
                "local n=redis.call('INCR',KEYS[1]); "
                "if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end; "
                "return n"
            )
            try:
                res = await self.redis.eval(script, 1, RATE_PREFIX + bucket, window_seconds)
                return int(res) <= max_requests
            except Exception as exc:
                logger.debug(
                    "Falha ao verificar rate limit no Redis", bucket=bucket, error=str(exc)
                )

        if not self.single_worker_fallback:
            return False

        now = time.monotonic()
        count, start = self.local_rate.get(bucket, (0, now))
        if now - start >= window_seconds:
            count, start = 0, now
        self.local_rate[bucket] = (count + 1, start)

        if len(self.local_rate) > 10000:
            self.local_rate = {
                k: v for k, v in self.local_rate.items() if now - v[1] < window_seconds
            }

        return count < max_requests

    def _current_month_key(self, provider: str) -> str:
        """Gera a chave de cota e métricas no formato provedor:AAAA-MM.

        Args:
            provider: Identificador do provedor meteorológico.

        Returns:
            Chave composta com ano e mês UTC.
        """
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        return f"{provider.lower()}:{month}"

    async def record_upstream_call(self, provider: str, shared: bool) -> int:
        """Registra chamada externa upstream realizada ao fornecedor.

        Args:
            provider: Nome do provedor.
            shared: Indicador de disponibilidade do Redis compartilhado.

        Returns:
            Total acumulado de chamadas no mês corrente.
        """
        key = f"upstream:{self._current_month_key(provider)}"
        self.local_metrics[key] = self.local_metrics.get(key, 0) + 1
        if shared:
            try:
                val = await self.redis.incr(METRICS_PREFIX + key)
                await self.redis.expire(METRICS_PREFIX + key, 90 * 86400)
                return int(val)
            except Exception as exc:
                logger.debug("Falha ao registrar chamada upstream no Redis", error=str(exc))
        return self.local_metrics[key]

    async def record_cache_hit(self, provider: str, shared: bool) -> None:
        """Registra ocorrência de cache hit para o provedor."""
        key = f"hit:{provider.lower()}"
        self.local_metrics[key] = self.local_metrics.get(key, 0) + 1
        if shared:
            try:
                await self.redis.incr(METRICS_PREFIX + key)
            except Exception as exc:
                logger.debug("Falha ao registrar cache hit no Redis", error=str(exc))

    async def record_cache_miss(self, provider: str, shared: bool) -> None:
        """Registra ocorrência de cache miss para o provedor."""
        key = f"miss:{provider.lower()}"
        self.local_metrics[key] = self.local_metrics.get(key, 0) + 1
        if shared:
            try:
                await self.redis.incr(METRICS_PREFIX + key)
            except Exception as exc:
                logger.debug("Falha ao registrar cache miss no Redis", error=str(exc))

    async def record_error(self, provider: str, error_type: str, shared: bool) -> None:
        """Registra erro ou timeout operacional para diagnóstico."""
        key = f"error:{provider.lower()}:{error_type}"
        self.local_metrics[key] = self.local_metrics.get(key, 0) + 1
        if shared:
            try:
                await self.redis.incr(METRICS_PREFIX + key)
            except Exception as exc:
                logger.debug("Falha ao registrar erro no Redis", error=str(exc))

    async def reserve_monthly_quota(
        self, provider: str, limit: int, shared: bool
    ) -> tuple[bool, int]:
        """Reserva atomicamente 1 chamada da cota mensal antes da requisição externa.

        Utiliza script Lua no Redis para eliminar a janela de concorrência (TOCTOU).
        Na indisponibilidade do Redis, aplica política conservadora degradada
        para mitigar estouro acidental de franquia entre workers independentes.

        Args:
            provider: Nome do provedor meteorológico.
            limit: Limite máximo mensal (0 = ilimitado).
            shared: Indicador de disponibilidade do Redis compartilhado.

        Returns:
            Tupla (reservado: bool, contagem_atual: int).
        """
        if limit <= 0:
            return True, 0

        key = f"upstream:{self._current_month_key(provider)}"
        full_key = METRICS_PREFIX + key

        if shared:
            # Script Lua atômico: valida se current < limit antes de incrementar
            script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local current = tonumber(redis.call('get', key) or '0')
            if limit > 0 and current >= limit then
                return {0, current}
            end
            local new_val = redis.call('incr', key)
            redis.call('expire', key, 90 * 86400)
            return {1, new_val}
            """
            try:
                res = await self.redis.eval(script, 1, full_key, limit)
                reserved = bool(res[0] == 1)
                count = int(res[1])
                self.local_metrics[key] = count
                return reserved, count
            except Exception as exc:
                logger.debug(
                    "Falha ao executar reserva atômica de cota no Redis, aplicando fallback conservador",
                    error=str(exc),
                )

        # Política conservadora degradada sem Redis:
        # Divide a franquia para evitar que N workers consumam N * limit chamadas
        conservative_limit = max(1, limit // 10) if not self.single_worker_fallback else limit
        current = self.local_metrics.get(key, 0)
        if current >= conservative_limit:
            return False, current

        self.local_metrics[key] = current + 1
        return True, current + 1

    async def rollback_quota_reservation(self, provider: str, shared: bool) -> None:
        """Estorna 1 unidade de cota caso a chamada falhe antes do consumo upstream."""
        key = f"upstream:{self._current_month_key(provider)}"
        full_key = METRICS_PREFIX + key
        self.local_metrics[key] = max(0, self.local_metrics.get(key, 1) - 1)
        if shared:
            try:
                script = """
                local key = KEYS[1]
                local current = tonumber(redis.call('get', key) or '0')
                if current > 0 then
                    return redis.call('decr', key)
                end
                return 0
                """
                await self.redis.eval(script, 1, full_key)
            except Exception as exc:
                logger.debug("Falha ao estornar cota no Redis", error=str(exc))

    async def check_monthly_quota(self, provider: str, limit: int, shared: bool) -> bool:
        """Verifica se a franquia mensal de chamadas upstream ainda está disponível.

        Args:
            provider: Nome do provedor.
            limit: Limite numérico mensal de chamadas.
            shared: Indicador de uso do Redis compartilhado.

        Returns:
            True se a cota não foi excedida; False caso contrário.
        """
        if limit <= 0:
            return True
        key = f"upstream:{self._current_month_key(provider)}"
        current = 0
        if shared:
            try:
                val = await self.redis.get(METRICS_PREFIX + key)
                if val:
                    current = int(val)
            except Exception as exc:
                logger.debug("Falha ao consultar cota no Redis", error=str(exc))
                current = self.local_metrics.get(key, 0)
        else:
            current = self.local_metrics.get(key, 0)
        return current < limit

    async def get_metrics(self, provider: str, shared: bool) -> dict[str, int]:
        """Recupera métricas operacionais consolidadas sem expor dados sensíveis.

        Args:
            provider: Nome do provedor.
            shared: Indicador de uso do Redis compartilhado.

        Returns:
            Dicionário com contadores de upstream, hits, misses e erros.
        """
        p = provider.lower()
        up_k = f"upstream:{self._current_month_key(provider)}"
        metrics = {
            "upstream_calls_month": self.local_metrics.get(up_k, 0),
            "cache_hits": self.local_metrics.get(f"hit:{p}", 0),
            "cache_misses": self.local_metrics.get(f"miss:{p}", 0),
            "timeouts": self.local_metrics.get(f"error:{p}:timeout", 0),
            "failures": self.local_metrics.get(f"error:{p}:failure", 0),
        }
        if shared:
            try:
                pipe = self.redis.pipeline()
                for k in [up_k, f"hit:{p}", f"miss:{p}", f"error:{p}:timeout", f"error:{p}:failure"]:
                    pipe.get(METRICS_PREFIX + k)
                vals = await pipe.execute()
                keys = ["upstream_calls_month", "cache_hits", "cache_misses", "timeouts", "failures"]
                for i, key_name in enumerate(keys):
                    if vals[i]:
                        metrics[key_name] = int(vals[i])
            except Exception as exc:
                logger.debug("Falha ao recuperar métricas no Redis", error=str(exc))
        return metrics
