from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.dependencies import get_session, get_tenant_id, require_module
from pecuaria.advanced_schemas import (
    PecuariaGeneticaCreate,
    PecuariaGeneticaResponse,
    PecuariaSugestaoCreate,
    PecuariaSugestaoResponse,
    PecuariaGeneticaResumoResponse,
)
from pecuaria.advanced_service import PecuariaAdvancedService

router = APIRouter(
    prefix="/pecuaria/genetica",
    tags=["Pecuária - Genética"],
    dependencies=[Depends(require_module("P2_GENETICA"))],
)


@router.get("/dashboard", response_model=PecuariaGeneticaResumoResponse)
async def dashboard(
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    return await svc.resumo_genetica()


@router.get("/animais", response_model=List[PecuariaGeneticaResponse])
async def listar(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    return await svc.listar_genetica(skip=skip, limit=limit)


@router.post("/animais", response_model=PecuariaGeneticaResponse, status_code=status.HTTP_201_CREATED)
async def criar(
    payload: PecuariaGeneticaCreate,
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    obj = await svc.criar_genetica(payload.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/acasalamentos", response_model=List[PecuariaSugestaoResponse])
async def listar_sugestoes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    return await svc.listar_sugestoes(skip=skip, limit=limit)


@router.post("/acasalamentos", response_model=PecuariaSugestaoResponse, status_code=status.HTTP_201_CREATED)
async def criar_sugestao(
    payload: PecuariaSugestaoCreate,
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    obj = await svc.criar_sugestao(payload.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(obj)
    return obj
