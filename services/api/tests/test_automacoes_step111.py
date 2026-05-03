"""
Step 111 — Testes de Agendamento de Automações
Cobre: frequência padrão MANUAL, cálculo de proxima_execucao, persistência, sem scheduler.
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from automacoes.service import AutomacoesService, _calcular_proxima_execucao, FREQUENCIA_DELTAS


def _make_session(scalar_one=None, scalars_result=None):
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = scalars_result or []
    result.scalar_one_or_none.return_value = scalar_one
    session.execute = AsyncMock(return_value=result)
    return session


# ── _calcular_proxima_execucao ──────────────────────────────────────────────

def test_proxima_manual_retorna_none():
    assert _calcular_proxima_execucao("MANUAL") is None


def test_proxima_diaria():
    before = datetime.now(timezone.utc)
    result = _calcular_proxima_execucao("DIARIA")
    assert result is not None
    diff = result - before
    assert timedelta(hours=23) < diff <= timedelta(days=1, seconds=5)


def test_proxima_semanal():
    before = datetime.now(timezone.utc)
    result = _calcular_proxima_execucao("SEMANAL")
    assert result is not None
    diff = result - before
    assert timedelta(days=6, hours=23) < diff <= timedelta(days=7, seconds=5)


def test_proxima_mensal():
    before = datetime.now(timezone.utc)
    result = _calcular_proxima_execucao("MENSAL")
    assert result is not None
    diff = result - before
    assert timedelta(days=29, hours=23) < diff <= timedelta(days=30, seconds=5)


def test_proxima_frequencia_desconhecida_retorna_none():
    assert _calcular_proxima_execucao("BIMESTRAL") is None


# ── atualizar_configuracao com frequencia ──────────────────────────────────

@pytest.mark.asyncio
async def test_criar_com_frequencia_semanal():
    session = _make_session(scalar_one=None)
    svc = AutomacoesService(session, uuid.uuid4())
    cfg = await svc.atualizar_configuracao("MARGEM_NEGATIVA", True, frequencia="SEMANAL")

    assert cfg.frequencia == "SEMANAL"
    assert cfg.proxima_execucao is not None
    diff = cfg.proxima_execucao - datetime.now(timezone.utc)
    assert timedelta(days=6) < diff <= timedelta(days=7, seconds=10)


@pytest.mark.asyncio
async def test_criar_sem_frequencia_usa_manual():
    session = _make_session(scalar_one=None)
    svc = AutomacoesService(session, uuid.uuid4())
    cfg = await svc.atualizar_configuracao("INSUMOS_DOMINANTE", True)

    assert cfg.frequencia == "MANUAL"
    assert cfg.proxima_execucao is None


@pytest.mark.asyncio
async def test_atualizar_frequencia_existente():
    """Mudança de MANUAL → DIARIA deve recalcular proxima_execucao."""
    existing = MagicMock()
    existing.regra = "AUMENTO_CUSTO"
    existing.ativa = True
    existing.frequencia = "MANUAL"
    existing.proxima_execucao = None
    session = _make_session(scalar_one=existing)

    svc = AutomacoesService(session, uuid.uuid4())
    cfg = await svc.atualizar_configuracao("AUMENTO_CUSTO", True, frequencia="DIARIA")

    assert cfg.frequencia == "DIARIA"
    assert cfg.proxima_execucao is not None
    assert existing.frequencia == "DIARIA"


@pytest.mark.asyncio
async def test_listar_configuracoes_inclui_frequencia():
    """listar_configuracoes deve retornar frequencia e proxima_execucao."""
    db_cfg = MagicMock()
    db_cfg.regra = "MARGEM_NEGATIVA"
    db_cfg.ativa = True
    db_cfg.frequencia = "SEMANAL"
    db_cfg.proxima_execucao = datetime.now(timezone.utc) + timedelta(days=7)

    session = _make_session(scalars_result=[db_cfg])
    svc = AutomacoesService(session, uuid.uuid4())
    configs = await svc.listar_configuracoes()

    margem = next(c for c in configs if c.regra == "MARGEM_NEGATIVA")
    assert margem.frequencia == "SEMANAL"
    assert margem.proxima_execucao is not None

    outras = [c for c in configs if c.regra != "MARGEM_NEGATIVA"]
    for c in outras:
        assert c.frequencia == "MANUAL"
        assert c.proxima_execucao is None
