import uuid
import httpx
import pytest
from datetime import datetime, timedelta, date

from sqlalchemy import text
from campo.models import DispositivoCampo

pytestmark = pytest.mark.asyncio

async def test_sync_pull_pessoas_operacionais_integration(client: httpx.AsyncClient, session, tenant_id):
    # Setup UPs
    up_autorizada = uuid.uuid4()
    up_nao_autorizada = uuid.uuid4()
    
    await session.execute(
        text(
            "INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'Fazenda Autorizada', true, now(), now()), "
            "       (:id2, :tenant_id, 'Fazenda Nao Autorizada', true, now(), now()) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": str(up_autorizada), "id2": str(up_nao_autorizada), "tenant_id": str(tenant_id)},
    )

    # Criar um papel
    papel_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_tipos_relacionamento (id, tenant_id, codigo, nome, sistema, ativo, cor, icone) "
            "VALUES (:id, :tenant_id, 'TRABALHADOR', 'Trabalhador', false, true, '#6B7280', 'user')"
        ),
        {"id": str(papel_id), "tenant_id": str(tenant_id)},
    )

    # Inserir Pessoa 1 na UP autorizada
    p1 = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_pessoas (id, tenant_id, tipo, nome_exibicao, base_legal, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'PF', 'Pedro Autorizado', 'CONTRATO', true, now(), now())"
        ),
        {"id": str(p1), "tenant_id": str(tenant_id)}
    )
    await session.execute(
        text(
            "INSERT INTO cadastros_pessoa_relacionamentos (id, pessoa_id, tipo_id, unidade_produtiva_id) "
            "VALUES (:id, :pessoa_id, :tipo_id, :up_id)"
        ),
        {"id": str(uuid.uuid4()), "pessoa_id": str(p1), "tipo_id": str(papel_id), "up_id": str(up_autorizada)}
    )

    # Inserir Pessoa 2 na UP NAO autorizada
    p2 = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO cadastros_pessoas (id, tenant_id, tipo, nome_exibicao, base_legal, ativo, created_at, updated_at) "
            "VALUES (:id, :tenant_id, 'PF', 'Lucas Nao Autorizado', 'CONTRATO', true, now(), now())"
        ),
        {"id": str(p2), "tenant_id": str(tenant_id)}
    )
    await session.execute(
        text(
            "INSERT INTO cadastros_pessoa_relacionamentos (id, pessoa_id, tipo_id, unidade_produtiva_id) "
            "VALUES (:id, :pessoa_id, :tipo_id, :up_id)"
        ),
        {"id": str(uuid.uuid4()), "pessoa_id": str(p2), "tipo_id": str(papel_id), "up_id": str(up_nao_autorizada)}
    )

    # Inserir usuário
    user_id = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO usuarios (id, email, username, nome_completo, senha_hash, ativo, is_superuser, created_at, updated_at) "
            "VALUES (:id, :email, :username, 'User Integ PWA', 'hash', true, false, now(), now())"
        ),
        {"id": str(user_id), "email": f"{user_id}@test.com", "username": f"user_{user_id}"}
    )

    # Criar dispositivo autorizado apenas na UP 1
    device_id = uuid.uuid4()
    device = DispositivoCampo(
        id=device_id,
        tenant_id=tenant_id,
        user_id=user_id,
        nome="Device Integracao",
        fazenda_ids=[up_autorizada],
        modulos=["agricola"],
        status="ATIVO",
        expires_at=datetime.utcnow() + timedelta(days=1),
    )
    session.add(device)
    await session.commit()

    # Em vez de chamar a rota full (que requer token especifico do device), vamos usar a test auth_headers pra simular
    # Mocks ou injeções seriam necessarias porque a rota usa _get_device_from_token via JWT
    # Para simplificar na camada de roteador, geramos um token real de dispositivo usando o JWT helper
    from campo.service import _make_device_jwt
    device_token = _make_device_jwt(device, "Teste", None)

    response = await client.get(
        f"/api/v1/sync/pull?device_id={device_id}",
        headers={"Authorization": f"Bearer {device_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    pessoas_operacionais = data.get("pessoas_operacionais", [])
    
    assert len(pessoas_operacionais) == 1
    assert pessoas_operacionais[0]["pessoa_id"] == str(p1)
    assert pessoas_operacionais[0]["nome_exibicao"] == "Pedro Autorizado"
    assert pessoas_operacionais[0]["unidade_produtiva_id"] == str(up_autorizada)
    assert "TRABALHADOR" in pessoas_operacionais[0]["papeis"]
