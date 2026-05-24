from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from agricola.benchmark.service import BenchmarkAgricolaV1Service
from agricola.dre.schemas import DREAgricolaKpis, DREAgricolaResponse, DREAgricolaSection, DREReconcilacaoMeta, DREWarning
from agricola.eficiencia.schemas import EficienciaOperacionalAgricolaResponse, EficienciaOperacionalItem
from agricola.rentabilidade.schemas import RentabilidadeAgricolaItem, RentabilidadeAgricolaResponse


def _warning(codigo: str, origem: str) -> DREWarning:
    return DREWarning(
        codigo=codigo,
        titulo=codigo.replace("_", " ").title(),
        severidade="INCONSISTENCIA_MODERADA",
        mensagem=f"Aviso oficial {codigo}",
        origem=origem,
        amostras=[str(uuid.uuid4())],
        meta={"codigo": codigo},
    )


def _dre_response(
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    warnings: list[DREWarning] | None = None,
) -> DREAgricolaResponse:
    warnings = warnings or []
    return DREAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        cultura="SOJA",
        receita_bruta=120000.0,
        deducoes=8000.0,
        receita_liquida=112000.0,
        custos_diretos=40000.0,
        custos_operacionais=15000.0,
        margem_bruta=72000.0,
        despesas_operacionais=12000.0,
        resultado_operacional=45000.0,
        kpis=DREAgricolaKpis(
            area_total_ha=30.0,
            receita_liquida=112000.0,
            custo_operacional_total=67000.0,
            margem_bruta=72000.0,
            resultado_operacional=45000.0,
            margem_pct=40.18,
            custo_por_hectare=2233.33,
            receita_por_hectare=3733.33,
            resultado_por_hectare=1500.0,
            sujeito_reconciliacao=bool(warnings),
            observacao_reconciliacao="benchmark sujeito à reconciliação." if warnings else None,
            warnings_relevantes=[warning.codigo for warning in warnings],
        ),
        receita=DREAgricolaSection(),
        custos_diretos_detalhe=DREAgricolaSection(),
        custos_operacionais_detalhe=DREAgricolaSection(),
        despesas_operacionais_detalhe=DREAgricolaSection(),
        warnings=warnings,
        reconciliacao=DREReconcilacaoMeta(),
    )


def _rentabilidade_response(
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    pu_a: uuid.UUID,
    pu_b: uuid.UUID,
) -> RentabilidadeAgricolaResponse:
    item_a = RentabilidadeAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=pu_a,
        label="Talhão A",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=10.0,
        resultado_operacional=7000.0,
        margem_pct=25.0,
        receita_liquida_por_hectare=1000.0,
        resultado_por_hectare=700.0,
        warnings_relevantes=["BENCHMARK_RENTA_A"],
    )
    item_b = RentabilidadeAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=pu_b,
        label="Talhão B",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=20.0,
        resultado_operacional=10000.0,
        margem_pct=30.0,
        receita_liquida_por_hectare=1100.0,
        resultado_por_hectare=500.0,
        warnings_relevantes=[],
    )
    item_a.posicao = 1
    item_b.posicao = 2

    safra = RentabilidadeAgricolaItem(
        scope="SAFRA",
        id=safra_id,
        label="SAFRA • SOJA",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=30.0,
        resultado_operacional=17000.0,
        margem_pct=27.5,
        receita_liquida_por_hectare=1066.67,
        resultado_por_hectare=566.67,
        sujeito_reconciliacao=True,
        observacao_reconciliacao="benchmark sujeito à reconciliação.",
        warnings_relevantes=["BENCHMARK_RENTA_A"],
    )

    return RentabilidadeAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=safra,
        production_units=[item_a, item_b],
        ranking=[item_b, item_a],
        warnings=[_warning("BENCHMARK_RENTA_A", "rentabilidade_v1")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="benchmark sujeito à reconciliação.",
    )


def _eficiencia_response(
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    pu_a: uuid.UUID,
    pu_b: uuid.UUID,
) -> EficienciaOperacionalAgricolaResponse:
    item_a = EficienciaOperacionalItem(
        scope="PRODUCTION_UNIT",
        id=str(pu_a),
        label="Talhão A",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=pu_a,
        area_total_ha=10.0,
        hectares_totais=12.0,
        horas_totais=12.0,
        quantidade_operacoes=3,
        quantidade_jornadas=2,
        quantidade_apontamentos=3,
        custo_operacional_total=3500.0,
        custo_operacional_por_hectare=350.0,
        custo_operacional_por_operacao=1166.67,
        horas_por_hectare=1.0,
        hectares_por_jornada=6.0,
        resultado_operacional=7000.0,
        resultado_por_hectare=700.0,
        margem_pct=25.0,
        warnings_relevantes=["BENCHMARK_EFICIENCIA_A"],
    )
    item_b = EficienciaOperacionalItem(
        scope="PRODUCTION_UNIT",
        id=str(pu_b),
        label="Talhão B",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=pu_b,
        area_total_ha=20.0,
        hectares_totais=18.0,
        horas_totais=10.0,
        quantidade_operacoes=4,
        quantidade_jornadas=2,
        quantidade_apontamentos=4,
        custo_operacional_total=6000.0,
        custo_operacional_por_hectare=300.0,
        custo_operacional_por_operacao=1500.0,
        horas_por_hectare=0.5,
        hectares_por_jornada=9.0,
        resultado_operacional=10000.0,
        resultado_por_hectare=500.0,
        margem_pct=30.0,
        warnings_relevantes=[],
    )
    item_a.posicao = 1
    item_b.posicao = 2

    safra = EficienciaOperacionalItem(
        scope="SAFRA",
        id=str(safra_id),
        label="SAFRA • SOJA",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=30.0,
        hectares_totais=30.0,
        horas_totais=22.0,
        quantidade_operacoes=7,
        quantidade_jornadas=4,
        quantidade_apontamentos=7,
        custo_operacional_total=9500.0,
        custo_operacional_por_hectare=316.67,
        custo_operacional_por_operacao=1357.14,
        horas_por_hectare=0.73,
        hectares_por_jornada=7.5,
        resultado_operacional=17000.0,
        resultado_por_hectare=566.67,
        margem_pct=27.5,
        sujeito_reconciliacao=True,
        observacao_reconciliacao="benchmark sujeito à reconciliação.",
        warnings_relevantes=["BENCHMARK_EFICIENCIA_A"],
    )

    return EficienciaOperacionalAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=safra,
        production_units=[item_b, item_a],
        equipamentos=[],
        operacoes=[],
        ranking=[item_b, item_a],
        warnings=[_warning("BENCHMARK_EFICIENCIA_A", "eficiencia_v1")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="benchmark sujeito à reconciliação.",
    )


@pytest.mark.asyncio
async def test_benchmark_v1_service_rankings_warnings_e_tenant_isolation():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    pu_a = uuid.uuid4()
    pu_b = uuid.uuid4()
    session = AsyncMock()
    captured = {}

    class FakeDreService:
        def __init__(self, session, tenant_id):
            captured["dre_tenant_id"] = tenant_id

        async def gerar(self, **kwargs):
            captured["dre_kwargs"] = kwargs
            return _dre_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                warnings=[_warning("BENCHMARK_DRE_WARN", "dre_v1")],
            )

    class FakeRentabilidadeService:
        def __init__(self, session, tenant_id):
            captured["rent_tenant_id"] = tenant_id

        async def gerar(self, **kwargs):
            captured["rent_kwargs"] = kwargs
            return _rentabilidade_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_a=pu_a,
                pu_b=pu_b,
            )

    class FakeEficienciaService:
        def __init__(self, session, tenant_id):
            captured["ef_tenant_id"] = tenant_id

        async def gerar(self, **kwargs):
            captured["ef_kwargs"] = kwargs
            return _eficiencia_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_a=pu_a,
                pu_b=pu_b,
            )

    with (
        patch("agricola.benchmark.service.DREAgricolaV1Service", FakeDreService),
        patch("agricola.benchmark.service.RentabilidadeAgricolaV1Service", FakeRentabilidadeService),
        patch("agricola.benchmark.service.EficienciaOperacionalAgricolaV1Service", FakeEficienciaService),
    ):
        svc = BenchmarkAgricolaV1Service(session, tenant_id)
        response = await svc.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=datetime(2026, 1, 1, tzinfo=timezone.utc).date(),
            data_fim=datetime(2026, 3, 31, tzinfo=timezone.utc).date(),
        )

    assert captured["dre_tenant_id"] == tenant_id
    assert captured["rent_tenant_id"] == tenant_id
    assert captured["ef_tenant_id"] == tenant_id
    assert response.sujeito_reconciliacao is True
    assert response.observacao_reconciliacao == "benchmark sujeito à reconciliação."
    assert response.ranking[0].id == pu_a
    assert response.ranking[0].destaque == "MELHOR"
    assert response.ranking[-1].id == pu_b
    assert response.ranking[-1].destaque == "PONTO_ATENCAO"
    assert response.destaques.melhor is not None
    assert response.destaques.ponto_atencao is not None
    assert response.production_units[0].custo_operacional_por_hectare == 350.0
    assert response.production_units[1].resultado_por_hectare == 500.0
    assert any(w.codigo == "BENCHMARK_DRE_WARN" for w in response.warnings)
