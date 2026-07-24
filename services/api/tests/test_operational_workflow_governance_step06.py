from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import agricola.alertas.service as alertas_module
from core.cadastros.produtos.models import Produto
from core.exceptions import BusinessRuleError
from operacional.models.compras import DevolucaoFornecedor, ItemDevolucao, PedidoCompra, Fornecedor
from core.cadastros.pessoas.models import Pessoa
from operacional.models.estoque import EstoqueMovimento, LoteEstoque, SaldoEstoque
from operacional.routers.compras import atualizar_status_devolucao
from operacional.schemas.compras import DevolucaoStatusUpdate
from operacional.services.compras_service import ComprasService
from test_operational_workflow_governance_step05 import (
    _criar_deposito,
    _criar_pedido,
    _criar_plano_conta,
    _criar_produto,
)
from test_operational_workflow_governance_step03 import _criar_unidade_produtiva, _garantir_tenant
from tests.integration.helpers import garantir_assinatura


async def _criar_recebimento_base(session: AsyncSession, tenant_id: uuid.UUID):
    await garantir_assinatura(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto = await _criar_produto(session, tenant_id, preco_medio=77.0)
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    await _criar_plano_conta(session, tenant_id, codigo="9.99", nome="Genérico")
    pessoa = Pessoa(id=uuid.uuid4(), tenant_id=tenant_id, tipo="PJ", nome_exibicao="Fornecedor Step05", base_legal="CONTRATO", ativo=True)
    session.add(pessoa)
    await session.flush()
    fornecedor = Fornecedor(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        pessoa_id=pessoa.id,
    )
    session.add(fornecedor)
    await session.flush()
    pedido = await _criar_pedido(session, tenant_id, produto.id, deposito.id, quantidade=20.0, valor_unitario=15.0)

    recebido = await ComprasService(session, tenant_id).receber_pedido(pedido.id)
    await session.commit()

    lote = (
        await session.execute(
            select(LoteEstoque).where(
                LoteEstoque.produto_id == produto.id,
                LoteEstoque.deposito_id == deposito.id,
            )
        )
    ).scalars().first()
    saldo = (
        await session.execute(
            select(SaldoEstoque).where(
                SaldoEstoque.produto_id == produto.id,
                SaldoEstoque.deposito_id == deposito.id,
            )
        )
    ).scalars().first()
    mov = (
        await session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.tenant_id == tenant_id,
                EstoqueMovimento.origem == "COMPRA",
                EstoqueMovimento.origem_id == pedido.id,
            )
        )
    ).scalars().first()
    return produto, deposito, fornecedor, pedido, recebido, lote, saldo, mov


@pytest.mark.asyncio
async def test_devolucao_parcial_gera_movimento_reverso_e_preserva_custo(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    produto, deposito, fornecedor, pedido, _, lote, saldo, mov_original = await _criar_recebimento_base(session, tenant_id)
    quantidade_inicial = float(saldo.quantidade_atual)

    devolucao = DevolucaoFornecedor(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        pedido_id=pedido.id,
        fornecedor_id=fornecedor.id,
        data_devolucao=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        motivo="DEFEITO",
        status="ABERTA",
    )
    session.add(devolucao)
    await session.flush()

    item_dev = ItemDevolucao(
        id=uuid.uuid4(),
        devolucao_id=devolucao.id,
        produto_id=produto.id,
        deposito_origem_id=deposito.id,
        lote_id=lote.id,
        quantidade=5.0,
        custo_unitario=15.0,
    )
    session.add(item_dev)
    await session.commit()

    await atualizar_status_devolucao(
        dev_id=devolucao.id,
        data=DevolucaoStatusUpdate(status="CONCLUIDA"),
        tenant=SimpleNamespace(id=tenant_id),
        session=session,
    )
    await session.commit()

    await session.refresh(lote)
    await session.refresh(saldo)
    await session.refresh(devolucao)
    movimentos = (
        await session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.tenant_id == tenant_id,
                EstoqueMovimento.origem_id == devolucao.id,
                EstoqueMovimento.tipo_movimento == "AJUSTE",
            )
        )
    ).scalars().all()

    assert devolucao.status == "CONCLUIDA"
    assert len(movimentos) == 1
    assert movimentos[0].ajuste_de == mov_original.id
    assert float(movimentos[0].quantidade) == 5.0
    assert float(lote.quantidade_atual) == 25.0
    assert float(saldo.quantidade_atual) == quantidade_inicial + 5.0
    assert produto.preco_medio == 77.0
    original_count = (
        await session.execute(
            select(func.count(EstoqueMovimento.id)).where(
                EstoqueMovimento.tenant_id == tenant_id,
                EstoqueMovimento.origem == "COMPRA",
                EstoqueMovimento.origem_id == pedido.id,
            )
        )
    ).scalar_one()
    assert original_count == 1


@pytest.mark.asyncio
async def test_cancelar_pedido_recebido_sem_reversao_bloqueia_no_block_critical(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_CRITICAL)

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    _, _, _, pedido, recebido, _, _, _ = await _criar_recebimento_base(session, tenant_id)
    pedido_id = pedido.id

    with pytest.raises(BusinessRuleError, match="Nao e possivel cancelar pedido recebido sem reversao operacional"):
        await ComprasService(session, tenant_id).atualizar_status_pedido(pedido_id, "CANCELADO")

    await session.rollback()
    pedido_db = await session.get(PedidoCompra, pedido_id)
    assert pedido_db.status == "RECEBIDO"


@pytest.mark.asyncio
async def test_cancelar_pedido_recebido_com_reversao_permite(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_ECONOMIC_AND_CRITICAL)

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    produto, deposito, fornecedor, pedido, _, lote, saldo, _ = await _criar_recebimento_base(session, tenant_id)

    devolucao = DevolucaoFornecedor(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        pedido_id=pedido.id,
        fornecedor_id=fornecedor.id,
        data_devolucao=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        motivo="DEFEITO",
        status="ABERTA",
    )
    session.add(devolucao)
    await session.flush()
    session.add(
        ItemDevolucao(
            id=uuid.uuid4(),
            devolucao_id=devolucao.id,
            produto_id=produto.id,
            deposito_origem_id=deposito.id,
            lote_id=lote.id,
            quantidade=5.0,
            custo_unitario=15.0,
        )
    )
    await session.commit()

    await atualizar_status_devolucao(
        dev_id=devolucao.id,
        data=DevolucaoStatusUpdate(status="CONCLUIDA"),
        tenant=SimpleNamespace(id=tenant_id),
        session=session,
    )
    await ComprasService(session, tenant_id).atualizar_status_pedido(pedido.id, "CANCELADO")
    await session.commit()

    pedido_db = await session.get(PedidoCompra, pedido.id)
    assert pedido_db.status == "CANCELADO"


@pytest.mark.asyncio
async def test_devolucao_sem_lote_original_bloqueia_critico(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_CRITICAL)

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    produto, deposito, fornecedor, pedido, _, _, _, _ = await _criar_recebimento_base(session, tenant_id)

    devolucao = DevolucaoFornecedor(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        pedido_id=pedido.id,
        fornecedor_id=fornecedor.id,
        data_devolucao=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        motivo="DEFEITO",
        status="ABERTA",
    )
    session.add(devolucao)
    await session.flush()
    session.add(
        ItemDevolucao(
            id=uuid.uuid4(),
            devolucao_id=devolucao.id,
            produto_id=produto.id,
            deposito_origem_id=deposito.id,
            lote_id=None,
            quantidade=5.0,
            custo_unitario=15.0,
        )
    )
    await session.commit()

    with pytest.raises(BusinessRuleError, match="Nao e possivel concluir a devolucao sem o lote original"):
        await atualizar_status_devolucao(
            dev_id=devolucao.id,
            data=DevolucaoStatusUpdate(status="CONCLUIDA"),
            tenant=SimpleNamespace(id=tenant_id),
            session=session,
        )

    devolucao_id = devolucao.id
    await session.rollback()
    devolucao_db = await session.get(DevolucaoFornecedor, devolucao_id)
    assert devolucao_db.status == "ABERTA"


@pytest.mark.asyncio
async def test_tenant_isolation_devolucao_nao_mexe_em_outro_tenant(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alertas_module, "WORKFLOW_ENFORCEMENT_MODE", alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY)

    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _garantir_tenant(session, tenant_a)
    await _garantir_tenant(session, tenant_b)

    produto, deposito, fornecedor, pedido, _, lote, saldo, _ = await _criar_recebimento_base(session, tenant_a)
    devolucao = DevolucaoFornecedor(
        id=uuid.uuid4(),
        tenant_id=tenant_a,
        pedido_id=pedido.id,
        fornecedor_id=fornecedor.id,
        data_devolucao=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        motivo="DEFEITO",
        status="ABERTA",
    )
    session.add(devolucao)
    await session.flush()
    session.add(
        ItemDevolucao(
            id=uuid.uuid4(),
            devolucao_id=devolucao.id,
            produto_id=produto.id,
            deposito_origem_id=deposito.id,
            lote_id=lote.id,
            quantidade=5.0,
            custo_unitario=15.0,
        )
    )
    await session.commit()

    with pytest.raises(BusinessRuleError, match="Devolução não encontrada"):
        await atualizar_status_devolucao(
            dev_id=devolucao.id,
            data=DevolucaoStatusUpdate(status="CONCLUIDA"),
            tenant=SimpleNamespace(id=tenant_b),
            session=session,
        )

    original_count = (
        await session.execute(
            select(func.count(EstoqueMovimento.id)).where(
                EstoqueMovimento.tenant_id == tenant_a,
                EstoqueMovimento.origem == "COMPRA",
                EstoqueMovimento.origem_id == pedido.id,
            )
        )
    ).scalar_one()
    assert original_count == 1
