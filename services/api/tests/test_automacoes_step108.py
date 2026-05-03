"""Testes de idempotência e criação correta das automações — Step 108."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from automacoes.service import AutomacoesService
from financeiro.schemas.lancamento_schema import InsightDashboard, SerieTemporal, CategoriaBreakdown


def _mock_session():
    scalars = MagicMock()
    scalars.scalar_one_or_none.return_value = None
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


def _insight(margem: float | None = None, categorias: dict | None = None) -> InsightDashboard:
    cats = [CategoriaBreakdown(nome=k, valor=v) for k, v in (categorias or {}).items()]
    return InsightDashboard(
        total_custos=5000.0,
        quantidade_lancamentos=10,
        safra_id=None,
        safra_nome="2024/25",
        cenario_custo_total=6000.0,
        cenario_receita_total=5000.0 if margem is not None and margem < 0 else 8000.0,
        cenario_margem=margem,
        mensagem=None,
        categorias=cats,
    )


@pytest.mark.asyncio
async def test_margem_negativa_cria_acao():
    """Com margem negativa deve criar ação e notificação."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = _mock_session()

    svc = AutomacoesService(session, tenant_id)

    with patch("automacoes.service.LancamentoService") as MockLanc, \
         patch("automacoes.service.PlanoAcaoService"), \
         patch("automacoes.service.NotificacaoService") as MockNotif:

        MockLanc.return_value.insight_dashboard = AsyncMock(return_value=_insight(margem=-15.0))
        MockLanc.return_value.serie_temporal = AsyncMock(return_value=[])
        MockLanc.return_value.gerar_alertas = AsyncMock(return_value=[])
        MockNotif.return_value.criar_sem_duplicar = AsyncMock(return_value=MagicMock())

        resultado = await svc.executar(safra_id)

    assert resultado.acoes_criadas >= 1
    assert resultado.notificacoes_criadas >= 1


@pytest.mark.asyncio
async def test_margem_positiva_nao_cria_acao_margem():
    """Com margem positiva não deve criar ação de margem negativa."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = _mock_session()

    svc = AutomacoesService(session, tenant_id)

    with patch("automacoes.service.LancamentoService") as MockLanc, \
         patch("automacoes.service.PlanoAcaoService"), \
         patch("automacoes.service.NotificacaoService") as MockNotif:

        MockLanc.return_value.insight_dashboard = AsyncMock(return_value=_insight(margem=25.0))
        MockLanc.return_value.serie_temporal = AsyncMock(return_value=[])
        MockLanc.return_value.gerar_alertas = AsyncMock(return_value=[])
        MockNotif.return_value.criar_sem_duplicar = AsyncMock(return_value=None)

        resultado = await svc.executar(safra_id)

    assert "margem negativa" not in " ".join(resultado.detalhes)


@pytest.mark.asyncio
async def test_insumos_dominante_cria_acao():
    """INSUMOS como maior categoria deve criar ação."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = _mock_session()

    svc = AutomacoesService(session, tenant_id)

    with patch("automacoes.service.LancamentoService") as MockLanc, \
         patch("automacoes.service.PlanoAcaoService"), \
         patch("automacoes.service.NotificacaoService") as MockNotif:

        MockLanc.return_value.insight_dashboard = AsyncMock(
            return_value=_insight(margem=10.0, categorias={"INSUMOS": 3000.0, "OPERACOES": 1000.0})
        )
        MockLanc.return_value.serie_temporal = AsyncMock(return_value=[])
        MockLanc.return_value.gerar_alertas = AsyncMock(return_value=[])
        MockNotif.return_value.criar_sem_duplicar = AsyncMock(return_value=None)

        resultado = await svc.executar(safra_id)

    assert resultado.acoes_criadas >= 1
    assert any("insumo" in d.lower() for d in resultado.detalhes)


@pytest.mark.asyncio
async def test_aumento_custo_cria_notificacao():
    """Aumento de custo > 20% deve criar notificação."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    session = _mock_session()

    svc = AutomacoesService(session, tenant_id)
    serie = [
        SerieTemporal(periodo="2026-03", total=1000.0),
        SerieTemporal(periodo="2026-04", total=1300.0),  # 30% de aumento
    ]

    with patch("automacoes.service.LancamentoService") as MockLanc, \
         patch("automacoes.service.PlanoAcaoService"), \
         patch("automacoes.service.NotificacaoService") as MockNotif:

        MockLanc.return_value.insight_dashboard = AsyncMock(return_value=_insight(margem=5.0))
        MockLanc.return_value.serie_temporal = AsyncMock(return_value=serie)
        MockLanc.return_value.gerar_alertas = AsyncMock(return_value=[])
        notif_mock = MagicMock()
        MockNotif.return_value.criar_sem_duplicar = AsyncMock(return_value=notif_mock)

        resultado = await svc.executar(safra_id)

    assert resultado.notificacoes_criadas >= 1


@pytest.mark.asyncio
async def test_idempotencia_nao_duplica_acao():
    """Executar duas vezes não deve duplicar ações quando já existe PENDENTE."""
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()

    # Simula item já existente
    existente = MagicMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existente
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    svc = AutomacoesService(session, tenant_id)

    with patch("automacoes.service.LancamentoService") as MockLanc, \
         patch("automacoes.service.PlanoAcaoService"), \
         patch("automacoes.service.NotificacaoService") as MockNotif:

        MockLanc.return_value.insight_dashboard = AsyncMock(return_value=_insight(margem=-10.0))
        MockLanc.return_value.serie_temporal = AsyncMock(return_value=[])
        MockLanc.return_value.gerar_alertas = AsyncMock(return_value=[])
        MockNotif.return_value.criar_sem_duplicar = AsyncMock(return_value=None)

        resultado = await svc.executar(safra_id)

    # Ação não criada pois já existe
    assert resultado.acoes_criadas == 0
    session.add.assert_not_called()
