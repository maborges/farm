from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.routers import backoffice_crm_ofertas as router_module


class _FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalarResult(self._rows)


def _build_client(session):
    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/v1")
    app.dependency_overrides[router_module.get_current_admin] = lambda: {
        "sub": str(uuid.uuid4()),
        "is_superuser": True,
    }
    app.dependency_overrides[router_module.get_session] = lambda: session
    return TestClient(app)


def test_listar_planos_normaliza_modulos_inclusos_legados():
    plano_com_string = SimpleNamespace(
        id=uuid.uuid4(),
        nome="Starter",
        slug="starter",
        tipo_oferta="bundle",
        modulos_inclusos='["crm","email-marketing"]',
        preco_mensal_padrao=200,
        preco_anual_padrao=2000,
        ativo=True,
    )
    plano_com_none = SimpleNamespace(
        id=uuid.uuid4(),
        nome="Enterprise",
        slug="enterprise",
        tipo_oferta="modular",
        modulos_inclusos=None,
        preco_mensal_padrao=None,
        preco_anual_padrao=None,
        ativo=True,
    )
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_FakeResult([plano_com_string, plano_com_none]))

    client = _build_client(session)
    response = client.get("/api/v1/backoffice/crm/ofertas/planos?ativo_apenas=true")

    assert response.status_code == 200
    assert response.json()[0]["modulos_inclusos"] == ["crm", "email-marketing"]
    assert response.json()[1]["modulos_inclusos"] == []
    session.execute.assert_awaited_once()
