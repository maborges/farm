"""Testes de governança de automações — Step 109."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from automacoes.service import AutomacoesService
from automacoes.models import AutomacaoExecucao
from financeiro.schemas.lancamento_schema import InsightDashboard, SerieTemporal, CategoriaBreakdown


def _mock_session():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


def _insight(margem=None, categorias=None):
    cats = [CategoriaBreakdown(nome=k, valor=v) for k, v in (categorias or {}).items()]
    return InsightDashboard(
        total_custos=5000.0, quantidade_lancamentos=10,
        safra_id=None, safra_nome="2024/25",
        cenario_custo_total=6000.0, cenario_receita_total=7000.0,
        cenario_margem=margem, mensagem=None, categorias=cats,
    )


@pytest.mark.asyncio
async def test_execucao_registrada_sem_regras():
    """Mesmo sem regras disparadas, execução deve ser registrada."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = _mock_session()

    svc = AutomacoesService(session, tenant_id)

    with patch("automacoes.service.LancamentoService") as MockLanc, \
         patch("automacoes.service.NotificacaoService") as MockNotif:
        MockLanc.return_value.insight_dashboard = AsyncMock(return_value=_insight(margem=20.0))
        MockLanc.return_value.serie_temporal = AsyncMock(return_value=[])
        MockLanc.return_value.gerar_alertas = AsyncMock(return_value=[])
        MockNotif.return_value.criar_sem_duplicar = AsyncMock(return_value=None)

        await svc.executar(safra_id)

    # session.add deve ter sido chamado pelo menos uma vez (para AutomacaoExecucao)
    assert session.add.call_count >= 1
    added = session.add.call_args_list[-1][0][0]
    assert isinstance(added, AutomacaoExecucao)
    assert added.status == "SUCESSO"
    assert added.safra_id == safra_id
    assert added.tenant_id == tenant_id


@pytest.mark.asyncio
async def test_execucao_com_regras_registra_nomes():
    """Regras disparadas devem ser salvas na execução."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = _mock_session()

    svc = AutomacoesService(session, tenant_id)

    with patch("automacoes.service.LancamentoService") as MockLanc, \
         patch("automacoes.service.NotificacaoService") as MockNotif:
        MockLanc.return_value.insight_dashboard = AsyncMock(return_value=_insight(margem=-10.0))
        MockLanc.return_value.serie_temporal = AsyncMock(return_value=[])
        MockLanc.return_value.gerar_alertas = AsyncMock(return_value=[])
        MockNotif.return_value.criar_sem_duplicar = AsyncMock(return_value=MagicMock())

        await svc.executar(safra_id)

    added = session.add.call_args_list[-1][0][0]
    assert isinstance(added, AutomacaoExecucao)
    assert "MARGEM_NEGATIVA" in added.regras_disparadas


@pytest.mark.asyncio
async def test_execucao_erro_registra_status_erro():
    """Exceção durante execução deve registrar status ERRO."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = _mock_session()

    svc = AutomacoesService(session, tenant_id)

    with patch("automacoes.service.LancamentoService") as MockLanc, \
         patch("automacoes.service.NotificacaoService"):
        MockLanc.return_value.insight_dashboard = AsyncMock(side_effect=RuntimeError("DB Error"))
        MockLanc.return_value.serie_temporal = AsyncMock(return_value=[])
        MockLanc.return_value.gerar_alertas = AsyncMock(return_value=[])

        resultado = await svc.executar(safra_id)

    added = session.add.call_args_list[-1][0][0]
    assert isinstance(added, AutomacaoExecucao)
    assert added.status == "ERRO"
    assert resultado.mensagem.startswith("Erro durante")


@pytest.mark.asyncio
async def test_listar_execucoes():
    """listar_execucoes deve retornar registros do tenant."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    exec1 = AutomacaoExecucao()
    exec1.id = uuid.uuid4()
    exec1.tenant_id = tenant_id
    exec1.safra_id = safra_id
    exec1.status = "SUCESSO"
    exec1.acoes_criadas = 1
    exec1.notificacoes_criadas = 0
    exec1.regras_disparadas = ["MARGEM_NEGATIVA"]
    exec1.mensagem = ""

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [exec1]
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    svc = AutomacoesService(session, tenant_id)
    execucoes = await svc.listar_execucoes(safra_id)

    assert len(execucoes) == 1
    assert execucoes[0].status == "SUCESSO"
