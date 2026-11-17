from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_module
from core.schemas.plano_acao_schemas import PlanoAcaoCreate, PlanoAcaoResponse, PlanoAcaoUpdate
from core.services.plano_acao_service import PlanoAcaoService

router = APIRouter(
    prefix="/planos-acao",
    tags=["Planos de Ação Gerenciais"],
    dependencies=[Depends(require_module("CORE"))],
)


@router.get("/", response_model=list[PlanoAcaoResponse])
async def listar_planos_acao(
    status_filtro: Optional[str] = Query(None, alias="status"),
    safra_id: Optional[UUID] = Query(None),
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    return await PlanoAcaoService(session, tenant_id).listar(status=status_filtro, safra_id=safra_id)


@router.post("/", response_model=PlanoAcaoResponse, status_code=status.HTTP_201_CREATED)
async def criar_plano_acao(
    dados: PlanoAcaoCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    plano = await PlanoAcaoService(session, tenant_id).criar(dados)
    await session.commit()
    return plano


@router.patch("/{plano_id}", response_model=PlanoAcaoResponse)
async def atualizar_plano_acao(
    plano_id: UUID,
    dados: PlanoAcaoUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    plano = await PlanoAcaoService(session, tenant_id).atualizar(plano_id, dados)
    await session.commit()
    return plano


@router.delete("/{plano_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_plano_acao(
    plano_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    await PlanoAcaoService(session, tenant_id).excluir(plano_id)
    await session.commit()
