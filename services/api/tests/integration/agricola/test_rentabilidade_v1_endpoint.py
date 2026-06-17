from __future__ import annotations

import importlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from agricola.dre.schemas import DREAgricolaKpis, DREAgricolaResponse, DREAgricolaSection, DREReconcilacaoMeta
from agricola.rentabilidade.schemas import RentabilidadeAgricolaItem, RentabilidadeAgricolaResponse


def _fake_response() -> RentabilidadeAgricolaResponse:
    item = RentabilidadeAgricolaItem(
        scope="SAFRA",
        id=uuid4(),
        label="SAFRA • SOJA",
        safra_id=uuid4(),
        area_total_ha=10.0,
        resultado_operacional=1000.0,
        margem_pct=25.0,
        receita_liquida_por_hectare=400.0,
        resultado_por_hectare=100.0,
    )
    return RentabilidadeAgricolaResponse(
        tenant_id=uuid4(),
        gerado_em=datetime.now(timezone.utc),
        safra_id=item.safra_id,
        safra=item,
        production_units=[item],
        ranking=[item],
        warnings=[],
        sujeito_reconciliacao=False,
    )


@pytest.mark.asyncio
async def test_rentabilidade_v1_endpoint_delega_servico_e_nao_usa_legado(
    client: AsyncClient,
    headers_agricola: dict,
):
    fake_response = _fake_response()
    captured = {}

    class FakeService:
        def __init__(self, session, tenant_id):
            captured["tenant_id"] = tenant_id
            captured["session_type"] = type(session).__name__

        async def gerar(self, **kwargs):
            captured["kwargs"] = kwargs
            return fake_response

    rent_router = importlib.import_module("agricola.rentabilidade.router")

    with (
        patch.object(rent_router, "RentabilidadeAgricolaV1Service", FakeService),
        patch("financeiro.services.relatorio_service.RelatorioService.dre", new=AsyncMock()) as legacy_report,
        patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", new=AsyncMock()) as legacy_lancamento,
    ):
        response = await client.get(
            "/api/v1/agricola/rentabilidade/v1",
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

@pytest.mark.asyncio
async def test_rentabilidade_service_kpis_fisicos():
    from agricola.rentabilidade.service import RentabilidadeAgricolaV1Service
    from unittest.mock import MagicMock
    
    svc = RentabilidadeAgricolaV1Service(AsyncMock(), uuid4())
    dre = MagicMock()
    dre.custos_diretos = 100.0
    dre.custos_operacionais = 50.0
    dre.despesas_operacionais = 10.0
    dre.receita_liquida = 1000.0
    dre.margem_bruta = 900.0
    dre.resultado_operacional = 840.0
    
    
    kpis_zero = svc._montar_kpis_fisicos(dre, 0.0, "INDISPONIVEL")
    assert kpis_zero.quantidade_sacas == 0.0
    assert kpis_zero.lucro_por_saca is None
    assert kpis_zero.base_volume == "INDISPONIVEL"
    
    kpis_real = svc._montar_kpis_fisicos(dre, 100.0, "REAL")
    assert kpis_real.quantidade_sacas == 100.0
    assert kpis_real.base_volume == "REAL"
    assert kpis_real.custo_por_saca == 0.50
    assert kpis_real.lucro_por_saca == 8.40
    assert kpis_real.preco_equilibrio == 1.60

