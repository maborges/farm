import pytest
import uuid
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_compras_preco_ideal_step157(client: AsyncClient, headers_operacional: dict):
    """
    Testa o endpoint de preço ideal (Step 157).
    """
    # 1. Caso sem histórico suficiente
    item_id_vazio = str(uuid.uuid4())
    response = await client.get(
        f"/api/v1/compras/precos/preco-ideal?item_id={item_id_vazio}",
        headers=headers_operacional
    )
    assert response.status_code == 200
    assert response.json() is None

    # Nota: Em um teste real com DB, sementaríamos dados aqui para testar o cálculo.
    # Como não temos sementes automáticas garantidas neste momento, focamos no contrato.
