from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.dependencies import get_session, get_tenant_id, require_module
from pecuaria.advanced_schemas import (
    ConfinamentoLoteCreate,
    ConfinamentoLoteEncerrar,
    ConfinamentoLoteResponse,
    RacaoTMRCreate,
    RacaoTMRResponse,
    CochoCreate,
    CochoResponse,
    ConfinamentoResumoResponse,
)
from pecuaria.advanced_service import PecuariaAdvancedService

router = APIRouter(
    prefix="/pecuaria/confinamento",
    tags=["Pecuária - Confinamento"],
    dependencies=[Depends(require_module("P3_CONFINAMENTO"))],
)


@router.get("/dashboard", response_model=ConfinamentoResumoResponse)
async def dashboard(
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    return await svc.resumo_confinamento()


@router.get("/lotes", response_model=List[ConfinamentoLoteResponse])
async def listar_lotes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    return await svc.listar_confinamentos(skip=skip, limit=limit)


@router.post("/lotes", response_model=ConfinamentoLoteResponse, status_code=status.HTTP_201_CREATED)
async def criar_lote(
    payload: ConfinamentoLoteCreate,
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    obj = await svc.criar_confinamento(payload.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(obj)
    return obj


@router.post("/lotes/{lote_id}/encerrar", response_model=ConfinamentoLoteResponse)
async def encerrar_lote(
    lote_id: int,
    payload: ConfinamentoLoteEncerrar,
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    obj = await svc.encerrar_confinamento(
        lote_id, payload.peso_saida_kg, payload.data_saida_real, payload.consumo_total_racao_kg
    )
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/racoes", response_model=List[RacaoTMRResponse])
async def listar_racoes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    return await svc.listar_racoes(skip=skip, limit=limit)


@router.post("/racoes", response_model=RacaoTMRResponse, status_code=status.HTTP_201_CREATED)
async def criar_racao(
    payload: RacaoTMRCreate,
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    obj = await svc.criar_racao(payload.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/cochos", response_model=List[CochoResponse])
async def listar_cochos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    return await svc.listar_cochos(skip=skip, limit=limit)


@router.post("/cochos", response_model=CochoResponse, status_code=status.HTTP_201_CREATED)
async def criar_cocho(
    payload: CochoCreate,
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    obj = await svc.criar_cocho(payload.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(obj)
    return obj
