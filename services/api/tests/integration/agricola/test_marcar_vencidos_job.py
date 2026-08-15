from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.receituario_agronomico.models import StatusReceituario
from agricola.receituario_agronomico.schemas import ReceituarioAgronomicoCreate, ReceituarioItemCreate
from agricola.receituario_agronomico.service import ReceituarioAgronomicoService
from agricola.receituario_agronomico.vencimento_service import marcar_receituarios_vencidos
from agricola.logistica_reversa_embalagens.models import DevolucaoEmbalagem, StatusDevolucaoEmbalagem
from agricola.logistica_reversa_embalagens.vencimento_service import marcar_devolucoes_vencidas
from core.cadastros.pessoas.models import Pessoa, PessoaProfissionalAgronomo
from core.cadastros.produtos.models import Produto, ProdutoEstoque
from operacional.models.compras import Fornecedor, ItemPedidoCompra, PedidoCompra
from operacional.models.estoque import Deposito
from operacional.schemas.compras import ItemRecebimentoCreate, RecebimentoCreate
from operacional.services.compras_service import ComprasService
from test_operational_workflow_governance_step03 import _criar_unidade_produtiva, _garantir_tenant


async def _criar_pessoa_agronomo(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    pessoa = Pessoa(tenant_id=tenant_id, tipo="PF", nome_exibicao="Agrônomo Teste")
    session.add(pessoa)
    await session.flush()
    perfil = PessoaProfissionalAgronomo(
        tenant_id=tenant_id, pessoa_id=pessoa.id,
        crea_numero="123456", crea_uf="SP", crea_validade=date.today() + timedelta(days=365), ativo=True,
    )
    session.add(perfil)
    await session.commit()
    return pessoa.id


async def _criar_produto_defensivo(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    produto = Produto(tenant_id=tenant_id, nome="Herbicida Teste", tipo="DEFENSIVO", unidade_medida="L")
    session.add(produto)
    await session.flush()
    session.add(ProdutoEstoque(produto_id=produto.id, requer_receituario=True))
    await session.commit()
    return produto.id


async def _criar_receituario_emitido(
    session: AsyncSession, tenant_id: uuid.UUID, *, produto_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID, agronomo_pessoa_id: uuid.UUID,
    data_emissao: date, validade_dias: int,
):
    svc = ReceituarioAgronomicoService(session, tenant_id)
    receituario = await svc.emitir(ReceituarioAgronomicoCreate(
        agronomo_pessoa_id=agronomo_pessoa_id,
        unidade_produtiva_id=unidade_produtiva_id,
        data_emissao=data_emissao,
        validade_dias=validade_dias,
        itens=[ReceituarioItemCreate(produto_id=produto_id, dose=2.5, unidade_dose="L/ha")],
    ))
    receituario.status = StatusReceituario.EMITIDO.value
    await session.commit()
    return receituario


async def _criar_deposito(session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> uuid.UUID:
    deposito = Deposito(tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id, nome="Depósito Teste")
    session.add(deposito)
    await session.commit()
    return deposito.id


async def _criar_fornecedor(session: AsyncSession, tenant_id: uuid.UUID) -> uuid.UUID:
    pessoa = Pessoa(tenant_id=tenant_id, tipo="PJ", nome_exibicao="Revenda Teste")
    session.add(pessoa)
    await session.flush()
    fornecedor = Fornecedor(tenant_id=tenant_id, pessoa_id=pessoa.id)
    session.add(fornecedor)
    await session.commit()
    return fornecedor.id


async def _criar_pedido_com_item(
    session: AsyncSession, tenant_id: uuid.UUID, *, produto_id: uuid.UUID, deposito_id: uuid.UUID, fornecedor_id: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID]:
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


async def _receber_com_embalagens(
    session: AsyncSession, tenant_id: uuid.UUID, *, pedido_id: uuid.UUID, item_pedido_id: uuid.UUID,
):
    svc = ComprasService(session, tenant_id)
    await svc.receber_pedido(
        pedido_id,
        data=RecebimentoCreate(itens=[
            ItemRecebimentoCreate(
                item_pedido_id=item_pedido_id, quantidade_recebida=20.0,
                preco_real_unitario=0.0, quantidade_embalagens=8,
            )
        ]),
    )
    await session.commit()


@pytest.mark.asyncio
async def test_marcar_receituarios_vencidos_marca_emitido_vencido(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto_id = await _criar_produto_defensivo(session, tenant_id)
    agronomo_id = await _criar_pessoa_agronomo(session, tenant_id)

    receituario = await _criar_receituario_emitido(
        session, tenant_id, produto_id=produto_id, unidade_produtiva_id=unidade_id,
        agronomo_pessoa_id=agronomo_id,
        data_emissao=date.today() - timedelta(days=200), validade_dias=90,
    )

    count = await marcar_receituarios_vencidos(session)

    assert count >= 1
    await session.refresh(receituario)
    assert receituario.status == StatusReceituario.VENCIDO.value


@pytest.mark.asyncio
async def test_marcar_receituarios_vencidos_ignora_ainda_validos(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    produto_id = await _criar_produto_defensivo(session, tenant_id)
    agronomo_id = await _criar_pessoa_agronomo(session, tenant_id)

    receituario = await _criar_receituario_emitido(
        session, tenant_id, produto_id=produto_id, unidade_produtiva_id=unidade_id,
        agronomo_pessoa_id=agronomo_id,
        data_emissao=date.today(), validade_dias=90,
    )

    count = await marcar_receituarios_vencidos(session)

    assert count == 0
    await session.refresh(receituario)
    assert receituario.status == StatusReceituario.EMITIDO.value


@pytest.mark.asyncio
async def test_marcar_devolucoes_vencidas_marca_pendente_vencido(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    deposito_id = await _criar_deposito(session, tenant_id, unidade_id)
    produto_id = await _criar_produto_defensivo(session, tenant_id)
    fornecedor_id = await _criar_fornecedor(session, tenant_id)
    pedido_id, item_pedido_id = await _criar_pedido_com_item(
        session, tenant_id, produto_id=produto_id, deposito_id=deposito_id, fornecedor_id=fornecedor_id,
    )
    await _receber_com_embalagens(session, tenant_id, pedido_id=pedido_id, item_pedido_id=item_pedido_id)

    from sqlalchemy import select
    devolucao = (
        await session.execute(select(DevolucaoEmbalagem).where(DevolucaoEmbalagem.tenant_id == tenant_id))
    ).scalars().first()
    devolucao.prazo_limite = date.today() - timedelta(days=1)
    await session.commit()

    count = await marcar_devolucoes_vencidas(session)

    assert count == 1
    await session.refresh(devolucao)
    assert devolucao.status == StatusDevolucaoEmbalagem.VENCIDO.value


@pytest.mark.asyncio
async def test_marcar_devolucoes_vencidas_ignora_prazo_futuro(session, tenant_id):
    await _garantir_tenant(session, tenant_id)
    unidade_id = await _criar_unidade_produtiva(session, tenant_id)
    deposito_id = await _criar_deposito(session, tenant_id, unidade_id)
    produto_id = await _criar_produto_defensivo(session, tenant_id)
    fornecedor_id = await _criar_fornecedor(session, tenant_id)
    pedido_id, item_pedido_id = await _criar_pedido_com_item(
        session, tenant_id, produto_id=produto_id, deposito_id=deposito_id, fornecedor_id=fornecedor_id,
    )
    await _receber_com_embalagens(session, tenant_id, pedido_id=pedido_id, item_pedido_id=item_pedido_id)

    count = await marcar_devolucoes_vencidas(session)

    assert count == 0
