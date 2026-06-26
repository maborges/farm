from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


class _Result:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return self

    def first(self):
        if isinstance(self._value, list):
            return self._value[0] if self._value else None
        return self._value

    def all(self):
        if isinstance(self._value, list):
            return self._value
        return [self._value] if self._value is not None else []

    def scalar_one_or_none(self):
        return self.first()


@pytest.mark.asyncio
async def test_resolver_safra_contexto_requisicao_prefere_origem_operacao():
    from operacional.services.estoque_service import EstoqueService

    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    operacao_id = uuid.uuid4()

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_Result(safra_id)])
    svc = EstoqueService(session, tenant_id)

    requisicao = SimpleNamespace(
        origem_tipo="ORDEM_SERVICO",
        origem_id=operacao_id,
        unidade_produtiva_id=uuid.uuid4(),
    )

    resultado = await svc._resolver_safra_contexto_requisicao(requisicao)

    assert resultado == safra_id


@pytest.mark.asyncio
async def test_entregar_requisicao_repassa_safra_para_lancamento_financeiro():
    from operacional.services.estoque_service import EstoqueService

    tenant_id = uuid.uuid4()
    requisicao_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    item_id = uuid.uuid4()

    req = SimpleNamespace(
        id=requisicao_id,
        tenant_id=tenant_id,
        unidade_produtiva_id=uuid.uuid4(),
        origem_tipo="ORDEM_SERVICO",
        origem_id=uuid.uuid4(),
        status="APROVADA",
    )
    item = SimpleNamespace(
        id=item_id,
        requisicao_id=requisicao_id,
        produto_id=uuid.uuid4(),
        deposito_id=uuid.uuid4(),
        quantidade_solicitada=10.0,
        quantidade_aprovada=10.0,
        quantidade_entregue=None,
        lote_id=None,
    )

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[_Result(req), _Result([item])])
    svc = EstoqueService(session, tenant_id)
    svc._resolver_safra_contexto_requisicao = AsyncMock(return_value=safra_id)
    svc.registrar_saida = AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4()))

    resultado = await svc.entregar_requisicao(
        requisicao_id,
        SimpleNamespace(
            itens=[SimpleNamespace(item_id=item_id, quantidade_entregue=10.0, lote_id=None)]
        ),
    )

    assert resultado.status == "ENTREGUE"
    assert svc.registrar_saida.await_count == 1
    saida_payload = svc.registrar_saida.await_args.args[0]
    assert saida_payload.safra_id == safra_id
    assert saida_payload.origem_tipo == "REQUISICAO"
