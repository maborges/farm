import uuid
from datetime import timedelta

import httpx
import pytest
from unittest.mock import MagicMock
from sqlalchemy import text

from core.services.auth_service import AuthService

pytestmark = pytest.mark.asyncio


def _gerar_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    svc = AuthService(MagicMock())
    claims = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "modules": ["CORE"],
        "is_superuser": False,
        "plan_tier": "PROFISSIONAL",
    }
    return svc.create_access_token(claims, expires_delta=timedelta(hours=1))


async def _criar_tenant_com_owner(session, tenant_id: uuid.UUID, user_id: uuid.UUID, nome: str) -> str:
    """Cria tenant + usuário owner (bypassa PERMISSIONS_MAP via TenantUsuario.is_owner)."""
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, storage_limite_mb, "
            "idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now()) ON CONFLICT DO NOTHING"
        ),
        {"id": str(tenant_id), "nome": nome, "doc": str(tenant_id)[:11]},
    )
    await session.execute(
        text(
            "INSERT INTO usuarios (id, email, username, senha_hash, ativo, is_superuser, created_at, updated_at) "
            "VALUES (:id, :email, :username, 'hash', true, false, now(), now()) ON CONFLICT DO NOTHING"
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
    await session.commit()
    return _gerar_token(user_id, tenant_id)


async def test_fluxo_completo_pesagem_manual_e_isolamento_tenant(client: httpx.AsyncClient, session):
    tenant_a_id = uuid.uuid4()
    user_a_id = uuid.uuid4()
    tenant_b_id = uuid.uuid4()
    user_b_id = uuid.uuid4()

    token_a = await _criar_tenant_com_owner(session, tenant_a_id, user_a_id, "Tenant Balança A")
    token_b = await _criar_tenant_com_owner(session, tenant_b_id, user_b_id, "Tenant Balança B")

    headers_a = {"Authorization": f"Bearer {token_a}", "X-Tenant-ID": str(tenant_a_id)}
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Tenant-ID": str(tenant_b_id)}

    fazenda_id = uuid.uuid4()

    # 1) Tenant A cria uma estação de balança
    resp = await client.post(
        "/api/v1/balanca/devices",
        json={"nome": "Balança Portaria", "fazenda_ids": [str(fazenda_id)]},
        headers=headers_a,
    )
    assert resp.status_code == 201, resp.text
    device_data = resp.json()
    activation_code = device_data["activation_code"]

    # 2) Ativação não usa JWT de usuário, e sim o código gerado
    resp = await client.post(
        "/api/v1/balanca/devices/activate",
        json={
            "activation_code": activation_code,
            "pin_hash": "hash-fake-pin",
            "device_fingerprint": f"fp-{uuid.uuid4()}",
        },
    )
    assert resp.status_code == 200, resp.text
    activation_data = resp.json()
    device_token = activation_data["device_token"]
    device_id = activation_data["device_id"]
    assert activation_data["tenant_id"] == str(tenant_a_id)

    # 3) Um módulo cliente (aqui simulado direto via API) solicita pesagem
    resp = await client.post(
        "/api/v1/balanca/ordens",
        json={
            "origem_tipo": "OUTRO",
            "subject_type": "VEICULO",
            "tipo_pesagem": "UNICA",
            "contexto": {"placa": "ABC1D23"},
        },
        headers=headers_a,
    )
    assert resp.status_code == 201, resp.text
    ordem = resp.json()
    ordem_id = ordem["id"]
    assert ordem["status"] == "PENDENTE"

    # 4) Isolamento de tenant: tenant B (sem is_owner em A) não enxerga a ordem
    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers_b)
    assert resp.status_code == 404

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers_a)
    assert resp.status_code == 200

    # 5) Pull traz a ordem pendente para a estação ativada
    resp = await client.get(
        f"/api/v1/balanca/sync/pull?device_id={device_id}",
        headers={"Authorization": f"Bearer {device_token}"},
    )
    assert resp.status_code == 200, resp.text
    pull_data = resp.json()
    assert any(o["id"] == ordem_id for o in pull_data["ordens_pendentes"])

    # 6) Estação registra a pesagem offline e sincroniza (push)
    local_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/balanca/sync/push",
        json={
            "device_id": device_id,
            "items": [
                {
                    "local_id": local_id,
                    "operation": "CREATE",
                    "entity_type": "pesagem",
                    "payload": {
                        "ordem_id": ordem_id,
                        "etapa": "UNICA",
                        "peso_informado_kg": "18500.500",
                        "peso_aferido_kg": "18500.500",
                        "peso_tara_kg": "8000.000",
                        "captured_via": "MANUAL",
                        "placa": "ABC1D23",
                    },
                    "client_created_at": "2026-08-16T10:00:00Z",
                    "client_updated_at": "2026-08-16T10:00:00Z",
                }
            ],
        },
        headers={"Authorization": f"Bearer {device_token}"},
    )
    assert resp.status_code == 200, resp.text
    push_data = resp.json()
    assert push_data["results"][0]["status"] == "CREATED"

    # Reenviar o mesmo local_id deve ser idempotente (mesmo server_id, sem duplicar)
    resp = await client.post(
        "/api/v1/balanca/sync/push",
        json={
            "device_id": device_id,
            "items": [
                {
                    "local_id": local_id,
                    "operation": "CREATE",
                    "entity_type": "pesagem",
                    "payload": {"ordem_id": ordem_id, "etapa": "UNICA", "peso_aferido_kg": "18500.500"},
                    "client_created_at": "2026-08-16T10:00:00Z",
                    "client_updated_at": "2026-08-16T10:00:00Z",
                }
            ],
        },
        headers={"Authorization": f"Bearer {device_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["server_id"] == push_data["results"][0]["server_id"]

    # 7) Ordem de pesagem única é concluída automaticamente, com peso líquido calculado
    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers_a)
    assert resp.status_code == 200
    ordem_final = resp.json()
    assert ordem_final["status"] == "CONCLUIDA"
    assert ordem_final["peso_liquido_kg"] == "10500.500"

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}/pesagens", headers=headers_a)
    assert resp.status_code == 200
    pesagens = resp.json()
    assert len(pesagens) == 1
    assert pesagens[0]["etapa"] == "UNICA"
    assert pesagens[0]["peso_aferido_kg"] == "18500.500"

    # 8) Token de dispositivo não serve para outro device_id (mesmo tenant)
    resp = await client.get(
        f"/api/v1/balanca/sync/pull?device_id={uuid.uuid4()}",
        headers={"Authorization": f"Bearer {device_token}"},
    )
    assert resp.status_code == 403


async def test_pesagem_avulsa_cria_ordem_sombra_e_permite_reconciliacao(
    client: httpx.AsyncClient, session
):
    """Pesagem sem ordem prévia (estação vendida/rodando standalone, ou ordem do
    processo ainda não chegou): a estação cria uma OrdemPesagem 'sombra'
    (origem_tipo=OUTRO) e a pesagem fica disponível para reconciliação depois."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    token = await _criar_tenant_com_owner(session, tenant_id, user_id, "Tenant Avulsa")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}

    resp = await client.post(
        "/api/v1/balanca/devices",
        json={"nome": "Balança Avulsa", "fazenda_ids": [str(uuid.uuid4())]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    activation_code = resp.json()["activation_code"]

    resp = await client.post(
        "/api/v1/balanca/devices/activate",
        json={
            "activation_code": activation_code,
            "pin_hash": "hash-fake-pin",
            "device_fingerprint": f"fp-{uuid.uuid4()}",
        },
    )
    assert resp.status_code == 200, resp.text
    device_token = resp.json()["device_token"]
    device_id = resp.json()["device_id"]

    # Estação pesa sem nenhuma ordem prévia — payload sem ordem_id, mas com
    # subject_type/tipo_pesagem (obrigatórios para a ordem sombra saber o quê pesou).
    local_id = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/balanca/sync/push",
        json={
            "device_id": device_id,
            "items": [
                {
                    "local_id": local_id,
                    "operation": "CREATE",
                    "entity_type": "pesagem",
                    "payload": {
                        "subject_type": "VEICULO",
                        "tipo_pesagem": "UNICA",
                        "etapa": "UNICA",
                        "peso_aferido_kg": "2300.000",
                        "captured_via": "MANUAL",
                        "placa": "XYZ9A87",
                    },
                    "client_created_at": "2026-08-16T10:00:00Z",
                    "client_updated_at": "2026-08-16T10:00:00Z",
                }
            ],
        },
        headers={"Authorization": f"Bearer {device_token}"},
    )
    assert resp.status_code == 200, resp.text
    push_result = resp.json()["results"][0]
    assert push_result["status"] == "CREATED"
    pesagem_id = push_result["server_id"]

    # A ordem sombra aparece na fila de reconciliação
    resp = await client.get("/api/v1/balanca/ordens/pendentes-reconciliacao", headers=headers)
    assert resp.status_code == 200
    pendentes = resp.json()
    assert len(pendentes) == 1
    ordem_sombra_id = pendentes[0]["id"]
    assert pendentes[0]["origem_tipo"] == "OUTRO"
    assert pendentes[0]["origem_id"] is None

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_sombra_id}/pesagens", headers=headers)
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == pesagem_id

    # Reconciliação: associa a pesagem avulsa a uma compra real
    compra_id = uuid.uuid4()
    resp = await client.post(
        f"/api/v1/balanca/ordens/{ordem_sombra_id}/reatribuir",
        json={"origem_tipo": "COMPRA", "origem_id": str(compra_id)},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    ordem_reatribuida = resp.json()
    assert ordem_reatribuida["origem_tipo"] == "COMPRA"
    assert ordem_reatribuida["origem_id"] == str(compra_id)

    # Depois de reconciliada, não aparece mais como pendente
    resp = await client.get("/api/v1/balanca/ordens/pendentes-reconciliacao", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_pesagem_dupla_com_descarga_calcula_liquido_por_etapas(client: httpx.AsyncClient, session):
    """Cenário combinado: colheita com produto/volumes/NF na ordem, e pesagem em
    duas etapas com (des)carregamento no meio — chegada e pós-descarga, cada
    uma com peso informado (declarado) e aferido (balança) separados."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    token = await _criar_tenant_com_owner(session, tenant_id, user_id, "Tenant Dupla Descarga")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}

    resp = await client.post(
        "/api/v1/balanca/devices",
        json={"nome": "Balança Silo", "fazenda_ids": [str(uuid.uuid4())]},
        headers=headers,
    )
    activation_code = resp.json()["activation_code"]
    resp = await client.post(
        "/api/v1/balanca/devices/activate",
        json={"activation_code": activation_code, "pin_hash": "hash", "device_fingerprint": f"fp-{uuid.uuid4()}"},
    )
    device_token = resp.json()["device_token"]
    device_id = resp.json()["device_id"]

    produto_id = uuid.uuid4()
    resp = await client.post(
        "/api/v1/balanca/ordens",
        json={
            "origem_tipo": "COLHEITA",
            "subject_type": "VEICULO",
            "tipo_pesagem": "DUPLA_ENTRADA_DESCARGA",
            "produto_id": str(produto_id),
            "produto_tipo": "COMMODITY",
            "tipo_volume": "GRANEL",
            "quantidade_volumes": "1",
            "numero_documento_fiscal": "NFE-000123",
            "contexto": {"placa": "GRA1N23"},
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    ordem_id = resp.json()["id"]

    async def _pesar(etapa: str, aferido: str, informado: str):
        return await client.post(
            "/api/v1/balanca/sync/push",
            json={
                "device_id": device_id,
                "items": [
                    {
                        "local_id": str(uuid.uuid4()),
                        "operation": "CREATE",
                        "entity_type": "pesagem",
                        "payload": {
                            "ordem_id": ordem_id,
                            "etapa": etapa,
                            "peso_informado_kg": informado,
                            "peso_aferido_kg": aferido,
                            "captured_via": "MANUAL",
                        },
                        "client_created_at": "2026-08-16T10:00:00Z",
                        "client_updated_at": "2026-08-16T10:00:00Z",
                    }
                ],
            },
            headers={"Authorization": f"Bearer {device_token}"},
        )

    resp = await _pesar("CHEGADA", aferido="45000.000", informado="45200.000")
    assert resp.status_code == 200, resp.text
    assert resp.json()["results"][0]["status"] == "CREATED"

    # Ordem ainda não completou o par de etapas esperado
    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers)
    assert resp.json()["status"] == "EM_PESAGEM"

    # Etapa fora do conjunto esperado (SAIDA não é válida para DUPLA_ENTRADA_DESCARGA)
    resp = await _pesar("SAIDA", aferido="30000.000", informado="30000.000")
    assert resp.status_code == 200
    assert resp.json()["results"][0]["status"] == "ERROR"

    resp = await _pesar("POS_DESCARGA", aferido="30500.000", informado="30500.000")
    assert resp.status_code == 200, resp.text
    assert resp.json()["results"][0]["status"] == "CREATED"

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}", headers=headers)
    ordem_final = resp.json()
    assert ordem_final["status"] == "CONCLUIDA"
    assert ordem_final["peso_liquido_kg"] == "14500.000"  # |45000 - 30500|
    assert ordem_final["numero_documento_fiscal"] == "NFE-000123"
    assert ordem_final["produto_id"] == str(produto_id)

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}/pesagens", headers=headers)
    pesagens = {p["etapa"]: p for p in resp.json()}
    assert set(pesagens.keys()) == {"CHEGADA", "POS_DESCARGA"}
    assert pesagens["CHEGADA"]["peso_informado_kg"] == "45200.000"
    assert pesagens["CHEGADA"]["peso_aferido_kg"] == "45000.000"
