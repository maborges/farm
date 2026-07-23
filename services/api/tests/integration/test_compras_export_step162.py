import pytest
from httpx import AsyncClient
import uuid
from sqlalchemy import text
from operacional.models.compras import SolicitacaoCompra, CotacaoCompra
from core.cadastros.produtos.models import Produto
from operacional.models.estoque import Deposito

@pytest.mark.asyncio
async def test_export_comparativo_pdf_step162(client: AsyncClient, session, headers_operacional: dict):
    # 1. Setup Data
    # NOTA: não usar o fixture global `unidade_produtiva_id` — ele cria a fazenda
    # sob um tenant diferente (fixture `tenant_id` de tests/conftest.py), que não
    # bate com o tenant real deste teste (vindo de X-Tenant-ID / headers_operacional).
    tenant_id = uuid.UUID(headers_operacional["X-Tenant-ID"])
    item_id = uuid.uuid4()
    deposito_id = uuid.uuid4()
    solicitacao_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()

    await session.execute(text("""
        INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
        VALUES (:id, :tenant_id, 'Fazenda Teste Export', true, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id)})

    # Criar Produto e Depósito para o PDF não dar N/A
    produto = Produto(id=item_id, tenant_id=tenant_id, nome="Produto Teste Export", tipo="PECA", unidade_medida="UN")
    deposito = Deposito(id=deposito_id, tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id, nome="Deposito Teste Export")
    session.add_all([produto, deposito])
    await session.flush()

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
    await session.flush() # GARANTIR QUE EXISTE NO DB PARA A COTACAO USAR FK

    cotacao = CotacaoCompra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        solicitacao_id=solicitacao_id,
        fornecedor_nome="Fornecedor Teste PDF",
        valor_unitario=100.0,
        valor_total=1000.0,
        prazo_entrega_dias=5,
        status="RECEBIDA"
    )
    session.add(cotacao)
    await session.commit()

    # 2. Test Export
    response = await client.get(
        f"/api/v1/compras/solicitacoes/{solicitacao_id}/cotacoes/export.pdf",
        headers=headers_operacional
    )

    # 3. Assertions
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert f"comparativo_solicitacao_{solicitacao_id}.pdf" in response.headers["content-disposition"]
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_export_comparativo_pdf_not_found_step162(client: AsyncClient, headers_operacional: dict):
    # Testar que retorna 404 para solicitação inexistente
    solicitacao_id = uuid.uuid4()
    
    response = await client.get(
        f"/api/v1/compras/solicitacoes/{solicitacao_id}/cotacoes/export.pdf",
        headers=headers_operacional
    )

    assert response.status_code == 404
