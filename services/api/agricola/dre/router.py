from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.dre.service import DREAgricolaV1Service
from agricola.dre.schemas import DREAgricolaResponse
from core.constants import PlanTier, Modulos
from core.dependencies import (
    get_session_with_tenant,
    get_tenant_id,
    require_module,
    require_tenant_permission,
    require_tier,
)

router = APIRouter(
    prefix="/agricola/dre",
    tags=["DRE Agrícola v1"],
    dependencies=[
        Depends(require_module(Modulos.AGRICOLA_PLANEJAMENTO)),
        Depends(require_tier(PlanTier.PROFISSIONAL)),
    ],
)


@router.get(
    "/v1",
    response_model=DREAgricolaResponse,
    summary="DRE agrícola v1 somente leitura",
)
async def dre_agricola_v1(
    safra_id: UUID = Query(..., description="Safra alvo da consolidação"),
    production_unit_id: UUID | None = Query(None, description="Filtra por ProductionUnit específica"),
    unidade_produtiva_id: UUID | None = Query(None, description="Filtra por unidade produtiva"),
    data_inicio: date | None = Query(None, description="Período opcional reservado para futuras janelas"),
    data_fim: date | None = Query(None, description="Período opcional reservado para futuras janelas"),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session_with_tenant),
    _: None = Depends(require_tenant_permission("agricola:safras:view")),
):
    """
    Endpoint interno da DRE agrícola v1.

    O router apenas delega ao serviço consolidado e não recalcula valores.
    Os filtros de período são aceitos para compatibilidade futura, mas a
    consolidação atual permanece baseada na precedência econômica oficial.
    """
    svc = DREAgricolaV1Service(session, tenant_id)
    return await svc.gerar(
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
