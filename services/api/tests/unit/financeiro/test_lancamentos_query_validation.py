"""Testes de validação de query parameters do router financeiro de lançamentos."""

from __future__ import annotations

import uuid
from typing import Literal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.dependencies import get_session, get_tenant_id
from financeiro.routers.lancamentos import router


@pytest.fixture
def test_app() -> FastAPI:
    """Cria uma aplicação FastAPI de teste contendo o router de lançamentos."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/financeiro")

    tenant_id = uuid.uuid4()
    mock_session = AsyncMock()

    app.dependency_overrides[get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[get_session] = lambda: mock_session

    return app


@pytest.mark.asyncio
async def test_listar_lancamentos_tipo_query_validation(test_app: FastAPI) -> None:
    """Valida que o parâmetro 'tipo' aceita CUSTO e RECEITA e rejeita valores inválidos com HTTP 422."""
    from financeiro.services.lancamento_service import LancamentoService

    mock_response = {
        "items": [],
        "total": 0,
        "page": 1,
        "limit": 100,
        "pages": 0,
        "offset": 0,
    }

    with patch.object(LancamentoService, "listar", new_callable=AsyncMock) as mock_listar:
        mock_listar.return_value = mock_response

        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Sem parâmetro tipo -> Sucesso
            res = await client.get("/api/v1/financeiro/lancamentos")
            assert res.status_code == 200

            # 2. tipo=CUSTO -> Sucesso
            res_custo = await client.get("/api/v1/financeiro/lancamentos?tipo=CUSTO")
            assert res_custo.status_code == 200
            assert mock_listar.call_args[1]["tipo"] == "CUSTO"

            # 3. tipo=RECEITA -> Sucesso
            res_receita = await client.get("/api/v1/financeiro/lancamentos?tipo=RECEITA")
            assert res_receita.status_code == 200
            assert mock_listar.call_args[1]["tipo"] == "RECEITA"

            # 4. tipo=INVALIDO -> Rejeitado com 422 Unprocessable Entity
            res_invalido = await client.get("/api/v1/financeiro/lancamentos?tipo=INVALIDO")
            assert res_invalido.status_code == 422


def test_listar_lancamentos_openapi_schema(test_app: FastAPI) -> None:
    """Verifica que o esquema OpenAPI contém enum=['CUSTO', 'RECEITA'] para o parâmetro tipo."""
    openapi = test_app.openapi()
    params = openapi["paths"]["/api/v1/financeiro/lancamentos/"]["get"]["parameters"]
    tipo_param = next(p for p in params if p["name"] == "tipo")

    # Verifica enum no schema Pydantic/OpenAPI
    schema = tipo_param["schema"]
    if "enum" in schema:
        enum_values = schema["enum"]
    elif "anyOf" in schema:
        enum_values = next(sub["enum"] for sub in schema["anyOf"] if "enum" in sub)
    else:
        pytest.fail(f"Esquema OpenAPI não define enum para tipo: {schema}")

    assert set(enum_values) == {"CUSTO", "RECEITA"}

