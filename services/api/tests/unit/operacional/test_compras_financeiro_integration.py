from __future__ import annotations

import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from operacional.services.compras_service import ComprasService


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalar_one(self):
        return self._value


@pytest.mark.asyncio
async def test_parse_condicoes_pagamento_em_dias():
    svc = ComprasService(AsyncMock(), uuid.uuid4())

    assert svc._parse_condicoes_pagamento_em_dias("28 dias") == 28
    assert svc._parse_condicoes_pagamento_em_dias("boleto 7d") == 7
    assert svc._parse_condicoes_pagamento_em_dias("à vista") is None


@pytest.mark.asyncio
async def test_garantir_despesa_financeira_compra_cria_conta_a_pagar():
    tenant_id = uuid.uuid4()
    pedido_id = uuid.uuid4()
    deposito_id = uuid.uuid4()
    produto_id = uuid.uuid4()
    unidade_id = uuid.uuid4()
    plano_id = uuid.uuid4()

    session = AsyncMock()
    session.execute.side_effect = [
        _ScalarResult(None),
        _ScalarResult(None),
    ]
    session.get.side_effect = [
        SimpleNamespace(id=deposito_id, tenant_id=tenant_id, unidade_produtiva_id=unidade_id),
        SimpleNamespace(id=produto_id, tenant_id=tenant_id, nome="MAP", tipo="FERTILIZANTE"),
    ]

    svc = ComprasService(session, tenant_id)
    svc._resolver_plano_conta_compra = AsyncMock(return_value=plano_id)
    svc._resolver_fornecedor_financeiro = AsyncMock(return_value=(None, "Fornecedor X", None))

    recebimento_id = uuid.uuid4()
    recebimento = SimpleNamespace(
        id=recebimento_id,
        data_recebimento=SimpleNamespace(date=lambda: date(2026, 6, 26)),
        numero_nf="NF-1",
        chave_nfe="123",
    )
    pedido = SimpleNamespace(
        id=pedido_id,
        deposito_id=deposito_id,
        item_id=produto_id,
        valor_total=500.0,
        valor_adiantamento=None,
        condicoes_pagamento=None,
        fornecedor_nome="Fornecedor X",
    )

    with patch("operacional.services.compras_service.DespesaService") as despesa_service_cls:
        despesa_service = despesa_service_cls.return_value
        despesa_service.create_with_rateio = AsyncMock(
            return_value=[SimpleNamespace(id=uuid.uuid4(), origem_id=pedido_id)]
        )

        await svc._garantir_despesa_financeira_compra(pedido, recebimento=recebimento)

    payload = despesa_service.create_with_rateio.await_args.args[0]
    assert payload.unidade_produtiva_id == unidade_id
    assert payload.plano_conta_id == plano_id
    assert payload.descricao == "Compra de MAP (NF NF-1)"
    assert payload.valor_total == 500.0
    assert payload.status == "A_PAGAR"
    assert payload.numero_nf == "NF-1"
    assert payload.origem_id == recebimento_id
    assert payload.origem_tipo == "COMPRA"


@pytest.mark.asyncio
async def test_garantir_despesa_financeira_compra_e_idempotente():
    tenant_id = uuid.uuid4()
    pedido_id = uuid.uuid4()
    existente = SimpleNamespace(id=uuid.uuid4(), origem_id=pedido_id)

    session = AsyncMock()
    session.execute.return_value = _ScalarResult(existente)
    svc = ComprasService(session, tenant_id)

    pedido = SimpleNamespace(
        id=pedido_id,
        deposito_id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        valor_total=10.0,
    )
    resultado = await svc._garantir_despesa_financeira_compra(pedido)

    assert resultado is existente
    session.get.assert_not_awaited()
