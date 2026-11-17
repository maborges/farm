from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_module
from core.services.maturidade_service import MaturidadeService

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard Executivo"],
    dependencies=[Depends(require_module("CORE"))],
)


@router.get("/maturidade")
async def obter_score_maturidade(
    unidade_produtiva_id: Optional[UUID] = Query(None),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    resultado = await MaturidadeService(session, tenant_id, unidade_produtiva_id).calcular_e_registrar()
    await session.commit()
    return resultado
