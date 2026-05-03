import pytest
from httpx import AsyncClient
import uuid
from datetime import datetime, timezone
from operacional.models.compras import PedidoCompra

@pytest.mark.asyncio
async def test_savings_trend_aggregation_step164(client: AsyncClient, session, headers_operacional: dict):
    # Use an existing tenant and valid foreign keys from the DB
    # Based on manual DB check
    valid_tenant_id = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
    valid_item_id = uuid.UUID("6f3a40ac-be14-4249-b77a-498266ebae57")
    valid_deposito_id = uuid.UUID("ff000001-0000-0000-0000-000000000001")
    
    new_headers = headers_operacional.copy()
    new_headers["X-Tenant-ID"] = str(valid_tenant_id)
    
    # 1. Add sample data for different months
    # We create unique pedido IDs to avoid collisions
    
    # Month 1: 2026-01
    p1 = PedidoCompra(
        id=uuid.uuid4(),
        tenant_id=valid_tenant_id, 
        fornecedor_nome="F1", 
        item_id=valid_item_id, 
        deposito_id=valid_deposito_id,
        quantidade=1, 
        unidade="UN", 
        valor_unitario=100.0, 
        valor_total=100.0,
        economia_absoluta=500.0, 
        economia_percentual=10.0, 
        status="ABERTO",
        created_at=datetime(2026, 1, 15, tzinfo=timezone.utc)
    )
    
    # Month 1: 2026-01 (Another one)
    p2 = PedidoCompra(
        id=uuid.uuid4(),
        tenant_id=valid_tenant_id, 
        fornecedor_nome="F2", 
        item_id=valid_item_id, 
        deposito_id=valid_deposito_id,
        quantidade=1, 
        unidade="UN", 
        valor_unitario=100.0, 
        valor_total=100.0,
        economia_absoluta=300.0, 
        economia_percentual=5.0, 
        status="ABERTO",
        created_at=datetime(2026, 1, 20, tzinfo=timezone.utc)
    )
    
    # Month 2: 2026-02
    p3 = PedidoCompra(
        id=uuid.uuid4(),
        tenant_id=valid_tenant_id, 
        fornecedor_nome="F3", 
        item_id=valid_item_id, 
        deposito_id=valid_deposito_id,
        quantidade=1, 
        unidade="UN", 
        valor_unitario=100.0, 
        valor_total=100.0,
        economia_absoluta=1200.0, 
        economia_percentual=15.0, 
        status="ABERTO",
        created_at=datetime(2026, 2, 10, tzinfo=timezone.utc)
    )
    
    session.add_all([p1, p2, p3])
    await session.commit()

    # 2. Call Time Series endpoint
    response = await client.get("/api/v1/compras/analytics/economia/serie-temporal", headers=new_headers)
    assert response.status_code == 200
    data = response.json()
    
    items = data["items"]
    # Filter for the months we just added (to ignore existing noise in DB)
    jan = [i for i in items if i["periodo"] == "2026-01"]
    feb = [i for i in items if i["periodo"] == "2026-02"]
    
    assert len(jan) == 1
    assert len(feb) == 1
    
    # Values might be higher than our inserts if there was previous data for this tenant
    assert float(jan[0]["economia_total"]) >= 800.0
    assert float(feb[0]["economia_total"]) >= 1200.0
