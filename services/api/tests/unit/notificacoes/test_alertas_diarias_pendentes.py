"""Testes do gerador real de notificações DIARIA_PENDENTE (antes só existia via /demo)."""
import uuid
import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from notificacoes.alertas_engine import AlertasEngine


def _lancamento(colaborador_id: uuid.UUID, valor: float = 100.0) -> MagicMock:
    lanc = MagicMock()
    lanc.id = uuid.uuid4()
    lanc.colaborador_id = colaborador_id
    lanc.valor_diaria = valor
    return lanc


@pytest.mark.asyncio
async def test_agrupa_diarias_pendentes_por_colaborador_com_acao_de_pagamento():
    tenant_id = uuid.uuid4()
    colaborador_id = uuid.uuid4()
    lancamentos = [_lancamento(colaborador_id, 100.0), _lancamento(colaborador_id, 150.0)]

    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = lancamentos
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    engine = AlertasEngine()
    with patch(
        "rh.service.obter_dados_exibicao_colaborador",
        new=AsyncMock(return_value={"nome": "João Silva", "cpf": "123"}),
    ):
        alertas = await engine._verificar_diarias_pendentes(session, tenant_id)

    assert len(alertas) == 1
    alerta = alertas[0]
    assert alerta.tipo == "DIARIA_PENDENTE"
    assert "João Silva" in alerta.titulo
    assert alerta.origem == "rh_diaria"
    assert alerta.origem_id == str(colaborador_id)
    assert alerta.meta["quantidade"] == 2
    assert alerta.meta["total_pendente"] == 250.0
    acao = alerta.meta["acoes"][0]
    assert acao["acao"] == "pagar"
    assert acao["endpoint"] == "/rh/diarias/pagar-lote"
    assert set(acao["body"]["ids"]) == {str(l.id) for l in lancamentos}


@pytest.mark.asyncio
async def test_sem_diarias_pendentes_nao_gera_alerta():
    tenant_id = uuid.uuid4()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session = AsyncMock()
    session.execute = AsyncMock(return_value=result_mock)

    engine = AlertasEngine()
    alertas = await engine._verificar_diarias_pendentes(session, tenant_id)

    assert alertas == []
