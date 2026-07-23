import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from operacional.models.compras import PedidoCompra, SolicitacaoCompra, SolicitacaoItem, ItemPedidoCompra
from operacional.services.compras_service import ComprasService


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.get = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def compras_service(mock_session):
    return ComprasService(mock_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_criar_cotacao_usa_historico_compativel_e_nao_snapshot_de_produto(
    compras_service,
    mock_session,
):
    produto_id = uuid.uuid4()
    solicitacao = SolicitacaoCompra(
        id=uuid.uuid4(),
        tenant_id=compras_service.tenant_id,
        produto_id=produto_id,
        deposito_id=uuid.uuid4(),
        quantidade_solicitada=100.0,
        unidade="KG",
        origem="MANUAL",
        status="APROVADA",
    )
    solicitacao_item = SolicitacaoItem(
        id=uuid.uuid4(),
        solicitacao_id=solicitacao.id,
        produto_id=produto_id,
        deposito_id=solicitacao.deposito_id,
        quantidade_solicitada=100.0,
        unidade="KG",
    )
    solicitacao_item.produto_nome = "Produto Guardrail"

    async def _mock_get(model, _id):
        if model is SolicitacaoCompra:
            return solicitacao
        return None

    mock_session.get.side_effect = _mock_get
    compras_service._enriquecer_itens_solicitacao = AsyncMock(return_value=[solicitacao_item])
    compras_service._enriquecer_itens_cotacao = AsyncMock(return_value=[])
    compras_service.obter_fornecedor_orm = AsyncMock(
        return_value=SimpleNamespace(id=uuid.uuid4(), pessoa_id=uuid.uuid4(), condicoes_pagamento=None, prazo_entrega_dias=None)
    )
    compras_service.get_historico_precos = AsyncMock(
        return_value={
            "preco_medio": 10.0,
            "menor_preco": 8.0,
            "maior_preco": 12.0,
            "historico": [],
        }
    )

    with patch(
        "operacional.services.compras_service.obter_dados_exibicao_fornecedor",
        new=AsyncMock(return_value={"nome_fantasia": "Fornecedor Guardrail", "email": None, "telefone": None}),
    ), patch(
        "operacional.services.compras_service.SequencialService.proximo_numero",
        new=AsyncMock(return_value="COT-2026-000001"),
    ):
        cotacao = await compras_service.criar_cotacao(
            solicitacao.id,
            SimpleNamespace(
                fornecedor_id=uuid.uuid4(),
                condicoes_pagamento=None,
                prazo_entrega_dias=3,
                itens=None,
                valor_unitario=11.5,
            ),
        )

    assert cotacao is not None
    assert cotacao.acima_media is False
    assert cotacao.mensagem_alerta is None
    compras_service.get_historico_precos.assert_awaited_once_with(produto_id)
    mock_session.add.assert_called()


@pytest.mark.asyncio
async def test_receber_pedido_usa_valor_do_pedido_como_custo_operacional(
    compras_service,
    mock_session,
):
    pedido = PedidoCompra(
        id=uuid.uuid4(),
        tenant_id=compras_service.tenant_id,
        solicitacao_id=None,
        cotacao_id=None,
        fornecedor_nome="Fornecedor Guardrail",
        fornecedor_contato=None,
        valor_total=750.0,
        status="ABERTO",
    )

    item_pedido = ItemPedidoCompra(
        id=uuid.uuid4(),
        pedido_id=pedido.id,
        produto_id=uuid.uuid4(),
        deposito_id=uuid.uuid4(),
        unidade="L",
        quantidade_solicitada=20.0,
        preco_estimado_unitario=37.5,
        valor_total=pedido.valor_total,
        quantidade_recebida=0.0,
        status_item="PENDENTE",
    )

    async def _mock_get(model, _id):
        if model is PedidoCompra:
            return pedido
        return None

    mock_session.get.side_effect = _mock_get
    exec_results = []
    for scalar_value in (None, SimpleNamespace(id=uuid.uuid4(), quantidade_atual=20.0)):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = scalar_value
        exec_results.append(mock_result)
    mock_session.execute.side_effect = exec_results

    lote_mock = SimpleNamespace(id=uuid.uuid4(), quantidade_atual=0.0)
    movimento_mock = SimpleNamespace(id=uuid.uuid4())
    with patch("operacional.services.compras_service.EstoqueService.criar_lote", new=AsyncMock(return_value=lote_mock)) as criar_lote, \
         patch("operacional.services.compras_service.EstoqueService.registrar_entrada", new=AsyncMock(return_value=movimento_mock)) as registrar_entrada, \
         patch.object(compras_service, "_get_or_create_item_pedido_principal", new=AsyncMock(return_value=item_pedido)), \
         patch.object(compras_service, "_build_recebimento_fallback", new=AsyncMock(return_value=SimpleNamespace(
             numero_nf=None, chave_nfe=None, observacoes=None,
             itens=[SimpleNamespace(
                 item_pedido_id=item_pedido.id,
                 quantidade_recebida=item_pedido.quantidade_solicitada,
                 preco_real_unitario=None,
                 numero_lote_fornecedor=None,
                 lote_id=None,
             )],
         ))), \
         patch.object(compras_service, "_resolver_fornecedor_financeiro", new=AsyncMock(return_value=(None, "Fornecedor Guardrail", SimpleNamespace(id=uuid.uuid4())))), \
         patch.object(compras_service, "_garantir_despesa_financeira_compra", new=AsyncMock(return_value=None)), \
         patch.object(compras_service, "_enriquecer_pedido", new=AsyncMock(return_value=pedido)):
        recebido = await compras_service.receber_pedido(pedido.id)

    assert recebido.status == "RECEBIDO"
    criar_lote.assert_awaited_once()
    registrar_entrada.assert_awaited_once()
    entrada_req = registrar_entrada.await_args.args[0]
    assert entrada_req.custo_unitario == 37.5
    assert entrada_req.quantidade == 20.0
    assert pedido.status == "RECEBIDO"
