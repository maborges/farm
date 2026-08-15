from core.dependencies import require_tenant_permission
from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_module, require_role
from agricola.tarefas.schemas import (
    TarefaCreate,
    TarefaUpdate,
    TarefaResponse,
    PlanejarOperacaoRequest,
    SafraTarefaNecessidadeCreate,
    SafraTarefaNecessidadeUpdate,
    SafraTarefaNecessidadeResponse,
)
from agricola.operacoes.schemas import OperacaoAgricolaResponse
from agricola.tarefas.service import TarefaService

router = APIRouter(tags=["Agrícola - Tarefas (A2)"])
MODULE = "A2_CAMPO"


@router.get(
    "/safras/{safra_id}/tarefas",
    response_model=List[TarefaResponse],
    summary="Lista tarefas planejadas da safra",
)
async def listar_tarefas(
    safra_id: UUID,
    status: Optional[str] = Query(None),
    talhao_id: Optional[UUID] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = TarefaService(session, tenant_id)
    return await svc.listar(safra_id, status=status, talhao_id=talhao_id)


@router.post(
    "/safras/{safra_id}/tarefas",
    response_model=TarefaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria tarefa (MANUAL nasce APROVADA; SOLO/TEMPLATE nasce PENDENTE_APROVACAO)",
)
async def criar_tarefa(
    safra_id: UUID,
    dados: TarefaCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    user_id = UUID(user["sub"]) if user.get("sub") else None
    svc = TarefaService(session, tenant_id, user_id=user_id)
    tarefa = await svc.criar(safra_id, dados, user_id=user_id)
    await session.commit()
    await session.refresh(tarefa)
    return tarefa


@router.post(
    "/safras/{safra_id}/tarefas/multi-talhao",
    response_model=List[TarefaResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Fan-out: cria 1 tarefa por talhão em talhoes_ids, unidas por grupo_geracao_id",
)
async def criar_tarefa_multi_talhao(
    safra_id: UUID,
    dados: TarefaCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    user_id = UUID(user["sub"]) if user.get("sub") else None
    svc = TarefaService(session, tenant_id, user_id=user_id)
    tarefas = await svc.criar_multi_talhao(safra_id, dados, user_id=user_id)
    await session.commit()
    for tarefa in tarefas:
        await session.refresh(tarefa)
    return tarefas


@router.get(
    "/tarefas/{tarefa_id}",
    response_model=TarefaResponse,
    summary="Detalha uma tarefa",
)
async def detalhar_tarefa(
    tarefa_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = TarefaService(session, tenant_id)
    return await svc.get(tarefa_id)


@router.patch(
    "/tarefas/{tarefa_id}",
    response_model=TarefaResponse,
    summary="Atualiza dados da tarefa",
)
async def atualizar_tarefa(
    tarefa_id: UUID,
    dados: TarefaUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    user_id = UUID(user["sub"]) if user.get("sub") else None
    svc = TarefaService(session, tenant_id, user_id=user_id)
    tarefa = await svc.atualizar(tarefa_id, dados)
    await session.commit()
    await session.refresh(tarefa)
    return tarefa


@router.patch(
    "/tarefas/{tarefa_id}/aprovar",
    response_model=TarefaResponse,
    summary="Aprova tarefa pendente",
)
async def aprovar_tarefa(
    tarefa_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    aprovador_id = UUID(user["sub"]) if user.get("sub") else tenant_id
    svc = TarefaService(session, tenant_id, user_id=aprovador_id)
    tarefa = await svc.aprovar(tarefa_id, aprovador_id)
    await session.commit()
    await session.refresh(tarefa)
    return tarefa


@router.delete(
    "/tarefas/{tarefa_id}/rejeitar",
    response_model=TarefaResponse,
    summary="Rejeita/cancela tarefa",
)
async def rejeitar_tarefa(
    tarefa_id: UUID,
    motivo: str = Query(..., min_length=3),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    user_id = UUID(user["sub"]) if user.get("sub") else None
    svc = TarefaService(session, tenant_id, user_id=user_id)
    tarefa = await svc.rejeitar(tarefa_id, motivo=motivo, user_id=user_id)
    await session.commit()
    await session.refresh(tarefa)
    return tarefa


@router.patch(
    "/tarefas/{tarefa_id}/invalidar",
    response_model=TarefaResponse,
    summary="Invalida tarefa que já integra o histórico operacional",
)
async def invalidar_tarefa(
    tarefa_id: UUID,
    motivo: str = Query(..., min_length=3),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    user_id = UUID(user["sub"]) if user.get("sub") else None
    svc = TarefaService(session, tenant_id, user_id=user_id)
    tarefa = await svc.invalidar(tarefa_id, motivo=motivo, user_id=user_id)
    await session.commit()
    await session.refresh(tarefa)
    return tarefa


@router.patch(
    "/tarefas/{tarefa_id}/iniciar",
    response_model=TarefaResponse,
    summary="Marca tarefa como em execução",
)
async def iniciar_tarefa(
    tarefa_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente", "operador"])),
):
    user_id = UUID(user["sub"]) if user.get("sub") else None
    svc = TarefaService(session, tenant_id, user_id=user_id)
    tarefa = await svc.iniciar(tarefa_id)
    await session.commit()
    await session.refresh(tarefa)
    return tarefa


@router.patch(
    "/tarefas/{tarefa_id}/concluir",
    response_model=TarefaResponse,
    summary="Conclui tarefa manualmente",
)
async def concluir_tarefa(
    tarefa_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente", "operador"])),
):
    user_id = UUID(user["sub"]) if user.get("sub") else None
    svc = TarefaService(session, tenant_id, user_id=user_id)
    tarefa = await svc.concluir(tarefa_id)
    await session.commit()
    await session.refresh(tarefa)
    return tarefa


@router.delete(
    "/tarefas/{tarefa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui fisicamente tarefa apenas antes de gerar fatos operacionais",
)
async def cancelar_tarefa(
    tarefa_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin"])),
):
    user_id = UUID(user["sub"]) if user.get("sub") else None
    svc = TarefaService(session, tenant_id, user_id=user_id)
    await svc.excluir(tarefa_id)
    await session.commit()


@router.post(
    "/tarefas/{tarefa_id}/planejar-operacao",
    response_model=OperacaoAgricolaResponse,
    summary="Gera uma Operação Agrícola PLANEJADA (Ordem de Serviço) a partir desta Tarefa"
)
async def planejar_operacao(
    tarefa_id: UUID,
    dados: PlanejarOperacaoRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    user_id = UUID(user["sub"]) if user.get("sub") else None
    svc = TarefaService(session, tenant_id, user_id)
    operacao = await svc.gerar_operacao_planejada(tarefa_id, dados)
    await session.commit()
    await session.refresh(operacao)
    return operacao


@router.post(
    "/tarefas/{tarefa_id}/necessidades",
    response_model=SafraTarefaNecessidadeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adiciona uma necessidade agronômica estruturada à tarefa",
)
async def adicionar_necessidade(
    tarefa_id: UUID,
    dados: SafraTarefaNecessidadeCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    svc = TarefaService(session, tenant_id)
    necessidade = await svc.adicionar_necessidade(tarefa_id, dados)
    await session.commit()
    await session.refresh(necessidade)
    return necessidade


@router.get(
    "/tarefas/{tarefa_id}/necessidades",
    response_model=List[SafraTarefaNecessidadeResponse],
    summary="Lista as necessidades agronômicas da tarefa",
)
async def listar_necessidades(
    tarefa_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = TarefaService(session, tenant_id)
    return await svc.listar_necessidades(tarefa_id)


@router.patch(
    "/tarefas/{tarefa_id}/necessidades/{necessidade_id}",
    response_model=SafraTarefaNecessidadeResponse,
    summary="Atualiza uma necessidade agronômica da tarefa",
)
async def atualizar_necessidade(
    tarefa_id: UUID,
    necessidade_id: UUID,
    dados: SafraTarefaNecessidadeUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    svc = TarefaService(session, tenant_id)
    necessidade = await svc.atualizar_necessidade(tarefa_id, necessidade_id, dados)
    await session.commit()
    await session.refresh(necessidade)
    return necessidade


@router.delete(
    "/tarefas/{tarefa_id}/necessidades/{necessidade_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove uma necessidade agronômica da tarefa",
)
async def remover_necessidade(
    tarefa_id: UUID,
    necessidade_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "gerente"])),
):
    svc = TarefaService(session, tenant_id)
    await svc.remover_necessidade(tarefa_id, necessidade_id)
    await session.commit()
