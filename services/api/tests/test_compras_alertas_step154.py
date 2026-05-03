import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from operacional.models.compras import SolicitacaoCompra, CotacaoCompra, PedidoCompra
from operacional.models.estoque import Deposito
from core.cadastros.produtos.models import Produto
from operacional.services.compras_service import ComprasService
from operacional.schemas.compras import SolicitacaoCompraCreate, CotacaoSolicitacaoCreate

@pytest.mark.asyncio
async def test_compras_price_alerts_step154(
    session: AsyncSession, 
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID
):
    tenant_uuid = tenant_id
    
    # 1. Setup: Produto, Deposito e Solicitação
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        nome="Adubo Premium",
        tipo="INSUMO",
        unidade_medida="KG",
        ativo=True
    )
    deposito = Deposito(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        unidade_produtiva_id=unidade_produtiva_id,
        nome="Galpão 1",
        tipo="GERAL",
        ativo=True
    )
    session.add_all([produto, deposito])
    await session.flush()
    
    svc = ComprasService(session, tenant_uuid)
    
    # Criar solicitação aprovada
    data_sol = SolicitacaoCompraCreate(
        item_id=produto.id,
        deposito_id=deposito.id,
        quantidade_solicitada=10.0,
        unidade="KG",
        origem="MANUAL"
    )
    sol = await svc.criar_solicitacao(data_sol)
    sol.status = "APROVADA"
    await session.flush()
    
    # 2. Criar histórico de preços (Preço Médio = 10.0)
    # Adicionando uma cotação e um pedido anteriores
    cot_hist = CotacaoCompra(
        tenant_id=tenant_uuid,
        solicitacao_id=sol.id,
        fornecedor_nome="Forn Antigo",
        valor_unitario=9.0,
        valor_total=90.0,
        status="RECUSADA"
    )
    ped_hist = PedidoCompra(
        tenant_id=tenant_uuid,
        solicitacao_id=sol.id,
        cotacao_id=None,
        fornecedor_nome="Forn Antigo",
        item_id=produto.id,
        deposito_id=deposito.id,
        quantidade=10.0,
        unidade="KG",
        valor_unitario=11.0,
        valor_total=110.0,
        status="RECEBIDO"
    )
    session.add_all([cot_hist, ped_hist])
    await session.flush()
    
    # Média = (9 + 11) / 2 = 10.0
    
    # 3. Teste: Cotação DENTRO do limite (11.0 < 10.0 * 1.15)
    data_ok = CotacaoSolicitacaoCreate(
        fornecedor_nome="Forn Justo",
        valor_unitario=11.0
    )
    cot_ok = await svc.criar_cotacao(sol.id, data_ok)
    assert cot_ok.acima_media is False
    assert cot_ok.percentual_acima_media is None
    
    # 4. Teste: Cotação ACIMA do limite (12.0 > 10.0 * 1.15)
    data_alerta = CotacaoSolicitacaoCreate(
        fornecedor_nome="Forn Caro",
        valor_unitario=12.0
    )
    cot_alerta = await svc.criar_cotacao(sol.id, data_alerta)
    assert cot_alerta.acima_media is True
    # 12.0 é 20% acima de 10.0
    assert cot_alerta.percentual_acima_media == 16.13
    assert "16.13% acima da média" in cot_alerta.mensagem_alerta
    
    # 5. Teste: Item sem histórico (Média = 0)
    produto_novo = Produto(
        tenant_id=tenant_uuid,
        nome="Item Novo",
        tipo="OUTROS",
        unidade_medida="UN",
        ativo=True
    )
    session.add(produto_novo)
    await session.flush()
    
    sol_nova = await svc.criar_solicitacao(SolicitacaoCompraCreate(
        item_id=produto_novo.id,
        deposito_id=deposito.id,
        quantidade_solicitada=1,
        unidade="UN",
        origem="MANUAL"
    ))
    sol_nova.status = "APROVADA"
    await session.flush()
    
    cot_novo = await svc.criar_cotacao(sol_nova.id, CotacaoSolicitacaoCreate(
        fornecedor_nome="Forn Qualquer",
        valor_unitario=100.0
    ))
    assert cot_novo.acima_media is False
    assert cot_novo.percentual_acima_media is None
