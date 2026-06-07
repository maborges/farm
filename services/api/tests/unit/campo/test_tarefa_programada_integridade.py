from __future__ import annotations

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from campo.models import TarefaCampo
from campo.service import TarefaProgramadaService
from core.exceptions import BusinessRuleError, EntityNotFoundError


pytestmark = pytest.mark.asyncio


def _make_task(status_execucao: str) -> TarefaCampo:
    return TarefaCampo(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        origem="PROGRAMADA",
        status_execucao=status_execucao,
        titulo="Pulverização",
        data_programada=date.today(),
        prioridade="NORMAL",
        type="APLICACAO_DEFENSIVO",
        module="agricola",
        unidade_produtiva_id=uuid.uuid4(),
        status="PENDENTE",
        dados={},
        fotos=[],
        localizacao_status="DISPONIVEL",
        concluida_em=datetime.utcnow() if status_execucao == "CONCLUIDA" else None,
        invalidado_em=datetime.utcnow() if status_execucao == "INVALIDADA" else None,
        motivo_invalidacao="Correção documental" if status_execucao == "INVALIDADA" else None,
    )


async def test_tarefa_concluida_nao_pode_ser_cancelada():
    session = AsyncMock(spec=AsyncSession)
    service = TarefaProgramadaService(session, uuid.uuid4(), uuid.uuid4())
    service.get_or_fail = AsyncMock(return_value=_make_task("CONCLUIDA"))

    with pytest.raises(BusinessRuleError, match="histórico operacional"):
        await service.cancelar(uuid.uuid4())

    session.flush.assert_not_called()


async def test_tarefa_pendente_pode_ser_cancelada():
    session = AsyncMock(spec=AsyncSession)
    session.flush = AsyncMock()
    task = _make_task("PENDENTE")
    service = TarefaProgramadaService(session, uuid.uuid4(), uuid.uuid4())
    service.get_or_fail = AsyncMock(return_value=task)

    updated = await service.cancelar(task.id)

    assert updated.status_execucao == "CANCELADA"
    session.flush.assert_awaited_once()


async def test_tarefa_concluida_pode_ser_invalidada():
    session = AsyncMock(spec=AsyncSession)
    session.flush = AsyncMock()
    task = _make_task("CONCLUIDA")
    service = TarefaProgramadaService(session, uuid.uuid4(), uuid.uuid4(), ip_address="127.0.0.1")
    service.get_or_fail = AsyncMock(return_value=task)

    with (
        patch("campo.service.write_audit_log", new=AsyncMock()) as write_audit_log,
        patch(
            "agricola.caderno.service.CadernoCampoService.propagar_invalidacao_origem_operacional",
            new=AsyncMock(),
        ) as propagar_invalidacao,
    ):
        updated = await service.invalidar(task.id, "Aplicação registrada incorretamente")

    assert updated.status_execucao == "INVALIDADA"
    assert updated.motivo_invalidacao == "Aplicação registrada incorretamente"
    assert updated.invalidado_por == service.user_id
    session.flush.assert_awaited_once()
    write_audit_log.assert_awaited_once()
    propagar_invalidacao.assert_awaited_once()


async def test_tarefa_invalidada_nao_pode_ser_cancelada():
    session = AsyncMock(spec=AsyncSession)
    task = _make_task("INVALIDADA")
    service = TarefaProgramadaService(session, uuid.uuid4(), uuid.uuid4())
    service.get_or_fail = AsyncMock(return_value=task)

    with pytest.raises(BusinessRuleError, match="histórico operacional"):
        await service.cancelar(task.id)


async def test_tarefa_invalidada_exige_motivo():
    session = AsyncMock(spec=AsyncSession)
    task = _make_task("CONCLUIDA")
    service = TarefaProgramadaService(session, uuid.uuid4(), uuid.uuid4())
    service.get_or_fail = AsyncMock(return_value=task)

    with pytest.raises(BusinessRuleError, match="Motivo de invalidação é obrigatório"):
        await service.invalidar(task.id, " ")


async def test_tarefa_invalidada_exige_status_concluido():
    session = AsyncMock(spec=AsyncSession)
    task = _make_task("PENDENTE")
    service = TarefaProgramadaService(session, uuid.uuid4(), uuid.uuid4())
    service.get_or_fail = AsyncMock(return_value=task)

    with pytest.raises(BusinessRuleError, match="tarefas concluídas"):
        await service.invalidar(task.id, "Aplicação registrada incorretamente")


async def test_get_or_fail_filtra_por_tenant():
    session = AsyncMock(spec=AsyncSession)
    service = TarefaProgramadaService(session, uuid.uuid4(), uuid.uuid4())
    session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    with pytest.raises(EntityNotFoundError):
        await service.get_or_fail(uuid.uuid4())

    stmt = session.execute.await_args.args[0]
    assert "campo_tarefas.tenant_id" in str(stmt)
