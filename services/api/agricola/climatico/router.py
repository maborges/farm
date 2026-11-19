from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from agricola.climatico.schemas import (
    ClimaResponse, ClimaResumoResponse, ClimaAlertaResponse, 
    RecomendacaoOperacionalResponse, PrevisaoClimaResponse, ClimaInteligenciaResponse,
    ModeloFitossanitarioResponse, ModeloFitossanitarioCreate, ModeloFitossanitarioUpdate
)
from agricola.climatico.service import ClimaService, ModeloFitossanitarioService
from agricola.climatico.recommendation_service import ClimaRecommendationService
from core.dependencies import (
    get_catalog_admin_session,
    get_current_admin,
    get_session,
    get_tenant_id,
    require_module,
    require_tenant_permission,
)
from integracoes.openweather.services import OpenWeatherService

router = APIRouter(prefix="/climatico", tags=["Clima e Pluviometria"])

@router.post("/sincronizar/{unidade_produtiva_id}", status_code=status.HTTP_202_ACCEPTED)
async def sincronizar_api_clima(
    unidade_produtiva_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
    __: None = Depends(require_tenant_permission("integrations:sync")),
):
    try:
        service = OpenWeatherService(session)
        await service.sincronizar_clima_unidade(str(tenant_id), str(unidade_produtiva_id))
        await service.sincronizar_previsao_unidade(str(tenant_id), str(unidade_produtiva_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return {"message": "Sincronização do clima e da previsão concluída com sucesso."}

@router.get("/historico/{unidade_produtiva_id}", response_model=list[ClimaResponse])
async def historico_clima(
    unidade_produtiva_id: UUID,
    dias: int = Query(30, ge=1, le=3650),
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
    dias: int = Query(30, ge=1, le=3650),
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
    logger.info(
        "Consulta climática resumo",
        tenant_id=str(tenant_id),
        unidade_produtiva_id=str(unidade_produtiva_id),
    )
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

@router.get("/previsao/{unidade_produtiva_id}", response_model=list[PrevisaoClimaResponse])
async def previsao_clima(
    unidade_produtiva_id: UUID,
    dias: int = Query(5, ge=1, le=16),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ClimaService(session, tenant_id)
    registros = await svc.get_previsoes_unidade(unidade_produtiva_id, dias)
    return [PrevisaoClimaResponse.model_validate(r) for r in registros]

@router.get("/inteligencia/{unidade_produtiva_id}", response_model=ClimaInteligenciaResponse)
async def inteligencia_climatica(
    unidade_produtiva_id: UUID,
    dias_historico: int = Query(30, ge=1, le=3650),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    logger.info(
        "Consulta climática inteligência",
        tenant_id=str(tenant_id),
        unidade_produtiva_id=str(unidade_produtiva_id),
        dias_historico=dias_historico,
    )
    svc = ClimaService(session, tenant_id)
    resultado = await svc.get_analise_avancada(unidade_produtiva_id, dias_historico)
    return ClimaInteligenciaResponse.model_validate(resultado)

@router.get("/modelos-fitossanitarios", response_model=list[ModeloFitossanitarioResponse])
async def list_modelos_fitossanitarios(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ModeloFitossanitarioService(session, tenant_id)
    return await svc.get_all(include_globals=True)

@router.post("/modelos-fitossanitarios", response_model=ModeloFitossanitarioResponse, status_code=status.HTTP_201_CREATED)
async def create_modelo_fitossanitario(
    data: ModeloFitossanitarioCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ModeloFitossanitarioService(session, tenant_id)
    return await svc.create(data)

@router.patch("/modelos-fitossanitarios/{id}", response_model=ModeloFitossanitarioResponse)
async def update_modelo_fitossanitario(
    id: UUID,
    data: ModeloFitossanitarioUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ModeloFitossanitarioService(session, tenant_id)
    return await svc.update(id, data)

@router.delete("/modelos-fitossanitarios/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_modelo_fitossanitario(
    id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ModeloFitossanitarioService(session, tenant_id)
    await svc.delete(id)

@router.post("/modelos-fitossanitarios/{id}/copiar", response_model=ModeloFitossanitarioResponse)
async def copiar_modelo_fitossanitario(
    id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A1_PLANEJAMENTO")),
):
    svc = ModeloFitossanitarioService(session, tenant_id)
    return await svc.copiar_modelo_global(id)

# ---------------------------------------------------------
# BACKOFFICE: Modelos Globais
# ---------------------------------------------------------

@router.get("/backoffice/modelos-fitossanitarios", response_model=list[ModeloFitossanitarioResponse], dependencies=[Depends(get_current_admin)])
async def backoffice_list_modelos_fitossanitarios(
    session: AsyncSession = Depends(get_catalog_admin_session),
    # _: None = Depends(require_role(["ADMIN"])) # Descomentar se existir role check
):
    svc = ModeloFitossanitarioService(session, tenant_id=None)
    return await svc.get_all()

@router.post("/backoffice/modelos-fitossanitarios", response_model=ModeloFitossanitarioResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(get_current_admin)])
async def backoffice_create_modelo_fitossanitario(
    data: ModeloFitossanitarioCreate,
    session: AsyncSession = Depends(get_catalog_admin_session),
):
    svc = ModeloFitossanitarioService(session, tenant_id=None)
    return await svc.create(data)

@router.patch("/backoffice/modelos-fitossanitarios/{id}", response_model=ModeloFitossanitarioResponse, dependencies=[Depends(get_current_admin)])
async def backoffice_update_modelo_fitossanitario(
    id: UUID,
    data: ModeloFitossanitarioUpdate,
    session: AsyncSession = Depends(get_catalog_admin_session),
):
    svc = ModeloFitossanitarioService(session, tenant_id=None)
    return await svc.update(id, data)

@router.delete("/backoffice/modelos-fitossanitarios/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin)])
async def backoffice_delete_modelo_fitossanitario(
    id: UUID,
    session: AsyncSession = Depends(get_catalog_admin_session),
):
    svc = ModeloFitossanitarioService(session, tenant_id=None)
    await svc.delete(id)
