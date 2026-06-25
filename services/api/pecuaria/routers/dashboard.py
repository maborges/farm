from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, get_unidade_produtiva_context, require_module
from core.operational_context import UnidadeProdutivaContext
from pecuaria.schemas.dashboard_resumo_schema import PecuariaDashboardResumoExecutivoResponse
from pecuaria.services.dashboard_resumo_service import PecuariaDashboardResumoService

router = APIRouter(
    prefix="/pecuaria/dashboard",
    tags=["Pecuária - Dashboard"],
    dependencies=[Depends(require_module("P1_REBANHO"))],
)


@router.get("/resumo-executivo", response_model=PecuariaDashboardResumoExecutivoResponse)
async def resumo_executivo(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    contexto: UnidadeProdutivaContext | None = Depends(get_unidade_produtiva_context),
):
    service = PecuariaDashboardResumoService(
        session,
        tenant_id,
        unidade_produtiva_id=contexto.unidade_produtiva_id if contexto else None,
    )
    return await service.resumir()

