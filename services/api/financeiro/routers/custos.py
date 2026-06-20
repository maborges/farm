from __future__ import annotations

from datetime import date
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_module
from financeiro.schemas.relatorio_schema import CentroCustoResponse
from financeiro.services.relatorio_service import RelatorioService

MODULE_DEPENDENCY = require_module("F2_CUSTOS_ABC")
router = APIRouter(
    prefix="/custos",
    tags=["Financeiro — Custos ABC (F2)"],
    dependencies=[Depends(MODULE_DEPENDENCY)],
)


@router.get("/centro-custos", response_model=CentroCustoResponse)
async def centro_custos(
    data_inicio: date = Query(..., description="Início do período (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Fim do período (YYYY-MM-DD)"),
    unidade_produtiva_id: Optional[uuid.UUID] = Query(None),
    safra_id: Optional[uuid.UUID] = Query(None, description="Filtrar por safra específica"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Custo por centro de custo (safra/talhão) com gate comercial F2."""
    svc = RelatorioService(db, tenant_id)
    return await svc.centro_custos(data_inicio, data_fim, unidade_produtiva_id, safra_id)
