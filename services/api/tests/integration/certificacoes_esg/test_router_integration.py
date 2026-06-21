from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from certificacoes_esg.models import (
    PrioridadePlanoAcao,
    SeveridadeNaoConformidade,
    StatusNaoConformidade,
    StatusPlanoAcao,
    TipoEvidencia,
)
from certificacoes_esg import router as router_module
from core.exceptions import TenantViolationError
from main import app


@pytest.fixture
def tenant():
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture
def user():
    return SimpleNamespace(id=uuid.uuid4())


@pytest.fixture
def session():
    sess = AsyncMock()
    sess.commit = AsyncMock()
    sess.refresh = AsyncMock()
    return sess


@pytest.fixture
def client(tenant, user, session):
    app.dependency_overrides[router_module.get_tenant_id] = lambda: tenant.id
    app.dependency_overrides[router_module.get_user_id] = lambda: user.id
    app.dependency_overrides[router_module.get_session] = lambda: session
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


def _evidencia(tenant_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        programa_id=uuid.uuid4(),
        checklist_id=None,
        criterio_id=None,
        avaliacao_id=None,
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
        responsavel_pessoa_id=None,
        tipo_evidencia=TipoEvidencia.DOCUMENTO_PDF,
        titulo="Evidência técnica",
        descricao="Documento interno",
        origem_tipo="RELATORIO_TECNICO",
        origem_id=uuid.uuid4(),
        arquivo_url=None,
        arquivo_hash=None,
        snapshot_json={"source": "app", "captured_at": datetime.now(timezone.utc).isoformat()},
        snapshot_hash="hash-01",
        publico=True,
        created_by=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _nao_conformidade(tenant_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        programa_id=uuid.uuid4(),
        checklist_id=None,
        criterio_id=None,
        avaliacao_id=None,
        evidencia_id=None,
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
        responsavel_pessoa_id=None,
        titulo="NC 1",
        descricao="Descrição",
        severidade=SeveridadeNaoConformidade.MAIOR,
        status=StatusNaoConformidade.ABERTA,
        detectada_em=datetime.now(timezone.utc),
        prazo_correcao=None,
        resolvida_em=None,
        created_by=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _plano_acao(tenant_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        programa_id=uuid.uuid4(),
        nao_conformidade_id=None,
        evidencia_id=None,
        responsavel_pessoa_id=None,
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
        titulo="Plano 1",
        descricao="Ação corretiva",
        prioridade=PrioridadePlanoAcao.ALTA,
        status=StatusPlanoAcao.PENDENTE,
        prazo=datetime.now(timezone.utc),
        concluido_em=None,
        created_by=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_router_registrado_no_main_app(client):
    paths = {route.path for route in app.routes}
    assert "/api/v1/certificacoes-esg/evidencias" in paths
    assert "/api/v1/certificacoes-esg/nao-conformidades" in paths
    assert "/api/v1/certificacoes-esg/planos-acao" in paths


def test_criar_e_listar_evidencias_no_app(client, tenant, user, session):
    evidencia = _evidencia(tenant.id)
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.criar_evidencia = AsyncMock(return_value=evidencia)
        service.listar_evidencias = AsyncMock(return_value=[evidencia])

        response = client.post(
            "/api/v1/certificacoes-esg/evidencias",
            json={
                "programa_id": str(evidencia.programa_id),
                "tipo_evidencia": "DOCUMENTO_PDF",
                "titulo": evidencia.titulo,
                "descricao": evidencia.descricao,
                "origem_tipo": evidencia.origem_tipo,
                "origem_id": str(evidencia.origem_id),
                "snapshot_json": {"source": "app"},
                "snapshot_hash": "hash-01",
            },
        )
        list_response = client.get(
            "/api/v1/certificacoes-esg/evidencias"
            f"?programa_id={evidencia.programa_id}&tipo_evidencia=DOCUMENTO_PDF&publico=true"
        )

    assert response.status_code == 201
    assert list_response.status_code == 200
    assert list_response.json()[0]["tipo_evidencia"] == "DOCUMENTO_PDF"
    assert service_cls.call_count == 2
    first_call = service_cls.call_args_list[0]
    second_call = service_cls.call_args_list[1]
    assert first_call.args[0] == session
    assert first_call.args[1] == tenant.id
    assert first_call.kwargs["user_id"] == user.id
    assert second_call.args[0] == session
    assert second_call.args[1] == tenant.id
    assert second_call.kwargs["user_id"] == user.id
    assert service.listar_evidencias.await_args.kwargs["tipo_evidencia"] == TipoEvidencia.DOCUMENTO_PDF


def test_cross_tenant_bloqueado_no_app(client):
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.criar_nao_conformidade = AsyncMock(
            side_effect=TenantViolationError(
                "Tentativa de acesso cross-tenant interceptada.",
                tenant_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                resource="certificacao_nao_conformidades",
            )
        )

        response = client.post(
            "/api/v1/certificacoes-esg/nao-conformidades",
            json={
                "programa_id": str(uuid.uuid4()),
                "titulo": "NC 1",
                "descricao": "Descrição",
                "severidade": "MAIOR",
            },
        )

    assert response.status_code == 403


def test_planos_acao_valida_status_oficial_no_app(client):
    plano = _plano_acao(uuid.uuid4())
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.criar_plano_acao = AsyncMock(return_value=plano)
        service.atualizar_status_plano_acao = AsyncMock(return_value=plano)

        response = client.patch(
            f"/api/v1/certificacoes-esg/planos-acao/{plano.id}/status",
            json={"status": "CONCLUIDO"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "PENDENTE"
    service.atualizar_status_plano_acao.assert_awaited_once()
