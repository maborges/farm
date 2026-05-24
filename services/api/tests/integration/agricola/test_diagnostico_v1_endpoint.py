from __future__ import annotations

import importlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from agricola.diagnostico.schemas import DiagnosticoAgricolaItem, DiagnosticoAgricolaResponse, DiagnosticoAgricolaResumo


def _fake_response() -> DiagnosticoAgricolaResponse:
    safra_id = uuid4()
    item = DiagnosticoAgricolaItem(
        scope="SAFRA",
        id=str(safra_id),
        label="SAFRA • SOJA",
        codigo="MARGEM_ABAIXO_MEDIA_TENANT",
        titulo="Margem abaixo da média do tenant",
        severidade="ATENCAO",
        mensagem="Margem abaixo da média oficial.",
        categoria="ECONOMICO",
        valor_observado=12.3,
        valor_referencia=15.0,
        desvio_pct=-18.0,
        warnings_relevantes=["CUSTO_HECTARE_ACIMA_MEDIA"],
        posicao=1,
    )
    return DiagnosticoAgricolaResponse(
        tenant_id=uuid4(),
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        diagnosticos=[item],
        ranking=[item],
        resumo=DiagnosticoAgricolaResumo(total=1, info=0, atencao=1, risco_operacional=0, risco_economico=0),
        warnings=[],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="diagnósticos sujeitos à reconciliação.",
    )


@pytest.mark.asyncio
async def test_diagnostico_v1_endpoint_delega_servico_e_nao_usa_legado(
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

    diagnostico_router = importlib.import_module("agricola.diagnostico.router")

    with (
        patch.object(diagnostico_router, "DiagnosticoOperacionalEconomicoAgricolaV1Service", FakeService),
        patch("financeiro.services.relatorio_service.RelatorioService.dre", new=AsyncMock()) as legacy_report,
        patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", new=AsyncMock()) as legacy_lancamento,
    ):
        response = await client.get(
            "/api/v1/agricola/diagnostico/v1",
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
    assert payload["sujeito_reconciliacao"] is True
    assert captured["kwargs"]["safra_id"] == fake_response.safra_id
    assert captured["kwargs"]["data_inicio"].isoformat() == "2026-01-01"
    assert captured["kwargs"]["data_fim"].isoformat() == "2026-01-31"
    legacy_report.assert_not_called()
    legacy_lancamento.assert_not_called()

