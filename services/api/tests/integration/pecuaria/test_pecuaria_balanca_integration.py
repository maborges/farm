"""Integração Balança → Pecuária: animal solicita pesagem oficial na estação,
e quando a pesagem conclui (evento de domínio via outbox), um EventoAnimal(tipo=
PESAGEM) é criado e Animal.peso_atual_kg atualizado — sem a Balança conhecer
Animal/EventoAnimal."""
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
        "modules": ["CORE", "P1_REBANHO"],
        "is_superuser": True,
        "plan_tier": "PROFISSIONAL",
    }
    return svc.create_access_token(claims, expires_delta=timedelta(hours=1))


async def _setup_tenant_e_animal(session, tenant_id: uuid.UUID, user_id: uuid.UUID):
    from core.models.unidade_produtiva import UnidadeProdutiva
    from pecuaria.animal.models import Animal
    from sqlalchemy import text

    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, "
            "idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Pecuária Balança", "doc": str(tenant_id)[:11]},
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

    up = UnidadeProdutiva(id=uuid.uuid4(), tenant_id=tenant_id, nome="Fazenda Pecuária Teste")
    session.add(up)
    await session.flush()

    animal = Animal(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        unidade_produtiva_id=up.id,
        especie="BOVINO",
        categoria="BOI",
        sexo="MACHO",
        numero_brinco="BAL-0001",
        peso_atual_kg=None,
    )
    session.add(animal)
    await session.commit()
    await session.refresh(animal)
    return animal


async def test_animal_solicita_pesagem_e_evento_da_balanca_registra_evento(
    client: httpx.AsyncClient, session
):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    token = _gerar_token(user_id, tenant_id)
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}

    animal = await _setup_tenant_e_animal(session, tenant_id, user_id)
    assert animal.peso_atual_kg is None

    # 1) Solicita pesagem oficial na Balança pro animal
    resp = await client.post(
        f"/api/v1/pecuaria/animais/{animal.id}/pesagens/solicitar-balanca", headers=headers
    )
    assert resp.status_code == 201, resp.text
    ordem_id = resp.json()["ordem_pesagem_id"]

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers)
    ordem = resp.json()
    assert ordem["origem_tipo"] == "PECUARIA"
    assert ordem["origem_id"] == str(animal.id)
    assert ordem["subject_type"] == "ANIMAL"
    assert ordem["tipo_pesagem"] == "UNICA"

    # 2) Estação pesa o animal (balança de curral, pesagem única)
    resp = await client.post(
        "/api/v1/balanca/devices",
        json={"nome": "Balança Curral", "fazenda_ids": [str(uuid.uuid4())]},
        headers=headers,
    )
    activation_code = resp.json()["activation_code"]
    resp = await client.post(
        "/api/v1/balanca/devices/activate",
        json={"activation_code": activation_code, "pin_hash": "hash", "device_fingerprint": f"fp-{uuid.uuid4()}"},
    )
    device_id = resp.json()["device_id"]
    device_token = resp.json()["device_token"]

    resp = await client.post(
        "/api/v1/balanca/sync/push",
        json={
            "device_id": device_id,
            "items": [
                {
                    "local_id": str(uuid.uuid4()),
                    "operation": "CREATE",
                    "entity_type": "pesagem",
                    "payload": {"ordem_id": ordem_id, "etapa": "UNICA", "peso_aferido_kg": "412.500"},
                    "client_created_at": "2026-08-16T10:00:00Z",
                    "client_updated_at": "2026-08-16T10:00:00Z",
                }
            ],
        },
        headers={"Authorization": f"Bearer {device_token}"},
    )
    assert resp.json()["results"][0]["status"] == "CREATED"

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers)
    ordem_concluida = resp.json()
    assert ordem_concluida["status"] == "CONCLUIDA"
    assert ordem_concluida["peso_liquido_kg"] == "412.500"

    # 3) Processa a outbox — dispara o subscriber de pecuária
    relay = DomainEventOutboxRelay(session)
    result = await relay.run_once(event_type="balanca.pesagem.concluida", tenant_id=tenant_id)
    assert result.processed == 1
    assert result.failed == 0

    # 4) Animal e histórico de pesagens refletem o peso oficial
    resp = await client.get(f"/api/v1/pecuaria/animais/{animal.id}", headers=headers)
    assert float(resp.json()["peso_atual_kg"]) == 412.5

    resp = await client.get(f"/api/v1/pecuaria/animais/{animal.id}/pesagens", headers=headers)
    pesagens = resp.json()
    assert len(pesagens) == 1
    assert float(pesagens[0]["peso_kg"]) == 412.5
