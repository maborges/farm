from __future__ import annotations

import importlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from agricola.benchmark.schemas import BenchmarkAgricolaDestaques, BenchmarkAgricolaItem, BenchmarkAgricolaResponse


def _fake_response() -> BenchmarkAgricolaResponse:
    safra_id = uuid4()
    pu_id = uuid4()
    item = BenchmarkAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=pu_id,
        label="Talhão A",
        safra_id=safra_id,
        area_total_ha=10.0,
        resultado_operacional=7000.0,
        margem_pct=25.0,
        receita_liquida_por_hectare=1000.0,
        resultado_por_hectare=700.0,
        custo_operacional_total=3000.0,
        custo_operacional_por_hectare=300.0,
        custo_operacional_por_operacao=1500.0,
        horas_por_hectare=0.8,
        hectares_por_jornada=5.0,
        sujeito_reconciliacao=False,
        warnings_relevantes=[],
        posicao=1,
        destaque="MELHOR",
    )
    return BenchmarkAgricolaResponse(
        tenant_id=uuid4(),
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        safra=item.model_copy(update={"scope": "SAFRA"}),
        production_units=[item],
        ranking=[item],
        destaques=BenchmarkAgricolaDestaques(melhor=item, referencia=item, ponto_atencao=item),
        warnings=[],
        sujeito_reconciliacao=False,
    )


@pytest.mark.asyncio
async def test_benchmark_v1_endpoint_delega_servico_e_nao_usa_legado(
    client: AsyncClient,
    headers_agricola: dict,
):
    fake_response = _fake_response()
    captured: dict = {}

    class FakeService:
        def __init__(self, session, tenant_id):
            captured["tenant_id"] = tenant_id
            captured["session_type"] = type(session).__name__

        async def gerar(self, **kwargs):
            captured["kwargs"] = kwargs
            return fake_response

    benchmark_router = importlib.import_module("agricola.benchmark.router")

    with (
        patch.object(benchmark_router, "BenchmarkAgricolaV1Service", FakeService),
        patch("financeiro.services.relatorio_service.RelatorioService.dre", new=AsyncMock()) as legacy_report,
        patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", new=AsyncMock()) as legacy_lancamento,
    ):
        response = await client.get(
            "/api/v1/agricola/benchmark/v1",
            params={
                "safra_id": str(fake_response.safra_id),
                "production_unit_id": str(uuid4()),
                "unidade_produtiva_id": str(uuid4()),
                "data_inicio": "2026-01-01",
                "data_fim": "2026-01-31",
            },
            headers=headers_agricola,
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert str(captured["tenant_id"]) == headers_agricola["X-Tenant-ID"]
    assert payload["tenant_id"] == str(fake_response.tenant_id)
    assert payload["safra_id"] == str(fake_response.safra_id)
    assert payload["sujeito_reconciliacao"] is False
    assert captured["kwargs"]["safra_id"] == fake_response.safra_id
    assert captured["kwargs"]["data_inicio"].isoformat() == "2026-01-01"
    assert captured["kwargs"]["data_fim"].isoformat() == "2026-01-31"
    legacy_report.assert_not_called()
    legacy_lancamento.assert_not_called()
