from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from certificacoes_esg.models import (
    PrioridadePlanoAcao,
    SeveridadeNaoConformidade,
    StatusNaoConformidade,
    StatusPlanoAcao,
    TipoEvidencia,
)
from certificacoes_esg import router as router_module


def _build_client(tenant, user, session):
    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/v1")
    app.dependency_overrides[router_module.get_tenant_id] = lambda: tenant.id
    app.dependency_overrides[router_module.get_user_id] = lambda: user.id
    app.dependency_overrides[router_module.get_session] = lambda: session
    return TestClient(app)


def _evidencia(tenant_id: uuid.UUID, programa_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        programa_id=programa_id,
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
        snapshot_json={"source": "app"},
        snapshot_hash="hash-01",
        publico=True,
        created_by=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _nao_conformidade(tenant_id: uuid.UUID, programa_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        programa_id=programa_id,
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


def _plano_acao(tenant_id: uuid.UUID, programa_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        programa_id=programa_id,
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


def test_criar_evidencia_expoe_router_e_bloqueia_tenant_id():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    evidencia = _evidencia(tenant.id, uuid.uuid4())

    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.criar_evidencia = AsyncMock(return_value=evidencia)

        client = _build_client(tenant, user, session)
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
                "tenant_id": str(uuid.uuid4()),
            },
        )

    assert response.status_code == 422
    service.criar_evidencia.assert_not_awaited()


def test_listar_evidencias_aplica_filtros_e_enum():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    evidencia = _evidencia(tenant.id, uuid.uuid4())

    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.listar_evidencias = AsyncMock(return_value=[evidencia])

        client = _build_client(tenant, user, session)
        response = client.get(
            "/api/v1/certificacoes-esg/evidencias"
            f"?programa_id={evidencia.programa_id}&tipo_evidencia=DOCUMENTO_PDF&publico=true"
        )

    assert response.status_code == 200
    assert response.json()[0]["tipo_evidencia"] == "DOCUMENTO_PDF"
    called = service.listar_evidencias.await_args.kwargs
    assert called["programa_id"] == evidencia.programa_id
    assert called["tipo_evidencia"] == TipoEvidencia.DOCUMENTO_PDF
    assert called["publico"] is True


def test_criar_nao_conformidade_expoe_enum_oficial():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    nc = _nao_conformidade(tenant.id, uuid.uuid4())

    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.criar_nao_conformidade = AsyncMock(return_value=nc)

        client = _build_client(tenant, user, session)
        response = client.post(
            "/api/v1/certificacoes-esg/nao-conformidades",
            json={
                "programa_id": str(nc.programa_id),
                "titulo": nc.titulo,
                "descricao": nc.descricao,
                "severidade": "MAIOR",
                "status": "ABERTA",
                "tenant_id": str(uuid.uuid4()),
            },
        )

    assert response.status_code == 422
    service.criar_nao_conformidade.assert_not_awaited()


def test_atualizar_status_nao_conformidade_rejeita_status_invalido():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()

    client = _build_client(tenant, user, session)
    response = client.patch(
        f"/api/v1/certificacoes-esg/nao-conformidades/{uuid.uuid4()}/status",
        json={"status": "INVALIDO"},
    )

    assert response.status_code == 422


def test_criar_plano_acao_e_listar_com_filtros():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    plano = _plano_acao(tenant.id, uuid.uuid4())

    with patch("certificacoes_esg.router.CertificacoesESGService") as service_cls:
        service = service_cls.return_value
        service.criar_plano_acao = AsyncMock(return_value=plano)
        service.listar_planos_acao = AsyncMock(return_value=[plano])

        client = _build_client(tenant, user, session)
        create_response = client.post(
            "/api/v1/certificacoes-esg/planos-acao",
            json={
                "programa_id": str(plano.programa_id),
                "titulo": plano.titulo,
                "descricao": plano.descricao,
                "prioridade": "ALTA",
                "status": "PENDENTE",
            },
        )
        list_response = client.get(
            "/api/v1/certificacoes-esg/planos-acao"
            f"?programa_id={plano.programa_id}&prioridade=ALTA&status=PENDENTE"
        )

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    assert list_response.json()[0]["status"] == "PENDENTE"
    assert service_cls.call_count == 2
    first_call = service_cls.call_args_list[0]
    second_call = service_cls.call_args_list[1]
    assert first_call.args[0] == session
    assert first_call.args[1] == tenant.id
    assert first_call.kwargs["user_id"] == user.id
    assert second_call.args[0] == session
    assert second_call.args[1] == tenant.id
    assert second_call.kwargs["user_id"] == user.id
    assert service.listar_planos_acao.await_args.kwargs["prioridade"] == PrioridadePlanoAcao.ALTA
