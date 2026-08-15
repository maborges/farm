from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import agricola.alertas.service as alertas_module
from core.cadastros.produtos.models import Produto
from financeiro.models.despesa import Despesa
from operacional.models.compras import ItemPedidoCompra, ItemRecebimento, PedidoCompra, RecebimentoParcial
from operacional.models.estoque import EstoqueMovimento, LoteEstoque, SaldoEstoque
from operacional.services.compras_service import ComprasService
from test_operational_workflow_governance_step03 import _criar_unidade_produtiva, _garantir_tenant
from test_operational_workflow_governance_step05 import (
    _criar_deposito,
    _criar_fornecedor,
    _criar_plano_conta,
    _criar_produto,
)
from tests.integration.helpers import garantir_assinatura


async def _criar_produto_servico(session: AsyncSession, tenant_id: uuid.UUID) -> Produto:
    produto = Produto(
        id=uuid.uuid4(), tenant_id=tenant_id, nome="Colheita Terceirizada", tipo="SERVICO",
        unidade_medida="UN", preco_medio=0.0, ativo=True,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    return produto


async def _criar_pedido_servico(
    session: AsyncSession, tenant_id: uuid.UUID, produto_id: uuid.UUID, unidade_produtiva_id: uuid.UUID,
    *, quantidade: float = 1.0, valor_unitario: float = 5000.0,
) -> PedidoCompra:
    pedido = PedidoCompra(
        id=uuid.uuid4(), tenant_id=tenant_id, fornecedor_nome="Fornecedor Step07",
        fornecedor_contato="contato@step07.test", valor_total=quantidade * valor_unitario, status="ABERTO",
    )
    session.add(pedido)
    await session.flush()
    session.add(ItemPedidoCompra(
        id=uuid.uuid4(), pedido_id=pedido.id, produto_id=produto_id, deposito_id=None,
        unidade_produtiva_id=unidade_produtiva_id,
        unidade="UN", quantidade_solicitada=quantidade, preco_estimado_unitario=valor_unitario,
        valor_total=quantidade * valor_unitario,
    ))
    await session.commit()
    await session.refresh(pedido)
    return pedido


@pytest.mark.asyncio
async def test_recebimento_de_servico_nao_gera_lote_movimento_saldo_step07(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """OPERATIONS-GAP-01 §21.31: item de serviço não deve materializar estoque físico."""
    monkeypatch.setattr(
        alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await garantir_assinatura(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto_servico = await _criar_produto_servico(session, tenant_id)
    await _criar_plano_conta(session, tenant_id, codigo="3.14", nome="Serviços de Terceiros")
    await _criar_fornecedor(session, tenant_id)
    pedido = await _criar_pedido_servico(session, tenant_id, produto_servico.id, unidade_id, quantidade=1.0, valor_unitario=5000.0)

    recebido = await ComprasService(session, tenant_id).receber_pedido(pedido.id)
    await session.commit()

    assert recebido.status == "RECEBIDO"

    recebimento = (
        await session.execute(select(RecebimentoParcial).where(RecebimentoParcial.pedido_id == pedido.id))
    ).scalars().first()
    assert recebimento is not None

    item_recebimento = (
        await session.execute(select(ItemRecebimento).where(ItemRecebimento.recebimento_id == recebimento.id))
    ).scalars().first()
    assert item_recebimento is not None
    assert item_recebimento.lote_id is None

    movimento = (
        await session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.tenant_id == tenant_id,
                EstoqueMovimento.origem == "COMPRA",
                EstoqueMovimento.origem_id == pedido.id,
            )
        )
    ).scalars().first()
    assert movimento is None

    lotes = (await session.execute(select(LoteEstoque).where(LoteEstoque.produto_id == produto_servico.id))).scalars().all()
    assert lotes == []


@pytest.mark.asyncio
async def test_recebimento_de_servico_ainda_gera_despesa_a_pagar_step07(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """OPERATIONS-GAP-01 §21.31: mesmo sem estoque, o pagamento do serviço é gerado normalmente."""
    monkeypatch.setattr(
        alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await garantir_assinatura(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto_servico = await _criar_produto_servico(session, tenant_id)
    await _criar_plano_conta(session, tenant_id, codigo="3.14", nome="Serviços de Terceiros")
    fornecedor = await _criar_fornecedor(session, tenant_id)
    pedido = await _criar_pedido_servico(session, tenant_id, produto_servico.id, unidade_id, quantidade=1.0, valor_unitario=5000.0)

    await ComprasService(session, tenant_id).receber_pedido(pedido.id)
    await session.commit()

    recebimento = (
        await session.execute(select(RecebimentoParcial).where(RecebimentoParcial.pedido_id == pedido.id))
    ).scalars().first()
    despesa = (
        await session.execute(
            select(Despesa).where(
                Despesa.tenant_id == tenant_id, Despesa.origem_tipo == "COMPRA", Despesa.origem_id == recebimento.id,
            )
        )
    ).scalars().first()

    assert despesa is not None
    assert despesa.status == "A_PAGAR"
    assert float(despesa.valor_total) == 5000.0
