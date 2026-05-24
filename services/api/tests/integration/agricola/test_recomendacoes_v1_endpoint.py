from __future__ import annotations

import importlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from agricola.recomendacoes.schemas import RecomendacaoAgricolaItem, RecomendacaoAgricolaResponse, RecomendacaoAgricolaResumo


def _fake_response() -> RecomendacaoAgricolaResponse:
    safra_id = uuid4()
    item = RecomendacaoAgricolaItem(
        scope="SAFRA",
        id=str(safra_id),
        label="SAFRA • SOJA",
        tipo="REVISAO_CUSTO_HECTARE",
        severidade="ATENCAO",
        origem_diagnostica_codigo="CUSTO_HECTARE_ACIMA_MEDIA",
        origem_diagnostica_titulo="Custo/ha acima da média",
        contexto_operacional="Custo operacional elevado no recorte selecionado.",
        contexto_economico="Custo por hectare acima da referência oficial.",
        explicacao_objetiva="Revisão de custo por hectare necessária.",
        acao_sugerida="Revisar os componentes de custo por hectare.",
        entidade_tipo="SAFRA",
        entidade_id=str(safra_id),
        entidade_label="SAFRA • SOJA",
        warnings_relevantes=["CUSTO_HECTARE_ACIMA_MEDIA"],
        posicao=1,
    )
    return RecomendacaoAgricolaResponse(
        tenant_id=uuid4(),
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        recomendacoes=[item],
        resumo=RecomendacaoAgricolaResumo(total=1, nova=1, atencao=1, por_tipo={"REVISAO_CUSTO_HECTARE": 1}),
        warnings=[],
        sujeito_reconciliacao=False,
    )


@pytest.mark.asyncio
async def test_recomendacoes_v1_endpoint_delega_servico_e_nao_usa_legado(
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

    router_module = importlib.import_module("agricola.recomendacoes.router")

    with (
        patch.object(router_module, "RecomendacoesOperacionaisEconomicasAgricolaV1Service", FakeService),
        patch("financeiro.services.relatorio_service.RelatorioService.dre", new=AsyncMock()) as legacy_report,
        patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", new=AsyncMock()) as legacy_lancamento,
    ):
        response = await client.get(
            "/api/v1/agricola/recomendacoes/v1",
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
