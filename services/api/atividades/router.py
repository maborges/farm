import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id
from atividades.schemas import AtividadeItem
from atividades.service import AtividadesService

router = APIRouter(prefix="/atividades", tags=["Atividades da Safra"])


@router.get("/", response_model=list[AtividadeItem])
async def listar_atividades(
    safra_id: uuid.UUID = Query(...),
    limit: int = Query(20, ge=5, le=50),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = AtividadesService(session, tenant_id)
    return await svc.listar(safra_id, limit=limit)
