"""
Step 117 — Testes de pacotes de créditos de IA.
Cobre: limite plano + créditos extras, consumo por PLANO vs PACOTE, solicitação.
"""
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from ia.usage_service import (
    verificar_limite_ia,
    creditos_extras_ativos,
    consumir_credito_pacote,
    consultar_creditos,
    solicitar_creditos,
    LIMITES_MENSAIS,
)
from ia.models import IACreditosPacote


def _session_mock(scalar_one=0, scalar_one_or_none=None, scalars_all=None):
    session = MagicMock()
    result = MagicMock()
    result.scalar_one.return_value = scalar_one
    result.scalar_one_or_none.return_value = scalar_one_or_none
    result.scalars.return_value.all.return_value = scalars_all or []
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# ── verificar_limite_ia com créditos extras ──────────────────────────────────

@pytest.mark.asyncio
async def test_dentro_limite_plano_fonte_plano():
    """Dentro do limite do plano → fonte PLANO."""
    calls = [0]
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    async def execute(stmt):
        result = MagicMock()
        c = calls[0]; calls[0] += 1
        if c == 0:
            result.scalar_one.return_value = 10  # uso plano: 10 de 100
        else:
            result.scalar_one.return_value = 0
        return result

    session.execute = execute
    pode, fonte = await verificar_limite_ia(uuid.uuid4(), "PROFISSIONAL", session)
    assert pode is True
    assert fonte == "PLANO"


@pytest.mark.asyncio
async def test_limite_plano_esgotado_com_creditos_extras():
    """Plano esgotado + créditos extras → fonte PACOTE."""
    calls = [0]
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    async def execute(stmt):
        result = MagicMock()
        c = calls[0]; calls[0] += 1
        if c == 0:
            result.scalar_one.return_value = 100  # uso plano = limite
        else:
            result.scalar_one.return_value = 50   # créditos extras disponíveis
        return result

    session.execute = execute
    pode, fonte = await verificar_limite_ia(uuid.uuid4(), "PROFISSIONAL", session)
    assert pode is True
    assert fonte == "PACOTE"


@pytest.mark.asyncio
async def test_limite_plano_esgotado_sem_creditos():
    """Plano esgotado + sem créditos extras → não pode usar."""
    calls = [0]
    session = MagicMock()

    async def execute(stmt):
        result = MagicMock()
        c = calls[0]; calls[0] += 1
        result.scalar_one.return_value = 100 if c == 0 else 0
        return result

    session.execute = execute
    pode, fonte = await verificar_limite_ia(uuid.uuid4(), "PROFISSIONAL", session)
    assert pode is False


@pytest.mark.asyncio
async def test_tier_sem_ia_retorna_false():
    session = _session_mock()
    pode, _ = await verificar_limite_ia(uuid.uuid4(), "BASICO", session)
    assert pode is False


# ── consumir_credito_pacote ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consumir_credito_incrementa():
    pacote = MagicMock(spec=IACreditosPacote)
    pacote.creditos_usados = 5
    pacote.quantidade_creditos = 100
    pacote.status = "ATIVO"

    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = pacote
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()

    consumido = await consumir_credito_pacote(uuid.uuid4(), session)
    assert consumido is True
    assert pacote.creditos_usados == 6


@pytest.mark.asyncio
async def test_consumir_credito_esgota_pacote():
    pacote = MagicMock(spec=IACreditosPacote)
    pacote.creditos_usados = 99
    pacote.quantidade_creditos = 100
    pacote.status = "ATIVO"

    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = pacote
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()

    await consumir_credito_pacote(uuid.uuid4(), session)
    assert pacote.status == "ESGOTADO"


@pytest.mark.asyncio
async def test_consumir_sem_pacote_retorna_false():
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=result)

    consumido = await consumir_credito_pacote(uuid.uuid4(), session)
    assert consumido is False


# ── solicitar_creditos ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_solicitar_creditos_cria_pacote():
    session = MagicMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    pacote = await solicitar_creditos(uuid.uuid4(), 100, session)
    assert pacote.quantidade_creditos == 100
    assert pacote.status == "ATIVO"
    assert pacote.origem == "SOLICITACAO"
    session.add.assert_called_once()


# ── consultar_creditos ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_consultar_creditos_sem_extras():
    calls = [0]
    session = MagicMock()

    async def execute(stmt):
        result = MagicMock()
        c = calls[0]; calls[0] += 1
        result.scalar_one.return_value = 10 if c == 0 else 0
        return result

    session.execute = execute
    dados = await consultar_creditos(uuid.uuid4(), "PROFISSIONAL", session)

    assert dados["limite_plano"] == LIMITES_MENSAIS["PROFISSIONAL"]
    assert dados["usado_plano"] == 10
    assert dados["creditos_extras_disponiveis"] == 0
    assert dados["total_disponivel"] == LIMITES_MENSAIS["PROFISSIONAL"] - 10


@pytest.mark.asyncio
async def test_consultar_creditos_com_extras():
    calls = [0]
    session = MagicMock()

    async def execute(stmt):
        result = MagicMock()
        c = calls[0]; calls[0] += 1
        if c == 0:
            result.scalar_one.return_value = 100   # uso plano = limite
        elif c == 1:
            result.scalar_one.return_value = 40    # créditos extras disponíveis
        else:
            result.scalar_one.return_value = 10    # créditos usados de pacote
        return result

    session.execute = execute
    dados = await consultar_creditos(uuid.uuid4(), "PROFISSIONAL", session)

    assert dados["usado_plano"] == 100
    assert dados["creditos_extras_disponiveis"] == 40
    assert dados["total_disponivel"] == 40  # plano esgotado, só extras
