import pytest
from httpx import AsyncClient
import uuid
from datetime import timedelta
from unittest.mock import MagicMock
from sqlalchemy import text
from operacional.models.compras import PedidoCompra
from core.services.auth_service import AuthService
from tests.integration.helpers import garantir_assinatura

@pytest.mark.asyncio
async def test_analytics_v6_new_tenant(client: AsyncClient, session, headers_operacional: dict):
    # Usa um tenant totalmente novo para garantir isolamento de dados.
    # NOTA: o tenant efetivo da requisição vem do claim `tenant_id` do JWT (ver
    # core/dependencies.py:get_current_tenant), não do header X-Tenant-ID — por
    # isso é preciso gerar um token novo para este tenant, não só trocar o header.
    new_tenant_id = uuid.uuid4()

    await session.execute(text("""
        INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, idioma_padrao, created_at, updated_at)
        VALUES (:id, 'Tenant Analytics Novo', :doc, true, 0, 10240, 'pt-BR', NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """), {"id": str(new_tenant_id), "doc": str(new_tenant_id)[:11]})
    await garantir_assinatura(session, new_tenant_id)

    p1 = PedidoCompra(
        tenant_id=new_tenant_id,
        fornecedor_nome="Forn_X",
        valor_total=100.0,
        economia_absoluta=500.0,
        economia_percentual=20.0,
        status="ABERTO"
    )
    session.add(p1)
    await session.commit()

    novo_token = AuthService(MagicMock()).create_access_token({
        "sub": str(uuid.uuid4()),
        "tenant_id": str(new_tenant_id),
        "modules": ["CORE", "O1_FROTA", "O2_ESTOQUE", "O3_COMPRAS"],
        "fazendas_auth": [{"id": str(uuid.uuid4()), "role": "admin"}],
        "is_superuser": False,
        "plan_tier": "PROFISSIONAL",
    }, expires_delta=timedelta(hours=1))
    new_headers = dict(headers_operacional)
    new_headers["Authorization"] = f"Bearer {novo_token}"
    new_headers["X-Tenant-ID"] = str(new_tenant_id)

    response = await client.get("/api/v1/compras/analytics/economia", headers=new_headers)
    assert response.status_code == 200, response.text
    data = response.json()

    assert float(data["economia_total"]) == 500.0
