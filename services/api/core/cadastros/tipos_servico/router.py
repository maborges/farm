import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id
from core.exceptions import EntityNotFoundError
from .service import TipoServicoService
from .schemas import TipoServicoCreate, TipoServicoUpdate, TipoServicoResponse

router = APIRouter(prefix="/cadastros/tipos-servico", tags=["Cadastros — Tipos de Serviço"])


@router.get("/", response_model=list[TipoServicoResponse])
@router.get("", response_model=list[TipoServicoResponse])
async def listar(
    q: Optional[str] = Query(None, description="Busca por nome"),
    ativo: Optional[bool] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = TipoServicoService(session, tenant_id)
    return await svc.listar(q=q, ativo=ativo)


@router.post("/", response_model=TipoServicoResponse, status_code=201)
@router.post("", response_model=TipoServicoResponse, status_code=201)
async def criar(
    data: TipoServicoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = TipoServicoService(session, tenant_id)
    obj = await svc.criar(data)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/{tipo_servico_id}", response_model=TipoServicoResponse)
async def obter(
    tipo_servico_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = TipoServicoService(session, tenant_id)
    try:
        return await svc.obter(tipo_servico_id)
    except EntityNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de serviço não encontrado")


@router.patch("/{tipo_servico_id}", response_model=TipoServicoResponse)
async def atualizar(
    tipo_servico_id: uuid.UUID,
    data: TipoServicoUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = TipoServicoService(session, tenant_id)
    try:
        obj = await svc.atualizar(tipo_servico_id, data)
        await session.commit()
        await session.refresh(obj)
        return obj
    except EntityNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de serviço não encontrado")


@router.delete("/{tipo_servico_id}", status_code=204)
async def remover(
    tipo_servico_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = TipoServicoService(session, tenant_id)
    try:
        await svc.desativar(tipo_servico_id)
        await session.commit()
    except EntityNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de serviço não encontrado")
