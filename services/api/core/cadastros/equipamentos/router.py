import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id
from core.exceptions import EntityNotFoundError
from .service import EquipamentoService, EquipamentoCalibracaoService
from .schemas import (
    EquipamentoCreate,
    EquipamentoUpdate,
    EquipamentoResponse,
    EquipamentoCalibracaoCreate,
    EquipamentoCalibracaoResponse,
)

router = APIRouter(prefix="/cadastros/equipamentos", tags=["Cadastros — Equipamentos"])


@router.get("/", response_model=list[EquipamentoResponse])
@router.get("", response_model=list[EquipamentoResponse])
async def listar(
    tipo: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    unidade_produtiva_id: Optional[uuid.UUID] = Query(None),
    q: Optional[str] = Query(None, description="Busca por nome"),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = EquipamentoService(session, tenant_id)
    return await svc.listar(tipo=tipo, status=status_filter, unidade_produtiva_id=unidade_produtiva_id, q=q)


@router.post("/", response_model=EquipamentoResponse, status_code=201)
@router.post("", response_model=EquipamentoResponse, status_code=201)
async def criar(
    data: EquipamentoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = EquipamentoService(session, tenant_id)
    eq = await svc.criar(data)
    await session.commit()
    await session.refresh(eq)
    return eq


@router.get("/{eq_id}", response_model=EquipamentoResponse)
async def obter(
    eq_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = EquipamentoService(session, tenant_id)
    try:
        return await svc.obter(eq_id)
    except EntityNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipamento não encontrado")


@router.patch("/{eq_id}", response_model=EquipamentoResponse)
async def atualizar(
    eq_id: uuid.UUID,
    data: EquipamentoUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = EquipamentoService(session, tenant_id)
    try:
        obj = await svc.atualizar(eq_id, data)
        await session.commit()
        await session.refresh(obj)
        return obj
    except EntityNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipamento não encontrado")


@router.delete("/{eq_id}", status_code=204)
async def remover(
    eq_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = EquipamentoService(session, tenant_id)
    try:
        await svc.desativar(eq_id)
        await session.commit()
    except EntityNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipamento não encontrado")


@router.post("/calibracoes", response_model=EquipamentoCalibracaoResponse, status_code=201)
@router.post("/calibracoes/", response_model=EquipamentoCalibracaoResponse, status_code=201)
async def criar_calibracao(
    data: EquipamentoCalibracaoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = EquipamentoCalibracaoService(session, tenant_id)
    calib = await svc.criar_calibracao(data)
    await session.commit()
    await session.refresh(calib)
    return calib


@router.get("/calibracoes", response_model=list[EquipamentoCalibracaoResponse])
@router.get("/calibracoes/", response_model=list[EquipamentoCalibracaoResponse])
async def listar_calibracoes(
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    from sqlalchemy import select
    from .models import EquipamentoCalibracao
    stmt = select(EquipamentoCalibracao).where(EquipamentoCalibracao.tenant_id == tenant_id).order_by(EquipamentoCalibracao.data_calibracao.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{eq_id}/calibracoes", response_model=list[EquipamentoCalibracaoResponse])
async def obter_calibracoes_equipamento(
    eq_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc_eq = EquipamentoService(session, tenant_id)
    await svc_eq.obter(eq_id)

    from sqlalchemy import select
    from .models import EquipamentoCalibracao
    stmt = select(EquipamentoCalibracao).where(
        EquipamentoCalibracao.tenant_id == tenant_id,
        EquipamentoCalibracao.equipamento_id == eq_id
    ).order_by(EquipamentoCalibracao.data_calibracao.desc())
    result = await session.execute(stmt)
    return list(result.scalars().all())
