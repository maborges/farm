# ruff: noqa: UP017
"""Serviço de orquestração do clima público com isolamento comercial e resiliência."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from loguru import logger

from .adapters import (
    ProviderQuotaExceededError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnlicensedError,
    WeatherProvider,
)
from .cache import ClimaCache, ClimaCacheEntry
from .contracts import ClimaPrevisaoResponse
from .grid import GeoGridPolicy


class CoordinateValidationError(ValueError):
    """Exceção levantada quando as coordenadas geográficas são inválidas."""


class PublicClimaService:
    """Orquestrador público de dados meteorológicos.

    Garante isolamento absoluto de banco comercial, política de cache por grid
    espacial, concorrência controlada e fallback automático para contingência.
    """

    def __init__(
        self,
        cache: ClimaCache,
        provider: WeatherProvider,
        grid_policy: GeoGridPolicy | None = None,
        ttl_seconds: int = 1800,
        monthly_quota_limit: int = 0,
    ) -> None:
        self.cache = cache
        self.provider = provider
        self.grid_policy = grid_policy or GeoGridPolicy(step_degrees=0.05)
        self.ttl_seconds = max(60, min(ttl_seconds, 3600))
        self.monthly_quota_limit = max(0, monthly_quota_limit)

    async def get_previsao(
        self, lat: float, lon: float, now: datetime | None = None
    ) -> ClimaPrevisaoResponse:
        """Obtém a previsão do tempo para as coordenadas indicadas.

        Args:
            lat: Latitude em graus decimais (-90 a 90).
            lon: Longitude em graus decimais (-180 a 180).
            now: Timestamp de referência (opcional, padrão UTC atual).

        Returns:
            ClimaPrevisaoResponse contendo dados atuais, horários e diários.

        Raises:
            CoordinateValidationError: Se as coordenadas estiverem fora dos limites.
            ProviderUnlicensedError: Se o provedor não possuir licença autorizada.
            ProviderQuotaExceededError: Se a franquia mensal de chamadas for atingida.
            ProviderUnavailableError: Se o provedor falhar e não houver cache de contingência.
        """
        self._validar_coordenadas(lat, lon)
        now = now or datetime.now(timezone.utc)
        lat_grid, lon_grid = self.grid_policy.quantize(lat, lon)
        cache_key = f"{lat_grid:.4f}:{lon_grid:.4f}"
        provider_id = getattr(self.provider, "provider_id", "DESCONHECIDO")

        shared = await self.cache.redis_ready()

        # 1. Tentar leitura do cache recente
        fresh = await self.cache.get_fresh(cache_key, shared)
        if fresh:
            await self.cache.record_cache_hit(provider_id, shared)
            return self._formatar_resposta(
                fresh.response, lat, lon, em_cache=True, desatualizado=False
            )

        await self.cache.record_cache_miss(provider_id, shared)

        # 2. Adquirir lock atômico por nó de grid para evitar requisições redundantes
        lease_id = await self.cache.acquire(cache_key, shared)
        if lease_id is None:
            return await self._aguardar_concorrencia(cache_key, shared, lat, lon)

        try:
            # Revalida se outro worker preencheu o cache durante a disputa do lock
            fresh = await self.cache.get_fresh(cache_key, shared)
            if fresh:
                await self.cache.record_cache_hit(provider_id, shared)
                return self._formatar_resposta(
                    fresh.response, lat, lon, em_cache=True, desatualizado=False
                )

            # Verificar limite interno de cota mensal apenas se o provedor não for orquestrador dinâmico
            is_dynamic = hasattr(self.provider, "get_active_config")
            if not is_dynamic and self.monthly_quota_limit > 0:
                quota_ok = await self.cache.check_monthly_quota(
                    provider_id, self.monthly_quota_limit, shared
                )
                if not quota_ok:
                    await self.cache.record_error(provider_id, "quota_exceeded", shared)
                    last = await self.cache.get_last(cache_key, shared)
                    if last:
                        return self._formatar_resposta(
                            last.response, lat, lon, em_cache=True, desatualizado=True
                        )
                    raise ProviderQuotaExceededError(
                        f"Franquia mensal do provedor {provider_id} esgotada."
                    )

            try:
                if not is_dynamic:
                    await self.cache.record_upstream_call(provider_id, shared)
                forecast = await self.provider.fetch_forecast(lat_grid, lon_grid)
                # O MVP público anuncia um horizonte máximo de três dias. A
                # resposta permanece variável; nenhum dia ausente é sintetizado.
                forecast.previsaoDiaria = forecast.previsaoDiaria[:3]
            except Exception as exc:
                err_type = "timeout" if isinstance(exc, ProviderTimeoutError) else "failure"
                if not is_dynamic:
                    await self.cache.record_error(provider_id, err_type, shared)
                logger.warning(
                    "Falha ao consultar provedor meteorológico",
                    provider=provider_id,
                    lat=lat_grid,
                    lon=lon_grid,
                    error=str(exc),
                )
                last = await self.cache.get_last(cache_key, shared)
                if last:
                    return self._formatar_resposta(
                        last.response, lat, lon, em_cache=True, desatualizado=True
                    )
                raise

            # Preenche metadados definitivos e persiste no cache
            effective_ttl = self.ttl_seconds
            if is_dynamic:
                try:
                    cfg = await self.provider.get_active_config()
                    effective_ttl = cfg.cache_ttl_seconds
                except Exception:
                    pass
            effective_ttl = max(60, min(effective_ttl, 3600))

            forecast.latitude = lat
            forecast.longitude = lon
            forecast.latitudeGrid = lat_grid
            forecast.longitudeGrid = lon_grid
            forecast.validoAteIso = datetime.fromtimestamp(
                now.timestamp() + effective_ttl, tz=timezone.utc
            )

            entry = ClimaCacheEntry(response=forecast, synced_at=now)
            await self.cache.save(cache_key, entry, effective_ttl, shared)
            return self._formatar_resposta(
                forecast, lat, lon, em_cache=False, desatualizado=False
            )

        finally:
            await self.cache.release(cache_key, lease_id, shared)

    @staticmethod
    def _validar_coordenadas(lat: float, lon: float) -> None:
        """Valida os intervalos admissíveis de latitude e longitude."""
        if not (-90.0 <= lat <= 90.0):
            raise CoordinateValidationError(
                f"Latitude inválida ({lat}). O valor deve estar entre -90.0 e 90.0."
            )
        if not (-180.0 <= lon <= 180.0):
            raise CoordinateValidationError(
                f"Longitude inválida ({lon}). O valor deve estar entre -180.0 e 180.0."
            )

    async def _aguardar_concorrencia(
        self,
        cache_key: str,
        shared: bool,
        lat: float,
        lon: float,
    ) -> ClimaPrevisaoResponse:
        """Aguarda a finalização de requisição concorrente para a mesma coordenada."""
        for _ in range(15):
            await asyncio.sleep(0.2)
            fresh = await self.cache.get_fresh(cache_key, shared)
            if fresh:
                return self._formatar_resposta(
                    fresh.response, lat, lon, em_cache=True, desatualizado=False
                )

        last = await self.cache.get_last(cache_key, shared)
        if last:
            return self._formatar_resposta(
                last.response, lat, lon, em_cache=True, desatualizado=True
            )

        raise ProviderUnavailableError("Serviço meteorológico temporariamente ocupado.")

    @staticmethod
    def _formatar_resposta(
        resp: ClimaPrevisaoResponse,
        lat: float,
        lon: float,
        em_cache: bool,
        desatualizado: bool,
    ) -> ClimaPrevisaoResponse:
        """Copia e ajusta os metadados de entrega para a requisição corrente."""
        status = "DESATUALIZADO" if desatualizado else "NORMAL"
        return resp.model_copy(
            update={
                "latitude": lat,
                "longitude": lon,
                "emCache": em_cache,
                "desatualizado": desatualizado,
                "statusOperacional": status,
            }
        )
