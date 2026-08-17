import uuid
from datetime import timedelta

import httpx
import pytest
from unittest.mock import MagicMock
from sqlalchemy import text

from core.services.auth_service import AuthService, hash_password

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


async def test_sync_pull_traz_animais_da_fazenda_do_dispositivo_para_pesagem_de_animal(
    client: httpx.AsyncClient, session
):
    """Pull da estação deve incluir animais ATIVOS da(s) fazenda(s) vinculada(s) ao
    dispositivo, para autocomplete offline de brinco/SISBOV — sem a Balança importar
    o model de pecuária (SQL cru, ver comentário em SyncService.pull)."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    token = await _criar_tenant_com_owner(session, tenant_id, user_id, "Tenant Balança Pecuária")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}

    fazenda_id = uuid.uuid4()
    outra_fazenda_id = uuid.uuid4()

    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, tipo_propriedade, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Fazenda Teste Balança', 'fazenda', true, now(), now())"
        ),
        {"id": str(fazenda_id), "tenant_id": str(tenant_id)},
    )
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, tipo_propriedade, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Outra Fazenda', 'fazenda', true, now(), now())"
        ),
        {"id": str(outra_fazenda_id), "tenant_id": str(tenant_id)},
    )

    animal_ativo_id = uuid.uuid4()
    animal_inativo_id = uuid.uuid4()
    animal_outra_fazenda_id = uuid.uuid4()
    for animal_id, brinco, status, up_id in (
        (animal_ativo_id, "BR-001", "ATIVO", fazenda_id),
        (animal_inativo_id, "BR-002", "VENDIDO", fazenda_id),
        (animal_outra_fazenda_id, "BR-003", "ATIVO", outra_fazenda_id),
    ):
        await session.execute(
            text(
                "INSERT INTO pec_animais (id, tenant_id, unidade_produtiva_id, numero_brinco, especie, "
                "categoria, sexo, data_entrada, status, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :up_id, :brinco, 'BOVINO', 'BOI', 'M', CURRENT_DATE, :status, now(), now())"
            ),
            {
                "id": str(animal_id),
                "tenant_id": str(tenant_id),
                "up_id": str(up_id),
                "brinco": brinco,
                "status": status,
            },
        )
    await session.commit()

    resp = await client.post(
        "/api/v1/balanca/devices",
        json={"nome": "Balança Curral", "fazenda_ids": [str(fazenda_id)]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    activation_code = resp.json()["activation_code"]
    resp = await client.post(
        "/api/v1/balanca/devices/activate",
        json={"activation_code": activation_code, "pin_hash": "hash", "device_fingerprint": f"fp-{uuid.uuid4()}"},
    )
    device_id = resp.json()["device_id"]
    device_token = resp.json()["device_token"]

    resp = await client.get(
        f"/api/v1/balanca/sync/pull?device_id={device_id}",
        headers={"Authorization": f"Bearer {device_token}"},
    )
    assert resp.status_code == 200, resp.text
    animais = resp.json()["animais"]
    brincos = {a["numero_brinco"] for a in animais}

    assert "BR-001" in brincos
    assert "BR-002" not in brincos  # status VENDIDO não entra
    assert "BR-003" not in brincos  # fazenda não vinculada ao dispositivo

    ativo = next(a for a in animais if a["numero_brinco"] == "BR-001")
    assert ativo["id"] == str(animal_ativo_id)
    assert ativo["categoria"] == "BOI"
    assert ativo["unidade_produtiva_id"] == str(fazenda_id)

    # Round-trip: pesagem enviada com animal_id chega ao registro final
    resp = await client.post(
        "/api/v1/balanca/ordens",
        json={
            "origem_tipo": "PECUARIA",
            "subject_type": "ANIMAL",
            "tipo_pesagem": "UNICA",
            "contexto": {"numero_brinco": "BR-001"},
        },
        headers=headers,
    )
    ordem_id = resp.json()["id"]

    resp = await client.post(
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
                        "etapa": "UNICA",
                        "peso_aferido_kg": "450.000",
                        "animal_id": str(animal_ativo_id),
                    },
                    "client_created_at": "2026-08-17T10:00:00Z",
                    "client_updated_at": "2026-08-17T10:00:00Z",
                }
            ],
        },
        headers={"Authorization": f"Bearer {device_token}"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/api/v1/balanca/ordens/{ordem_id}/pesagens", headers=headers)
    pesagens = resp.json()
    assert pesagens[0]["animal_id"] == str(animal_ativo_id)


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


async def test_login_operador_por_pin_pessoal(client: httpx.AsyncClient, session):
    """Operador se autentica na estação por PIN pessoal (não o PIN da estação),
    permitindo rastrear quem pesou (Pesagem.operador_pessoa_id)."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    token = await _criar_tenant_com_owner(session, tenant_id, user_id, "Tenant Operador")
    headers = {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}

    resp = await client.post(
        "/api/v1/balanca/devices",
        json={"nome": "Balança Operador", "fazenda_ids": [str(uuid.uuid4())]},
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

    pessoa_id = uuid.uuid4()
    resp = await client.post(
        "/api/v1/balanca/operadores",
        json={"pessoa_id": str(pessoa_id), "nome_exibicao": "João Operador", "pin_hash": hash_password("4321")},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    operador_id = resp.json()["id"]

    # Sem token de dispositivo, endpoint da estação rejeita
    resp = await client.get(f"/api/v1/balanca/operadores/ativos?device_id={device_id}")
    assert resp.status_code == 401

    # Estação vê o operador cadastrado no seletor (sem PIN exposto)
    resp = await client.get(f"/api/v1/balanca/operadores/ativos?device_id={device_id}", headers=device_headers)
    assert resp.status_code == 200
    ativos = resp.json()
    assert len(ativos) == 1
    assert ativos[0]["id"] == operador_id
    assert "pin_hash" not in ativos[0]

    # PIN errado é rejeitado
    resp = await client.post(
        f"/api/v1/balanca/operadores/login?device_id={device_id}",
        json={"operador_id": operador_id, "pin": "0000"},
        headers=device_headers,
    )
    assert resp.status_code == 401

    # PIN correto autentica o operador
    resp = await client.post(
        f"/api/v1/balanca/operadores/login?device_id={device_id}",
        json={"operador_id": operador_id, "pin": "4321"},
        headers=device_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["nome_exibicao"] == "João Operador"
    assert resp.json()["pessoa_id"] == str(pessoa_id)

    # Revogado não consegue mais logar nem aparece no seletor
    resp = await client.post(f"/api/v1/balanca/operadores/{operador_id}/revogar", headers=headers)
    assert resp.status_code == 200
    resp = await client.get(f"/api/v1/balanca/operadores/ativos?device_id={device_id}", headers=device_headers)
    assert resp.json() == []
    resp = await client.post(
        f"/api/v1/balanca/operadores/login?device_id={device_id}",
        json={"operador_id": operador_id, "pin": "4321"},
        headers=device_headers,
    )
    assert resp.status_code == 401
