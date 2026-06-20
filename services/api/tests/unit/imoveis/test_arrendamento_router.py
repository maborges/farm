import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from imoveis.models.imovel import (
    Periodicidade,
    StatusContrato,
    StatusParcela,
    TipoArrendatario,
    TipoContrato,
    ValorModalidade,
)
from imoveis.routers import arrendamento as router_module


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
    app = FastAPI()
    app.include_router(router_module.router)
    app.dependency_overrides[router_module.MODULE_DEPENDENCY] = lambda: None
    app.dependency_overrides[router_module.get_current_tenant] = lambda: tenant
    app.dependency_overrides[router_module.get_current_user] = lambda: user
    app.dependency_overrides[router_module.get_session] = lambda: session
    return TestClient(app)


def _make_contrato():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        imovel_id=uuid.uuid4(),
        unidade_produtiva_id=uuid.uuid4(),
        tipo=TipoContrato.ARRENDAMENTO,
        arrendatario_tipo=TipoArrendatario.PESSOA_FISICA,
        arrendatario_pessoa_id=uuid.uuid4(),
        arrendatario_fazenda_id=None,
        area_arrendada_ha=Decimal("120.5000"),
        valor_modalidade=ValorModalidade.FIXO_BRL,
        valor=Decimal("120000.00"),
        commodity_referencia=None,
        periodicidade=Periodicidade.ANUAL,
        data_inicio=date(2024, 1, 1),
        data_fim=date(2026, 12, 31),
        dia_vencimento=10,
        indice_reajuste="IGP-M",
        data_reajuste_anual=date(2025, 1, 1),
        status=StatusContrato.ATIVO,
        motivo_rescisao=None,
        path_contrato_pdf=None,
        registro_cartorio=None,
        clausulas_observacoes=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_criar_contrato_expoe_router_e_converte_enums(client, tenant, user, session):
    contrato = _make_contrato()

    with patch("imoveis.routers.arrendamento.ArrendamentoService") as service_cls:
        service = service_cls.return_value
        service.criar_contrato = AsyncMock(return_value=(contrato, ["Contrato criado"]))

        response = client.post(
            "/imoveis/arrendamentos",
            json={
                "imovel_id": str(contrato.imovel_id),
                "unidade_produtiva_id": str(contrato.unidade_produtiva_id),
                "tipo": "arrendamento",
                "arrendatario_tipo": "pessoa_fisica",
                "area_arrendada_ha": "120.5000",
                "valor_modalidade": "fixo_brl",
                "valor": "120000.00",
                "periodicidade": "anual",
                "data_inicio": "2024-01-01",
                "data_fim": "2026-12-31",
                "dia_vencimento": 10,
                "indice_reajuste": "IGP-M",
            },
        )

    assert response.status_code == 201
    assert response.json()["tipo"] == "ARRENDAMENTO"
    assert response.json()["status"] == "ATIVO"
    service.criar_contrato.assert_awaited_once()
    called_kwargs = service.criar_contrato.await_args.kwargs
    assert called_kwargs["tenant_id"] == tenant.id
    assert called_kwargs["created_by"] == user.id
    assert called_kwargs["tipo"] == TipoContrato.ARRENDAMENTO
    assert called_kwargs["arrendatario_tipo"] == TipoArrendatario.PESSOA_FISICA


def test_listar_contratos_filtra_por_status(client, session):
    contrato = _make_contrato()

    with patch("imoveis.routers.arrendamento.ArrendamentoService") as service_cls:
        service = service_cls.return_value
        service.listar_contratos = AsyncMock(return_value=[contrato])

        response = client.get("/imoveis/arrendamentos?status=ATIVO")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "ATIVO"
    service.listar_contratos.assert_awaited_once()
    assert service.listar_contratos.await_args.kwargs["status"] == StatusContrato.ATIVO


def test_obter_resumo_contrato_expoe_agregados(client):
    contrato = _make_contrato()

    with patch("imoveis.routers.arrendamento.ArrendamentoService") as service_cls:
        service = service_cls.return_value
        service.get_resumo_contrato = AsyncMock(
            return_value={
                "contrato": contrato,
                "total_parcelas": 3,
                "parcelas_pagas": 1,
                "parcelas_pendentes": 1,
                "parcelas_vencidas": 1,
                "valor_total_centavos": 12000000,
                "valor_pago_centavos": 4000000,
                "valor_pendente_centavos": 8000000,
                "percentual_pago": 33.33,
            }
        )

        response = client.get(f"/imoveis/arrendamentos/{contrato.id}/resumo")

    assert response.status_code == 200
    assert response.json()["total_parcelas"] == 3
    assert response.json()["contrato"]["status"] == "ATIVO"
    service.get_resumo_contrato.assert_awaited_once()
    assert service.get_resumo_contrato.await_args.args[0] == contrato.id
