from __future__ import annotations

import importlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from agricola.eficiencia.schemas import EficienciaOperacionalAgricolaResponse, EficienciaOperacionalItem


def _fake_response() -> EficienciaOperacionalAgricolaResponse:
    safra_id = uuid4()
    item = EficienciaOperacionalItem(
        scope="SAFRA",
        id=str(safra_id),
        label="SAFRA • SOJA",
        safra_id=safra_id,
        area_total_ha=20.0,
        hectares_totais=10.0,
        horas_totais=5.0,
        quantidade_operacoes=2,
        quantidade_jornadas=1,
        quantidade_apontamentos=1,
        custo_operacional_total=6000.0,
        custo_operacional_por_hectare=300.0,
        custo_operacional_por_operacao=3000.0,
        horas_por_hectare=0.5,
        hectares_por_jornada=10.0,
        resultado_operacional=14000.0,
        resultado_por_hectare=700.0,
        margem_pct=70.0,
        sujeito_reconciliacao=False,
        warnings_relevantes=[],
    )
    return EficienciaOperacionalAgricolaResponse(
        tenant_id=uuid4(),
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        safra=item,
        production_units=[item],
        equipamentos=[item],
        operacoes=[item],
        ranking=[item],
        warnings=[],
        sujeito_reconciliacao=False,
    )


@pytest.mark.asyncio
async def test_eficiencia_v1_endpoint_delega_servico_e_nao_usa_legado(
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

    eficiencia_router = importlib.import_module("agricola.eficiencia.router")

    with (
        patch.object(eficiencia_router, "EficienciaOperacionalAgricolaV1Service", FakeService),
        patch("financeiro.services.relatorio_service.RelatorioService.dre", new=AsyncMock()) as legacy_report,
        patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", new=AsyncMock()) as legacy_lancamento,
    ):
        response = await client.get(
            "/api/v1/agricola/eficiencia/v1",
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
