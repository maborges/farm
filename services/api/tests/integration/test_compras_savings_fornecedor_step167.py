import pytest
from httpx import AsyncClient
import uuid
from datetime import datetime, timezone
from operacional.models.compras import PedidoCompra

@pytest.mark.asyncio
async def test_economia_por_fornecedor_agrupamento(client: AsyncClient, session, headers_operacional: dict):
    """Garante agrupamento correto por fornecedor_nome."""
    valid_tenant_id = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
    valid_item_id = uuid.UUID("cc000001-0000-0000-0000-000000000001")
    valid_deposito_id = uuid.UUID("ff000001-0000-0000-0000-000000000001")

    new_headers = headers_operacional.copy()
    new_headers["X-Tenant-ID"] = str(valid_tenant_id)

    p1 = PedidoCompra(
        id=uuid.uuid4(), tenant_id=valid_tenant_id,
        fornecedor_nome="AgroSup Ltda", item_id=valid_item_id, deposito_id=valid_deposito_id,
        quantidade=1, unidade="UN", valor_unitario=100.0, valor_total=100.0,
        economia_absoluta=600.0, economia_percentual=15.0, status="ABERTO",
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc)
    )
    p2 = PedidoCompra(
        id=uuid.uuid4(), tenant_id=valid_tenant_id,
        fornecedor_nome="AgroSup Ltda", item_id=valid_item_id, deposito_id=valid_deposito_id,
        quantidade=1, unidade="UN", valor_unitario=100.0, valor_total=100.0,
        economia_absoluta=400.0, economia_percentual=10.0, status="ABERTO",
        created_at=datetime(2026, 4, 2, tzinfo=timezone.utc)
    )
    p3 = PedidoCompra(
        id=uuid.uuid4(), tenant_id=valid_tenant_id,
        fornecedor_nome="Campo Verde", item_id=valid_item_id, deposito_id=valid_deposito_id,
        quantidade=1, unidade="UN", valor_unitario=100.0, valor_total=100.0,
        economia_absoluta=200.0, economia_percentual=5.0, status="ABERTO",
        created_at=datetime(2026, 4, 3, tzinfo=timezone.utc)
    )
    session.add_all([p1, p2, p3])
    await session.commit()

    response = await client.get("/api/v1/compras/analytics/economia/por-fornecedor", headers=new_headers)
    assert response.status_code == 200

    items = response.json()["items"]
    assert len(items) >= 2

    agro = next((i for i in items if i["fornecedor_nome"] == "AgroSup Ltda"), None)
    assert agro is not None
    assert abs(agro["economia_total"] - 1000.0) < 1.0
    assert agro["total_pedidos"] == 2


@pytest.mark.asyncio
async def test_economia_por_fornecedor_ordenacao(client: AsyncClient, session, headers_operacional: dict):
    """Garante ordenação decrescente por economia_total."""
    new_headers = headers_operacional.copy()
    new_headers["X-Tenant-ID"] = "aaaaaaaa-0000-0000-0000-000000000001"

    response = await client.get("/api/v1/compras/analytics/economia/por-fornecedor", headers=new_headers)
    assert response.status_code == 200

    items = response.json()["items"]
    if len(items) >= 2:
        for i in range(len(items) - 1):
            assert items[i]["economia_total"] >= items[i + 1]["economia_total"]


@pytest.mark.asyncio
async def test_economia_por_fornecedor_percentual(client: AsyncClient, session, headers_operacional: dict):
    """Garante que percentuais somam ~100%."""
    new_headers = headers_operacional.copy()
    new_headers["X-Tenant-ID"] = "aaaaaaaa-0000-0000-0000-000000000001"

    response = await client.get("/api/v1/compras/analytics/economia/por-fornecedor", headers=new_headers)
    assert response.status_code == 200

    items = response.json()["items"]
    if items:
        total_pct = sum(i["economia_percentual"] for i in items)
        assert abs(total_pct - 100.0) < 1.0


@pytest.mark.asyncio
async def test_economia_por_fornecedor_isolamento_tenant(client: AsyncClient, session, headers_operacional: dict):
    """Garante isolamento por tenant."""
    outro_tenant = uuid.UUID("cccccccc-0000-0000-0000-000000000003")
    valid_item_id = uuid.UUID("cc000001-0000-0000-0000-000000000001")
    valid_deposito_id = uuid.UUID("ff000001-0000-0000-0000-000000000001")

    p_outro = PedidoCompra(
        id=uuid.uuid4(), tenant_id=outro_tenant,
        fornecedor_nome="Fornecedor Invasor", item_id=valid_item_id, deposito_id=valid_deposito_id,
        quantidade=1, unidade="UN", valor_unitario=50.0, valor_total=50.0,
        economia_absoluta=8888.0, economia_percentual=50.0, status="ABERTO",
        created_at=datetime(2026, 4, 5, tzinfo=timezone.utc)
    )
    session.add(p_outro)
    await session.commit()

    response = await client.get("/api/v1/compras/analytics/economia/por-fornecedor", headers=headers_operacional)
    assert response.status_code == 200

    nomes = [i["fornecedor_nome"] for i in response.json()["items"]]
    assert "Fornecedor Invasor" not in nomes
