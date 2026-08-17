"""Integração Balança → Compras: pedido solicita pesagem oficial na estação
(entrada de carga — insumo ou produto de outro produtor), e quando a pesagem
conclui, o peso oficial é gravado no pedido — sem a Balança conhecer
PedidoCompra."""
from __future__ import annotations

import uuid
from datetime import timedelta

import httpx
import pytest
from unittest.mock import MagicMock

from core.services.auth_service import AuthService
from events.outbox_relay import DomainEventOutboxRelay

pytestmark = pytest.mark.asyncio


def _gerar_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    svc = AuthService(MagicMock())
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "modules": ["CORE", "O3_COMPRAS"],
        "is_superuser": True,
        "plan_tier": "PROFISSIONAL",
    }
    return svc.create_access_token(claims, expires_delta=timedelta(hours=1))


async def _setup_tenant_e_pedido(session, tenant_id: uuid.UUID, user_id: uuid.UUID):
    from operacional.models.compras import PedidoCompra
    from sqlalchemy import text

    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, "
            "idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Compras Balança", "doc": str(tenant_id)[:11]},
    )
    await session.execute(
        text(
            "INSERT INTO usuarios (id, email, username, senha_hash, ativo, is_superuser, created_at, updated_at) "
            "VALUES (:id, :email, :username, 'hash', true, true, now(), now()) ON CONFLICT DO NOTHING"
        ),
        {"id": str(user_id), "email": f"{user_id}@teste.com", "username": f"user_{user_id}"},
    )
    await session.execute(
        text(
            "INSERT INTO tenant_usuarios (id, tenant_id, usuario_id, is_owner, status, created_at) "
            "VALUES (:id, :tenant_id, :user_id, true, 'ATIVO', now()) ON CONFLICT DO NOTHING"
        ),
        {"id": str(uuid.uuid4()), "tenant_id": str(tenant_id), "user_id": str(user_id)},
    )

    pedido = PedidoCompra(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        fornecedor_nome="Produtor Vizinho Ltda",
        valor_total=0.0,
        status="ABERTO",
    )
    session.add(pedido)
    await session.commit()
    await session.refresh(pedido)
    return pedido


async def test_pedido_solicita_pesagem_e_evento_da_balanca_grava_peso(client: httpx.AsyncClient, session):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    token = _gerar_token(user_id, tenant_id)
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}

    pedido = await _setup_tenant_e_pedido(session, tenant_id, user_id)
    assert pedido.peso_liquido_kg is None

    resp = await client.post(
        f"/api/v1/compras/pedidos/{pedido.id}/solicitar-pesagem-balanca", headers=headers
    )
    assert resp.status_code == 201, resp.text
    ordem_id = resp.json()["ordem_pesagem_id"]

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers)
    ordem = resp.json()
    assert ordem["origem_tipo"] == "COMPRA"
    assert ordem["origem_id"] == str(pedido.id)
    assert ordem["tipo_pesagem"] == "DUPLA"

    resp = await client.post(
        "/api/v1/balanca/devices",
        json={"nome": "Balança Portaria Compras", "fazenda_ids": [str(uuid.uuid4())]},
        headers=headers,
    )
    activation_code = resp.json()["activation_code"]
    resp = await client.post(
        "/api/v1/balanca/devices/activate",
        json={"activation_code": activation_code, "pin_hash": "hash", "device_fingerprint": f"fp-{uuid.uuid4()}"},
    )
    device_id = resp.json()["device_id"]
    device_token = resp.json()["device_token"]

    async def _pesar(etapa: str, aferido: str):
        return await client.post(
            "/api/v1/balanca/sync/push",
            json={
                "device_id": device_id,
                "items": [
                    {
                        "local_id": str(uuid.uuid4()),
                        "operation": "CREATE",
                        "entity_type": "pesagem",
                        "payload": {"ordem_id": ordem_id, "etapa": etapa, "peso_aferido_kg": aferido},
                        "client_created_at": "2026-08-17T10:00:00Z",
                        "client_updated_at": "2026-08-17T10:00:00Z",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {device_token}"},
        )

    resp = await _pesar("CHEGADA", "24000.000")
    assert resp.json()["results"][0]["status"] == "CREATED"
    resp = await _pesar("SAIDA", "9500.000")
    assert resp.json()["results"][0]["status"] == "CREATED"

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers)
    assert resp.json()["status"] == "CONCLUIDA"
    assert resp.json()["peso_liquido_kg"] == "14500.000"  # |24000 - 9500|

    relay = DomainEventOutboxRelay(session)
    result = await relay.run_once(event_type="balanca.pesagem.concluida", tenant_id=tenant_id)
    assert result.processed == 1
    assert result.failed == 0

    resp = await client.get(f"/api/v1/compras/pedidos/{pedido.id}", headers=headers)
    pedido_atualizado = resp.json()
    assert float(pedido_atualizado["peso_bruto_kg"]) == 24000.0
    assert float(pedido_atualizado["peso_tara_kg"]) == 9500.0
    assert float(pedido_atualizado["peso_liquido_kg"]) == 14500.0
