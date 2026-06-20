import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from imoveis.models.imovel import MetodoAvaliacaoImovel
from imoveis.routers import avaliacao as router_module


def _make_imovel():
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        nome="Fazenda Boa Vista",
        municipio="Sorriso",
        uf="MT",
        area_total_ha=Decimal("1200.5000"),
    )


def _make_avaliacao(imovel_id: uuid.UUID):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        imovel_id=imovel_id,
        data_avaliacao=datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc),
        metodo=MetodoAvaliacaoImovel.LAUDO,
        valor_total=Decimal("3500000.00"),
        valor_por_hectare=Decimal("2915.46"),
        valor_terra_nua=Decimal("2500000.00"),
        valor_benfeitorias=Decimal("800000.00"),
        valor_lavoura_perene=None,
        moeda="BRL",
        responsavel="Eng. Agrônomo",
        numero_laudo="LAUDO-2026-001",
        observacoes="Avaliação patrimonial",
        anexos=[{"nome": "laudo.pdf"}],
        created_at=datetime.now(timezone.utc),
    )


def _build_client(tenant, user, session):
    app = FastAPI()
    app.include_router(router_module.router)
    app.dependency_overrides[router_module.MODULE_DEPENDENCY] = lambda: None
    app.dependency_overrides[router_module.get_current_tenant] = lambda: tenant
    app.dependency_overrides[router_module.get_current_user] = lambda: user
    app.dependency_overrides[router_module.get_session] = lambda: session
    return TestClient(app)


def test_criar_avaliacao_expoe_router_e_converte_enum():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    avaliacao = _make_avaliacao(uuid.uuid4())

    with patch("imoveis.routers.avaliacao.AvaliacaoService") as service_cls:
        service = service_cls.return_value
        service.criar_avaliacao = AsyncMock(return_value=(avaliacao, ["ok"]))

        client = _build_client(tenant, user, session)
        response = client.post(
            "/imoveis/avaliacoes",
            json={
                "imovel_id": str(avaliacao.imovel_id),
                "data_avaliacao": "2026-06-20",
                "metodo": "laudo",
                "valor_total": "3500000.00",
                "valor_por_hectare": "2915.46",
                "valor_terra_nua": "2500000.00",
                "valor_benfeitorias": "800000.00",
                "moeda": "brl",
                "responsavel": "Eng. Agrônomo",
                "numero_laudo": "LAUDO-2026-001",
                "observacoes": "Avaliação patrimonial",
                "anexos": [{"nome": "laudo.pdf"}],
            },
        )

    assert response.status_code == 201
    assert response.json()["metodo"] == "LAUDO"
    assert response.json()["valor_total"] == "3500000.00"
    service.criar_avaliacao.assert_awaited_once()
    kwargs = service.criar_avaliacao.await_args.kwargs
    assert kwargs["tenant_id"] == tenant.id
    assert kwargs["created_by"] == user.id
    assert kwargs["metodo"] == MetodoAvaliacaoImovel.LAUDO


def test_listar_avaliacoes_por_imovel():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()
    avaliacao = _make_avaliacao(uuid.uuid4())

    with patch("imoveis.routers.avaliacao.AvaliacaoService") as service_cls:
        service = service_cls.return_value
        service.listar_avaliacoes = AsyncMock(return_value=[avaliacao])

        client = _build_client(tenant, user, session)
        response = client.get(f"/imoveis/avaliacoes?imovel_id={avaliacao.imovel_id}")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["numero_laudo"] == "LAUDO-2026-001"
    service.listar_avaliacoes.assert_awaited_once()


def test_exportar_pdf_retorna_application_pdf():
    tenant = SimpleNamespace(id=uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4())
    session = AsyncMock()

    with patch("imoveis.routers.avaliacao.AvaliacaoService") as service_cls:
        service = service_cls.return_value
        service.gerar_pdf_historico = AsyncMock(return_value=b"%PDF-1.4 mock")

        client = _build_client(tenant, user, session)
        response = client.get(f"/imoveis/avaliacoes/{uuid.uuid4()}/export/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4 mock"
    service.gerar_pdf_historico.assert_awaited_once()
