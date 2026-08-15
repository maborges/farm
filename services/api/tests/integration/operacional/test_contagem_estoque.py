from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from core.exceptions import BusinessRuleError
from core.cadastros.produtos.models import Produto
from operacional.models.estoque import Deposito, EstoqueMovimento, SaldoEstoque
from operacional.models.contagem_estoque import ContagemEstoque, ContagemEstoqueItem
from operacional.schemas.contagem_estoque import ContagemAbrirRequest
from operacional.services.contagem_estoque_service import ContagemEstoqueService
from test_operational_workflow_governance_step03 import _criar_unidade_produtiva, _garantir_tenant


async def _criar_deposito(session, tenant_id, unidade_produtiva_id) -> uuid.UUID:
    deposito = Deposito(tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id, nome="Depósito Contagem Teste")
    session.add(deposito)
    await session.commit()
    await session.refresh(deposito)
    return deposito.id


async def _criar_produto(session, tenant_id, nome="Fertilizante Teste") -> uuid.UUID:
    produto = Produto(tenant_id=tenant_id, nome=nome, tipo="FERTILIZANTE", unidade_medida="KG")
    session.add(produto)
    await session.commit()
    await session.refresh(produto)
    return produto.id


async def _criar_saldo(session, deposito_id, produto_id, *, quantidade: float, custo_medio: float = 10.0) -> None:
    saldo = SaldoEstoque(deposito_id=deposito_id, produto_id=produto_id, quantidade_atual=quantidade, custo_medio=custo_medio)
    session.add(saldo)
    await session.commit()


async def _setup_base(session, tenant_id):
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    deposito_id = await _criar_deposito(session, tenant_id, unidade_id)
    produto_id = await _criar_produto(session, tenant_id)
    return unidade_id, deposito_id, produto_id


@pytest.mark.asyncio
async def test_abrir_contagem_prepopula_itens_com_saldo_correto(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id, deposito_id, produto_id = await _setup_base(session, tenant_id)
    await _criar_saldo(session, deposito_id, produto_id, quantidade=100.0)

    svc = ContagemEstoqueService(session, tenant_id)
    contagem = await svc.abrir_contagem(ContagemAbrirRequest(deposito_id=deposito_id))

    assert contagem.status == "ABERTA"
    stmt = select(ContagemEstoqueItem).where(ContagemEstoqueItem.contagem_id == contagem.id)
    itens = (await session.execute(stmt)).scalars().all()
    assert len(itens) == 1
    assert float(itens[0].quantidade_sistema) == 100.0
    assert itens[0].quantidade_contada is None


@pytest.mark.asyncio
async def test_concluir_sem_divergencia_nao_gera_ajuste(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id, deposito_id, produto_id = await _setup_base(session, tenant_id)
    await _criar_saldo(session, deposito_id, produto_id, quantidade=50.0)

    svc = ContagemEstoqueService(session, tenant_id)
    contagem = await svc.abrir_contagem(ContagemAbrirRequest(deposito_id=deposito_id))
    await svc.registrar_contagem_item(contagem.id, produto_id, 50.0)
    concluida = await svc.concluir_contagem(contagem.id)

    assert concluida.status == "CONCLUIDA"
    stmt = select(ContagemEstoqueItem).where(ContagemEstoqueItem.contagem_id == contagem.id)
    item = (await session.execute(stmt)).scalars().first()
    assert item.movimento_ajuste_id is None


@pytest.mark.asyncio
async def test_concluir_com_divergencia_gera_ajuste_e_atualiza_saldo(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id, deposito_id, produto_id = await _setup_base(session, tenant_id)
    await _criar_saldo(session, deposito_id, produto_id, quantidade=100.0, custo_medio=10.0)

    svc = ContagemEstoqueService(session, tenant_id)
    contagem = await svc.abrir_contagem(ContagemAbrirRequest(deposito_id=deposito_id))
    await svc.registrar_contagem_item(contagem.id, produto_id, 92.0)
    await svc.concluir_contagem(contagem.id)

    stmt = select(ContagemEstoqueItem).where(ContagemEstoqueItem.contagem_id == contagem.id)
    item = (await session.execute(stmt)).scalars().first()
    assert item.movimento_ajuste_id is not None

    mov = (await session.execute(
        select(EstoqueMovimento).where(EstoqueMovimento.id == item.movimento_ajuste_id)
    )).scalars().first()
    assert mov is not None
    assert mov.origem_tipo == "AJUSTE"

    saldo = (await session.execute(
        select(SaldoEstoque).where(SaldoEstoque.deposito_id == deposito_id, SaldoEstoque.produto_id == produto_id)
    )).scalars().first()
    assert float(saldo.quantidade_atual) == 92.0


@pytest.mark.asyncio
async def test_concluir_com_item_nao_contado_nao_gera_ajuste_para_ele(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id, deposito_id, produto_id = await _setup_base(session, tenant_id)
    produto_id_2 = await _criar_produto(session, tenant_id, nome="Adubo Teste")
    await _criar_saldo(session, deposito_id, produto_id, quantidade=100.0)
    await _criar_saldo(session, deposito_id, produto_id_2, quantidade=30.0)

    svc = ContagemEstoqueService(session, tenant_id)
    contagem = await svc.abrir_contagem(ContagemAbrirRequest(deposito_id=deposito_id))
    await svc.registrar_contagem_item(contagem.id, produto_id, 95.0)
    # produto_id_2 nunca é contado
    await svc.concluir_contagem(contagem.id)

    stmt = select(ContagemEstoqueItem).where(
        ContagemEstoqueItem.contagem_id == contagem.id, ContagemEstoqueItem.produto_id == produto_id_2,
    )
    item_nao_contado = (await session.execute(stmt)).scalars().first()
    assert item_nao_contado.movimento_ajuste_id is None

    saldo_2 = (await session.execute(
        select(SaldoEstoque).where(SaldoEstoque.deposito_id == deposito_id, SaldoEstoque.produto_id == produto_id_2)
    )).scalars().first()
    assert float(saldo_2.quantidade_atual) == 30.0


@pytest.mark.asyncio
async def test_cancelar_contagem_aberta_nao_toca_saldo(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id, deposito_id, produto_id = await _setup_base(session, tenant_id)
    await _criar_saldo(session, deposito_id, produto_id, quantidade=40.0)

    svc = ContagemEstoqueService(session, tenant_id)
    contagem = await svc.abrir_contagem(ContagemAbrirRequest(deposito_id=deposito_id))
    await svc.registrar_contagem_item(contagem.id, produto_id, 999.0)
    cancelada = await svc.cancelar_contagem(contagem.id)

    assert cancelada.status == "CANCELADA"
    saldo = (await session.execute(
        select(SaldoEstoque).where(SaldoEstoque.deposito_id == deposito_id, SaldoEstoque.produto_id == produto_id)
    )).scalars().first()
    assert float(saldo.quantidade_atual) == 40.0


@pytest.mark.asyncio
async def test_nao_permite_cancelar_contagem_concluida(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id, deposito_id, produto_id = await _setup_base(session, tenant_id)
    await _criar_saldo(session, deposito_id, produto_id, quantidade=10.0)

    svc = ContagemEstoqueService(session, tenant_id)
    contagem = await svc.abrir_contagem(ContagemAbrirRequest(deposito_id=deposito_id))
    await svc.concluir_contagem(contagem.id)

    with pytest.raises(BusinessRuleError):
        await svc.cancelar_contagem(contagem.id)


@pytest.mark.asyncio
async def test_isolamento_tenant_contagem(session_a, session_b, tenant_id, outro_tenant_id):
    await _garantir_tenant(session_a, tenant_id)
    unidade_id, deposito_id, produto_id = await _setup_base(session_a, tenant_id)
    await _criar_saldo(session_a, deposito_id, produto_id, quantidade=10.0)

    svc_a = ContagemEstoqueService(session_a, tenant_id)
    contagem = await svc_a.abrir_contagem(ContagemAbrirRequest(deposito_id=deposito_id))

    stmt = select(ContagemEstoque).where(
        ContagemEstoque.tenant_id == outro_tenant_id, ContagemEstoque.id == contagem.id,
    )
    assert (await session_b.execute(stmt)).scalars().first() is None
