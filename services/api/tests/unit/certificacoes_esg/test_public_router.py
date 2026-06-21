import uuid
from datetime import datetime, timezone
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from certificacoes_esg.public_router import router as public_router
from core.database import async_session_maker
from certificacoes_esg.models import PassaporteRastreabilidade, StatusPassaporte

# Use TestClient directly on a mocked app
app = FastAPI()
app.include_router(public_router, prefix="/api/v1/public")
client = TestClient(app)

@pytest.fixture
async def passaporte_publico_fixtures(tenant_id):
    user_id = uuid.uuid4()
    passaportes = []
    async with async_session_maker() as session:
        # Passaporte Rascunho
        p_rascunho = PassaporteRastreabilidade(
            tenant_id=tenant_id,
            created_by=user_id,
            titulo="Passaporte Rascunho",
            status=StatusPassaporte.RASCUNHO,
        )
        session.add(p_rascunho)

        # Passaporte Publicado e Público com Token
        token_valido = uuid.uuid4()
        p_publico = PassaporteRastreabilidade(
            tenant_id=tenant_id,
            created_by=user_id,
            titulo="Passaporte Público",
            status=StatusPassaporte.PUBLICADO,
            publico=True,
            snapshot_json={"test": "data"},
            snapshot_hash="hash_teste",
            publicado_em=datetime.now(timezone.utc),
            public_token=token_valido,
            publicado_publicamente_em=datetime.now(timezone.utc),
        )
        session.add(p_publico)

        # Passaporte Publicado mas privado (publico=False)
        token_invalido = uuid.uuid4()
        p_privado = PassaporteRastreabilidade(
            tenant_id=tenant_id,
            created_by=user_id,
            titulo="Passaporte Privado",
            status=StatusPassaporte.PUBLICADO,
            publico=False,
            snapshot_json={"test": "data"},
            snapshot_hash="hash_teste",
            publicado_em=datetime.now(timezone.utc),
            public_token=token_invalido,
            publicado_publicamente_em=datetime.now(timezone.utc),
        )
        session.add(p_privado)
        
        await session.commit()
        passaportes.append(p_publico)
        passaportes.append(p_rascunho)
        passaportes.append(p_privado)

    return passaportes


@pytest.mark.asyncio
async def test_get_passaporte_publico_sucesso(passaporte_publico_fixtures):
    p_publico = passaporte_publico_fixtures[0]
    # Nenhuma autenticação exigida
    response = client.get(f"/api/v1/public/passaportes/{str(p_publico.public_token)}")
    assert response.status_code == 200
    data = response.json()
    assert data["titulo"] == "Passaporte Público"
    assert "public_token" in data
    assert data["public_token"] == str(p_publico.public_token)
    assert "tenant_id" not in data
    assert "created_by" not in data
    assert "propriedade_id" not in data


@pytest.mark.asyncio
async def test_get_passaporte_publico_privado_falha(passaporte_publico_fixtures):
    p_privado = passaporte_publico_fixtures[2]
    response = client.get(f"/api/v1/public/passaportes/{str(p_privado.public_token)}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_passaporte_publico_not_found():
    token_falso = uuid.uuid4()
    response = client.get(f"/api/v1/public/passaportes/{str(token_falso)}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_passaporte_publico_sanitized_snapshot(passaporte_publico_fixtures):
    """
    Testa se o endpoint público omite corretamente as chaves sensíveis
    de dentro do snapshot_json.
    """
    from services.api.certificacoes_esg.schemas import StatusPassaporte
    from services.api.certificacoes_esg.models import PassaporteRastreabilidade
    
    tenant_id, _, _, _, passaporte_publico = passaporte_publico_fixtures

    # Injeta um snapshot mock com dados sensíveis e limpos
    async with async_session_maker() as session:
        passaporte = await session.get(PassaporteRastreabilidade, passaporte_publico.id)
        passaporte.snapshot_json = {
            "lote": "LOTE-123",
            "volume_kg": 1000,
            "tenant_id": str(tenant_id),
            "user_id_criacao": "user-123",
            "car_propriedade": "SP-1234567",
            "matricula_imovel": "MAT-999"
        }
        session.add(passaporte)
        await session.commit()

    response = client.get(f"/api/v1/public/passaportes/{passaporte_publico.public_token}")
    assert response.status_code == 200
    
    data = response.json()
    assert "snapshot_json" in data
    snapshot = data["snapshot_json"]
    
    # Validações do sanitizer
    assert "lote" in snapshot
    assert "volume_kg" in snapshot
    assert "tenant_id" not in snapshot
    assert "user_id_criacao" not in snapshot
    assert "car_propriedade" not in snapshot
    assert "matricula_imovel" not in snapshot
