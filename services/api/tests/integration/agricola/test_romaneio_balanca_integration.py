"""Integração Balança → Colheita: romaneio solicita pesagem oficial na estação,
e quando a pesagem conclui (evento de domínio via outbox), o romaneio é
atualizado com o peso medido — sem a Balança conhecer RomaneioColheita."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

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
        "modules": ["CORE", "A5_COLHEITA"],
        "is_superuser": True,  # simplifica RBAC — foco no vínculo balança↔colheita
        "plan_tier": "PROFISSIONAL",
    }
    return svc.create_access_token(claims, expires_delta=timedelta(hours=1))


async def _setup_tenant_safra_talhao_romaneio(session, tenant_id: uuid.UUID, user_id: uuid.UUID):
    from core.models.unidade_produtiva import UnidadeProdutiva
    from core.cadastros.propriedades.models import AreaRural
    from agricola.safras.models import Safra
    from agricola.romaneios.models import RomaneioColheita
    from sqlalchemy import text

    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, "
            "idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": "Tenant Colheita Balança", "doc": str(tenant_id)[:11]},
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

    up = UnidadeProdutiva(id=uuid.uuid4(), tenant_id=tenant_id, nome="Fazenda Teste")
    session.add(up)
    await session.flush()

    talhao = AreaRural(id=uuid.uuid4(), tenant_id=tenant_id, unidade_produtiva_id=up.id, tipo="TALHAO", nome="Talhão 1")
    session.add(talhao)
    await session.flush()

    safra = Safra(id=uuid.uuid4(), tenant_id=tenant_id, ano_safra="2026")
    session.add(safra)
    await session.flush()

    romaneio = RomaneioColheita(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        safra_id=safra.id,
        talhao_id=talhao.id,
        data_colheita=date.today(),
        numero_romaneio="ROM-BALANCA-001",
        peso_bruto_kg=1000.0,  # provisório — será substituído pelo peso oficial da balança
        tara_kg=0,
    )
    session.add(romaneio)
    await session.commit()
    await session.refresh(romaneio)
    return romaneio


async def test_romaneio_solicita_pesagem_e_evento_da_balanca_atualiza_peso(
    client: httpx.AsyncClient, session
):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    token = _gerar_token(user_id, tenant_id)
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}

    romaneio = await _setup_tenant_safra_talhao_romaneio(session, tenant_id, user_id)

    # 1) Romaneio solicita pesagem oficial na Balança
    resp = await client.post(
        f"/api/v1/romaneios/{romaneio.id}/solicitar-pesagem-balanca",
        json={"subject_type": "VEICULO", "tipo_pesagem": "DUPLA", "placa": "COL1H23"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    ordem_id = resp.json()["ordem_pesagem_id"]
    assert resp.json()["status"] == "PENDENTE"

    # A ordem foi criada com origem_tipo=COLHEITA apontando pro romaneio (desacoplado)
    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers)
    assert resp.status_code == 200
    ordem = resp.json()
    assert ordem["origem_tipo"] == "COLHEITA"
    assert ordem["origem_id"] == str(romaneio.id)
    assert ordem["tipo_pesagem"] == "DUPLA"

    # 2) Estação de balança pesa (chegada + saída) via sync push
    resp = await client.post(
        "/api/v1/balanca/devices",
        json={"nome": "Balança Colheita", "fazenda_ids": [str(uuid.uuid4())]},
        headers=headers,
    )
    activation_code = resp.json()["activation_code"]
    resp = await client.post(
        "/api/v1/balanca/devices/activate",
        json={"activation_code": activation_code, "pin_hash": "hash", "device_fingerprint": f"fp-{uuid.uuid4()}"},
    )
    device_id = resp.json()["device_id"]
    device_token = resp.json()["device_token"]
    device_headers = {"Authorization": f"Bearer {device_token}"}

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
                        "client_created_at": "2026-08-16T10:00:00Z",
                        "client_updated_at": "2026-08-16T10:00:00Z",
                    }
                ],
            },
            headers=device_headers,
        )

    resp = await _pesar("CHEGADA", "38500.000")
    assert resp.json()["results"][0]["status"] == "CREATED"
    resp = await _pesar("SAIDA", "16200.000")
    assert resp.json()["results"][0]["status"] == "CREATED"

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers)
    ordem_concluida = resp.json()
    assert ordem_concluida["status"] == "CONCLUIDA"
    assert ordem_concluida["peso_liquido_kg"] == "22300.000"  # |38500 - 16200|

    # 3) Romaneio ainda está com o peso provisório — o evento está na outbox, não processado ainda
    resp = await client.get(f"/api/v1/romaneios/{romaneio.id}", headers=headers)
    assert float(resp.json()["peso_bruto_kg"]) == 1000.0

    # 4) Processa a outbox (equivalente a rodar o worker uma vez) — dispara o subscriber
    relay = DomainEventOutboxRelay(session)
    result = await relay.run_once(event_type="balanca.pesagem.concluida", tenant_id=tenant_id)
    assert result.processed == 1
    assert result.failed == 0

    # 5) Romaneio agora reflete o peso oficial medido na balança (bruto=maior, tara=menor)
    resp = await client.get(f"/api/v1/romaneios/{romaneio.id}", headers=headers)
    romaneio_atualizado = resp.json()
    assert float(romaneio_atualizado["peso_bruto_kg"]) == 38500.0
    assert float(romaneio_atualizado["tara_kg"]) == 16200.0
    assert float(romaneio_atualizado["peso_liquido_kg"]) == 22300.0
