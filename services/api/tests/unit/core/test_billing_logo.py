"""Regressão do upload e da leitura da logo da conta, sem banco externo."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.routers import billing


@pytest.fixture
def account(monkeypatch):
    tenant = SimpleNamespace(
        id=uuid4(), nome="Grupo", documento="123", ativo=True,
        created_at=None, email_responsavel=None, telefone_responsavel=None,
        idioma_padrao="pt-BR", branding={"primaryColor": "green"},
    )
    session = AsyncMock()
    session.execute.return_value = Mock(first=Mock(return_value=None))
    save = Mock()
    monkeypatch.setattr(billing.StorageService, "save_blob", save)
    monkeypatch.setattr(billing.StorageService, "public_url", lambda path: f"/{path}")
    app = FastAPI()
    app.include_router(billing.router)
    app.dependency_overrides[billing.get_current_tenant] = lambda: tenant
    app.dependency_overrides[billing.get_session] = lambda: session
    with TestClient(app) as client:
        yield client, tenant, session, save


@pytest.mark.parametrize("mime,extension", [("image/png", ".png"), ("image/jpeg", ".jpg"), ("image/webp", ".webp")])
def test_upload_persists_logo_for_current_account(account, mime, extension):
    client, tenant, session, save = account
    response = client.post("/billing/my-account/logo", files={"arquivo": ("logo", b"image", mime)})
    assert response.status_code == 200
    url = response.json()["logo_url_grupo"]
    assert str(tenant.id) in url
    assert url.endswith(extension)
    assert tenant.branding == {"primaryColor": "green", "logoUrl": url}
    save.assert_called_once_with(b"image", url.lstrip("/"))
    session.commit.assert_awaited_once()
    assert client.get("/billing/my-account").json()["tenant"]["logo_url_grupo"] == url
    assert client.patch("/billing/my-account", json={"nome": "Atualizado"}).json()["tenant"]["logo_url_grupo"] == url


@pytest.mark.parametrize("content,mime", [(b"", "image/png"), (b"x", "image/svg+xml"), (b"x" * (2 * 1024 * 1024 + 1), "image/png")], ids=["empty", "unsupported", "oversized"])
def test_rejects_invalid_upload_without_writing(account, content, mime):
    client, tenant, session, save = account
    response = client.post("/billing/my-account/logo", files={"arquivo": ("logo", content, mime)})
    assert response.status_code == 400
    save.assert_not_called()
    session.commit.assert_not_awaited()
    assert tenant.branding == {"primaryColor": "green"}


def test_account_without_branding(account):
    client, tenant, _, _ = account
    tenant.branding = None
    assert client.get("/billing/my-account").json()["tenant"]["logo_url_grupo"] is None
