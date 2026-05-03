import pytest
from httpx import AsyncClient
import uuid
import sqlalchemy as sa
from operacional.models.compras import PedidoCompra

@pytest.mark.asyncio
async def test_analytics_v6_new_tenant(client: AsyncClient, session, headers_operacional: dict):
    # Use a COMPLETELY NEW tenant to avoid ANY existing data
    new_tenant_id = uuid.uuid4()
    new_headers = headers_operacional.copy()
    new_headers["X-Tenant-ID"] = str(new_tenant_id)
    
    # 1. Add sample data for this new tenant
    p1 = PedidoCompra(
        tenant_id=new_tenant_id, 
        fornecedor_nome="Forn_X", 
        item_id=uuid.uuid4(), 
        deposito_id=uuid.uuid4(),
        quantidade=1, 
        unidade="UN", 
        valor_unitario=100.0, 
        valor_total=100.0,
        economia_absoluta=500.0, 
        economia_percentual=20.0, 
        status="ABERTO"
    )
    session.add(p1)
    await session.commit()

    # 2. Call Analytics with the new tenant
    # Note: The service needs to handle the tenant from the header
    response = await client.get("/api/v1/compras/analytics/economia", headers=new_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert float(data["economia_total"]) == 500.0
