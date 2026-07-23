import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import text
from operacional.models.compras import SolicitacaoCompra, CotacaoCompra, PedidoCompra, ItemPedidoCompra
from operacional.models.estoque import Deposito
from core.cadastros.produtos.models import Produto
from operacional.services.compras_service import ComprasService

@pytest.mark.asyncio
async def test_explicacao_assistente_compra_step161(client: AsyncClient, headers_operacional: dict, session):
    """
    Testa a geração de explicações textuais do assistente de compra (Step 161).
    """
    # NOTA: não usar o fixture global `unidade_produtiva_id` — ele cria a fazenda
    # sob um tenant diferente do usado por headers_operacional.
    tenant_id = uuid.UUID(headers_operacional["X-Tenant-ID"])
    item_id = uuid.uuid4()
    solicitacao_id = uuid.uuid4()
    deposito_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()

    await session.execute(text("""
        INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
        VALUES (:id, :tenant_id, 'Fazenda Teste Assistente', true, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)})

    # Infra
    session.add(Produto(id=item_id, tenant_id=tenant_id, nome="Item Assistente", tipo="PECA", ativo=True))
    session.add(Deposito(id=deposito_id, tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id, nome="D1", ativo=True))
    await session.flush()
    
    # Adicionar Histórico para garantir score BOA (Preço Médio de 20.0)
    pedido_historico_id = uuid.uuid4()
    session.add(PedidoCompra(
        id=pedido_historico_id, tenant_id=tenant_id, fornecedor_nome="Antigo",
        valor_total=20.0, status="CONCLUIDO",
    ))
    await session.flush()
    session.add(ItemPedidoCompra(
        id=uuid.uuid4(), pedido_id=pedido_historico_id, produto_id=item_id, deposito_id=deposito_id,
        unidade="UN", quantidade_solicitada=1, preco_estimado_unitario=20.0, valor_total=20.0,
    ))
    
    solicitacao = SolicitacaoCompra(
        id=solicitacao_id, tenant_id=tenant_id, produto_id=item_id,
        deposito_id=deposito_id, quantidade_solicitada=1, unidade="UN", status="ABERTA"
    )
    session.add(solicitacao)
    await session.commit()
    
    # 1. Cotação BOA (Preço 10.0 < Média 20.0 -> +40)
    # Prazo 1 (+20) + Consistência fallback (+15) + Recorrência fallback (+5) = 80 (BOA)
    c_boa = CotacaoCompra(
        id=uuid.uuid4(), tenant_id=tenant_id, solicitacao_id=solicitacao_id,
        fornecedor_nome="Fornecedor Top", valor_unitario=10.0, valor_total=10.0,
        prazo_entrega_dias=1, status="RECEBIDA", acima_media=False
    )
    
    # 2. Cotação RUIM (Preço 100.0 > Média 20.0)
    c_ruim = CotacaoCompra(
        id=uuid.uuid4(), tenant_id=tenant_id, solicitacao_id=solicitacao_id,
        fornecedor_nome="Fornecedor Caro", valor_unitario=100.0, valor_total=100.0,
        prazo_entrega_dias=15, status="RECEBIDA", acima_media=True
    )

    session.add_all([c_boa, c_ruim])
    await session.commit()
    
    svc = ComprasService(session, tenant_id)
    ranking = await svc.listar_cotacoes(solicitacao_id)
    
    # Validar Cotação BOA (#1)
    boa = ranking[0]
    assert boa.fornecedor_nome == "Fornecedor Top"
    assert boa.classificacao_score == "BOA"
    assert "melhor escolha técnica" in boa.explicacao_compra
    assert len(boa.pontos_fortes) > 0
    assert any(word in p.lower() for p in boa.pontos_fortes for word in ["competitivo", "excelente"])

    # Validar Cotação RUIM (#2)
    ruim = ranking[1]
    assert ruim.fornecedor_nome == "Fornecedor Caro"
    assert ruim.classificacao_score == "RUIM"
    assert "Não recomendamos" in ruim.explicacao_compra
    assert len(ruim.pontos_atencao) > 0
