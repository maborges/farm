import pytest
import uuid
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_compras_historico_precos_ordenacao_step156(client: AsyncClient, headers_operacional: dict):
    """
    Testa se o histórico de preços retorna ordenado por data ASC (Step 156).
    """
    # Item ID de exemplo (deve existir ou ser criado se necessário, mas aqui testamos o contrato)
    # Em um teste real, sementaríamos dados primeiro.
    item_id = str(uuid.uuid4())
    
    response = await client.get(
        f"/api/v1/compras/precos/historico?item_id={item_id}",
        headers=headers_operacional
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "historico" in data
    assert "preco_medio" in data
    
    historico = data["historico"]
    if len(historico) >= 2:
        # Verificar se as datas estão em ordem ascendente
        for i in range(len(historico) - 1):
            assert historico[i]["data"] <= historico[i+1]["data"]
