"""
Step 110 — Testes de Configuração de Automações
Cobre: listar regras (padrão ativa=True), ativar/desativar, persistência, respeito nas execuções.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from automacoes.service import AutomacoesService, REGRAS_DISPONIVEIS


def _make_session():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


def _mock_execute(scalars_result=None, scalar_one="__unset__"):
    """Retorna um mock de session.execute() configurado."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars_result or []
    result.scalar_one_or_none.return_value = None if scalar_one == "__unset__" else scalar_one
    exec_mock = AsyncMock(return_value=result)
    return exec_mock


@pytest.mark.asyncio
async def test_listar_configuracoes_padrao_ativa():
    """Sem registros no banco, todas as regras devem vir ativas por padrão."""
    session = _make_session()
    session.execute = _mock_execute(scalars_result=[])

    svc = AutomacoesService(session, uuid.uuid4())
    configs = await svc.listar_configuracoes(safra_id=uuid.uuid4())

    assert len(configs) == len(REGRAS_DISPONIVEIS)
    for cfg in configs:
        assert cfg.ativa is True
        assert cfg.regra in REGRAS_DISPONIVEIS
        assert cfg.titulo == REGRAS_DISPONIVEIS[cfg.regra]["titulo"]


@pytest.mark.asyncio
async def test_listar_configuracoes_respeita_banco():
    """Se banco tiver regra desativada, deve refletir ativa=False."""
    session = _make_session()

    db_cfg = MagicMock()
    db_cfg.regra = "MARGEM_NEGATIVA"
    db_cfg.ativa = False
    session.execute = _mock_execute(scalars_result=[db_cfg])

    svc = AutomacoesService(session, uuid.uuid4())
    configs = await svc.listar_configuracoes(safra_id=uuid.uuid4())

    margem = next(c for c in configs if c.regra == "MARGEM_NEGATIVA")
    assert margem.ativa is False

    outras = [c for c in configs if c.regra != "MARGEM_NEGATIVA"]
    for c in outras:
        assert c.ativa is True


@pytest.mark.asyncio
async def test_atualizar_configuracao_cria_registro():
    """Sem registro existente, deve criar um novo."""
    session = _make_session()
    session.execute = _mock_execute(scalar_one=None)

    svc = AutomacoesService(session, uuid.uuid4())
    cfg = await svc.atualizar_configuracao("AUMENTO_CUSTO", False, safra_id=uuid.uuid4())

    assert cfg.regra == "AUMENTO_CUSTO"
    assert cfg.ativa is False
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_atualizar_configuracao_atualiza_existente():
    """Com registro existente, deve atualizar sem criar novo."""
    session = _make_session()
    existing = MagicMock()
    existing.regra = "INSUMOS_DOMINANTE"
    existing.ativa = True
    session.execute = _mock_execute(scalar_one=existing)

    svc = AutomacoesService(session, uuid.uuid4())
    cfg = await svc.atualizar_configuracao("INSUMOS_DOMINANTE", False, safra_id=uuid.uuid4())

    assert cfg.ativa is False
    assert existing.ativa is False
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_atualizar_configuracao_regra_invalida():
    """Regra inexistente deve lançar BusinessRuleError."""
    from core.exceptions import BusinessRuleError

    session = _make_session()
    svc = AutomacoesService(session, uuid.uuid4())

    with pytest.raises(BusinessRuleError):
        await svc.atualizar_configuracao("REGRA_FAKE", True)


@pytest.mark.asyncio
async def test_regras_ativas_filtra_desativadas():
    """_regras_ativas deve excluir regras com ativa=False."""
    session = _make_session()

    db_cfg = MagicMock()
    db_cfg.regra = "MARGEM_NEGATIVA"
    db_cfg.ativa = False
    session.execute = _mock_execute(scalars_result=[db_cfg])

    svc = AutomacoesService(session, uuid.uuid4())
    ativas = await svc._regras_ativas(safra_id=uuid.uuid4())

    assert "MARGEM_NEGATIVA" not in ativas
    assert "INSUMOS_DOMINANTE" in ativas
    assert "AUMENTO_CUSTO" in ativas


@pytest.mark.asyncio
async def test_executar_respeita_regra_desativada():
    """Regra desativada não deve gerar ação nem notificação."""
    session = _make_session()
    safra_id = uuid.uuid4()

    # Apenas MARGEM_NEGATIVA desativada
    db_cfg = MagicMock()
    db_cfg.regra = "MARGEM_NEGATIVA"
    db_cfg.ativa = False

    execute_calls = [0]

    async def execute_side_effect(stmt):
        result = MagicMock()
        call = execute_calls[0]
        execute_calls[0] += 1
        if call == 0:
            # listar_configuracoes
            result.scalars.return_value.all.return_value = [db_cfg]
        else:
            result.scalars.return_value.all.return_value = []
            result.scalar_one_or_none.return_value = None
        return result

    session.execute = execute_side_effect

    insight_mock = MagicMock()
    insight_mock.cenario_margem = -15.0
    insight_mock.categorias = []

    lancamento_mock = MagicMock()
    lancamento_mock.serie_temporal = AsyncMock(return_value=[])
    lancamento_mock.insight_dashboard = AsyncMock(return_value=insight_mock)

    notif_mock = MagicMock()
    notif_mock.criar_sem_duplicar = AsyncMock(return_value=None)

    with patch("automacoes.service.LancamentoService", return_value=lancamento_mock), \
         patch("automacoes.service.NotificacaoService", return_value=notif_mock):
        svc = AutomacoesService(session, uuid.uuid4())
        resultado = await svc.executar(safra_id)

    assert "MARGEM_NEGATIVA" not in resultado.regras_disparadas
