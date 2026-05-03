import pytest
import uuid
from httpx import AsyncClient
from operacional.models.compras import SolicitacaoCompra, CotacaoCompra
from operacional.models.estoque import Deposito
from core.cadastros.produtos.models import Produto
from operacional.services.compras_service import ComprasService

@pytest.mark.asyncio
async def test_ranking_comparativo_cotacoes_step160(client: AsyncClient, headers_operacional: dict, session, unidade_produtiva_id):
    """
    Testa a lógica de ranking comparativo de cotações (Step 160).
    """
    tenant_id = uuid.UUID(headers_operacional["X-Tenant-ID"])
    item_id = uuid.uuid4()
    solicitacao_id = uuid.uuid4()
    deposito_id = uuid.uuid4()
    
    # Criar Infraestrutura mínima
    session.add(Produto(id=item_id, tenant_id=tenant_id, nome="Item Ranking", tipo="PECA", ativo=True))
    session.add(Deposito(id=deposito_id, tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id, nome="D1", ativo=True))
    await session.flush()
    
    solicitacao = SolicitacaoCompra(
        id=solicitacao_id,
        tenant_id=tenant_id,
        produto_id=item_id,
        deposito_id=deposito_id,
        quantidade_solicitada=1,
        unidade="UN",
        status="ABERTA"
    )
    session.add(solicitacao)
    await session.commit()
    
    # 1. Cotação Ruim (Caro e Prazo longo)
    c1 = CotacaoCompra(
        id=uuid.uuid4(), tenant_id=tenant_id, solicitacao_id=solicitacao_id,
        fornecedor_nome="Ruim", valor_unitario=100.0, valor_total=100.0,
        prazo_entrega_dias=10, status="RECEBIDA", acima_media=True
    )
    
    # 2. Cotação Média (Preço OK, Prazo OK)
    c2 = CotacaoCompra(
        id=uuid.uuid4(), tenant_id=tenant_id, solicitacao_id=solicitacao_id,
        fornecedor_nome="Media", valor_unitario=50.0, valor_total=50.0,
        prazo_entrega_dias=5, status="RECEBIDA", acima_media=False
    )
    
    # 3. Cotação Boa (Barato e Rápido) -> Deve ser #1
    c3 = CotacaoCompra(
        id=uuid.uuid4(), tenant_id=tenant_id, solicitacao_id=solicitacao_id,
        fornecedor_nome="Boa", valor_unitario=30.0, valor_total=30.0,
        prazo_entrega_dias=2, status="RECEBIDA", acima_media=False
    )
    
    # 4. Empate com a Boa no Preço, mas Prazo Pior -> Deve ser #2
    c4 = CotacaoCompra(
        id=uuid.uuid4(), tenant_id=tenant_id, solicitacao_id=solicitacao_id,
        fornecedor_nome="Empate Preço", valor_unitario=30.0, valor_total=30.0,
        prazo_entrega_dias=5, status="RECEBIDA", acima_media=False
    )

    session.add_all([c1, c2, c3, c4])
    await session.commit()
    
    svc = ComprasService(session, tenant_id)
    ranking = await svc.listar_cotacoes(solicitacao_id)
    
    # Verificações de Ranking
    assert len(ranking) == 4
    
    # O #1 deve ser a 'Boa' (c3) devido ao menor preço e prazo
    assert ranking[0].fornecedor_nome == "Boa"
    assert ranking[0].posicao_ranking == 1
    assert ranking[0].melhor_opcao is True
    
    # O #2 deve ser a 'Empate Preço' (c4) - mesmo preço da Boa, mas prazo maior
    assert ranking[1].fornecedor_nome == "Empate Preço"
    assert ranking[1].posicao_ranking == 2
    assert ranking[1].melhor_opcao is False
    
    # O #3 deve ser a 'Media' (c2)
    assert ranking[2].fornecedor_nome == "Media"
    assert ranking[2].posicao_ranking == 3
    
    # O #4 deve ser a 'Ruim' (c1)
    assert ranking[3].fornecedor_nome == "Ruim"
    assert ranking[3].posicao_ranking == 4
    
    # Verificação de Desempate (se scores forem iguais)
    assert ranking[0].score_compra >= ranking[1].score_compra
    assert ranking[0].valor_total <= ranking[1].valor_total
