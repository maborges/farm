from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.dependencies import get_session, get_tenant_id, require_module
from pecuaria.advanced_schemas import (
    ProducaoLeiteCreate,
    ProducaoLeiteResponse,
    ProducaoLeiteResumoResponse,
)
from pecuaria.advanced_service import PecuariaAdvancedService

router = APIRouter(
    prefix="/pecuaria/leite",
    tags=["Pecuária - Leite"],
    dependencies=[Depends(require_module("P4_LEITE"))],
)


@router.get("/dashboard", response_model=ProducaoLeiteResumoResponse)
async def dashboard(
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    return await svc.resumo_leite()


@router.get("/producao", response_model=List[ProducaoLeiteResponse])
async def listar_producao(
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    return await svc.listar_producao()


@router.post("/producao", response_model=ProducaoLeiteResponse, status_code=status.HTTP_201_CREATED)
async def criar_producao(
    payload: ProducaoLeiteCreate,
    tenant_id=Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = PecuariaAdvancedService(session, tenant_id)
    obj = await svc.criar_producao(payload.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(obj)
    return obj
