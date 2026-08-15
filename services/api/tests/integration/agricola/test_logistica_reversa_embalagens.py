from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError
from core.cadastros.produtos.models import Produto, ProdutoEstoque
from operacional.models.compras import Fornecedor, ItemPedidoCompra, PedidoCompra
from operacional.models.estoque import Deposito
from operacional.schemas.compras import ItemRecebimentoCreate, RecebimentoCreate
from operacional.services.compras_service import ComprasService
from core.cadastros.pessoas.models import Pessoa
from agricola.logistica_reversa_embalagens.models import DevolucaoEmbalagem, StatusDevolucaoEmbalagem
from agricola.logistica_reversa_embalagens.service import DevolucaoEmbalagemService
from test_operational_workflow_governance_step03 import _criar_unidade_produtiva, _garantir_tenant


async def _criar_deposito(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> uuid.UUID:
    deposito = Deposito(tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id, nome="Depósito Teste")
    session.add(deposito)
    await session.commit()
    return deposito.id


async def _criar_produto(session: AsyncSession, tenant_id: uuid.UUID, *, requer_receituario: bool) -> uuid.UUID:
    produto = Produto(tenant_id=tenant_id, nome="Herbicida LRE Teste", tipo="DEFENSIVO", unidade_medida="L")
    session.add(produto)
    await session.flush()
    session.add(ProdutoEstoque(produto_id=produto.id, requer_receituario=requer_receituario))
    await session.commit()
    return produto.id


async def _criar_pedido_com_item(
    session: AsyncSession, tenant_id: uuid.UUID, *, produto_id: uuid.UUID, fornecedor_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, uuid.UUID]:
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    deposito_id = await _criar_deposito(session, tenant_id, unidade_id)
    pedido = PedidoCompra(
        tenant_id=tenant_id, fornecedor_id=fornecedor_id, fornecedor_nome="Fornecedor Teste",
        valor_total=0.0, status="ABERTO",
    )
    session.add(pedido)
    await session.flush()
    item = ItemPedidoCompra(
        pedido_id=pedido.id, produto_id=produto_id, deposito_id=deposito_id, unidade="L",
        quantidade_solicitada=20.0, preco_estimado_unitario=0.0, valor_total=0.0,
    )
    session.add(item)
    await session.commit()
    return pedido.id, item.id


async def _criar_fornecedor(session: AsyncSession, tenant_id: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    pessoa = Pessoa(tenant_id=tenant_id, tipo="PJ", nome_exibicao="Revenda Teste")
    session.add(pessoa)
    await session.flush()
    fornecedor = Fornecedor(tenant_id=tenant_id, pessoa_id=pessoa.id)
    session.add(fornecedor)
    await session.commit()
    return fornecedor.id, pessoa.id


async def _receber_com_embalagens(
    session: AsyncSession, tenant_id: uuid.UUID, *, pedido_id: uuid.UUID, item_pedido_id: uuid.UUID,
    quantidade_embalagens: int | None,
):
    svc = ComprasService(session, tenant_id)
    await svc.receber_pedido(
        pedido_id,
        data=RecebimentoCreate(itens=[
            ItemRecebimentoCreate(
                item_pedido_id=item_pedido_id, quantidade_recebida=20.0,
                preco_real_unitario=0.0, quantidade_embalagens=quantidade_embalagens,
            )
        ]),
    )
    await session.commit()


@pytest.mark.asyncio
async def test_recebimento_com_embalagens_cria_pendencia(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    produto_id = await _criar_produto(session, tenant_id, requer_receituario=True)
    fornecedor_id, pessoa_id = await _criar_fornecedor(session, tenant_id)
    pedido_id, item_pedido_id = await _criar_pedido_com_item(session, tenant_id, produto_id=produto_id, fornecedor_id=fornecedor_id)

    await _receber_com_embalagens(session, tenant_id, pedido_id=pedido_id, item_pedido_id=item_pedido_id, quantidade_embalagens=8)

    svc = DevolucaoEmbalagemService(session, tenant_id)
    pendentes = await svc.listar_pendentes()
    assert len(pendentes) == 1
    devolucao = pendentes[0]
    assert devolucao.produto_id == produto_id
    assert devolucao.quantidade_embalagens_compradas == 8
    assert devolucao.status == StatusDevolucaoEmbalagem.PENDENTE.value
    assert devolucao.destino_pessoa_id == pessoa_id
    assert devolucao.prazo_limite == devolucao.data_compra + timedelta(days=365)


@pytest.mark.asyncio
async def test_recebimento_sem_exigencia_nao_cria_pendencia(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    produto_id = await _criar_produto(session, tenant_id, requer_receituario=False)
    pedido_id, item_pedido_id = await _criar_pedido_com_item(session, tenant_id, produto_id=produto_id)

    await _receber_com_embalagens(session, tenant_id, pedido_id=pedido_id, item_pedido_id=item_pedido_id, quantidade_embalagens=8)

    svc = DevolucaoEmbalagemService(session, tenant_id)
    assert await svc.listar_pendentes() == []


@pytest.mark.asyncio
async def test_recebimento_sem_quantidade_embalagens_nao_cria_pendencia(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    produto_id = await _criar_produto(session, tenant_id, requer_receituario=True)
    pedido_id, item_pedido_id = await _criar_pedido_com_item(session, tenant_id, produto_id=produto_id)

    await _receber_com_embalagens(session, tenant_id, pedido_id=pedido_id, item_pedido_id=item_pedido_id, quantidade_embalagens=None)

    svc = DevolucaoEmbalagemService(session, tenant_id)
    assert await svc.listar_pendentes() == []


@pytest.mark.asyncio
async def test_devolucao_parcial_depois_completa_fecha_status(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    produto_id = await _criar_produto(session, tenant_id, requer_receituario=True)
    pedido_id, item_pedido_id = await _criar_pedido_com_item(session, tenant_id, produto_id=produto_id)
    await _receber_com_embalagens(session, tenant_id, pedido_id=pedido_id, item_pedido_id=item_pedido_id, quantidade_embalagens=10)

    svc = DevolucaoEmbalagemService(session, tenant_id)
    devolucao = (await svc.listar_pendentes())[0]

    await svc.registrar_devolucao(devolucao.id, 4)
    await session.commit()
    devolucao = await svc.get_or_fail(devolucao.id)
    assert devolucao.status == StatusDevolucaoEmbalagem.PENDENTE.value
    assert devolucao.quantidade_embalagens_devolvidas == 4

    await svc.registrar_devolucao(devolucao.id, 6)
    await session.commit()
    devolucao = await svc.get_or_fail(devolucao.id)
    assert devolucao.status == StatusDevolucaoEmbalagem.DEVOLVIDO.value
    assert devolucao.quantidade_embalagens_devolvidas == 10


@pytest.mark.asyncio
async def test_devolucao_acima_do_comprado_falha(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    produto_id = await _criar_produto(session, tenant_id, requer_receituario=True)
    pedido_id, item_pedido_id = await _criar_pedido_com_item(session, tenant_id, produto_id=produto_id)
    await _receber_com_embalagens(session, tenant_id, pedido_id=pedido_id, item_pedido_id=item_pedido_id, quantidade_embalagens=5)

    svc = DevolucaoEmbalagemService(session, tenant_id)
    devolucao = (await svc.listar_pendentes())[0]

    with pytest.raises(BusinessRuleError):
        await svc.registrar_devolucao(devolucao.id, 6)


@pytest.mark.asyncio
async def test_isolamento_tenant_devolucao(session: AsyncSession):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _garantir_tenant(session, tenant_a)
    await _garantir_tenant(session, tenant_b)
    produto_id = await _criar_produto(session, tenant_a, requer_receituario=True)
    pedido_id, item_pedido_id = await _criar_pedido_com_item(session, tenant_a, produto_id=produto_id)
    await _receber_com_embalagens(session, tenant_a, pedido_id=pedido_id, item_pedido_id=item_pedido_id, quantidade_embalagens=3)

    svc_a = DevolucaoEmbalagemService(session, tenant_a)
    devolucao = (await svc_a.listar_pendentes())[0]

    svc_b = DevolucaoEmbalagemService(session, tenant_b)
    from core.exceptions import EntityNotFoundError
    with pytest.raises(EntityNotFoundError):
        await svc_b.get_or_fail(devolucao.id)


@pytest.mark.asyncio
async def test_listar_pendentes_filtra_por_prazo(session: AsyncSession):
    tenant_id = uuid.uuid4()
    await _garantir_tenant(session, tenant_id)
    produto_id = await _criar_produto(session, tenant_id, requer_receituario=True)
    pedido_id, item_pedido_id = await _criar_pedido_com_item(session, tenant_id, produto_id=produto_id)
    await _receber_com_embalagens(session, tenant_id, pedido_id=pedido_id, item_pedido_id=item_pedido_id, quantidade_embalagens=2)

    svc = DevolucaoEmbalagemService(session, tenant_id)
    # prazo_limite = hoje + 365 dias, então filtrar por 30 dias não deve retornar nada.
    assert await svc.listar_pendentes(vencendo_em_dias=30) == []
    assert len(await svc.listar_pendentes(vencendo_em_dias=400)) == 1
