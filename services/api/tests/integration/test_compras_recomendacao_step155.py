import pytest
import uuid
from httpx import AsyncClient
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_obter_melhor_fornecedor_step155(client: AsyncClient, headers_operacional: dict):
    # 1. Criar um item
    item_id = str(uuid.uuid4())
    
    # 2. Testar endpoint
    response = await client.get(
        f"/api/v1/compras/precos/melhor-fornecedor?item_id={item_id}",
        headers=headers_operacional
    )
    
    # Se não houver histórico, deve retornar 200 None (ou nulo)
    assert response.status_code == 200
    res_data = response.json()
    
    if res_data:
        assert "fornecedor_nome" in res_data
        assert "score" in res_data
        assert "preco_medio" in res_data
        assert "qtd_compras" in res_data
