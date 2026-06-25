from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, get_unidade_produtiva_context
from core.operational_context import UnidadeProdutivaContext
from operacional.schemas.dashboard_resumo_schema import DashboardResumoOperacionalResponse
from operacional.services.dashboard_resumo_service import DashboardResumoOperacionalService

router = APIRouter(
    prefix="/operacional/dashboard",
    tags=["Operacional - Dashboard"],
)


@router.get("/resumo-operacional", response_model=DashboardResumoOperacionalResponse)
async def resumo_operacional(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    contexto: UnidadeProdutivaContext | None = Depends(get_unidade_produtiva_context),
):
    service = DashboardResumoOperacionalService(
        session,
        tenant_id,
        unidade_produtiva_id=contexto.unidade_produtiva_id if contexto else None,
    )
    return await service.resumir()

