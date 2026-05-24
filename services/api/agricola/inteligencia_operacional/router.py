from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import Modulos, PlanTier
from core.dependencies import (
    get_session_with_tenant,
    get_tenant_id,
    require_module,
    require_tenant_permission,
    require_tier,
)

from .schemas import PlanoAcaoOperacionalAgricolaResponse
from .service import InteligenciaOperacionalAgricolaV1Service

router = APIRouter(
    prefix="/agricola/inteligencia-operacional",
    tags=["Inteligência Operacional Agrícola v1"],
    dependencies=[
        Depends(require_module(Modulos.AGRICOLA_PLANEJAMENTO)),
        Depends(require_tier(PlanTier.PROFISSIONAL)),
    ],
)


@router.get(
    "/v1",
    response_model=PlanoAcaoOperacionalAgricolaResponse,
    summary="Planos de ação operacional assistidos da cadeia agrícola",
)
async def planos_de_acao_operacionais_agricolas_v1(
    safra_id: UUID = Query(..., description="Safra alvo dos planos assistidos"),
    production_unit_id: UUID | None = Query(None, description="Filtra por ProductionUnit específica"),
    unidade_produtiva_id: UUID | None = Query(None, description="Filtra por unidade produtiva"),
    data_inicio: date | None = Query(None, description="Período opcional dos planos assistidos"),
    data_fim: date | None = Query(None, description="Período opcional dos planos assistidos"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session_with_tenant),
    _: None = Depends(require_tenant_permission("agricola:safras:view")),
):
    svc = InteligenciaOperacionalAgricolaV1Service(session, tenant_id)
    return await svc.gerar(
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
