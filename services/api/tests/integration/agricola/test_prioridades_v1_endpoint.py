from __future__ import annotations

import importlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from agricola.prioridades.schemas import (
    PrioridadeAgricolaHistoricoItem,
    PrioridadeAgricolaItem,
    PrioridadeAgricolaResponse,
    PrioridadeAgricolaResumo,
    PrioridadeAgricolaStatusResponse,
)


def _fake_response() -> PrioridadeAgricolaResponse:
    safra_id = uuid4()
    item = PrioridadeAgricolaItem(
        scope="SAFRA",
        id=f"RESULTADO_OPERACIONAL_NEGATIVO:SAFRA:{safra_id}",
        label="SAFRA • SOJA",
        tipo="RESULTADO_OPERACIONAL_NEGATIVO",
        severidade="PRIORIDADE_CRITICA",
        score_prioridade=100,
        origem="DIAGNOSTICO",
        origem_codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        origem_titulo="Resultado operacional negativo",
        impacto_estimado=12000.0,
        contexto_operacional="Resultado operacional negativo na safra.",
        contexto_economico="Prioridade econômica consolidada.",
        acao_sugerida="Revisar margem, receita e custo.",
        entidade_tipo="SAFRA",
        entidade_id=str(safra_id),
        entidade_label="SAFRA • SOJA",
        warnings_relevantes=["RESULTADO_OPERACIONAL_NEGATIVO"],
        recorrencia=4,
        fontes_relacionadas=["DIAGNOSTICO", "RECOMENDACAO", "BENCHMARK", "WARNING"],
        posicao=1,
    )
    return PrioridadeAgricolaResponse(
        tenant_id=uuid4(),
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        prioridades=[item],
        resumo=PrioridadeAgricolaResumo(total=1, nova=1, prioridade_critica=1, por_origem={"DIAGNOSTICO": 1}, por_tipo={"RESULTADO_OPERACIONAL_NEGATIVO": 1}),
        warnings=[],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="prioridades sujeitas à reconciliação.",
    )


def _fake_status_response(prioridade_id: str) -> PrioridadeAgricolaStatusResponse:
    return PrioridadeAgricolaStatusResponse(
        prioridade_id=prioridade_id,
        prioridade_status_id=uuid4(),
        status_atual="EM_ANALISE",
        historico=[
            PrioridadeAgricolaHistoricoItem(
                id=uuid4(),
                prioridade_id=prioridade_id,
                status_anterior="NOVA",
                status_novo="EM_ANALISE",
                observacao="Observação curta",
                responsavel_id=uuid4(),
                responsavel_nome="Responsável",
                alterado_em=datetime.now(timezone.utc),
            )
        ],
        sujeito_reconciliacao=True,
    )


@pytest.mark.asyncio
async def test_prioridades_v1_endpoint_delega_servico_e_nao_usa_legado(
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

    router_module = importlib.import_module("agricola.prioridades.router")

    with (
        patch.object(router_module, "PrioridadesAgricolasV1Service", FakeService),
        patch("financeiro.services.relatorio_service.RelatorioService.dre", new=AsyncMock()) as legacy_report,
        patch("financeiro.services.lancamento_service.LancamentoService.gerar_dre", new=AsyncMock()) as legacy_lancamento,
    ):
        response = await client.get(
            "/api/v1/agricola/prioridades/v1",
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


@pytest.mark.asyncio
async def test_prioridades_v1_endpoint_atualiza_status_e_consulta_historico(
    client: AsyncClient,
    headers_agricola: dict,
):
    fake_response = _fake_response()
    prioridade_id = fake_response.prioridades[0].id
    fake_status = _fake_status_response(prioridade_id)
    captured: dict = {}

    class FakeService:
        def __init__(self, session, tenant_id):
            captured["tenant_id"] = tenant_id

        async def atualizar_status(self, **kwargs):
            captured["update_kwargs"] = kwargs
            return fake_status

        async def obter_status(self, **kwargs):
            captured["history_kwargs"] = kwargs
            return fake_status

    router_module = importlib.import_module("agricola.prioridades.router")

    with patch.object(router_module, "PrioridadesAgricolasV1Service", FakeService):
        response = await client.patch(
            f"/api/v1/agricola/prioridades/v1/{prioridade_id}/status",
            params={
                "safra_id": str(fake_response.safra_id),
                "production_unit_id": str(uuid4()),
                "unidade_produtiva_id": str(uuid4()),
            },
            json={"status": "EM_ANALISE", "observacao": "Em acompanhamento"},
            headers=headers_agricola,
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status_atual"] == "EM_ANALISE"
    assert captured["update_kwargs"]["status"] == "EM_ANALISE"
    assert captured["update_kwargs"]["observacao"] == "Em acompanhamento"
    assert captured["update_kwargs"]["prioridade_id"] == prioridade_id

    with patch.object(router_module, "PrioridadesAgricolasV1Service", FakeService):
        history_response = await client.get(
            f"/api/v1/agricola/prioridades/v1/{prioridade_id}/status",
            params={"safra_id": str(fake_response.safra_id)},
            headers=headers_agricola,
        )

    assert history_response.status_code == 200, history_response.text
    assert history_response.json()["status_atual"] == "EM_ANALISE"
