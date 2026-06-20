import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import financeiro.services.dashboard_service as dashboard_module
from financeiro.services.dashboard_service import DashboardService


pytestmark = pytest.mark.asyncio


class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 6, 20)


class FakeOneResult:
    def __init__(self, row):
        self._row = row

    def one(self):
        return self._row


class FakeAllResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeMappingsResult(FakeAllResult):
    def mappings(self):
        return self


async def test_dashboard_resumo_agrega_sem_carregar_tabelas_inteiras(monkeypatch):
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.side_effect = [
        FakeOneResult(SimpleNamespace(total_recebido_mes=1000.0, total_a_receber=300.0, total_atrasado_receitas=50.0)),
        FakeOneResult(SimpleNamespace(total_pago_mes=800.0, total_a_pagar=400.0, total_atrasado_despesas=25.0)),
        FakeMappingsResult([
            {
                "id": uuid.uuid4(),
                "tipo": "RECEITA",
                "descricao": "Receber 1",
                "valor": 200.0,
                "data_vencimento": FixedDate(2026, 6, 23),
                "pessoa_nome": "Cliente 1",
            }
        ]),
        FakeMappingsResult([
            {
                "id": uuid.uuid4(),
                "tipo": "DESPESA",
                "descricao": "Pagar 1",
                "valor": 150.0,
                "data_vencimento": FixedDate(2026, 6, 25),
                "pessoa_nome": "Fornecedor 1",
            },
            {
                "id": uuid.uuid4(),
                "tipo": "DESPESA",
                "descricao": "Pagar 2",
                "valor": 120.0,
                "data_vencimento": FixedDate(2026, 7, 2),
                "pessoa_nome": "Fornecedor 2",
            },
        ]),
        FakeAllResult([
            SimpleNamespace(plano_conta_nome="Receita Rural", categoria_rfb="RECEITA_ATIVIDADE", quantidade=2, total=700.0),
        ]),
        FakeAllResult([
            SimpleNamespace(plano_conta_nome="Custeio", categoria_rfb="CUSTEIO", quantidade=1, total=500.0),
        ]),
    ]
    monkeypatch.setattr(dashboard_module, "date", FixedDate)

    resposta = await DashboardService(session, tenant_id).resumo(unidade_produtiva_id)

    assert session.execute.await_count == 6
    assert resposta.total_recebido_mes == 1000.0
    assert resposta.total_pago_mes == 800.0
    assert resposta.saldo_mes == 200.0
    assert resposta.total_a_receber == 300.0
    assert resposta.total_a_pagar == 400.0
    assert len(resposta.vencendo_7d) == 2
    assert len(resposta.vencendo_8_15d) == 1
    assert len(resposta.vencendo_16_30d) == 0
    assert resposta.top_receitas[0].plano_conta_nome == "Receita Rural"
    assert resposta.top_despesas[0].categoria_rfb == "CUSTEIO"
    assert any(alerta.tipo == "SALDO_NEGATIVO" for alerta in resposta.alertas) is False
    assert any(alerta.tipo == "VENCIMENTO_PROXIMO" for alerta in resposta.alertas)


async def test_dashboard_resumo_retorna_zeros_quando_nao_houver_movimentos(monkeypatch):
    tenant_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.side_effect = [
        FakeOneResult(SimpleNamespace(total_recebido_mes=0.0, total_a_receber=0.0, total_atrasado_receitas=0.0)),
        FakeOneResult(SimpleNamespace(total_pago_mes=0.0, total_a_pagar=0.0, total_atrasado_despesas=0.0)),
        FakeMappingsResult([]),
        FakeMappingsResult([]),
        FakeAllResult([]),
        FakeAllResult([]),
    ]
    monkeypatch.setattr(dashboard_module, "date", FixedDate)

    resposta = await DashboardService(session, tenant_id).resumo()

    assert session.execute.await_count == 6
    assert resposta.total_recebido_mes == 0.0
    assert resposta.total_pago_mes == 0.0
    assert resposta.vencendo_7d == []
    assert resposta.top_receitas == []
    assert resposta.top_despesas == []
    assert resposta.alertas == []
