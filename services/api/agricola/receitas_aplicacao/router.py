from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import Modulos
from core.dependencies import get_session, get_tenant_id, get_current_user_claims, require_module, require_tenant_permission
from agricola.receitas_aplicacao.schemas import (
    ReceitaAplicacaoCreate,
    ReceitaAplicacaoUpdate,
    ReceitaAplicacaoResponse,
)
from agricola.receitas_aplicacao.service import ReceitaAplicacaoService

router = APIRouter(
    prefix="/agricola/cadastros/receitas-aplicacao",
    tags=["Agrícola - Receitas de Aplicação"],
    dependencies=[Depends(require_module(Modulos.AGRICOLA_PLANEJAMENTO))],
)


def _user_id(user: dict) -> UUID | None:
    sub = user.get("sub")
    return UUID(sub) if sub else None


@router.post(
    "/",
    response_model=ReceitaAplicacaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma Receita de Aplicação (produto+dose/ha e mão de obra padrão)",
)
async def criar_receita(
    dados: ReceitaAplicacaoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(get_current_user_claims),
    _: None = Depends(require_tenant_permission("agricola:receita_aplicacao:criar")),
):
    svc = ReceitaAplicacaoService(session, tenant_id, _user_id(user))
    receita = await svc.criar(dados)
    await session.commit()
    return await svc.obter_com_itens(receita.id)


@router.get(
    "/",
    response_model=List[ReceitaAplicacaoResponse],
    summary="Lista Receitas de Aplicação do tenant",
)
async def listar_receitas(
    apenas_ativas: bool = Query(True),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:receita_aplicacao:visualizar")),
):
    svc = ReceitaAplicacaoService(session, tenant_id)
    return await svc.listar_com_itens(apenas_ativas=apenas_ativas)


@router.get(
    "/{receita_id}",
    response_model=ReceitaAplicacaoResponse,
    summary="Detalha uma Receita de Aplicação",
)
async def obter_receita(
    receita_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:receita_aplicacao:visualizar")),
):
    svc = ReceitaAplicacaoService(session, tenant_id)
    return await svc.obter_com_itens(receita_id)


@router.patch(
    "/{receita_id}",
    response_model=ReceitaAplicacaoResponse,
    summary="Atualiza uma Receita de Aplicação (substitui insumos/mão de obra se informados)",
)
async def atualizar_receita(
    receita_id: UUID,
    dados: ReceitaAplicacaoUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:receita_aplicacao:editar")),
):
    svc = ReceitaAplicacaoService(session, tenant_id)
    receita = await svc.atualizar(receita_id, dados)
    await session.commit()
    return await svc.obter_com_itens(receita.id)


@router.delete(
    "/{receita_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui uma Receita de Aplicação",
)
async def excluir_receita(
    receita_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:receita_aplicacao:excluir")),
):
    svc = ReceitaAplicacaoService(session, tenant_id)
    await svc.excluir(receita_id)
    await session.commit()
