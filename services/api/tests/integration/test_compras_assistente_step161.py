import pytest
import uuid
from httpx import AsyncClient
from operacional.models.compras import SolicitacaoCompra, CotacaoCompra, PedidoCompra
from operacional.models.estoque import Deposito
from core.cadastros.produtos.models import Produto
from operacional.services.compras_service import ComprasService

@pytest.mark.asyncio
async def test_explicacao_assistente_compra_step161(client: AsyncClient, headers_operacional: dict, session, unidade_produtiva_id):
    """
    Testa a geração de explicações textuais do assistente de compra (Step 161).
    """
    tenant_id = uuid.UUID(headers_operacional["X-Tenant-ID"])
    item_id = uuid.uuid4()
    solicitacao_id = uuid.uuid4()
    deposito_id = uuid.uuid4()
    
    # Infra
    session.add(Produto(id=item_id, tenant_id=tenant_id, nome="Item Assistente", tipo="PECA", ativo=True))
    session.add(Deposito(id=deposito_id, tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id, nome="D1", ativo=True))
    await session.flush()
    
    # Adicionar Histórico para garantir score BOA (Preço Médio de 20.0)
    session.add(PedidoCompra(
        id=uuid.uuid4(), tenant_id=tenant_id, item_id=item_id, fornecedor_nome="Antigo",
        valor_unitario=20.0, quantidade=1, valor_total=20.0, status="CONCLUIDO", deposito_id=deposito_id
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
