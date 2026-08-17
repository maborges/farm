from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from notificacoes.alertas_engine import AlertasEngine


@pytest.mark.asyncio
async def test_verificar_afericao_vencida_gera_alerta_agregado():
    engine = AlertasEngine()
    session = AsyncMock()

    balanca_id = uuid4()
    validade = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=10)
    row = SimpleNamespace(id=balanca_id, nome="Balança Portaria 1", validade_ate=validade)

    mock_result = MagicMock()
    mock_result.all.return_value = [row]
    session.execute = AsyncMock(return_value=mock_result)

    alertas = await engine._verificar_afericao_vencida(session, uuid4())

    assert len(alertas) == 1
    alerta = alertas[0]
    assert alerta.tipo == "AFERICAO_BALANCA_VENCIDA"
    assert "Balança Portaria 1" in alerta.mensagem
    assert alerta.meta["quantidade"] == 1
    assert alerta.meta["balancas"][0]["id"] == str(balanca_id)


@pytest.mark.asyncio
async def test_sem_balanca_vencida_nao_gera_alerta():
    engine = AlertasEngine()
    session = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)

    alertas = await engine._verificar_afericao_vencida(session, uuid4())

    assert alertas == []
