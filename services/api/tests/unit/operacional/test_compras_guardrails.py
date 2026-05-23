import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from operacional.models.compras import PedidoCompra, SolicitacaoCompra
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
    solicitacao = SolicitacaoCompra(
        id=uuid.uuid4(),
        tenant_id=compras_service.tenant_id,
        produto_id=uuid.uuid4(),
        deposito_id=uuid.uuid4(),
        quantidade_solicitada=100.0,
        unidade="KG",
        origem="MANUAL",
        status="APROVADA",
    )

    mock_session.get.return_value = solicitacao
    compras_service.get_historico_precos = AsyncMock(
        return_value={
            "preco_medio": 10.0,
            "menor_preco": 8.0,
            "maior_preco": 12.0,
            "historico": [],
        }
    )

    cotacao = await compras_service.criar_cotacao(
        solicitacao.id,
        SimpleNamespace(
            fornecedor_nome="Fornecedor Guardrail",
            fornecedor_contato="11 99999-9999",
            valor_unitario=11.5,
            prazo_entrega_dias=3,
        ),
    )

    assert cotacao is not None
    assert cotacao.acima_media is False
    assert cotacao.mensagem_alerta is None
    compras_service.get_historico_precos.assert_awaited_once_with(solicitacao.produto_id)
    mock_session.add.assert_called_once()


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
        item_id=uuid.uuid4(),
        deposito_id=uuid.uuid4(),
        quantidade=20.0,
        unidade="L",
        valor_unitario=37.5,
        valor_total=750.0,
        status="ABERTO",
    )

    async def _mock_get(model, _id):
        if model is PedidoCompra:
            return pedido
        return None

    mock_session.get.side_effect = _mock_get
    exec_results = []
    for scalar_value in (None, None, SimpleNamespace(id=uuid.uuid4(), quantidade_atual=20.0)):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = scalar_value
        exec_results.append(mock_result)
    mock_session.execute.side_effect = exec_results

    lote_mock = SimpleNamespace(id=uuid.uuid4(), quantidade_atual=0.0)
    movimento_mock = SimpleNamespace(id=uuid.uuid4())
    with patch("operacional.services.compras_service.EstoqueService.criar_lote", new=AsyncMock(return_value=lote_mock)) as criar_lote, \
         patch("operacional.services.compras_service.EstoqueService.registrar_entrada", new=AsyncMock(return_value=movimento_mock)) as registrar_entrada, \
         patch.object(compras_service, "_enriquecer_pedido", new=AsyncMock(return_value=pedido)):
        recebido = await compras_service.receber_pedido(pedido.id)

    assert recebido.status == "RECEBIDO"
    criar_lote.assert_awaited_once()
    registrar_entrada.assert_awaited_once()
    entrada_req = registrar_entrada.await_args.args[0]
    assert entrada_req.custo_unitario == 37.5
    assert entrada_req.quantidade == 20.0
    assert pedido.status == "RECEBIDO"
