from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_admin, get_tenant_id, require_module
from pecuaria.climatico.schemas import (
    InteligenciaPecuariaResponse,
    ModeloZoosanitarioCreate,
    ModeloZoosanitarioResponse,
    ModeloZoosanitarioUpdate,
    RecomendacaoOperacionalResponse,
)
from pecuaria.climatico.recommendation_service import ClimaPecuariaRecommendationService
from pecuaria.climatico.service import InteligenciaPecuariaService, ModeloZoosanitarioService

router = APIRouter(prefix="/inteligencia", tags=["Inteligência Climática Pecuária"])

#
# 1. Dashboard / Análise (Apenas Tenants)
#
@router.get(
    "/analise",
    response_model=InteligenciaPecuariaResponse | None,
    summary="Análise Zoossanitária",
    description="Retorna o cálculo de ITH e alertas de bem-estar animal baseado no clima recente.",
)
async def analisar_estresse(
    unidade_produtiva_id: UUID,
    especie: str = Query(..., description="Bovino de Leite, Bovino de Corte, etc"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_module("P1_REBANHO")),
) -> InteligenciaPecuariaResponse | None:
    svc = InteligenciaPecuariaService(session)
    return await svc.analisar_estresse_termico(tenant_id, unidade_produtiva_id, especie)


#
# 2. Gerenciamento de Modelos Zoossanitários (Tenant)
#
@router.get(
    "/modelos",
    response_model=list[ModeloZoosanitarioResponse],
    summary="Listar Modelos",
)
async def listar_modelos(
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_module("P1_REBANHO")),
) -> list[ModeloZoosanitarioResponse]:
    svc = ModeloZoosanitarioService(session)
    return await svc.get_all_models(tenant_id)


@router.get("/recomendacoes/{unidade_produtiva_id}", response_model=list[RecomendacaoOperacionalResponse])
async def recomendacoes_operacionais_pecuaria(
    unidade_produtiva_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_module("P1_CONTROLE")),
):
    svc = ClimaPecuariaRecommendationService(session, tenant_id)
    return await svc.get_recomendacoes(unidade_produtiva_id)


@router.post(
    "/modelos",
    response_model=ModeloZoosanitarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar Modelo Personalizado",
)
async def criar_modelo(
    payload: ModeloZoosanitarioCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_module("P1_REBANHO")),
) -> ModeloZoosanitarioResponse:
    svc = ModeloZoosanitarioService(session)
    return await svc.create_model(tenant_id, payload, is_global=False)


@router.put(
    "/modelos/{model_id}",
    response_model=ModeloZoosanitarioResponse,
    summary="Atualizar Modelo",
)
async def atualizar_modelo(
    model_id: UUID,
    payload: ModeloZoosanitarioUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_module("P1_REBANHO")),
) -> ModeloZoosanitarioResponse:
    svc = ModeloZoosanitarioService(session)
    return await svc.update_model(tenant_id, model_id, payload)


@router.delete(
    "/modelos/{model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover Modelo",
)
async def remover_modelo(
    model_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_module("P1_REBANHO")),
) -> None:
    svc = ModeloZoosanitarioService(session)
    await svc.delete_model(tenant_id, model_id)


@router.post(
    "/modelos/{model_id}/copiar",
    response_model=ModeloZoosanitarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Copiar Modelo Global",
)
async def copiar_modelo_global(
    model_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_module("P1_REBANHO")),
) -> ModeloZoosanitarioResponse:
    svc = ModeloZoosanitarioService(session)
    return await svc.copy_global_to_tenant(tenant_id, model_id)


#
# 3. Gerenciamento Backoffice (Modelos Globais)
#
router_backoffice = APIRouter(
    prefix="/pecuaria/modelos",
    tags=["Backoffice - Modelos Pecuária"],
    dependencies=[Depends(get_current_admin)],
)

@router_backoffice.get("", response_model=list[ModeloZoosanitarioResponse])
async def list_global_models(session: AsyncSession = Depends(get_db)) -> list[ModeloZoosanitarioResponse]:
    # Acesso restrito via main.py (include_router under backoffice dependencies)
    svc = ModeloZoosanitarioService(session)
    return await svc.get_all_models(tenant_id=None)

@router_backoffice.post("", response_model=ModeloZoosanitarioResponse, status_code=status.HTTP_201_CREATED)
async def create_global_model(payload: ModeloZoosanitarioCreate, session: AsyncSession = Depends(get_db)) -> ModeloZoosanitarioResponse:
    svc = ModeloZoosanitarioService(session)
    return await svc.create_model(tenant_id=None, payload=payload, is_global=True)

@router_backoffice.put("/{model_id}", response_model=ModeloZoosanitarioResponse)
async def update_global_model(model_id: UUID, payload: ModeloZoosanitarioUpdate, session: AsyncSession = Depends(get_db)) -> ModeloZoosanitarioResponse:
    svc = ModeloZoosanitarioService(session)
    return await svc.update_model(tenant_id=None, model_id=model_id, payload=payload)

@router_backoffice.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_global_model(model_id: UUID, session: AsyncSession = Depends(get_db)) -> None:
    svc = ModeloZoosanitarioService(session)
    await svc.delete_model(tenant_id=None, model_id=model_id)
