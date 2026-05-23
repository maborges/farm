import uuid

import pytest

from core.cadastros.produtos.models import Produto
from operacional.models.estoque import Deposito, LoteEstoque, SaldoEstoque
from operacional.schemas.estoque import EntradaEstoqueRequest, SaidaEstoqueRequest
from operacional.services.estoque_service import EstoqueService


async def _criar_deposito(session, tenant_id, unidade_produtiva_id, nome="Depósito Guardrail"):
    deposito = Deposito(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome=nome,
        tipo="GERAL",
        ativo=True,
    )
    session.add(deposito)
    await session.flush()
    return deposito


@pytest.mark.asyncio
async def test_entrada_nao_reescreve_preco_medio_do_produto(
    session,
    tenant_id,
    unidade_produtiva_id,
):
    deposito = await _criar_deposito(session, tenant_id, unidade_produtiva_id)
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome="Produto Snapshot",
        tipo="INSUMO",
        unidade_medida="L",
        preco_medio=99.0,
        ativo=True,
    )
    session.add(produto)
    await session.commit()

    svc = EstoqueService(session, tenant_id)
    mov = await svc.registrar_entrada(
        EntradaEstoqueRequest(
            deposito_id=deposito.id,
            produto_id=produto.id,
            quantidade=10.0,
            custo_unitario=45.0,
            motivo="Entrada teste",
        )
    )
    await session.refresh(produto)

    assert mov.custo_unitario == 45.0
    assert produto.preco_medio == 99.0


@pytest.mark.asyncio
async def test_saida_com_lote_prioriza_custo_do_lote(
    session,
    tenant_id,
    unidade_produtiva_id,
):
    deposito = await _criar_deposito(session, tenant_id, unidade_produtiva_id, nome="Depósito FIFO")
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome="Produto Lote",
        tipo="INSUMO",
        unidade_medida="KG",
        preco_medio=88.0,
        ativo=True,
    )
    session.add(produto)
    await session.flush()

    lote = LoteEstoque(
        id=uuid.uuid4(),
        produto_id=produto.id,
        deposito_id=deposito.id,
        numero_lote="LOTE-GUARDRAIL",
        quantidade_inicial=100.0,
        quantidade_atual=100.0,
        custo_unitario=12.5,
        status="ATIVO",
    )
    saldo = SaldoEstoque(
        id=uuid.uuid4(),
        deposito_id=deposito.id,
        produto_id=produto.id,
        quantidade_atual=100.0,
        quantidade_reservada=0.0,
    )
    session.add_all([lote, saldo])
    await session.commit()

    svc = EstoqueService(session, tenant_id)
    mov = await svc.registrar_saida(
        SaidaEstoqueRequest(
            deposito_id=deposito.id,
            produto_id=produto.id,
            quantidade=10.0,
            motivo="Saída teste",
            lote_id=lote.id,
        )
    )
    await session.refresh(produto)

    assert mov.custo_unitario == 12.5
    assert produto.preco_medio == 88.0
