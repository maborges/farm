from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.climatico.schemas import ClimaResponse, ClimaResumoResponse, ClimaAlertaResponse, RecomendacaoOperacionalResponse
from agricola.climatico.service import ClimaService
from agricola.climatico.recommendation_service import ClimaRecommendationService
from core.dependencies import get_session, get_tenant_id, require_module

router = APIRouter(prefix="/climatico", tags=["Clima e Pluviometria"])

@router.post("/sincronizar/{unidade_produtiva_id}", status_code=status.HTTP_202_ACCEPTED)
async def sincronizar_api_clima(
    unidade_produtiva_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ClimaService(session, tenant_id)
    msg = await svc.sync_open_meteo(unidade_produtiva_id)
    return {"message": msg}

@router.get("/historico/{unidade_produtiva_id}", response_model=list[ClimaResponse])
async def historico_clima(
    unidade_produtiva_id: UUID,
    dias: int = 30,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ClimaService(session, tenant_id)
    hoje = date.today()
    inicio = hoje - timedelta(days=dias)
    registros = await svc.get_clima_periodo(unidade_produtiva_id, inicio, hoje)
    return [ClimaResponse.model_validate(r) for r in registros]

@router.get("/chuva-acumulada/{unidade_produtiva_id}")
async def acumulado_chuva(
    unidade_produtiva_id: UUID,
    dias: int = 30,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ClimaService(session, tenant_id)
    acumulado = await svc.get_chuva_acumulada(unidade_produtiva_id, dias)
    return {"unidade_produtiva_id": unidade_produtiva_id, "dias": dias, "chuva_acumulada_mm": acumulado}

@router.get("/resumo/{unidade_produtiva_id}", response_model=ClimaResumoResponse)
async def resumo_climatico(
    unidade_produtiva_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ClimaService(session, tenant_id)
    return await svc.get_resumo_climatico(unidade_produtiva_id)

@router.get("/alertas/{unidade_produtiva_id}", response_model=list[ClimaAlertaResponse])
async def alertas_climaticos(
    unidade_produtiva_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ClimaService(session, tenant_id)
    return await svc.get_alertas_ativos(unidade_produtiva_id)

@router.get("/recomendacoes/{unidade_produtiva_id}", response_model=list[RecomendacaoOperacionalResponse])
async def recomendacoes_operacionais(
    unidade_produtiva_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ClimaRecommendationService(session, tenant_id)
    return await svc.get_recomendacoes(unidade_produtiva_id)
