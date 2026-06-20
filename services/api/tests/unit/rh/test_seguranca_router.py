import uuid
from datetime import date, datetime, timezone
import importlib
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

rh_router = importlib.import_module("rh.router")


def _make_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


def test_criar_item_seguranca():
    tenant_id = uuid.uuid4()
    session = _make_session()
    item = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome="Capacete com jugular",
        tipo="EPI",
        ca_numero="12345",
        validade_dias=365,
        fornecedor="Fornecedor X",
        observacoes="",
        ativo=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    app = FastAPI()
    app.include_router(rh_router.router)
    app.dependency_overrides[rh_router.MODULE_DEPENDENCY] = lambda: None
    app.dependency_overrides[rh_router.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[rh_router.get_session] = lambda: session
    client = TestClient(app)

    with patch("rh.router.SegurancaTrabalhoService") as service_cls:
        service = service_cls.return_value
        service.criar_item = AsyncMock(return_value=item)
        response = client.post(
            "/rh/seguranca/itens",
            json={
                "nome": "Capacete com jugular",
                "tipo": "EPI",
                "ca_numero": "12345",
                "validade_dias": 365,
                "fornecedor": "Fornecedor X",
            },
        )

    assert response.status_code == 201
    assert response.json()["nome"] == "Capacete com jugular"
    service.criar_item.assert_awaited_once()


def test_registrar_entrega_seguranca():
    tenant_id = uuid.uuid4()
    session = _make_session()
    entrega = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        colaborador_id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        unidade_produtiva_id=None,
        data_entrega=date(2026, 6, 20),
        data_validade=date(2026, 12, 20),
        quantidade=1.0,
        status="ATIVA",
        termo_assinado_url=None,
        observacoes=None,
        created_at=datetime.now(timezone.utc),
    )

    app = FastAPI()
    app.include_router(rh_router.router)
    app.dependency_overrides[rh_router.MODULE_DEPENDENCY] = lambda: None
    app.dependency_overrides[rh_router.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[rh_router.get_session] = lambda: session
    client = TestClient(app)

    with patch("rh.router.SegurancaTrabalhoService") as service_cls:
        service = service_cls.return_value
        service.registrar_entrega = AsyncMock(return_value=entrega)
        response = client.post(
            "/rh/seguranca/entregas",
            json={
                "colaborador_id": str(entrega.colaborador_id),
                "item_id": str(entrega.item_id),
                "data_entrega": "2026-06-20",
                "quantidade": 1,
            },
        )

    assert response.status_code == 201
    assert response.json()["status"] == "ATIVA"
    service.registrar_entrega.assert_awaited_once()


def test_exportar_pdf_nr31():
    tenant_id = uuid.uuid4()
    session = _make_session()

    app = FastAPI()
    app.include_router(rh_router.router)
    app.dependency_overrides[rh_router.MODULE_DEPENDENCY] = lambda: None
    app.dependency_overrides[rh_router.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[rh_router.get_session] = lambda: session
    client = TestClient(app)

    with patch("rh.router.SegurancaTrabalhoService") as service_cls:
        service = service_cls.return_value
        service.gerar_pdf_nr31 = AsyncMock(return_value=b"%PDF-1.4 nr31")
        response = client.get("/rh/seguranca/export/nr31.pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4 nr31"
    service.gerar_pdf_nr31.assert_awaited_once()
