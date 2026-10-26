# ruff: noqa: B008
"""Rotas FastAPI do módulo público de clima do DeepFarms Agro."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from core.config import settings
from core.schemas.agro_config_schemas import KEY_FLAGS
from core.services.agro_config_service import agro_config_service

from .adapters import (
    OpenMeteoAdapter,
    OpenWeatherOneCallAdapter,
    ProviderAuthenticationError,
    ProviderLocationNotFoundError,
    ProviderQuotaExceededError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUnconfiguredError,
    ProviderUnlicensedError,
    WeatherAPIAdapter,
    WeatherProvider,
)
from .cache import ClimaCache
from .catalog import (
    CatalogUnavailableError,
    InvalidUfError,
    MunicipalCatalog,
    QueryTooShortError,
    SearchParams,
)
from .contracts import ClimaPrevisaoResponse, MunicipiosBuscaResponse
from .grid import GeoGridPolicy
from .service import CoordinateValidationError, PublicClimaService

router = APIRouter(prefix="/public/clima", tags=["Clima público"])

_cache = ClimaCache(
    redis_url=settings.redis_url,
    single_worker_fallback=settings.clima_single_worker_fallback,
)


def _init_weather_provider() -> WeatherProvider:
    """Instancia o provedor meteorológico ativo conforme configuração de ambiente."""
    active = settings.clima_active_provider.upper()
    if active == "WEATHERAPI":
        return WeatherAPIAdapter(
            api_base_url=settings.weatherapi_base_url,
            api_key=settings.weatherapi_api_key or None,
            is_enabled=settings.weatherapi_enabled,
            max_days=settings.weatherapi_max_forecast_days,
            timeout_seconds=settings.weatherapi_timeout_seconds,
        )
    if active == "OPENWEATHER":
        return OpenWeatherOneCallAdapter(
            api_base_url=settings.openweather_base_url,
            api_key=settings.openweather_api_key or None,
            timeout_seconds=settings.clima_timeout_seconds,
            is_licensed=settings.openweather_licensed,
            allow_unlicensed_public=settings.openweather_allow_unlicensed_public,
        )
    return OpenMeteoAdapter(
        api_base_url=settings.open_meteo_base_url,
        api_key=settings.open_meteo_api_key or None,
        timeout_seconds=settings.clima_timeout_seconds,
        is_licensed=settings.open_meteo_licensed,
        allow_unlicensed_public=settings.open_meteo_allow_unlicensed_public,
    )


from .dynamic_orchestrator import DynamicWeatherOrchestrator

_orchestrator = DynamicWeatherOrchestrator(cache=_cache)
_adapter = _orchestrator

_grid_policy = GeoGridPolicy(step_degrees=settings.clima_grid_step_degrees)

_catalog = MunicipalCatalog()

_monthly_quota = (
    settings.weatherapi_monthly_quota_limit
    if settings.clima_active_provider.upper() == "WEATHERAPI"
    else 0
)

service = PublicClimaService(
    cache=_cache,
    provider=_orchestrator,
    grid_policy=_grid_policy,
    ttl_seconds=settings.clima_cache_ttl_seconds,
    monthly_quota_limit=_monthly_quota,
)


def get_clima_service() -> PublicClimaService:
    """Dependency injection para o serviço público de clima."""
    return service


def get_weather_orchestrator() -> DynamicWeatherOrchestrator:
    """Dependency injection para o orquestrador dinâmico de clima."""
    return _orchestrator


def get_municipal_catalog() -> MunicipalCatalog:
    """Dependency injection para o catálogo oficial de municípios."""
    return _catalog


@router.get(
    "/municipios",
    response_model=MunicipiosBuscaResponse,
    summary="Consulta o catálogo oficial de municípios brasileiros",
    description=(
        "Pesquisa municípios brasileiros por nome (sem distinção de acentos ou caixa) "
        "e/ou sigla de UF, retornando coordenadas geográficas oficiais do IBGE."
    ),
)
async def get_public_municipios(
    response: Response,
    q: str | None = Query(
        default=None, max_length=100, description="Nome ou parte do nome do município"
    ),
    uf: str | None = Query(default=None, max_length=2, description="Sigla da UF (ex: PR, SP, GO)"),
    limit: int = Query(default=20, ge=1, le=100, description="Limite máximo de registros"),
    offset: int = Query(default=0, ge=0, description="Deslocamento para paginação"),
    catalog: MunicipalCatalog = Depends(get_municipal_catalog),
) -> MunicipiosBuscaResponse:
    try:
        resultado = catalog.search(SearchParams(query=q, uf=uf, limit=limit, offset=offset))
    except (InvalidUfError, QueryTooShortError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except CatalogUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
    return resultado


@router.get(
    "/previsao",
    response_model=ClimaPrevisaoResponse,
    summary="Consulta previsão do tempo pública por coordenadas",
    description=(
        "Retorna condições atuais, previsão horária de 24h e previsão diária de até 3 dias "
        "com isolamento de banco comercial e proteção contra rate-limit."
    ),
)
async def get_public_previsao(
    request: Request,
    response: Response,
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude decimal (-90.0 a 90.0)"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude decimal (-180.0 a 180.0)"),
    clima: PublicClimaService = Depends(get_clima_service),
) -> ClimaPrevisaoResponse:
    # Verificação dinâmica de Feature Flag operacional (01E5)
    flags = agro_config_service.get_cached_config_dict(KEY_FLAGS)
    if flags and not flags.get("clima_enabled", True):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Módulo de inteligência meteorológica temporariamente desabilitado pela administração.",
        )

    # Identifica o chamador por hash de IP seguro
    address = request.client.host if request.client else "unknown"
    bucket = hashlib.sha256(address.encode()).hexdigest()[:24]

    shared = await clima.cache.redis_ready()
    if not await clima.cache.allow_request(bucket, shared):
        if not shared and not clima.cache.single_worker_fallback:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache compartilhado indisponível para rate limiting.",
            )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de consultas de clima excedido. Aguarde um minuto.",
        )

    try:
        resultado = await clima.get_previsao(lat, lon)
    except CoordinateValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ProviderLocationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Localidade não encontrada para a consulta meteorológica.",
        ) from exc
    except ProviderQuotaExceededError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço meteorológico temporariamente indisponível: franquia de consultas excedida.",
        )
    except ProviderAuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço meteorológico temporariamente indisponível: erro de autenticação.",
        )
    except ProviderUnlicensedError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provedor meteorológico não licenciado para produção: {exc}",
        ) from exc
    except (ProviderUnavailableError, ProviderTimeoutError, ProviderUnconfiguredError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Serviço meteorológico temporariamente indisponível: {exc}",
        ) from exc

    cache_status = "HIT" if resultado.emCache and not resultado.desatualizado else (
        "STALE" if resultado.desatualizado else "MISS"
    )

    response.headers["Cache-Control"] = "public, max-age=60, must-revalidate"
    response.headers["X-Data-Source"] = resultado.provedor
    response.headers["X-Cache-Status"] = cache_status

    return resultado
