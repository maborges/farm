from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.routers import backoffice_tabelas as router_module


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


def _build_client(session):
    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/v1")
    app.dependency_overrides[router_module.get_current_admin] = lambda: {
        "sub": str(uuid.uuid4()),
        "is_superuser": True,
    }
    app.dependency_overrides[router_module.get_session] = lambda: session
    return TestClient(app)


def test_criar_commodity_sistema_retorna_409_quando_codigo_ja_existe():
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_FakeResult(uuid.uuid4()))
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    client = _build_client(session)
    response = client.post(
        "/api/v1/backoffice/tabelas/commodities",
        json={
            "nome": "Café Conilon",
            "codigo": "cafe_conilon",
            "tipo": "AGRICOLA",
            "unidade_padrao": "SACA_60KG",
            "peso_unidade": 60.0,
            "possui_cotacao": True,
            "bolsa_referencia": "ICE",
            "codigo_bolsa": "RC",
            "descricao": "Café",
            "ativo": True,
        },
    )

    assert response.status_code == 409
    assert "CAFE_CONILON" in response.json()["detail"]
    session.commit.assert_not_awaited()

