import pytest
import uuid
from httpx import AsyncClient
from datetime import date, timedelta
from sqlalchemy import text

@pytest.fixture
async def setup_hedge_recomendacoes(session, tenant_id, unidade_produtiva_id):
    """Cria os dados básicos para simular exposição e gerar recomendações."""
    safra_id = uuid.uuid4()
    commodity_id = uuid.uuid4()
    cultivo_id = uuid.uuid4()

    await session.execute(
        text("INSERT INTO cadastros_commodities (id, nome, unidade_medida, tenant_id) VALUES (:id, :nome, 'sc', :t)"),
        {"id": commodity_id, "nome": "SOJA", "t": tenant_id}
    )
    
    await session.execute(
        text("INSERT INTO safras (id, tenant_id, ano_safra, status) VALUES (:id, :t, '2023/2024', 'EM_ANDAMENTO')"),
        {"id": safra_id, "t": tenant_id}
    )

    data_colheita = date.today() + timedelta(days=30)
    await session.execute(
        text("""
            INSERT INTO cultivos (id, tenant_id, safra_id, commodity_id, cultura, status, consorciado, data_colheita_prevista, produtividade_meta_sc_ha) 
            VALUES (:id, :t, :s, :c, 'SOJA', 'EM_ANDAMENTO', false, :dc, 60.0)
        """),
        {"id": cultivo_id, "t": tenant_id, "s": safra_id, "c": commodity_id, "dc": data_colheita}
    )

    await session.execute(
        text("""
            INSERT INTO cultivos_areas (id, cultivo_id, unidade_produtiva_id, area_ha) 
            VALUES (:id, :cid, :uid, 1000.0)
        """),
        {
            "id": uuid.uuid4(), 
            "cid": cultivo_id, 
            "uid": unidade_produtiva_id
        }
    )
    # Produção Estimada: 60,000 sc

    await session.commit()
    
    return {
        "tenant_id": tenant_id,
        "safra_id": str(safra_id),
        "commodity_id": str(commodity_id),
    }

@pytest.mark.asyncio
async def test_gerar_recomendacoes_baixa_cobertura_safra_proxima(client: AsyncClient, setup_hedge_recomendacoes, headers_financeiro):
    """Verifica recomendação SAFRA_PROXIMA_BAIXA_COBERTURA quando cobertura < 50% e colheita < 60 dias."""
    safra_id = setup_hedge_recomendacoes["safra_id"]
    
    response = await client.get(
        f"/api/v1/hedge/exposicao/recomendacoes?safra_id={safra_id}",
        headers=headers_financeiro
    )
    
    assert response.status_code == 200
    dados = response.json()
    assert isinstance(dados, list)
    assert len(dados) >= 1
    regras = [r["id_regra"] for r in dados]
    assert "SAFRA_PROXIMA_BAIXA_COBERTURA" in regras

@pytest.mark.asyncio
async def test_gerar_recomendacoes_venda_sem_lastro(client: AsyncClient, setup_hedge_recomendacoes, session, headers_financeiro):
    """Verifica se Venda Sem Lastro dispara recomendação CRITICA."""
    safra_id = setup_hedge_recomendacoes["safra_id"]
    tenant_id = setup_hedge_recomendacoes["tenant_id"]
    
    # Inserir venda maior que 60.000 sc
    await session.execute(
        text("""
            INSERT INTO financeiro_comercializacoes (id, tenant_id, safra_id, quantidade, status)
            VALUES (:id, :t, :s, 70000.0, 'CONFIRMADO')
        """),
        {
            "id": uuid.uuid4(),
            "t": tenant_id,
            "s": safra_id
        }
    )
    await session.commit()
    
    response = await client.get(
        f"/api/v1/hedge/exposicao/recomendacoes?safra_id={safra_id}",
        headers=headers_financeiro
    )
    
    assert response.status_code == 200
    dados = response.json()
    
    regras = [r["id_regra"] for r in dados]
    assert "VENDA_SEM_LASTRO" in regras
    
    venda_lastro = next(r for r in dados if r["id_regra"] == "VENDA_SEM_LASTRO")
    assert venda_lastro["prioridade"] == "CRITICA"
