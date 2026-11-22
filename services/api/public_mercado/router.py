"""Endpoints públicos de mercado sem JWT nem contexto de tenant."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.dependencies import get_session
from core.schemas.agro_config_schemas import KEY_FLAGS, KEY_MERCADO
from core.services.agro_config_service import agro_config_service
from .cache import PtaxCache
from .macro_cache import MacroCache
from .macro_service import IndicadoresMacroService
from .ptax import BcbPtaxClient, PtaxResponse, public_response
from .service import PtaxService
from .sgs import BcbSgsClient, IndicadoresMacroResponse
from .sidra import (
    CatalogoIbgeResponse,
    EstatisticasIbgeResponse,
    Fonte,
    IbgeSidraClient,
    MunicipiosIbgeResponse,
    Nivel,
)
from .sidra_cache import SidraCache
from .sidra_service import IbgeSidraService
from .precos_publicos import CatalogoMercadoResponse, PrecoPublicoItem, PrecosPublicosResponse
from .precos_publicos_service import PrecosPublicosService
from .cotacoes_regiao_service import CotacaoMultiFonteService, CotacoesRegiaoResponse

router = APIRouter(prefix="/public/mercado", tags=["Mercado público"])
service = PtaxService(
    PtaxCache(settings.redis_url, settings.ptax_single_worker_fallback),
    BcbPtaxClient(),
    settings.ptax_cache_ttl_seconds,
)
macro_service = IndicadoresMacroService(
    MacroCache(settings.redis_url, settings.ptax_single_worker_fallback),
    BcbSgsClient(),
    settings.macro_cache_ttl_seconds,
)
sidra_service = IbgeSidraService(
    SidraCache(settings.redis_url, settings.ptax_single_worker_fallback),
    IbgeSidraClient(),
    ttl_annual_seconds=settings.macro_cache_ttl_seconds * 2,
    ttl_monthly_seconds=settings.macro_cache_ttl_seconds,
)


def apply_dynamic_market_config(config_dict: dict[str, Any]) -> None:
    """Aplica parâmetros operacionais dinâmicos nas instâncias dos serviços públicos."""
    if "ptax_cache_ttl_seconds" in config_dict:
        service.ttl_seconds = config_dict["ptax_cache_ttl_seconds"]
    if "macro_cache_ttl_seconds" in config_dict:
        macro_service.ttl_seconds = config_dict["macro_cache_ttl_seconds"]
    if "sidra_cache_ttl_seconds" in config_dict:
        sidra_service.ttl_annual_seconds = config_dict["sidra_cache_ttl_seconds"]
        sidra_service.ttl_monthly_seconds = max(300, config_dict["sidra_cache_ttl_seconds"] // 4)
    if "precos_cache_ttl_seconds" in config_dict:
        precos_service.ttl_seconds = config_dict["precos_cache_ttl_seconds"]
    if "max_defasagem_dias" in config_dict:
        novo_max = max(1, int(config_dict["max_defasagem_dias"]))
        if precos_service.max_defasagem_dias != novo_max:
            precos_service.max_defasagem_dias = novo_max
            precos_service.invalidate_cache()


def get_ptax_service() -> PtaxService:
    cfg = agro_config_service.get_cached_config_dict(KEY_MERCADO)
    if cfg:
        apply_dynamic_market_config(cfg)
    return service


def get_macro_service() -> IndicadoresMacroService:
    cfg = agro_config_service.get_cached_config_dict(KEY_MERCADO)
    if cfg:
        apply_dynamic_market_config(cfg)
    return macro_service


def get_sidra_service() -> IbgeSidraService:
    cfg = agro_config_service.get_cached_config_dict(KEY_MERCADO)
    if cfg:
        apply_dynamic_market_config(cfg)
    return sidra_service


precos_service = PrecosPublicosService(
    PtaxCache(settings.redis_url, settings.ptax_single_worker_fallback),
    ttl_seconds=settings.macro_cache_ttl_seconds,
)


def get_precos_service() -> PrecosPublicosService:
    cfg = agro_config_service.get_cached_config_dict(KEY_MERCADO)
    if cfg:
        apply_dynamic_market_config(cfg)
    return precos_service


@router.get("/ptax", response_model=PtaxResponse)
async def get_public_ptax(
    request: Request,
    response: Response,
    ptax: PtaxService = Depends(get_ptax_service),
) -> PtaxResponse:
    flags = agro_config_service.get_cached_config_dict(KEY_FLAGS)
    if flags and not flags.get("mercado_enabled", True):
        return public_response(None, datetime.now(timezone.utc), None, "MODULO_DESABILITADO_ADMIN")

    cfg = agro_config_service.get_cached_config_dict(KEY_MERCADO)
    if cfg and not cfg.get("ptax_enabled", True):
        return public_response(None, datetime.now(timezone.utc), None, "FONTE_DESABILITADA_ADMIN")

    address = request.client.host if request.client else "unknown"
    bucket = hashlib.sha256(address.encode()).hexdigest()[:24]
    shared = await ptax.cache.redis_ready()
    if not await ptax.cache.allow_request(bucket, shared):
        if not shared and not ptax.cache.single_worker_fallback:
            raise HTTPException(status_code=503, detail="Cache compartilhado indisponível")
        raise HTTPException(status_code=429, detail="Limite de consultas PTAX excedido")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return await ptax.get(datetime.now(timezone.utc))


@router.get("/indicadores-macro", response_model=IndicadoresMacroResponse)
async def get_public_indicadores_macro(
    request: Request,
    response: Response,
    macro: IndicadoresMacroService = Depends(get_macro_service),
) -> IndicadoresMacroResponse:
    flags = agro_config_service.get_cached_config_dict(KEY_FLAGS)
    if flags and not flags.get("mercado_enabled", True):
        return IndicadoresMacroResponse(
            sucesso=False,
            versao="1.0",
            dataConsultaIso=datetime.now(timezone.utc),
            cacheAtualizadoEmIso=None,
            estadoDisponibilidade="MODULO_DESABILITADO_ADMIN",
            avisoLegal="Módulo de mercado agrícola desabilitado temporariamente pelo administrador.",
            itens=[],
        )

    cfg = agro_config_service.get_cached_config_dict(KEY_MERCADO)
    if cfg and not cfg.get("sgs_enabled", True):
        return IndicadoresMacroResponse(
            sucesso=False,
            versao="1.0",
            dataConsultaIso=datetime.now(timezone.utc),
            cacheAtualizadoEmIso=None,
            estadoDisponibilidade="FONTE_DESABILITADA_ADMIN",
            avisoLegal="Módulo de indicadores macroeconômicos desabilitado pela administração.",
            itens=[],
        )

    address = request.client.host if request.client else "unknown"
    bucket = hashlib.sha256(address.encode()).hexdigest()[:24]
    shared = await macro.cache.redis_ready()
    if not await macro.cache.allow_request(bucket, shared):
        if not shared and not macro.cache.single_worker_fallback:
            raise HTTPException(status_code=503, detail="Cache compartilhado indisponível")
        raise HTTPException(status_code=429, detail="Limite de consultas excedido")
    response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=120"
    return await macro.get(datetime.now(timezone.utc))


@router.get("/ibge/catalogo", response_model=CatalogoIbgeResponse)
async def get_public_ibge_catalogo(
    response: Response,
    sidra: IbgeSidraService = Depends(get_sidra_service),
) -> CatalogoIbgeResponse:
    flags = agro_config_service.get_cached_config_dict(KEY_FLAGS)
    if (flags and not flags.get("mercado_enabled", True)) or (flags and not flags.get("ibge_enabled", True)):
        raise HTTPException(
            status_code=503,
            detail="Módulo de estatísticas agropecuárias IBGE/SIDRA desabilitado temporariamente pela administração.",
        )
    cfg = agro_config_service.get_cached_config_dict(KEY_MERCADO)
    if cfg and not cfg.get("sidra_enabled", True):
        raise HTTPException(
            status_code=503,
            detail="Estatísticas agropecuárias do IBGE (SIDRA) desabilitadas temporariamente pelo administrador.",
        )
    response.headers["Cache-Control"] = "public, max-age=3600, stale-while-revalidate=86400"
    return sidra.get_catalogo()


@router.get("/ibge/municipios/{uf}", response_model=MunicipiosIbgeResponse)
async def get_public_ibge_municipios(
    uf: str,
    request: Request,
    response: Response,
    sidra: IbgeSidraService = Depends(get_sidra_service),
) -> MunicipiosIbgeResponse:
    address = request.client.host if request.client else "unknown"
    bucket = hashlib.sha256(address.encode()).hexdigest()[:24]
    shared = await sidra.cache.redis_ready()
    if not await sidra.cache.allow_request(bucket, shared):
        if not shared and not sidra.cache.single_worker_fallback:
            raise HTTPException(status_code=503, detail="Cache compartilhado indisponível")
        raise HTTPException(status_code=429, detail="Limite de consultas excedido")
    try:
        resultado = await sidra.get_municipios(uf)
        response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=604800"
        return resultado
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/ibge/estatisticas", response_model=EstatisticasIbgeResponse)
async def get_public_ibge_estatisticas(
    request: Request,
    response: Response,
    produto: str,
    nivel: Nivel = "BRASIL",
    uf: str | None = None,
    municipio: str | None = None,
    anos: int = 5,
    fonte: Fonte | None = None,
    sidra: IbgeSidraService = Depends(get_sidra_service),
) -> EstatisticasIbgeResponse:
    address = request.client.host if request.client else "unknown"
    bucket = hashlib.sha256(address.encode()).hexdigest()[:24]
    shared = await sidra.cache.redis_ready()
    if not await sidra.cache.allow_request(bucket, shared):
        if not shared and not sidra.cache.single_worker_fallback:
            raise HTTPException(status_code=503, detail="Cache compartilhado indisponível")
        raise HTTPException(status_code=429, detail="Limite de consultas excedido")
    try:
        resultado = await sidra.get_estatisticas(
            produto_id=produto,
            nivel=nivel,
            uf=uf,
            municipio=municipio,
            anos=anos,
            fonte_override=fonte,
            now=datetime.now(timezone.utc),
        )
        response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
        return resultado
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/catalogo", response_model=CatalogoMercadoResponse)
async def get_public_catalogo(
    response: Response,
    session: AsyncSession = Depends(get_session),
    service: PrecosPublicosService = Depends(get_precos_service),
) -> CatalogoMercadoResponse:
    flags = agro_config_service.get_cached_config_dict(KEY_FLAGS)
    if flags and not flags.get("mercado_enabled", True):
        return CatalogoMercadoResponse(
            sucesso=False,
            versao="1.0",
            dataConsultaIso=datetime.now(timezone.utc),
            avisoLegal="Módulo de mercado agrícola desabilitado temporariamente pelo administrador.",
            totalItens=0,
            itens=[],
        )
    await service.sincronizar_snapshot_ativo(session)
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    return await service.get_catalogo(datetime.now(timezone.utc))


@router.get("/precos", response_model=PrecosPublicosResponse)
async def get_public_precos(
    response: Response,
    session: AsyncSession = Depends(get_session),
    service: PrecosPublicosService = Depends(get_precos_service),
) -> PrecosPublicosResponse:
    flags = agro_config_service.get_cached_config_dict(KEY_FLAGS)
    if flags and not flags.get("mercado_enabled", True):
        return PrecosPublicosResponse(
            sucesso=False,
            versao="1.0",
            dataConsultaIso=datetime.now(timezone.utc),
            cacheAtualizadoEmIso=None,
            estadoDisponibilidade="MODULO_DESABILITADO_ADMIN",
            avisoLegal="Módulo de mercado agrícola temporariamente desabilitado pela administração.",
            totalItens=0,
            itens=[],
        )
    cfg = agro_config_service.get_cached_config_dict(KEY_MERCADO)
    if cfg and not cfg.get("deral_enabled", True):
        return PrecosPublicosResponse(
            sucesso=False,
            versao="1.0",
            dataConsultaIso=datetime.now(timezone.utc),
            cacheAtualizadoEmIso=None,
            estadoDisponibilidade="FONTE_INDISPONIVEL",
            avisoLegal="Preços públicos DERAL temporariamente desabilitados pelo administrador.",
            totalItens=0,
            itens=[],
        )
    await service.sincronizar_snapshot_ativo(session)
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    return await service.get_precos(datetime.now(timezone.utc))


@router.get("/precos/{commodity_id}", response_model=PrecoPublicoItem)
async def get_public_preco_commodity(
    commodity_id: str,
    response: Response,
    session: AsyncSession = Depends(get_session),
    service: PrecosPublicosService = Depends(get_precos_service),
) -> PrecoPublicoItem:
    await service.sincronizar_snapshot_ativo(session)
    item = await service.get_preco_commodity(commodity_id, datetime.now(timezone.utc))
    if not item:
        raise HTTPException(
            status_code=404,
            detail=f"Cotação pública para commodity '{commodity_id}' não homologada",
        )
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    return item


@router.get("/cotacoes-regiao", response_model=CotacoesRegiaoResponse)
async def get_public_cotacoes_regiao(
    response: Response,
    produto: str | None = None,
    uf: str = "PR",
    praca: str | None = None,
    municipio_ibge: str | None = None,
    fonte: str | None = None,
    incluir_ibge: bool = True,
    session: AsyncSession = Depends(get_session),
    service: PrecosPublicosService = Depends(get_precos_service),
    sidra: IbgeSidraService = Depends(get_sidra_service),
) -> CotacoesRegiaoResponse:
    """Retorna painel comparativo de múltiplas fontes por produto, UF, município e praça."""
    await service.sincronizar_snapshot_ativo(session)
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=600"
    return await CotacaoMultiFonteService(sidra_service=sidra, session=session).consultar(
        produto=produto,
        uf=uf,
        praca=praca,
        municipio_ibge=municipio_ibge,
        fonte=fonte,
        incluir_ibge=incluir_ibge,
    )
