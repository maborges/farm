from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.tarefas.models import SafraTarefa
from agricola.tarefas.service import (
    TASK_DELETE_BLOCKED_MESSAGE,
    TaskDeleteEvaluation,
    TarefaService,
)
from core.exceptions import BusinessRuleError


pytestmark = pytest.mark.asyncio


def _make_task(*, status: str = "PENDENTE_APROVACAO") -> SafraTarefa:
    return SafraTarefa(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        safra_id=uuid.uuid4(),
        origem="MANUAL",
        tipo="PULVERIZACAO",
        descricao="Tarefa teste",
        criticidade="NORMAL",
        prioridade="MEDIA",
        status=status,
        concluida_em=datetime.utcnow() if status == "CONCLUIDA" else None,
    )


def _make_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    return session


async def test_tarefa_planejada_pode_ser_excluida():
    session = _make_session()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tarefa = _make_task(status="PENDENTE_APROVACAO")
    service = TarefaService(session, tenant_id, user_id=user_id)
    service._get = AsyncMock(return_value=tarefa)
    service._related_operacao_ids = AsyncMock(return_value=[])
    service._related_caderno_entry_ids = AsyncMock(return_value=[])

    with patch("agricola.tarefas.service.write_audit_log", new=AsyncMock()) as write_audit_log:
        assert await service.pode_excluir_tarefa(tarefa.id) is True
        await service.excluir(tarefa.id)

    session.delete.assert_awaited_once_with(tarefa)
    session.flush.assert_awaited()
    write_audit_log.assert_awaited_once()


async def test_tarefa_aprovada_nao_pode_ser_excluida():
    session = _make_session()
    tarefa = _make_task(status="APROVADA")
    service = TarefaService(session, tarefa.tenant_id, user_id=uuid.uuid4())
    service._related_operacao_ids = AsyncMock(return_value=[])
    service._related_caderno_entry_ids = AsyncMock(return_value=[])

    evaluation = await service._avaliar_exclusao_tarefa(tarefa)

    assert evaluation.allowed is False
    assert "status:APROVADA" in evaluation.blockers


async def test_tarefa_realizada_nao_pode_ser_excluida():
    session = _make_session()
    tarefa = _make_task(status="CONCLUIDA")
    service = TarefaService(session, uuid.uuid4(), user_id=uuid.uuid4())
    service._get = AsyncMock(return_value=tarefa)
    service._avaliar_exclusao_tarefa = AsyncMock(
        return_value=TaskDeleteEvaluation(allowed=False, blockers=["status:CONCLUIDA"]),
    )

    with pytest.raises(BusinessRuleError, match=TASK_DELETE_BLOCKED_MESSAGE):
        await service.excluir(tarefa.id)

    session.delete.assert_not_called()


async def test_tarefa_com_evento_no_caderno_nao_pode_ser_excluida():
    session = _make_session()
    tarefa = _make_task(status="APROVADA")
    service = TarefaService(session, tarefa.tenant_id, user_id=uuid.uuid4())
    service._related_operacao_ids = AsyncMock(return_value=[])
    service._related_caderno_entry_ids = AsyncMock(return_value=[uuid.uuid4()])
    session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=0))

    evaluation = await service._avaliar_exclusao_tarefa(tarefa)

    assert evaluation.allowed is False
    assert "caderno" in evaluation.blockers


async def test_tarefa_com_operacao_agricola_nao_pode_ser_excluida():
    session = _make_session()
    tarefa = _make_task(status="APROVADA")
    operacao_id = uuid.uuid4()
    service = TarefaService(session, tarefa.tenant_id, user_id=uuid.uuid4())
    service._related_operacao_ids = AsyncMock(return_value=[operacao_id])
    service._related_caderno_entry_ids = AsyncMock(return_value=[])
    session.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))),
        MagicMock(scalar_one=MagicMock(return_value=0)),
    ]

    evaluation = await service._avaliar_exclusao_tarefa(tarefa)

    assert evaluation.allowed is False
    assert "operacao_agricola" in evaluation.blockers


async def test_tarefa_com_evidencia_nao_pode_ser_excluida():
    session = _make_session()
    tarefa = _make_task(status="PENDENTE_APROVACAO")
    service = TarefaService(session, tarefa.tenant_id, user_id=uuid.uuid4())
    service._related_operacao_ids = AsyncMock(return_value=[])
    service._related_caderno_entry_ids = AsyncMock(return_value=[uuid.uuid4()])
    session.execute.return_value = MagicMock(scalar_one=MagicMock(return_value=1))

    evaluation = await service._avaliar_exclusao_tarefa(tarefa)

    assert evaluation.allowed is False
    assert "evidencia" in evaluation.blockers


async def test_tarefa_com_movimentacao_estoque_nao_pode_ser_excluida():
    session = _make_session()
    tarefa = _make_task(status="PENDENTE_APROVACAO")
    operacao_id = uuid.uuid4()
    execucao_id = uuid.uuid4()
    service = TarefaService(session, tarefa.tenant_id, user_id=uuid.uuid4())
    service._related_operacao_ids = AsyncMock(return_value=[operacao_id])
    service._related_caderno_entry_ids = AsyncMock(return_value=[])
    session.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[execucao_id])))),
        MagicMock(scalar_one=MagicMock(return_value=1)),
        MagicMock(scalar_one=MagicMock(return_value=0)),
        MagicMock(scalar_one=MagicMock(return_value=0)),
    ]

    evaluation = await service._avaliar_exclusao_tarefa(tarefa)

    assert evaluation.allowed is False
    assert "estoque" in evaluation.blockers


async def test_tarefa_com_impacto_financeiro_nao_pode_ser_excluida():
    session = _make_session()
    tarefa = _make_task(status="PENDENTE_APROVACAO")
    operacao_id = uuid.uuid4()
    execucao_id = uuid.uuid4()
    service = TarefaService(session, tarefa.tenant_id, user_id=uuid.uuid4())
    service._related_operacao_ids = AsyncMock(return_value=[operacao_id])
    service._related_caderno_entry_ids = AsyncMock(return_value=[])
    session.execute.side_effect = [
        MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[execucao_id])))),
        MagicMock(scalar_one=MagicMock(return_value=0)),
        MagicMock(scalar_one=MagicMock(return_value=1)),
        MagicMock(scalar_one=MagicMock(return_value=0)),
    ]

    evaluation = await service._avaliar_exclusao_tarefa(tarefa)

    assert evaluation.allowed is False
    assert "financeiro" in evaluation.blockers


async def test_tarefa_cancelada_mantem_historico_e_auditoria():
    session = _make_session()
    user_id = uuid.uuid4()
    tarefa = _make_task(status="APROVADA")
    service = TarefaService(session, tarefa.tenant_id, user_id=user_id)
    service._get = AsyncMock(return_value=tarefa)

    with patch("agricola.tarefas.service.write_audit_log", new=AsyncMock()) as write_audit_log:
        updated = await service.rejeitar(
            tarefa.id,
            motivo="Janela operacional perdida",
            user_id=user_id,
        )

    assert updated.status == "CANCELADA"
    assert updated.motivo_cancelamento == "Janela operacional perdida"
    assert updated.cancelado_por == user_id
    write_audit_log.assert_awaited_once()


async def test_tarefa_invalidada_registra_auditoria():
    session = _make_session()
    user_id = uuid.uuid4()
    tarefa = _make_task(status="CONCLUIDA")
    service = TarefaService(session, tarefa.tenant_id, user_id=user_id)
    service._get = AsyncMock(return_value=tarefa)
    service._related_operacao_ids = AsyncMock(return_value=[])
    service._avaliar_exclusao_tarefa = AsyncMock(
        return_value=TaskDeleteEvaluation(allowed=False, blockers=["operacao_agricola"]),
    )

    with (
        patch("agricola.tarefas.service.write_audit_log", new=AsyncMock()) as write_audit_log,
        patch(
            "agricola.caderno.service.CadernoCampoService.propagar_invalidacao_origem_operacional",
            new=AsyncMock(),
        ) as propagar_invalidacao,
    ):
        updated = await service.invalidar(
            tarefa.id,
            motivo="Registro executado em talhão incorreto",
            user_id=user_id,
        )

    assert updated.status == "INVALIDADA"
    assert updated.motivo_invalidacao == "Registro executado em talhão incorreto"
    assert updated.invalidado_por == user_id
    write_audit_log.assert_awaited_once()
    propagar_invalidacao.assert_awaited_once()


async def test_validacao_de_operacao_filtra_por_tenant():
    session = _make_session()
    tenant_id = uuid.uuid4()
    tarefa = _make_task(status="APROVADA")
    tarefa.tenant_id = tenant_id
    service = TarefaService(session, tenant_id, user_id=uuid.uuid4())
    session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
    )

    await service._related_operacao_ids(tarefa)

    stmt = session.execute.await_args.args[0]
    assert "operacoes_agricolas.tenant_id" in str(stmt)
