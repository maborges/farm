from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import Modulos, PlanTier
from core.dependencies import (
    get_current_user,
    get_session,
    get_tenant_id,
    require_module,
    require_tenant_permission,
    require_tier,
)

from .schemas import (
    PrioridadeAgricolaComentarioCreate,
    PrioridadeAgricolaResponse,
    PrioridadeAgricolaStatusResponse,
    PrioridadeAgricolaStatusUpdate,
)
from .service import PrioridadesAgricolasV1Service

router = APIRouter(
    prefix="/agricola/prioridades",
    tags=["Central Inteligente de Prioridades Agrícolas v1"],
    dependencies=[
        Depends(require_module(Modulos.AGRICOLA_PLANEJAMENTO)),
        Depends(require_tier(PlanTier.PROFISSIONAL)),
    ],
)


@router.get(
    "/v1",
    response_model=PrioridadeAgricolaResponse,
    summary="Central inteligente de prioridades agrícolas",
)
async def central_inteligente_prioridades_agricolas_v1(
    safra_id: UUID = Query(..., description="Safra alvo da consolidação"),
    production_unit_id: UUID | None = Query(None, description="Filtra por ProductionUnit específica"),
    unidade_produtiva_id: UUID | None = Query(None, description="Filtra por unidade produtiva"),
    data_inicio: date | None = Query(None, description="Período opcional da central"),
    data_fim: date | None = Query(None, description="Período opcional da central"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_tenant_permission("agricola:safras:view")),
):
    svc = PrioridadesAgricolasV1Service(session, tenant_id)
    return await svc.gerar(
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@router.patch(
    "/v1/{prioridade_id}/status",
    response_model=PrioridadeAgricolaStatusResponse,
    summary="Atualiza o status operacional de uma prioridade agrícola",
)
async def atualizar_status_prioridade_agricola_v1(
    prioridade_id: str,
    payload: PrioridadeAgricolaStatusUpdate,
    safra_id: UUID = Query(..., description="Safra alvo da prioridade"),
    production_unit_id: UUID | None = Query(None, description="Filtra por ProductionUnit específica"),
    unidade_produtiva_id: UUID | None = Query(None, description="Filtra por unidade produtiva"),
    data_inicio: date | None = Query(None, description="Período opcional da central"),
    data_fim: date | None = Query(None, description="Período opcional da central"),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_tenant_permission("agricola:safras:view")),
):
    svc = PrioridadesAgricolasV1Service(session, tenant_id)
    try:
        return await svc.atualizar_status(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            status=payload.status,
            observacao=payload.observacao,
            user_id=current_user.id,
            responsavel_nome=current_user.nome_completo or current_user.username,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/v1/{prioridade_id}/status",
    response_model=PrioridadeAgricolaStatusResponse,
    summary="Consulta o histórico de status de uma prioridade agrícola",
)
async def obter_status_prioridade_agricola_v1(
    prioridade_id: str,
    safra_id: UUID = Query(..., description="Safra alvo da prioridade"),
    production_unit_id: UUID | None = Query(None, description="Filtra por ProductionUnit específica"),
    unidade_produtiva_id: UUID | None = Query(None, description="Filtra por unidade produtiva"),
    data_inicio: date | None = Query(None, description="Período opcional da central"),
    data_fim: date | None = Query(None, description="Período opcional da central"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_tenant_permission("agricola:safras:view")),
):
    svc = PrioridadesAgricolasV1Service(session, tenant_id)
    try:
        return await svc.obter_status(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/v1/{prioridade_id}/comentarios",
    response_model=PrioridadeAgricolaStatusResponse,
    summary="Adiciona um comentário interno em uma prioridade agrícola",
)
async def comentar_prioridade_agricola_v1(
    prioridade_id: str,
    payload: PrioridadeAgricolaComentarioCreate,
    safra_id: UUID = Query(..., description="Safra alvo da prioridade"),
    production_unit_id: UUID | None = Query(None, description="Filtra por ProductionUnit específica"),
    unidade_produtiva_id: UUID | None = Query(None, description="Filtra por unidade produtiva"),
    data_inicio: date | None = Query(None, description="Período opcional da central"),
    data_fim: date | None = Query(None, description="Período opcional da central"),
    tenant_id: UUID = Depends(get_tenant_id),
    current_user = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_tenant_permission("agricola:safras:view")),
):
    svc = PrioridadesAgricolasV1Service(session, tenant_id)
    try:
        return await svc.adicionar_comentario(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            comentario=payload.comentario,
            user_id=current_user.id,
            responsavel_nome=current_user.nome_completo or current_user.username,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get(
    "/v1/{prioridade_id}/historico",
    response_model=PrioridadeAgricolaStatusResponse,
    summary="Consulta histórico completo de status e comentários de uma prioridade agrícola",
)
async def obter_historico_prioridade_agricola_v1(
    prioridade_id: str,
    safra_id: UUID = Query(..., description="Safra alvo da prioridade"),
    production_unit_id: UUID | None = Query(None, description="Filtra por ProductionUnit específica"),
    unidade_produtiva_id: UUID | None = Query(None, description="Filtra por unidade produtiva"),
    data_inicio: date | None = Query(None, description="Período opcional da central"),
    data_fim: date | None = Query(None, description="Período opcional da central"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_tenant_permission("agricola:safras:view")),
):
    svc = PrioridadesAgricolasV1Service(session, tenant_id)
    try:
        return await svc.obter_historico(
            safra_id=safra_id,
            prioridade_id=prioridade_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
