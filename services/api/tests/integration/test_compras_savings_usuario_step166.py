import pytest
from httpx import AsyncClient
import uuid
from datetime import datetime, timezone
from sqlalchemy import text
from operacional.models.compras import PedidoCompra

@pytest.mark.asyncio
async def test_economia_por_usuario_agrupamento(client: AsyncClient, session, headers_operacional: dict):
    """Garante agrupamento correto por usuario_solicitante_id."""
    valid_tenant_id = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
    user_a = uuid.UUID("aa000001-0000-0000-0000-000000000001")
    user_b = uuid.UUID("bb000001-0000-0000-0000-000000000001")

    for uid, nome in ((user_a, "usuario_a"), (user_b, "usuario_b")):
        await session.execute(text("""
            INSERT INTO usuarios (id, email, username, ativo, is_superuser, created_at, updated_at)
            VALUES (:id, :email, :username, true, false, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """), {"id": str(uid), "email": f"{nome}@teste.com", "username": nome})

    new_headers = headers_operacional.copy()
    new_headers["X-Tenant-ID"] = str(valid_tenant_id)

    p1 = PedidoCompra(
        id=uuid.uuid4(), tenant_id=valid_tenant_id,
        fornecedor_nome="F1", valor_total=100.0,
        economia_absoluta=800.0, economia_percentual=20.0, status="ABERTO",
        usuario_solicitante_id=user_a,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc)
    )
    p2 = PedidoCompra(
        id=uuid.uuid4(), tenant_id=valid_tenant_id,
        fornecedor_nome="F2", valor_total=100.0,
        economia_absoluta=400.0, economia_percentual=10.0, status="ABERTO",
        usuario_solicitante_id=user_a,
        created_at=datetime(2026, 3, 2, tzinfo=timezone.utc)
    )
    p3 = PedidoCompra(
        id=uuid.uuid4(), tenant_id=valid_tenant_id,
        fornecedor_nome="F3", valor_total=100.0,
        economia_absoluta=200.0, economia_percentual=5.0, status="ABERTO",
        usuario_solicitante_id=user_b,
        created_at=datetime(2026, 3, 3, tzinfo=timezone.utc)
    )
    session.add_all([p1, p2, p3])
    await session.commit()

    response = await client.get("/api/v1/compras/analytics/economia/por-usuario", headers=new_headers)
    assert response.status_code == 200

    data = response.json()
    items = data["items"]
    assert len(items) >= 2

    # user_a deve ter economia_total = 1200 (800 + 400)
    item_a = next((i for i in items if i.get("usuario_id") == str(user_a)), None)
    assert item_a is not None
    assert abs(item_a["economia_total"] - 1200.0) < 1.0
    assert item_a["total_pedidos"] == 2


@pytest.mark.asyncio
async def test_economia_por_usuario_ordenacao(client: AsyncClient, session, headers_operacional: dict):
    """Garante ordenação decrescente por economia_total."""
    valid_tenant_id = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
    new_headers = headers_operacional.copy()
    new_headers["X-Tenant-ID"] = str(valid_tenant_id)

    response = await client.get("/api/v1/compras/analytics/economia/por-usuario", headers=new_headers)
    assert response.status_code == 200

    items = response.json()["items"]
    if len(items) >= 2:
        for i in range(len(items) - 1):
            assert items[i]["economia_total"] >= items[i + 1]["economia_total"]


@pytest.mark.asyncio
async def test_economia_por_usuario_percentual(client: AsyncClient, session, headers_operacional: dict):
    """Garante que percentuais somam ~100% quando há dados."""
    valid_tenant_id = uuid.UUID("aaaaaaaa-0000-0000-0000-000000000001")
    new_headers = headers_operacional.copy()
    new_headers["X-Tenant-ID"] = str(valid_tenant_id)

    response = await client.get("/api/v1/compras/analytics/economia/por-usuario", headers=new_headers)
    assert response.status_code == 200

    items = response.json()["items"]
    if items:
        total_pct = sum(i["economia_percentual"] for i in items)
        assert abs(total_pct - 100.0) < 1.0


@pytest.mark.asyncio
async def test_economia_por_usuario_isolamento_tenant(client: AsyncClient, session, headers_operacional: dict):
    """Garante que dados de outro tenant não aparecem no resultado."""
    outro_tenant = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000002")

    await session.execute(text("""
        INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
        VALUES (:id, 'Tenant Isolamento Usuario', :doc, true, 0, 10240, 'pt-BR', NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {"id": str(outro_tenant), "doc": str(outro_tenant)[:11]})

    p_outro = PedidoCompra(
        id=uuid.uuid4(), tenant_id=outro_tenant,
        fornecedor_nome="Outro", valor_total=50.0,
        economia_absoluta=9999.0, economia_percentual=50.0, status="ABERTO",
        created_at=datetime(2026, 3, 5, tzinfo=timezone.utc)
    )
    session.add(p_outro)
    await session.commit()

    # Headers do tenant principal (aaaaaaaa...)
    response = await client.get("/api/v1/compras/analytics/economia/por-usuario", headers=headers_operacional)
    assert response.status_code == 200
    items = response.json()["items"]
    totais = [i["economia_total"] for i in items]
    assert 9999.0 not in totais
