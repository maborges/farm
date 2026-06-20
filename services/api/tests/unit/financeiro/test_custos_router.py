from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from financeiro.routers import custos as custos_router


def _make_response():
    return SimpleNamespace(
        data_inicio=date(2026, 1, 1),
        data_fim=date(2026, 1, 31),
        unidade_produtiva_id=None,
        total_geral=150000.0,
        centros=[
            SimpleNamespace(
                safra_id=uuid.uuid4(),
                safra_nome="Soja 2026",
                talhao_id=uuid.uuid4(),
                talhao_nome="Talhão 01",
                total_rateado=150000.0,
                por_categoria=[
                    SimpleNamespace(
                        plano_conta_nome="Insumos",
                        categoria_rfb="CUSTEIO",
                        total_rateado=90000.0,
                        quantidade=2,
                    ),
                    SimpleNamespace(
                        plano_conta_nome="Mão de obra",
                        categoria_rfb="CUSTEIO",
                        total_rateado=60000.0,
                        quantidade=1,
                    ),
                ],
            )
        ],
    )


def test_centro_custos_exige_f2_e_retorna_resumo():
    app = FastAPI()
    app.include_router(custos_router.router)
    app.dependency_overrides[custos_router.get_tenant_id] = lambda: uuid.uuid4()
    app.dependency_overrides[custos_router.get_session] = lambda: AsyncMock()
    app.dependency_overrides[custos_router.MODULE_DEPENDENCY] = lambda: None

    with patch("financeiro.routers.custos.RelatorioService") as service_cls:
        service = service_cls.return_value
        service.centro_custos = AsyncMock(return_value=_make_response())

        client = TestClient(app)
        response = client.get(
            "/custos/centro-custos",
            params={"data_inicio": "2026-01-01", "data_fim": "2026-01-31"},
        )

    assert response.status_code == 200
    assert response.json()["total_geral"] == 150000.0
    assert response.json()["centros"][0]["por_categoria"][0]["plano_conta_nome"] == "Insumos"
    service.centro_custos.assert_awaited_once()
