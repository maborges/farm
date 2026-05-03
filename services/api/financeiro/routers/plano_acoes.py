import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id
from financeiro.schemas.plano_acao_schema import PlanoAcaoItemResponse, PlanoAcaoStatusUpdate
from financeiro.services.plano_acao_service import PlanoAcaoService

router = APIRouter(prefix="/plano-acoes", tags=["Financeiro — Plano de Ação"])


@router.get("/", response_model=list[PlanoAcaoItemResponse])
async def listar_plano(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PlanoAcaoService(session, tenant_id)
    return await svc.listar(safra_id)


@router.post("/sincronizar", response_model=list[PlanoAcaoItemResponse])
async def sincronizar_plano(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PlanoAcaoService(session, tenant_id)
    itens = await svc.sincronizar(safra_id)
    await session.commit()
    return itens


@router.patch("/{item_id}/status", response_model=PlanoAcaoItemResponse)
async def atualizar_status(
    item_id: uuid.UUID,
    body: PlanoAcaoStatusUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PlanoAcaoService(session, tenant_id)
    item = await svc.atualizar_status(item_id, body.status)
    await session.commit()
    return item
