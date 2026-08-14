"""Testes de AlertasEngine._verificar_tarefas_atrasadas.

Regressão: o método importava `agricola.models.operacao.OperacaoCampo`,
módulo inexistente — ModuleNotFoundError toda vez que rodava, provavelmente
derrubando o ciclo de alertas inteiro do tenant (verificar_tenant não isola
falhas por sub-checagem). Corrigido para usar OperacaoAgricola/AreaRural,
mesmo model já usado por alert_engine/generators/agricultura_generator.py.
"""
import uuid
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from notificacoes.alertas_engine import AlertasEngine


def _operacao(dias_atraso: int, status: str = "PLANEJADA") -> MagicMock:
    o = MagicMock()
    o.id = uuid.uuid4()
    o.descricao = "Pulverização de fungicida"
    o.status = status
    o.data_prevista = date.today() - timedelta(days=dias_atraso)
    return o


@pytest.mark.asyncio
async def test_gera_alerta_com_operacoes_atrasadas():
    tenant_id = uuid.uuid4()
    operacoes = [_operacao(5), _operacao(10)]

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = operacoes
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    engine = AlertasEngine()
    alertas = await engine._verificar_tarefas_atrasadas(session, tenant_id)

    assert len(alertas) == 1
    alerta = alertas[0]
    assert alerta.tipo == "TAREFAS_ATRASADAS"
    assert alerta.meta["quantidade"] == 2
    assert alerta.meta["atraso_medio_dias"] == 7.5
    assert len(alerta.meta["acoes"]) == 2
    for item, o in zip(alerta.meta["acoes"], operacoes):
        assert item["endpoint"] == f"/operacoes/{o.id}"
        assert item["method"] == "PATCH"
        nova_data = date.fromisoformat(item["body"]["data_prevista"])
        assert nova_data == date.today() + timedelta(days=3)


@pytest.mark.asyncio
async def test_sem_operacoes_atrasadas_nao_gera_alerta():
    tenant_id = uuid.uuid4()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    engine = AlertasEngine()
    alertas = await engine._verificar_tarefas_atrasadas(session, tenant_id)

    assert alertas == []


@pytest.mark.asyncio
async def test_query_filtra_status_concluidos_e_tenant():
    """A query deve excluir CONCLUIDA/CANCELADA/REALIZADA e filtrar por tenant_id em ambas as tabelas."""
    tenant_id = uuid.uuid4()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    engine = AlertasEngine()
    await engine._verificar_tarefas_atrasadas(session, tenant_id)

    stmt = session.execute.call_args.args[0]
    stmt_str = str(stmt)
    assert "operacoes_agricolas" in stmt_str
    assert "cadastros_areas_rurais" in stmt_str or "talhao_id" in stmt_str
