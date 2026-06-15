import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from core.services.auth_service import AuthService
from unittest.mock import MagicMock

from tests.integration.conftest import TENANT_ID


@pytest.mark.asyncio
async def test_qualidade_rbac(client: AsyncClient, session):
    user_id = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO usuarios (id, email, username, nome_completo, senha_hash, ativo, is_superuser, created_at, updated_at)
            VALUES (:id, :email, :username, :nome_completo, :senha_hash, true, false, now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(user_id),
            "email": f"qualidade-rbac-{user_id.hex[:8]}@teste.local",
            "username": f"qualidade_rbac_{user_id.hex[:8]}",
            "nome_completo": "Usuario Qualidade RBAC",
            "senha_hash": "hash",
        },
    )
    await session.execute(
        text(
            """
            INSERT INTO tenant_usuarios (id, tenant_id, usuario_id, is_owner, status, created_at)
            VALUES (:id, :tenant_id, :usuario_id, false, 'ATIVO', now())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(uuid.uuid4()),
            "tenant_id": str(TENANT_ID),
            "usuario_id": str(user_id),
        },
    )
    await session.commit()

    svc = AuthService(MagicMock())
    token = svc.create_access_token(
        {
            "sub": str(user_id),
            "tenant_id": str(TENANT_ID),
            "modules": ["CORE"],
            "fazendas_auth": [{"id": str(uuid.uuid4()), "role": "viewer"}],
            "is_superuser": False,
            "plan_tier": "PROFISSIONAL",
        }
    )
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.get("/api/v1/qualidade/protocolos", headers=headers)
    assert res.status_code == 403

@pytest.mark.asyncio
async def test_invalid_criteria_types(client: AsyncClient, token_admin: str):
    headers = {"Authorization": f"Bearer {token_admin}"}
    
    # Create Protocol
    proto_payload = {
        "nome": "Proto Limites",
        "ativo": True,
        "criterios": [
            {
                "nome": "Umidade",
                "tipo_dado": "NUMERIC",
                "min_aceitavel": 10.0,
                "max_aceitavel": 14.0
            },
            {
                "nome": "Aparencia",
                "tipo_dado": "ENUM"
            }
        ]
    }
    res_proto = await client.post("/api/v1/qualidade/protocolos", json=proto_payload, headers=headers)
    assert res_proto.status_code == 201
    proto_id = res_proto.json()["id"]
    crit_umidade = next(c["id"] for c in res_proto.json()["criterios"] if c["nome"] == "Umidade")
    crit_aparencia = next(c["id"] for c in res_proto.json()["criterios"] if c["nome"] == "Aparencia")
    
    # Fail 1: Below min
    res1 = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": proto_id,
        "resultados": [{"criterio_id": crit_umidade, "valor_numerico": 9.0}]
    }, headers=headers)
    assert res1.status_code == 400
    assert "menor que o mínimo" in res1.json()["detail"]
    
    # Fail 2: ENUM sem valor_texto
    res2 = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": proto_id,
        "resultados": [{"criterio_id": crit_aparencia, "valor_numerico": 1}]
    }, headers=headers)
    assert res2.status_code == 400
    assert "requer um valor_texto" in res2.json()["detail"]

@pytest.mark.asyncio
async def test_duplicate_criteria_rejected(client: AsyncClient, token_admin: str):
    headers = {"Authorization": f"Bearer {token_admin}"}
    proto_payload = {
        "nome": "Proto Dup",
        "ativo": True,
        "criterios": [{"nome": "Crit1", "tipo_dado": "NUMERIC"}]
    }
    res_proto = await client.post("/api/v1/qualidade/protocolos", json=proto_payload, headers=headers)
    proto_id = res_proto.json()["id"]
    crit1 = res_proto.json()["criterios"][0]["id"]
    
    res_laudo = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": proto_id,
        "resultados": [
            {"criterio_id": crit1, "valor_numerico": 10},
            {"criterio_id": crit1, "valor_numerico": 12}
        ]
    }, headers=headers)
    assert res_laudo.status_code == 400
    assert "duplicado no laudo" in res_laudo.json()["detail"]

@pytest.mark.asyncio
async def test_inactive_protocol_rejected(client: AsyncClient, token_admin: str):
    headers = {"Authorization": f"Bearer {token_admin}"}
    proto_payload = {
        "nome": "Proto Inativo",
        "ativo": False,
        "criterios": [{"nome": "Crit1", "tipo_dado": "NUMERIC"}]
    }
    res_proto = await client.post("/api/v1/qualidade/protocolos", json=proto_payload, headers=headers)
    proto_id = res_proto.json()["id"]
    
    res_laudo = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": proto_id,
        "resultados": []
    }, headers=headers)
    assert res_laudo.status_code == 400
    assert "inativo" in res_laudo.json()["detail"]

@pytest.mark.asyncio
async def test_laudo_status_flow(client: AsyncClient, token_admin: str):
    headers = {"Authorization": f"Bearer {token_admin}"}
    proto_payload = {"nome": "Proto Flow", "ativo": True, "criterios": []}
    res_proto = await client.post("/api/v1/qualidade/protocolos", json=proto_payload, headers=headers)
    proto_id = res_proto.json()["id"]
    
    res_laudo = await client.post("/api/v1/qualidade/laudos", json={
        "protocolo_id": proto_id,
        "status": "RASCUNHO",
        "resultados": []
    }, headers=headers)
    laudo_id = res_laudo.json()["id"]
    
    # Update status to APROVADO
    res_patch = await client.patch(f"/api/v1/qualidade/laudos/{laudo_id}/status", json={
        "status": "APROVADO"
    }, headers=headers)
    assert res_patch.status_code == 200
    assert res_patch.json()["status"] == "APROVADO"
    
    # Try updating again, should fail
    res_patch_fail = await client.patch(f"/api/v1/qualidade/laudos/{laudo_id}/status", json={
        "status": "REJEITADO"
    }, headers=headers)
    assert res_patch_fail.status_code == 400
    assert "RASCUNHO" in res_patch_fail.json()["detail"]
