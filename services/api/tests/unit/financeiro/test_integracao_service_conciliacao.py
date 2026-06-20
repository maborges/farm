import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from financeiro.services.integracao_service import ConciliacaoService


pytestmark = pytest.mark.asyncio


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class FakeRowsResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


async def test_sugerir_conciliacao_agrega_consultas_por_tipo():
    tenant_id = uuid.uuid4()
    conta_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.side_effect = [
        FakeScalarResult(
            [
                SimpleNamespace(
                    id=uuid.uuid4(),
                    data=date(2026, 6, 10),
                    valor=Decimal("-120.00"),
                    descricao="Débito 1",
                ),
                SimpleNamespace(
                    id=uuid.uuid4(),
                    data=date(2026, 6, 12),
                    valor=Decimal("-80.00"),
                    descricao="Débito 2",
                ),
                SimpleNamespace(
                    id=uuid.uuid4(),
                    data=date(2026, 6, 15),
                    valor=Decimal("250.00"),
                    descricao="Crédito 1",
                ),
            ]
        ),
        FakeRowsResult(
            [
                SimpleNamespace(
                    id=uuid.uuid4(),
                    descricao="Despesa compatível",
                    valor_total=Decimal("120.00"),
                    data_vencimento=date(2026, 6, 11),
                ),
                SimpleNamespace(
                    id=uuid.uuid4(),
                    descricao="Despesa fora da janela",
                    valor_total=Decimal("80.00"),
                    data_vencimento=date(2026, 6, 20),
                ),
            ]
        ),
        FakeRowsResult(
            [
                SimpleNamespace(
                    id=uuid.uuid4(),
                    descricao="Receita compatível",
                    valor_total=Decimal("250.00"),
                    data_vencimento=date(2026, 6, 15),
                )
            ]
        ),
    ]

    resposta = await ConciliacaoService(session, tenant_id).sugerir_conciliacao(conta_id)

    assert session.execute.await_count == 3
    assert len(resposta) == 2
    assert {item["tipo"] for item in resposta} == {"DESPESA", "RECEITA"}
    assert any(item["descricao_fin"] == "Despesa compatível" for item in resposta)
    assert any(item["descricao_fin"] == "Receita compatível" for item in resposta)
    assert any(item["confianca"] == "ALTA" for item in resposta)
    assert any(item["confianca"] == "MEDIA" for item in resposta)


async def test_sugerir_conciliacao_retorna_vazio_quando_nao_houver_lancamentos():
    tenant_id = uuid.uuid4()
    conta_id = uuid.uuid4()
    session = AsyncMock()
    session.execute.return_value = FakeScalarResult([])

    resposta = await ConciliacaoService(session, tenant_id).sugerir_conciliacao(conta_id)

    assert session.execute.await_count == 1
    assert resposta == []
