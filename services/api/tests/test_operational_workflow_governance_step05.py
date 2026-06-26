from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import agricola.alertas.service as alertas_module
from core.cadastros.produtos.models import Produto
from financeiro.models.despesa import Despesa
from financeiro.models.plano_conta import PlanoConta
from financeiro.services.relatorio_service import RelatorioService
from notificacoes.models import Notificacao
from operacional.models.compras import Fornecedor, ItemRecebimento, PedidoCompra, RecebimentoParcial
from operacional.models.estoque import Deposito, EstoqueMovimento, LoteEstoque, SaldoEstoque
from operacional.schemas.compras import RecebimentoCreate
from tests.integration.helpers import garantir_assinatura
from operacional.services.compras_service import ComprasService
from test_operational_workflow_governance_step03 import _criar_unidade_produtiva, _garantir_tenant
from core.exceptions import BusinessRuleError


async def _criar_produto(session: AsyncSession, tenant_id: uuid.UUID, *, preco_medio: float = 99.0) -> Produto:
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome=f"Produto Step05 {str(tenant_id)[:8]}",
        tipo="INSUMO",
        unidade_medida="KG",
        preco_medio=preco_medio,
        ativo=True,
    )
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    return produto


async def _criar_deposito(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> Deposito:
    deposito = Deposito(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome="Deposito Step05",
        tipo="GERAL",
        ativo=True,
    )
    session.add(deposito)
    await session.commit()
    await session.refresh(deposito)
    return deposito


async def _criar_plano_conta(session: AsyncSession, tenant_id: uuid.UUID, *, codigo: str, nome: str) -> PlanoConta:
    plano = PlanoConta(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        codigo=codigo,
        nome=nome,
        tipo="DESPESA",
        natureza="ANALITICA",
        categoria_rfb="CUSTEIO",
        ativo=True,
    )
    session.add(plano)
    await session.commit()
    await session.refresh(plano)
    return plano


async def _criar_fornecedor(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    nome: str = "Fornecedor Step05",
    condicoes_pagamento: str = "28 dias",
) -> Fornecedor:
    fornecedor = Fornecedor(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome_fantasia=nome,
        condicoes_pagamento=condicoes_pagamento,
        email="financeiro@step05.test",
    )
    session.add(fornecedor)
    await session.commit()
    await session.refresh(fornecedor)
    return fornecedor


async def _criar_pedido(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    produto_id: uuid.UUID,
    deposito_id: uuid.UUID,
    *,
    quantidade: float = 25.0,
    valor_unitario: float = 42.0,
) -> PedidoCompra:
    pedido = PedidoCompra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        fornecedor_nome="Fornecedor Step05",
        fornecedor_contato="contato@step05.test",
        item_id=produto_id,
        deposito_id=deposito_id,
        quantidade=quantidade,
        unidade="KG",
        valor_unitario=valor_unitario,
        valor_total=quantidade * valor_unitario,
        status="ABERTO",
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)
    return pedido


@pytest.mark.asyncio
async def test_recebimento_novo_gera_lote_movimento_saldo_step05(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto = await _criar_produto(session, tenant_id, preco_medio=99.0)
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    pedido = await _criar_pedido(session, tenant_id, produto.id, deposito.id, quantidade=25.0, valor_unitario=42.0)

    recebido = await ComprasService(session, tenant_id).receber_pedido(pedido.id)
    await session.commit()
    await session.refresh(produto)

    recebimento = (
        await session.execute(select(RecebimentoParcial).where(RecebimentoParcial.pedido_id == pedido.id))
    ).scalars().first()
    item_recebimento = (
        await session.execute(
            select(ItemRecebimento).where(ItemRecebimento.recebimento_id == recebimento.id)
        )
    ).scalars().first()
    lote = (
        await session.execute(select(LoteEstoque).where(LoteEstoque.id == item_recebimento.lote_id))
    ).scalars().first()
    movimento = (
        await session.execute(
            select(EstoqueMovimento).where(
                EstoqueMovimento.tenant_id == tenant_id,
                EstoqueMovimento.origem == "COMPRA",
                EstoqueMovimento.origem_id == pedido.id,
            )
        )
    ).scalars().first()
    saldo = (
        await session.execute(
            select(SaldoEstoque).where(
                SaldoEstoque.deposito_id == deposito.id,
                SaldoEstoque.produto_id == produto.id,
            )
        )
    ).scalars().first()

    assert recebido.status == "RECEBIDO"
    assert recebimento is not None
    assert item_recebimento is not None
    assert lote is not None
    assert movimento is not None
    assert saldo is not None
    assert float(lote.custo_unitario) == 42.0
    assert float(movimento.custo_unitario) == 42.0
    assert float(saldo.quantidade_atual) == 25.0
    assert produto.preco_medio == 99.0


@pytest.mark.asyncio
async def test_recebimento_gera_conta_a_pagar_step05(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await garantir_assinatura(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto = await _criar_produto(session, tenant_id, preco_medio=120.0)
    produto.tipo = "FERTILIZANTE"
    session.add(produto)
    await session.commit()
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    await _criar_plano_conta(session, tenant_id, codigo="3.02", nome="Fertilizantes e Corretivos")
    fornecedor = await _criar_fornecedor(session, tenant_id)
    pedido = await _criar_pedido(session, tenant_id, produto.id, deposito.id, quantidade=10.0, valor_unitario=55.0)

    await ComprasService(session, tenant_id).receber_pedido(
        pedido.id,
        data=RecebimentoCreate(
            numero_nf="NF-STEP05-001",
            chave_nfe="12345678901234567890123456789012345678901234",
        ),
    )
    await session.commit()

    despesa = (
        await session.execute(
            select(Despesa).where(
                Despesa.tenant_id == tenant_id,
                Despesa.origem_tipo == "COMPRA",
                Despesa.origem_id == pedido.id,
            )
        )
    ).scalars().first()
    await session.refresh(fornecedor)

    assert despesa is not None
    assert despesa.status == "A_PAGAR"
    assert float(despesa.valor_total) == 550.0
    assert despesa.unidade_produtiva_id == unidade_id
    assert despesa.pessoa_id == fornecedor.pessoa_id
    assert despesa.numero_nf == "NF-STEP05-001"
    assert despesa.data_vencimento == despesa.data_emissao + timedelta(days=28)


@pytest.mark.asyncio
async def test_recebimento_financeiro_idempotente_step05(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await garantir_assinatura(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto = await _criar_produto(session, tenant_id)
    produto.tipo = "FERTILIZANTE"
    session.add(produto)
    await session.commit()
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    await _criar_plano_conta(session, tenant_id, codigo="3.02", nome="Fertilizantes e Corretivos")
    await _criar_fornecedor(session, tenant_id)
    pedido = await _criar_pedido(session, tenant_id, produto.id, deposito.id)

    svc = ComprasService(session, tenant_id)
    await svc.receber_pedido(pedido.id)
    await session.commit()
    await svc.receber_pedido(pedido.id)
    await session.commit()

    total_despesas = (
        await session.execute(
            select(func.count(Despesa.id)).where(
                Despesa.tenant_id == tenant_id,
                Despesa.origem_tipo == "COMPRA",
                Despesa.origem_id == pedido.id,
            )
        )
    ).scalar_one()

    assert total_despesas == 1


@pytest.mark.asyncio
async def test_recebimento_compra_atualiza_fluxo_previsto_step05(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    await garantir_assinatura(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto = await _criar_produto(session, tenant_id)
    produto.tipo = "FERTILIZANTE"
    session.add(produto)
    await session.commit()
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    await _criar_plano_conta(session, tenant_id, codigo="3.02", nome="Fertilizantes e Corretivos")
    await _criar_fornecedor(session, tenant_id, condicoes_pagamento="0 dias")
    pedido = await _criar_pedido(session, tenant_id, produto.id, deposito.id, quantidade=5.0, valor_unitario=80.0)

    await ComprasService(session, tenant_id).receber_pedido(pedido.id)
    await session.commit()

    hoje = date.today()
    fluxo = await RelatorioService(session, tenant_id).fluxo_caixa(
        hoje.replace(day=1),
        date(hoje.year, 12, 31),
        unidade_id,
    )

    assert fluxo.totais.total_despesas_previstas >= 400.0


@pytest.mark.asyncio
async def test_pedido_so_vira_recebido_apos_materializacao_step05(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto = await _criar_produto(session, tenant_id)
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    pedido = await _criar_pedido(session, tenant_id, produto.id, deposito.id)

    await ComprasService(session, tenant_id).receber_pedido(pedido.id)
    await session.commit()

    total_movimentos = (
        await session.execute(
            select(func.count(EstoqueMovimento.id)).where(
                EstoqueMovimento.tenant_id == tenant_id,
                EstoqueMovimento.origem == "COMPRA",
                EstoqueMovimento.origem_id == pedido.id,
            )
        )
    ).scalar_one()
    pedido_db = await session.get(PedidoCompra, pedido.id)

    assert pedido_db.status == "RECEBIDO"
    assert total_movimentos == 1


@pytest.mark.asyncio
async def test_recebimento_sem_valuation_gera_warning_no_warning_only(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto = await _criar_produto(session, tenant_id, preco_medio=0.0)
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    pedido = await _criar_pedido(session, tenant_id, produto.id, deposito.id, valor_unitario=0.0)

    await ComprasService(session, tenant_id).receber_pedido(pedido.id)
    await session.commit()

    notif = (
        await session.execute(
            select(Notificacao).where(
                Notificacao.tenant_id == tenant_id,
                Notificacao.tipo == "WORKFLOW_OPERACIONAL",
            )
        )
    ).scalars().first()
    pedido_db = await session.get(PedidoCompra, pedido.id)

    assert pedido_db.status == "RECEBIDO"
    assert notif is not None


@pytest.mark.asyncio
async def test_recebimento_critico_bloqueia_no_block_critical(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_BLOCK_CRITICAL,
    )

    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto = await _criar_produto(session, tenant_id, preco_medio=0.0)
    deposito = await _criar_deposito(session, tenant_id, unidade_id)
    pedido = await _criar_pedido(session, tenant_id, produto.id, deposito.id, valor_unitario=0.0)
    pedido_id = pedido.id

    with pytest.raises(BusinessRuleError, match="Nao e possivel materializar o recebimento sem quantidade e custo unitario validos"):
        await ComprasService(session, tenant_id).receber_pedido(pedido_id)

    await session.rollback()
    pedido_db = await session.get(PedidoCompra, pedido_id)
    if pedido_db is not None:
        assert pedido_db.status == "ABERTO"


@pytest.mark.asyncio
async def test_tenant_isolation_no_recebimento_step05(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alertas_module,
        "WORKFLOW_ENFORCEMENT_MODE",
        alertas_module.WORKFLOW_ENFORCEMENT_WARNING_ONLY,
    )

    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _garantir_tenant(session, tenant_a)
    await _garantir_tenant(session, tenant_b)
    unidade_id = await _criar_unidade_produtiva(session, tenant_a)
    produto = await _criar_produto(session, tenant_a)
    deposito = await _criar_deposito(session, tenant_a, unidade_id)
    pedido = await _criar_pedido(session, tenant_a, produto.id, deposito.id)

    recebido = await ComprasService(session, tenant_b).receber_pedido(pedido.id)
    await session.commit()

    total_movimentos = (
        await session.execute(
            select(func.count(EstoqueMovimento.id)).where(
                EstoqueMovimento.origem == "COMPRA",
                EstoqueMovimento.origem_id == pedido.id,
            )
        )
    ).scalar_one()

    assert recebido is None
    assert total_movimentos == 0
