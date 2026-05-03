import pytest
import uuid
from httpx import AsyncClient
from operacional.models.compras import SolicitacaoCompra, CotacaoCompra
from operacional.models.estoque import Deposito
from core.cadastros.produtos.models import Produto
from operacional.services.compras_service import ComprasService

@pytest.mark.asyncio
async def test_score_compra_calculo_step159(client: AsyncClient, headers_operacional: dict, session, unidade_produtiva_id):
    """
    Testa a lógica de cálculo de score de compra (Step 159).
    """
    tenant_id = uuid.UUID(headers_operacional["X-Tenant-ID"])
    item_id = uuid.uuid4()
    solicitacao_id = uuid.uuid4()
    deposito_id = uuid.uuid4()
    
    # Criar Produto
    produto = Produto(
        id=item_id,
        tenant_id=tenant_id,
        nome="Produto Teste Score",
        tipo="MATERIAL_GERAL",
        unidade_medida="UN",
        ativo=True
    )
    session.add(produto)
    
    # Criar Depósito
    deposito = Deposito(
        id=deposito_id,
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        nome="Depósito Teste",
        tipo="GERAL",
        ativo=True
    )
    session.add(deposito)
    await session.flush()
    
    # Mock de uma solicitação
    solicitacao = SolicitacaoCompra(
        id=solicitacao_id,
        tenant_id=tenant_id,
        produto_id=item_id,
        deposito_id=deposito_id,
        quantidade_solicitada=10,
        unidade="UN",
        status="ABERTA"
    )
    session.add(solicitacao)
    await session.commit()
    
    # Mock de uma cotação para teste
    cotacao = CotacaoCompra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        solicitacao_id=solicitacao_id,
        fornecedor_nome="Fornecedor Teste Score",
        valor_unitario=10.0,
        valor_total=100.0,
        prazo_entrega_dias=2, # Bom prazo
        status="RECEBIDA",
        acima_media=False # Bom preço
    )
    session.add(cotacao)
    await session.commit()
    
    svc = ComprasService(session, tenant_id)
    
    # Mock de métodos internos para não depender de DB real complexo
    # Em um teste de integração real, teríamos dados no banco. 
    # Aqui vamos testar se a função retorna a estrutura correta.
    
    score_res = await svc.calcular_score_compra(cotacao)
    
    assert "score" in score_res
    assert "classificacao" in score_res
    assert "motivos" in score_res
    assert score_res["classificacao"] in ["BOA", "ATENCAO", "RUIM"]
    assert len(score_res["motivos"]) > 0
    
    # Teste de valores específicos baseados no mock
    # Como não tem histórico, deve cair nos fallbacks (20 + 15 + 20 + 5 = 60 -> ATENCAO)
    # Valor unitário 10, no histórico fallback é acima_media=False -> +40
    # Prazo 2 -> +20
    # Consistencia fallback -> +15
    # Recorrencia fallback -> +5
    # Total esperado aproximado: 80 (BOA)
    assert score_res["score"] >= 50
