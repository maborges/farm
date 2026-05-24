from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from agricola.benchmark.schemas import BenchmarkAgricolaDestaques, BenchmarkAgricolaItem, BenchmarkAgricolaResponse
from agricola.diagnostico.schemas import DiagnosticoAgricolaItem, DiagnosticoAgricolaResponse, DiagnosticoAgricolaResumo
from agricola.dre.schemas import DREAgricolaKpis, DREAgricolaResponse, DREAgricolaSection, DREReconcilacaoMeta
from agricola.dre.service import DREAgricolaV1Service
from agricola.eficiencia.schemas import EficienciaOperacionalAgricolaResponse, EficienciaOperacionalItem
from agricola.prioridades.service import PrioridadesAgricolasV1Service
from agricola.recomendacoes.schemas import RecomendacaoAgricolaItem, RecomendacaoAgricolaResponse, RecomendacaoAgricolaResumo
from agricola.rentabilidade.schemas import RentabilidadeAgricolaItem, RentabilidadeAgricolaResponse
from core.services.analytics_request_cache import (
    clear_analytics_request_cache,
    get_analytics_request_stats,
    record_analytics_cache_miss,
    record_analytics_service_call,
)


@pytest.fixture(autouse=True)
def _limpar_cache_e_stats():
    clear_analytics_request_cache()
    yield
    clear_analytics_request_cache()


def _fake_dre_response(*, tenant_id, safra_id, unidade_produtiva_id, production_unit_id) -> DREAgricolaResponse:
    return DREAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
        cultura="SOJA",
        production_unit_ids=[production_unit_id],
        receita_bruta=100.0,
        deducoes=0.0,
        receita_liquida=100.0,
        custos_diretos=20.0,
        custos_operacionais=10.0,
        margem_bruta=80.0,
        despesas_operacionais=5.0,
        resultado_operacional=65.0,
        receita=DREAgricolaSection(valor=100.0),
        custos_diretos_detalhe=DREAgricolaSection(valor=20.0),
        custos_operacionais_detalhe=DREAgricolaSection(valor=10.0),
        despesas_operacionais_detalhe=DREAgricolaSection(valor=5.0),
        kpis=DREAgricolaKpis(
            area_total_ha=10.0,
            receita_liquida=100.0,
            custo_operacional_total=35.0,
            margem_bruta=80.0,
            resultado_operacional=65.0,
            margem_pct=65.0,
            custo_por_hectare=3.5,
            receita_por_hectare=10.0,
            resultado_por_hectare=6.5,
            sujeito_reconciliacao=False,
            warnings_relevantes=[],
        ),
        warnings=[],
    )


def _fake_rentabilidade_response(*, tenant_id, safra_id, unidade_produtiva_id, production_unit_id) -> RentabilidadeAgricolaResponse:
    item = RentabilidadeAgricolaItem(
        scope="SAFRA",
        id=safra_id,
        label="Safra teste",
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=10.0,
        resultado_operacional=65.0,
        margem_pct=65.0,
        receita_liquida_por_hectare=10.0,
        resultado_por_hectare=6.5,
    )
    pu_item = RentabilidadeAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=production_unit_id,
        label="PU teste",
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=10.0,
        resultado_operacional=65.0,
        margem_pct=65.0,
        receita_liquida_por_hectare=10.0,
        resultado_por_hectare=6.5,
    )
    return RentabilidadeAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=item,
        production_units=[pu_item],
        ranking=[item, pu_item],
        warnings=[],
    )


def _fake_eficiencia_response(*, tenant_id, safra_id, unidade_produtiva_id, production_unit_id) -> EficienciaOperacionalAgricolaResponse:
    item = EficienciaOperacionalItem(
        scope="SAFRA",
        id=str(safra_id),
        label="Safra teste",
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=10.0,
        hectares_totais=10.0,
        horas_totais=5.0,
        quantidade_operacoes=1,
        quantidade_jornadas=1,
        quantidade_apontamentos=1,
        custo_operacional_total=35.0,
        custo_operacional_por_hectare=3.5,
        custo_operacional_por_operacao=35.0,
        horas_por_hectare=0.5,
        hectares_por_jornada=2.0,
        resultado_operacional=65.0,
        resultado_por_hectare=6.5,
        margem_pct=65.0,
    )
    return EficienciaOperacionalAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=item,
        production_units=[item],
        equipamentos=[],
        operacoes=[],
        ranking=[item],
        warnings=[],
    )


def _fake_benchmark_response(*, tenant_id, safra_id, unidade_produtiva_id, production_unit_id) -> BenchmarkAgricolaResponse:
    item = BenchmarkAgricolaItem(
        scope="SAFRA",
        id=safra_id,
        label="Safra teste",
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=10.0,
        resultado_operacional=65.0,
        margem_pct=65.0,
        receita_liquida_por_hectare=10.0,
        resultado_por_hectare=6.5,
        custo_operacional_total=35.0,
        custo_operacional_por_hectare=3.5,
        custo_operacional_por_operacao=35.0,
        horas_por_hectare=0.5,
        hectares_por_jornada=2.0,
        quantidade_operacoes=1,
        quantidade_jornadas=1,
        quantidade_apontamentos=1,
    )
    return BenchmarkAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=item,
        production_units=[item],
        ranking=[item],
        destaques=BenchmarkAgricolaDestaques(melhor=item, referencia=item, ponto_atencao=item),
        warnings=[],
    )


def _fake_diagnostico_response(*, tenant_id, safra_id, unidade_produtiva_id, production_unit_id) -> DiagnosticoAgricolaResponse:
    item = DiagnosticoAgricolaItem(
        scope="SAFRA",
        id=str(safra_id),
        label="Safra teste",
        codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        titulo="Resultado operacional negativo",
        severidade="RISCO_ECONOMICO",
        mensagem="teste",
        categoria="ECONOMICO",
    )
    return DiagnosticoAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        diagnosticos=[item],
        ranking=[item],
        resumo=DiagnosticoAgricolaResumo(total=1, info=0, atencao=0, risco_operacional=0, risco_economico=1),
        warnings=[],
    )


def _fake_recomendacoes_response(*, tenant_id, safra_id, unidade_produtiva_id, production_unit_id) -> RecomendacaoAgricolaResponse:
    item = RecomendacaoAgricolaItem(
        scope="SAFRA",
        id="RESULTADO_OPERACIONAL_NEGATIVO:1",
        label="Safra teste",
        tipo="INVESTIGACAO_MARGEM_NEGATIVA",
        severidade="RISCO_ECONOMICO",
        origem_diagnostica_codigo="RESULTADO_OPERACIONAL_NEGATIVO",
        origem_diagnostica_titulo="Resultado operacional negativo",
        contexto_operacional="teste",
        contexto_economico="teste",
        explicacao_objetiva="teste",
        acao_sugerida="teste",
        entidade_tipo="SAFRA",
        entidade_id=str(safra_id),
        entidade_label="Safra teste",
        warnings_relevantes=[],
    )
    return RecomendacaoAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        unidade_produtiva_id=unidade_produtiva_id,
        recomendacoes=[item],
        resumo=RecomendacaoAgricolaResumo(total=1, nova=1, visualizada=0, aceita=0, ignorada=0, info=0, atencao=0, risco_operacional=0, risco_economico=1, por_tipo={"INVESTIGACAO_MARGEM_NEGATIVA": 1}),
        warnings=[],
    )


@pytest.mark.asyncio
async def test_prioridades_medem_fanout_e_reaproveitam_cache():
    tenant_id = uuid4()
    safra_id = uuid4()
    unidade_produtiva_id = uuid4()
    production_unit_id = uuid4()
    session = SimpleNamespace()

    fake_dre = _fake_dre_response(
        tenant_id=tenant_id,
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
    )
    fake_rent = _fake_rentabilidade_response(
        tenant_id=tenant_id,
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
    )
    fake_eff = _fake_eficiencia_response(
        tenant_id=tenant_id,
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
    )
    fake_bench = _fake_benchmark_response(
        tenant_id=tenant_id,
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
    )
    fake_diag = _fake_diagnostico_response(
        tenant_id=tenant_id,
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
    )
    fake_recs = _fake_recomendacoes_response(
        tenant_id=tenant_id,
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=production_unit_id,
    )

    async def _fake_service_call(service_name: str, payload):
        record_analytics_service_call(service_name)
        record_analytics_cache_miss(service_name)
        return payload

    async def _fake_dre_call(*args, **kwargs):
        return await _fake_service_call("agricola.dre.v1", fake_dre)

    async def _fake_rent_call(*args, **kwargs):
        return await _fake_service_call("agricola.rentabilidade.v1", fake_rent)

    async def _fake_eff_call(*args, **kwargs):
        return await _fake_service_call("agricola.eficiencia.v1", fake_eff)

    async def _fake_bench_call(*args, **kwargs):
        return await _fake_service_call("agricola.benchmark.v1", fake_bench)

    async def _fake_diag_call(*args, **kwargs):
        return await _fake_service_call("agricola.diagnostico.v1", fake_diag)

    async def _fake_recs_call(*args, **kwargs):
        return await _fake_service_call("agricola.recomendacoes.v1", fake_recs)

    with (
        patch(
            "agricola.prioridades.service.DREAgricolaV1Service.gerar",
            new=AsyncMock(side_effect=_fake_dre_call),
        ) as dre_mock,
        patch(
            "agricola.prioridades.service.RentabilidadeAgricolaV1Service.gerar",
            new=AsyncMock(side_effect=_fake_rent_call),
        ) as rent_mock,
        patch(
            "agricola.prioridades.service.EficienciaOperacionalAgricolaV1Service.gerar",
            new=AsyncMock(side_effect=_fake_eff_call),
        ) as eff_mock,
        patch(
            "agricola.prioridades.service.BenchmarkAgricolaV1Service.gerar",
            new=AsyncMock(side_effect=_fake_bench_call),
        ) as bench_mock,
        patch(
            "agricola.prioridades.service.DiagnosticoOperacionalEconomicoAgricolaV1Service.gerar",
            new=AsyncMock(side_effect=_fake_diag_call),
        ) as diag_mock,
        patch(
            "agricola.prioridades.service.RecomendacoesOperacionaisEconomicasAgricolaV1Service.gerar",
            new=AsyncMock(side_effect=_fake_recs_call),
        ) as recs_mock,
        patch("agricola.prioridades.service.PrioridadesAgricolasV1Service._carregar_statuses", new=AsyncMock(return_value={})),
    ):
        svc = PrioridadesAgricolasV1Service(session, tenant_id)
        resposta_1 = await svc.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=None,
            data_fim=None,
        )
        resposta_2 = await svc.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=None,
            data_fim=None,
        )

    assert resposta_1.model_dump() == resposta_2.model_dump()
    assert dre_mock.await_count == 1
    assert rent_mock.await_count == 1
    assert eff_mock.await_count == 1
    assert bench_mock.await_count == 1
    assert diag_mock.await_count == 1
    assert recs_mock.await_count == 1

    stats = get_analytics_request_stats()
    assert stats["services"]["agricola.prioridades.v1"]["calls"] == 2
    assert stats["services"]["agricola.prioridades.v1"]["cache_hits"] == 1
    assert stats["services"]["agricola.prioridades.v1"]["cache_misses"] == 1
    assert stats["services"]["agricola.dre.v1"]["calls"] == 1
    assert stats["services"]["agricola.dre.v1"]["cache_misses"] == 1
    assert stats["cache_hits"] >= 1
    assert stats["cache_misses"] >= 6


@pytest.mark.asyncio
async def test_dre_stats_cache_hit_e_miss_sao_coerentes():
    tenant_id = uuid4()
    safra_id = uuid4()
    unidade_produtiva_id = uuid4()
    production_unit_id = uuid4()
    session = SimpleNamespace()

    async def _fake_resolver(*, safra_id, unidade_produtiva_id, production_unit_id, production_unit_ids, cultura, unidade_operacional_id):
        return {
            "production_units": [SimpleNamespace(id=production_unit_id, area_ha=10.0)],
            "production_unit_ids": [production_unit_id],
            "safra_id": safra_id,
            "safra": None,
            "cultura": cultura or "SOJA",
            "unidade_produtiva_id": unidade_produtiva_id,
            "unidade_operacional_id": unidade_operacional_id,
            "unidade_operacional_resolvida": None,
        }

    async def _fake_consolidar_receitas(*args, **kwargs):
        return DREAgricolaSection(valor=100.0), 0.0, [], 0

    async def _fake_consolidar_costs(*args, **kwargs):
        return DREAgricolaSection(valor=10.0)

    async def _fake_consolidar_despesas(*args, **kwargs):
        return DREAgricolaSection(valor=5.0), 0

    async def _fake_reconciliacao(*args, **kwargs):
        return DREReconcilacaoMeta()

    async def _fake_warnings(*args, **kwargs):
        return []

    with (
        patch.object(DREAgricolaV1Service, "_resolver_escopo", new=AsyncMock(side_effect=_fake_resolver)),
        patch.object(DREAgricolaV1Service, "_consolidar_receitas", new=AsyncMock(side_effect=_fake_consolidar_receitas)),
        patch.object(DREAgricolaV1Service, "_consolidar_costs", new=AsyncMock(side_effect=_fake_consolidar_costs)),
        patch.object(DREAgricolaV1Service, "_consolidar_despesas", new=AsyncMock(side_effect=_fake_consolidar_despesas)),
        patch.object(DREAgricolaV1Service, "_montar_reconciliacao", new=AsyncMock(side_effect=_fake_reconciliacao)),
        patch.object(DREAgricolaV1Service, "_montar_warnings", new=AsyncMock(side_effect=_fake_warnings)),
    ):
        svc = DREAgricolaV1Service(session, tenant_id)
        await svc.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=None,
            data_fim=None,
        )
        await svc.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=None,
            data_fim=None,
        )

    stats = get_analytics_request_stats()
    assert stats["services"]["agricola.dre.v1"]["calls"] == 2
    assert stats["services"]["agricola.dre.v1"]["cache_hits"] == 1
    assert stats["services"]["agricola.dre.v1"]["cache_misses"] == 1
