"""Orquestrador dinâmico de provedores climáticos com chaveamento em tempo de execução.

Permite alternar provedores (WeatherAPI, OpenWeather, Open-Meteo), configurar timeouts,
definir cadeia de fallback e limites de cota sem exigir reinício de FastAPI/Uvicorn.
Sincroniza workers via Redis Pub/Sub e mantém clientes HTTP reutilizáveis.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

UTC = timezone.utc

import httpx
from loguru import logger

from core.config import settings
from core.database import async_session_maker
from core.schemas.agro_config_schemas import (
    KEY_CLIMA,
    AgroClimaConfig,
)
from core.services.agro_config_service import agro_config_service
from core.services.platform_weather_credentials import PlatformWeatherCredentialsService

from .adapters import (
    OpenMeteoAdapter,
    OpenWeatherOneCallAdapter,
    ProviderAuthenticationError,
    ProviderError,
    ProviderQuotaExceededError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnconfiguredError,
    WeatherAPIAdapter,
    WeatherProvider,
    is_provider_authorized_for_public,
)
from .cache import ClimaCache
from .contracts import ClimaPrevisaoResponse


class DynamicWeatherOrchestrator:
    """Orquestrador meteorológico resiliente com chaveamento dinâmico e fallback em cadeia."""

    def __init__(
        self,
        cache: ClimaCache,
        refresh_ttl: float = 30.0,
    ) -> None:
        self.cache = cache
        self.refresh_ttl = refresh_ttl
        self._config: AgroClimaConfig = AgroClimaConfig(
            active_provider=settings.clima_active_provider.upper(),
            fallback_chain=["WEATHERAPI", "OPENWEATHER", "OPEN_METEO"],
            timeout_seconds=settings.clima_timeout_seconds,
            cache_ttl_seconds=settings.clima_cache_ttl_seconds,
            monthly_quota_limit=settings.weatherapi_monthly_quota_limit,
            openweather_licensed=settings.openweather_licensed,
            open_meteo_licensed=settings.open_meteo_licensed,
        )
        self._config_revision: int = 0
        self._last_refresh: float = 0.0
        self._adapters: dict[str, WeatherProvider] = {}
        self._test_adapters: dict[str, WeatherProvider] = {}
        self._http_clients: dict[str, httpx.AsyncClient] = {}
        self._credentials: dict[str, str | None] = {}
        self._lock = asyncio.Lock()
        self._sub_task: asyncio.Task | None = None
        self._quota_alerted_80: set[str] = set()
        self._quota_alerted_95: set[str] = set()

    @property
    def provider_id(self) -> str:
        return self._config.active_provider

    @property
    def is_licensed(self) -> bool:
        return True

    async def initialize(self) -> None:
        """Inicializa configurações iniciais e assina eventos do Redis."""
        await self.refresh_config()
        self._start_redis_listener()

    def _start_redis_listener(self) -> None:
        """Inicia escuta em segundo plano de invalidações publicadas no Redis."""
        if self._sub_task is not None and not self._sub_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
            self._sub_task = loop.create_task(self._listen_redis_events())
        except RuntimeError:
            pass

    async def _listen_redis_events(self) -> None:
        """Loop de escuta no canal 'agro:config:events' para invalidação imediata."""
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe("agro:config:events")
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                if msg and isinstance(msg.get("data"), str):
                    try:
                        data = json.loads(msg["data"])
                        event = data.get("event")
                        chave = data.get("chave")
                        if event in ("config_updated", "credentials_updated") and (
                            chave == KEY_CLIMA or data.get("provider") or not chave
                        ):
                            logger.info("Invalidação de configuração recebida via Redis Pub/Sub", data=data)
                            self.invalidate_cache()
                    except Exception as err:
                        logger.debug("Erro ao decodificar mensagem do canal agro:config:events", error=str(err))
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.debug("Ouvinte do Redis desativado ou indisponível", error=str(exc))

    def invalidate_cache(self) -> None:
        """Força a revalidação imediata das configurações na próxima consulta."""
        self._last_refresh = 0.0

    async def get_active_config(self) -> AgroClimaConfig:
        """Retorna a configuração climática ativa, atualizando se expirada."""
        now = time.monotonic()
        if now - self._last_refresh > self.refresh_ttl:
            async with self._lock:
                if now - self._last_refresh > self.refresh_ttl:
                    await self.refresh_config()
        return self._config

    async def refresh_config(self) -> None:
        """Recarrega a configuração e credenciais do banco com fallback resiliente."""
        source = settings.clima_config_source.strip().lower()
        if source == "environment":
            # Modo explícito para deployments públicos sem dependência de PostgreSQL.
            # Não consulta nem tenta abrir sessão no banco neste caminho.
            self._config = AgroClimaConfig(
                active_provider=settings.clima_active_provider.upper(),
                fallback_chain=[],
                timeout_seconds=settings.clima_timeout_seconds,
                cache_ttl_seconds=settings.clima_cache_ttl_seconds,
                monthly_quota_limit=settings.weatherapi_monthly_quota_limit,
                openweather_licensed=settings.openweather_licensed,
                open_meteo_licensed=settings.open_meteo_licensed,
            )
            self._credentials = {
                "WEATHERAPI": settings.weatherapi_api_key or None,
                "OPENWEATHER": settings.openweather_api_key or None,
            }
            self._rebuild_adapters()
            self._last_refresh = time.monotonic()
            return
        if source != "database":
            raise ValueError("CLIMA_CONFIG_SOURCE deve ser 'database' ou 'environment'.")
        try:
            async with async_session_maker() as session:
                valor, meta, ativo = await agro_config_service.get_config(session, KEY_CLIMA)
                if valor:
                    self._config = AgroClimaConfig.model_validate(valor)

                # Recarrega credenciais dos provedores
                self._credentials["WEATHERAPI"] = await PlatformWeatherCredentialsService.get_decrypted_key(
                    session, "WEATHERAPI"
                )
                self._credentials["OPENWEATHER"] = await PlatformWeatherCredentialsService.get_decrypted_key(
                    session, "OPENWEATHER"
                )
        except Exception as exc:
            logger.debug(
                "Falha ao carregar AgroClimaConfig do banco, mantendo configuração em memória",
                error=str(exc),
            )
            if "WEATHERAPI" not in self._credentials:
                self._credentials["WEATHERAPI"] = settings.weatherapi_api_key or None
            if "OPENWEATHER" not in self._credentials:
                self._credentials["OPENWEATHER"] = settings.openweather_api_key or None

        self._rebuild_adapters()
        self._last_refresh = time.monotonic()

    def register_test_adapter(self, provider_id: str, adapter: WeatherProvider) -> None:
        """Registra adaptador sintético exclusivo para suíte de testes."""
        pid = provider_id.upper()
        self._test_adapters[pid] = adapter
        self._adapters[pid] = adapter
        self._last_refresh = time.monotonic()

    def _rebuild_adapters(self) -> None:
        """Instancia ou reconfigura os adaptadores HTTP reutilizáveis."""
        cfg = self._config

        # 1. WeatherAPI
        w_key = self._credentials.get("WEATHERAPI") or settings.weatherapi_api_key or None
        w_client = self._http_clients.get("WEATHERAPI")
        if w_client is None or w_client.is_closed:
            w_client = httpx.AsyncClient(timeout=cfg.timeout_seconds)
            self._http_clients["WEATHERAPI"] = w_client
        self._adapters["WEATHERAPI"] = WeatherAPIAdapter(
            api_base_url=settings.weatherapi_base_url,
            api_key=w_key,
            is_enabled=settings.weatherapi_enabled and bool(w_key),
            max_days=settings.weatherapi_max_forecast_days,
            timeout_seconds=cfg.timeout_seconds,
            client=w_client,
        )

        # 2. OpenWeather
        ow_key = self._credentials.get("OPENWEATHER") or settings.openweather_api_key or None
        ow_client = self._http_clients.get("OPENWEATHER")
        if ow_client is None or ow_client.is_closed:
            ow_client = httpx.AsyncClient(timeout=cfg.timeout_seconds)
            self._http_clients["OPENWEATHER"] = ow_client
        self._adapters["OPENWEATHER"] = OpenWeatherOneCallAdapter(
            api_base_url=settings.openweather_base_url,
            api_key=ow_key,
            timeout_seconds=cfg.timeout_seconds,
            is_licensed=is_provider_authorized_for_public("OPENWEATHER", cfg, self._credentials),
            allow_unlicensed_public=settings.openweather_allow_unlicensed_public,
            client=ow_client,
        )

        # 3. Open-Meteo
        om_client = self._http_clients.get("OPEN_METEO")
        if om_client is None or om_client.is_closed:
            om_client = httpx.AsyncClient(timeout=cfg.timeout_seconds)
            self._http_clients["OPEN_METEO"] = om_client
        self._adapters["OPEN_METEO"] = OpenMeteoAdapter(
            api_base_url=settings.open_meteo_base_url,
            api_key=settings.open_meteo_api_key or None,
            timeout_seconds=cfg.timeout_seconds,
            is_licensed=is_provider_authorized_for_public("OPEN_METEO", cfg, self._credentials),
            allow_unlicensed_public=settings.open_meteo_allow_unlicensed_public,
            client=om_client,
        )

        # Restaura adaptadores sintéticos de teste cadastrados
        if self._test_adapters:
            self._adapters.update(self._test_adapters)

    async def fetch_forecast(self, lat: float, lon: float) -> ClimaPrevisaoResponse:
        """Executa a consulta meteorológica percorrendo a cadeia de fallback configurada.

        Raises:
            ProviderUnavailableError: Se todos os provedores da cadeia falharem.
        """
        cfg = await self.get_active_config()
        shared = await self.cache.redis_ready()

        # Determina a ordem efetiva de tentativa
        chain: list[str] = []
        if cfg.active_provider:
            chain.append(cfg.active_provider.upper())
        for p in cfg.fallback_chain:
            p_up = p.upper()
            if p_up not in chain:
                chain.append(p_up)

        if not chain:
            raise ProviderUnconfiguredError("Nenhum provedor meteorológico configurado.")

        last_exception: Exception | None = None

        for provider_slug in chain:
            adapter = self._adapters.get(provider_slug)
            if adapter is None:
                logger.warning("Adaptador meteorológico não registrado", provider=provider_slug)
                continue

            # Validação estrita de autorização de uso e licença pública em runtime
            if not is_provider_authorized_for_public(provider_slug, cfg, self._credentials):
                logger.warning(
                    "Provedor ignorado na cadeia: não licenciado ou sem autorização pública contratual",
                    provider=provider_slug,
                )
                continue

            # Validação de credencial obrigatória
            if provider_slug in ("WEATHERAPI", "OPENWEATHER"):
                key = getattr(adapter, "api_key", None)
                if not key:
                    logger.warning("Provedor requer chave de API válida", provider=provider_slug)
                    continue

            # Verificação e reserva atômica de cotas específicas por provedor
            if provider_slug == cfg.active_provider:
                quota_limit = cfg.monthly_quota_limit
            elif provider_slug == "WEATHERAPI":
                quota_limit = getattr(settings, "weatherapi_monthly_quota_limit", 100000)
            elif provider_slug == "OPENWEATHER":
                quota_limit = 30000
            else:
                quota_limit = 0  # OPEN_METEO e INMET são abertos/não-faturáveis

            if quota_limit > 0:
                reserved, current_count = await self.cache.reserve_monthly_quota(
                    provider_slug, quota_limit, shared
                )
                if not reserved:
                    logger.warning(
                        "Cota mensal esgotada para o provedor (reserva atômica), acionando contingência",
                        provider=provider_slug,
                        limit=quota_limit,
                        current=current_count,
                    )
                    await self.cache.record_error(provider_slug, "quota_exceeded", shared)
                    last_exception = ProviderQuotaExceededError(
                        f"Cota mensal do provedor {provider_slug} esgotada ({current_count}/{quota_limit})."
                    )
                    continue

                # Alertas proativos aos 80% e 95%
                await self._check_quota_alerts(provider_slug, quota_limit, shared, cfg)
            else:
                await self.cache.record_upstream_call(provider_slug, shared)

            # Execução da chamada ao upstream
            try:
                forecast = await adapter.fetch_forecast(lat, lon)
                forecast.provedor = provider_slug
                return forecast
            except (ProviderTimeoutError, httpx.TimeoutException) as exc:
                logger.warning(
                    "Timeout no provedor meteorológico, estornando reserva de cota e tentando próximo",
                    provider=provider_slug,
                    error=str(exc),
                )
                if quota_limit > 0:
                    await self.cache.rollback_quota_reservation(provider_slug, shared)
                await self.cache.record_error(provider_slug, "timeout", shared)
                last_exception = exc
            except (ProviderUnavailableError, ProviderAuthenticationError, ProviderQuotaExceededError) as exc:
                logger.warning(
                    "Falha no provedor meteorológico, estornando cota e alternando para contingência",
                    provider=provider_slug,
                    error=str(exc),
                )
                if quota_limit > 0:
                    await self.cache.rollback_quota_reservation(provider_slug, shared)
                await self.cache.record_error(provider_slug, "failure", shared)
                last_exception = exc
            except Exception as exc:
                logger.warning(
                    "Exceção inesperada no provedor meteorológico",
                    provider=provider_slug,
                    error=str(exc),
                )
                if quota_limit > 0:
                    await self.cache.rollback_quota_reservation(provider_slug, shared)
                await self.cache.record_error(provider_slug, "failure", shared)
                last_exception = exc

        # Se todos os provedores da cadeia falharam
        if last_exception is not None:
            if isinstance(last_exception, ProviderError):
                raise last_exception
            raise ProviderUnavailableError(
                f"Todos os provedores da cadeia falharam ({', '.join(chain)}): {type(last_exception).__name__}"
            )
        raise ProviderUnavailableError("Todos os provedores configurados estão indisponíveis.")

    async def _check_quota_alerts(
        self,
        provider: str,
        limit: int,
        shared: bool,
        cfg: AgroClimaConfig,
    ) -> None:
        """Monitora e emite logs de alerta preventivo aos 80% e 95% da franquia."""
        try:
            metrics = await self.cache.get_metrics(provider, shared)
            used = metrics.get("upstream_calls_month", 0)
            if limit <= 0:
                return

            ratio = used / float(limit)
            month = datetime.now(UTC).strftime("%Y-%m")
            alert_key_80 = f"{provider}:{month}:80"
            alert_key_95 = f"{provider}:{month}:95"

            if cfg.quota_alert_threshold_95 and ratio >= 0.95 and alert_key_95 not in self._quota_alerted_95:
                logger.critical(
                    "ALERTA CRÍTICO DE COTA: 95% da franquia atingida para provedor meteorológico",
                    provider=provider,
                    used=used,
                    limit=limit,
                    percent=round(ratio * 100, 1),
                )
                self._quota_alerted_95.add(alert_key_95)
            elif cfg.quota_alert_threshold_80 and ratio >= 0.80 and alert_key_80 not in self._quota_alerted_80:
                logger.warning(
                    "ALERTA PREVENTIVO DE COTA: 80% da franquia atingida para provedor meteorológico",
                    provider=provider,
                    used=used,
                    limit=limit,
                    percent=round(ratio * 100, 1),
                )
                self._quota_alerted_80.add(alert_key_80)
        except Exception as exc:
            logger.debug("Falha ao avaliar alertas de cota", error=str(exc))

    async def aclose(self) -> None:
        """Encerra graciosamente recursos de rede e tarefas assíncronas."""
        if self._sub_task is not None and not self._sub_task.done():
            self._sub_task.cancel()
        for client in self._http_clients.values():
            if not client.is_closed:
                await client.aclose()
        self._http_clients.clear()
