import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from operacional.models.compras import SolicitacaoCompra
from operacional.models.estoque import Deposito
from core.cadastros.produtos.models import Produto
from operacional.services.compras_service import ComprasService
from operacional.schemas.compras import SolicitacaoCompraCreate

@pytest.mark.asyncio
async def test_solicitacao_compra_enrichment_and_status(
    session: AsyncSession, 
    tenant_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID
):
    tenant_uuid = tenant_id
    
    # 1. Setup: Produto e Deposito
    produto = Produto(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        nome="Fertilizante Super",
        tipo="INSUMO",
        unidade_medida="KG",
        ativo=True
    )
    deposito = Deposito(
        id=uuid.uuid4(),
        tenant_id=tenant_uuid,
        unidade_produtiva_id=unidade_produtiva_id,
        nome="Almoxarifado Central",
        tipo="GERAL",
        ativo=True
    )
    session.add_all([produto, deposito])
    await session.flush()
    
    svc = ComprasService(session, tenant_uuid)
    
    # 2. Criar solicitação
    data = SolicitacaoCompraCreate(
        item_id=produto.id,
        deposito_id=deposito.id,
        quantidade_solicitada=100.0,
        unidade="KG",
        origem="MANUAL"
    )
    sol = await svc.criar_solicitacao(data)
    await session.commit()
    
    # 3. Listar e validar enriquecimento
    solicitacoes = await svc.listar_solicitacoes()
    assert len(solicitacoes) == 1
    assert solicitacoes[0].produto_nome == "Fertilizante Super"
    assert solicitacoes[0].deposito_nome == "Almoxarifado Central"
    assert solicitacoes[0].status == "ABERTA"
    
    # 4. Atualizar status
    updated = await svc.atualizar_status(sol.id, "EM_ANALISE")
    await session.commit()
    
    assert updated.status == "EM_ANALISE"
    assert updated.produto_nome == "Fertilizante Super"
    
    # 5. Validar filtro por status
    sols_analise = await svc.listar_solicitacoes(status="EM_ANALISE")
    assert len(sols_analise) == 1
    
    sols_aberta = await svc.listar_solicitacoes(status="ABERTA")
    assert len(sols_aberta) == 0
