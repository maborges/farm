"""Integração Balança → Vendas: comercialização solicita pesagem oficial na
estação (venda de carga), e quando a pesagem conclui, o peso oficial é
gravado — sem a Balança conhecer ComercializacaoCommodity."""
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
        "modules": ["CORE"],
        "is_superuser": True,
        "plan_tier": "PROFISSIONAL",
    }
    return svc.create_access_token(claims, expires_delta=timedelta(hours=1))


async def _setup_tenant_e_comercializacao(session, tenant_id: uuid.UUID, user_id: uuid.UUID):
    from financeiro.comercializacao.models import ComercializacaoCommodity
    from sqlalchemy import text

    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, "
            "idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Vendas Balança", "doc": str(tenant_id)[:11]},
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

    commodity_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_commodities (id, tenant_id, sistema, nome, codigo, tipo, unidade_padrao, ativo, "
            "created_at, updated_at) "
            "VALUES (:id, :tenant_id, false, 'Soja Teste Balança', :codigo, 'GRAO', 'SACA_60KG', true, now(), now())"
        ),
        {"id": str(commodity_id), "tenant_id": str(tenant_id), "codigo": f"SOJA-BAL-{uuid.uuid4().hex[:8]}"},
    )

    comprador_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_pessoas (id, tenant_id, tipo, nome_exibicao, base_legal, ativo, tags, "
            "dados_extras, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'PJ', 'Comprador Teste', 'CONTRATO', true, '[]'::jsonb, '{}'::jsonb, now(), now())"
        ),
        {"id": str(comprador_id), "tenant_id": str(tenant_id)},
    )

    com = ComercializacaoCommodity(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        commodity_id=commodity_id,
        comprador_id=comprador_id,
        quantidade=100.0,
        unidade="SACA_60KG",
        preco_unitario=120.0,
        valor_total=12000.0,
        status="CONFIRMADO",
    )
    session.add(com)
    await session.commit()
    await session.refresh(com)
    return com


async def test_comercializacao_solicita_pesagem_e_evento_da_balanca_grava_peso(
    client: httpx.AsyncClient, session
):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    token = _gerar_token(user_id, tenant_id)
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}

    com = await _setup_tenant_e_comercializacao(session, tenant_id, user_id)
    assert com.peso_liquido_kg is None

    resp = await client.post(
        f"/api/v1/financeiro/comercializacoes/{com.id}/solicitar-pesagem-balanca", headers=headers
    )
    assert resp.status_code == 201, resp.text
    ordem_id = resp.json()["ordem_pesagem_id"]

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers)
    ordem = resp.json()
    assert ordem["origem_tipo"] == "VENDA"
    assert ordem["origem_id"] == str(com.id)

    resp = await client.post(
        "/api/v1/balanca/devices",
        json={"nome": "Balança Portaria Vendas", "fazenda_ids": [str(uuid.uuid4())]},
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

    resp = await _pesar("CHEGADA", "18000.000")
    assert resp.json()["results"][0]["status"] == "CREATED"
    resp = await _pesar("SAIDA", "42000.000")
    assert resp.json()["results"][0]["status"] == "CREATED"

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers)
    assert resp.json()["status"] == "CONCLUIDA"
    assert resp.json()["peso_liquido_kg"] == "24000.000"  # |18000 - 42000|

    relay = DomainEventOutboxRelay(session)
    result = await relay.run_once(event_type="balanca.pesagem.concluida", tenant_id=tenant_id)
    assert result.processed == 1
    assert result.failed == 0

    resp = await client.get(f"/api/v1/financeiro/comercializacoes/{com.id}", headers=headers)
    com_atualizada = resp.json()
    assert float(com_atualizada["peso_bruto_kg"]) == 42000.0
    assert float(com_atualizada["peso_tara_kg"]) == 18000.0
    assert float(com_atualizada["peso_liquido_kg"]) == 24000.0
