from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from certificacoes_esg import router as router_module
from certificacoes_esg.models import StatusPassaporte, StatusRelatorioESG
from core.exceptions import TenantViolationError

def _build_client(tenant, user, session):
    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/v1")
    app.dependency_overrides[router_module.get_tenant_id] = lambda: tenant.id
    app.dependency_overrides[router_module.get_user_id] = lambda: user.id
    app.dependency_overrides[router_module.get_session] = lambda: session

    @app.exception_handler(TenantViolationError)
    async def tenant_violation_handler(request, exc: TenantViolationError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    return TestClient(app)


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
    client = _build_client(tenant, user, session)
    yield client


def _relatorio(tenant_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        programa_id=None,
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
        responsavel_pessoa_id=None,
        titulo="Relatório ESG Anual",
        periodo_inicio=None,
        periodo_fim=None,
        status=StatusRelatorioESG.RASCUNHO,
        versao=1,
        snapshot_json=None,
        snapshot_hash=None,
        publico=False,
        publicado_em=None,
        cancelado_em=None,
        created_by=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _passaporte(tenant_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        programa_id=None,
        propriedade_id=None,
        imovel_rural_id=None,
        propriedade_imovel_id=None,
        lote_rastreabilidade_id=None,
        caderno_lote_comercial_id=None,
        responsavel_pessoa_id=None,
        titulo="Passaporte de Rastreabilidade Lote 1",
        status=StatusPassaporte.RASCUNHO,
        versao=1,
        snapshot_json=None,
        snapshot_hash=None,
        publico=False,
        publicado_em=None,
        revogado_em=None,
        created_by=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _indicador(relatorio_id: uuid.UUID, tenant_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        relatorio_id=relatorio_id,
        evidencia_id=None,
        nome="Emissão de GEE",
        categoria="Ambiental",
        valor=100.0,
        unidade="tCO2e",
        score=None,
        metodologia=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _evento(passaporte_id: uuid.UUID, tenant_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        passaporte_id=passaporte_id,
        tipo_evento="GERADO",
        titulo="Colheita Finalizada",
        descricao="Lote colhido",
        ocorrido_em=datetime.now(timezone.utc),
        origem_tipo="COLHEITA",
        origem_id=uuid.uuid4(),
        snapshot_json=None,
        snapshot_hash=None,
        created_at=datetime.now(timezone.utc),
    )


def _evidencia_relatorio(relatorio_id: uuid.UUID, tenant_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        relatorio_id=relatorio_id,
        evidencia_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
    )


def _evidencia_passaporte(passaporte_id: uuid.UUID, tenant_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        passaporte_id=passaporte_id,
        evidencia_id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
    )


def test_criar_e_listar_relatorios(client, tenant, user, session):
    relatorio = _relatorio(tenant.id)
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.criar_relatorio_esg = AsyncMock(return_value=relatorio)
        service.listar_relatorios_esg = AsyncMock(return_value=[relatorio])

        response = client.post(
            "/api/v1/certificacoes-esg/relatorios-esg",
            json={
                "titulo": relatorio.titulo,
                "versao": relatorio.versao,
            },
        )
        assert response.status_code == 201

        list_response = client.get("/api/v1/certificacoes-esg/relatorios-esg")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1


def test_atualizar_status_relatorio(client, tenant, user, session):
    relatorio = _relatorio(tenant.id)
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.atualizar_status_relatorio_esg = AsyncMock(return_value=relatorio)

        response = client.patch(
            f"/api/v1/certificacoes-esg/relatorios-esg/{relatorio.id}/status",
            json={"status": "PUBLICADO", "publicado_em": datetime.now(timezone.utc).isoformat()},
        )
        assert response.status_code == 200
        service.atualizar_status_relatorio_esg.assert_awaited_once()


def test_indicadores_relatorio(client, tenant, user, session):
    relatorio_id = uuid.uuid4()
    indicador = _indicador(relatorio_id, tenant.id)
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.adicionar_indicador_relatorio_esg = AsyncMock(return_value=indicador)
        service.listar_indicadores_relatorio_esg = AsyncMock(return_value=[indicador])

        response = client.post(
            f"/api/v1/certificacoes-esg/relatorios-esg/{relatorio_id}/indicadores",
            json={
                "relatorio_id": str(relatorio_id),
                "nome": "Emissão de GEE",
            },
        )
        assert response.status_code == 201

        list_response = client.get(f"/api/v1/certificacoes-esg/relatorios-esg/{relatorio_id}/indicadores")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1


def test_evidencias_relatorio(client, tenant, user, session):
    relatorio_id = uuid.uuid4()
    evid = _evidencia_relatorio(relatorio_id, tenant.id)
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.vincular_evidencia_relatorio_esg = AsyncMock(return_value=evid)
        service.listar_evidencias_relatorio_esg = AsyncMock(return_value=[evid])

        response = client.post(
            f"/api/v1/certificacoes-esg/relatorios-esg/{relatorio_id}/evidencias",
            json={
                "relatorio_id": str(relatorio_id),
                "evidencia_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 201

        list_response = client.get(f"/api/v1/certificacoes-esg/relatorios-esg/{relatorio_id}/evidencias")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1


def test_criar_e_listar_passaportes(client, tenant, user, session):
    passaporte = _passaporte(tenant.id)
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.criar_passaporte_rastreabilidade = AsyncMock(return_value=passaporte)
        service.listar_passaportes_rastreabilidade = AsyncMock(return_value=[passaporte])

        response = client.post(
            "/api/v1/certificacoes-esg/passaportes",
            json={
                "titulo": passaporte.titulo,
            },
        )
        assert response.status_code == 201

        list_response = client.get("/api/v1/certificacoes-esg/passaportes")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1


def test_atualizar_status_passaporte(client, tenant, user, session):
    passaporte = _passaporte(tenant.id)
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.atualizar_status_passaporte_rastreabilidade = AsyncMock(return_value=passaporte)

        response = client.patch(
            f"/api/v1/certificacoes-esg/passaportes/{passaporte.id}/status",
            json={"status": "PUBLICADO", "publicado_em": datetime.now(timezone.utc).isoformat()},
        )
        assert response.status_code == 200
        service.atualizar_status_passaporte_rastreabilidade.assert_awaited_once()


def test_eventos_passaporte(client, tenant, user, session):
    passaporte_id = uuid.uuid4()
    evento = _evento(passaporte_id, tenant.id)
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.adicionar_evento_passaporte = AsyncMock(return_value=evento)
        service.listar_eventos_passaporte = AsyncMock(return_value=[evento])

        response = client.post(
            f"/api/v1/certificacoes-esg/passaportes/{passaporte_id}/eventos",
            json={
                "passaporte_id": str(passaporte_id),
                "tipo_evento": "GERADO",
                "titulo": "Colheita",
                "descricao": "Lote",
                "ocorrido_em": datetime.now(timezone.utc).isoformat(),
                "origem_tipo": "COL",
                "origem_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 201

        list_response = client.get(f"/api/v1/certificacoes-esg/passaportes/{passaporte_id}/eventos")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1


def test_evidencias_passaporte(client, tenant, user, session):
    passaporte_id = uuid.uuid4()
    evid = _evidencia_passaporte(passaporte_id, tenant.id)
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.vincular_evidencia_passaporte = AsyncMock(return_value=evid)
        service.listar_evidencias_passaporte = AsyncMock(return_value=[evid])

        response = client.post(
            f"/api/v1/certificacoes-esg/passaportes/{passaporte_id}/evidencias",
            json={
                "passaporte_id": str(passaporte_id),
                "evidencia_id": str(uuid.uuid4()),
            },
        )
        assert response.status_code == 201

        list_response = client.get(f"/api/v1/certificacoes-esg/passaportes/{passaporte_id}/evidencias")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1


def test_impedir_tenant_id_no_payload(client):
    response = client.post(
        "/api/v1/certificacoes-esg/relatorios-esg",
        json={"titulo": "Teste", "tenant_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422


def test_validar_erro_para_status_invalido(client):
    response = client.patch(
        f"/api/v1/certificacoes-esg/relatorios-esg/{uuid.uuid4()}/status",
        json={"status": "INEXISTENTE"},
    )
    assert response.status_code == 422


def test_bloquear_cross_tenant_quando_aplicavel(client, tenant, user, session):
    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.listar_relatorios_esg = AsyncMock(
            side_effect=TenantViolationError(
                "Tentativa de acesso cross-tenant interceptada.",
                tenant_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                resource="relatorios_esg",
            )
        )

        response = client.get("/api/v1/certificacoes-esg/relatorios-esg")
        assert response.status_code == 403

