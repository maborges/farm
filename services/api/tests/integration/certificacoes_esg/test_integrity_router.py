import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from certificacoes_esg import public_router as public_router_module

def _build_public_client(session):
    app = FastAPI()
    app.include_router(public_router_module.router, prefix="/api/v1/public")
    app.dependency_overrides[public_router_module.get_db] = lambda: session
    return TestClient(app)

@pytest.fixture
def session():
    sess = AsyncMock()
    return sess

@pytest.fixture
def client(session):
    client = _build_public_client(session)
    yield client

def test_verificar_integridade_passaporte_valido(client, session):
    token = uuid.uuid4()
    
    with patch("certificacoes_esg.public_router.CertificacoesESGPublicService") as service_cls:
        service = service_cls.return_value
        service.verificar_integridade_passaporte = AsyncMock(return_value={
            "integridade": "VALIDA",
            "algoritmo": "SHA256",
            "hash": "somehash",
            "versao": 1,
            "publicado_em": "2024-01-01T00:00:00Z"
        })

        response = client.get(f"/api/v1/public/passaportes/{token}/verify")
        assert response.status_code == 200
        data = response.json()
        assert data["integridade"] == "VALIDA"
        assert data["algoritmo"] == "SHA256"
        assert data["hash"] == "somehash"
        service.verificar_integridade_passaporte.assert_awaited_once_with(token)

def test_verificar_integridade_passaporte_invalido(client, session):
    token = uuid.uuid4()
    
    with patch("certificacoes_esg.public_router.CertificacoesESGPublicService") as service_cls:
        service = service_cls.return_value
        service.verificar_integridade_passaporte = AsyncMock(return_value={
            "integridade": "INVALIDA"
        })

        response = client.get(f"/api/v1/public/passaportes/{token}/verify")
        assert response.status_code == 200
        data = response.json()
        assert data["integridade"] == "INVALIDA"
        assert "hash" not in data or data["hash"] is None
        service.verificar_integridade_passaporte.assert_awaited_once_with(token)

def test_verificar_integridade_token_inexistente(client, session):
    # This also exercises the case where the service returns INVALIDA because passaporte is not found
    token = uuid.uuid4()
    
    with patch("certificacoes_esg.public_router.CertificacoesESGPublicService") as service_cls:
        service = service_cls.return_value
        service.verificar_integridade_passaporte = AsyncMock(return_value={
            "integridade": "INVALIDA"
        })

        response = client.get(f"/api/v1/public/passaportes/{token}/verify")
        assert response.status_code == 200
        assert response.json()["integridade"] == "INVALIDA"
