import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_tenant_permission
from imoveis.schemas.irrigacao import (
    SistemaIrrigacaoCreate,
    SistemaIrrigacaoResponse,
    SistemaIrrigacaoUpdate,
)
from imoveis.services.irrigacao_service import IrrigacaoService

router = APIRouter(prefix="/imoveis/irrigacao", tags=["Imóveis — Irrigação"])


@router.post(
    "/",
    response_model=SistemaIrrigacaoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission("operacional:*"))],
)
async def criar_sistema_irrigacao(
    data: SistemaIrrigacaoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    service = IrrigacaoService(session, tenant_id)
    return await service.create(data)


@router.get("/", response_model=List[SistemaIrrigacaoResponse])
async def listar_sistemas_irrigacao(
    imovel_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    service = IrrigacaoService(session, tenant_id)
    return await service.listar_por_imovel(imovel_id)


@router.get("/{sistema_id}", response_model=SistemaIrrigacaoResponse)
async def obter_sistema_irrigacao(
    sistema_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    service = IrrigacaoService(session, tenant_id)
    return await service.get_or_fail(sistema_id)


@router.patch(
    "/{sistema_id}",
    response_model=SistemaIrrigacaoResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))],
)
async def atualizar_sistema_irrigacao(
    sistema_id: uuid.UUID,
    data: SistemaIrrigacaoUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    service = IrrigacaoService(session, tenant_id)
    return await service.update(sistema_id, data.model_dump(exclude_unset=True))


@router.delete(
    "/{sistema_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_tenant_permission("operacional:*"))],
)
async def remover_sistema_irrigacao(
    sistema_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    service = IrrigacaoService(session, tenant_id)
    await service.hard_delete(sistema_id)
