from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from agricola.benchmark.schemas import BenchmarkAgricolaDestaques, BenchmarkAgricolaItem, BenchmarkAgricolaResponse
from agricola.diagnostico.service import DiagnosticoOperacionalEconomicoAgricolaV1Service
from agricola.dre.schemas import DREAgricolaKpis, DREAgricolaResponse, DREAgricolaSection, DREReconcilacaoMeta, DREWarning
from agricola.eficiencia.schemas import EficienciaOperacionalAgricolaResponse, EficienciaOperacionalItem
from agricola.rentabilidade.schemas import RentabilidadeAgricolaItem, RentabilidadeAgricolaResponse


def _warning(codigo: str, origem: str) -> DREWarning:
    severidade = "RISCO_ECONOMICO" if "CUSTO" in codigo or "ALLOCATION" in codigo else "INCONSISTENCIA_MODERADA"
    return DREWarning(
        codigo=codigo,
        titulo=codigo.replace("_", " ").title(),
        severidade=severidade,
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
        receita_bruta=200000.0,
        deducoes=10000.0,
        receita_liquida=190000.0,
        custos_diretos=70000.0,
        custos_operacionais=40000.0,
        margem_bruta=120000.0,
        despesas_operacionais=50000.0,
        resultado_operacional=30000.0,
        kpis=DREAgricolaKpis(
            area_total_ha=50.0,
            receita_liquida=190000.0,
            custo_operacional_total=160000.0,
            margem_bruta=120000.0,
            resultado_operacional=30000.0,
            margem_pct=15.79,
            custo_por_hectare=3200.0,
            receita_por_hectare=3800.0,
            resultado_por_hectare=600.0,
            sujeito_reconciliacao=bool(warnings),
            observacao_reconciliacao="diagnóstico sujeito à reconciliação." if warnings else None,
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
        label="PU A",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=20.0,
        resultado_operacional=12000.0,
        margem_pct=18.0,
        receita_liquida_por_hectare=4000.0,
        resultado_por_hectare=600.0,
        warnings_relevantes=["CUSTO_HECTARE_ACIMA_MEDIA"],
    )
    item_b = RentabilidadeAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=pu_b,
        label="PU B",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=30.0,
        resultado_operacional=18000.0,
        margem_pct=12.0,
        receita_liquida_por_hectare=3600.0,
        resultado_por_hectare=450.0,
        warnings_relevantes=["OPERACAO_CUSTO_FORA_CURVA"],
    )
    item_a.posicao = 1
    item_b.posicao = 2

    safra = RentabilidadeAgricolaItem(
        scope="SAFRA",
        id=safra_id,
        label="SAFRA • SOJA",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=50.0,
        resultado_operacional=30000.0,
        margem_pct=15.79,
        receita_liquida_por_hectare=3800.0,
        resultado_por_hectare=600.0,
        sujeito_reconciliacao=True,
        observacao_reconciliacao="diagnóstico sujeito à reconciliação.",
        warnings_relevantes=["CUSTO_HECTARE_ACIMA_MEDIA"],
    )

    return RentabilidadeAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=safra,
        production_units=[item_a, item_b],
        ranking=[item_a, item_b],
        warnings=[_warning("CUSTO_HECTARE_ACIMA_MEDIA", "rentabilidade_v1")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="diagnóstico sujeito à reconciliação.",
    )


def _eficiencia_response(
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    pu_a: uuid.UUID,
    pu_b: uuid.UUID,
    equipamento_a: uuid.UUID,
    equipamento_b: uuid.UUID,
) -> EficienciaOperacionalAgricolaResponse:
    item_a = EficienciaOperacionalItem(
        scope="PRODUCTION_UNIT",
        id=str(pu_a),
        label="PU A",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=pu_a,
        area_total_ha=20.0,
        hectares_totais=18.0,
        horas_totais=24.0,
        quantidade_operacoes=3,
        quantidade_jornadas=2,
        quantidade_apontamentos=3,
        custo_operacional_total=64000.0,
        custo_operacional_por_hectare=3200.0,
        custo_operacional_por_operacao=21333.33,
        horas_por_hectare=1.2,
        hectares_por_jornada=10.0,
        resultado_operacional=12000.0,
        resultado_por_hectare=600.0,
        margem_pct=18.0,
        warnings_relevantes=["JORNADA_BAIXA_PRODUTIVIDADE"],
    )
    item_b = EficienciaOperacionalItem(
        scope="PRODUCTION_UNIT",
        id=str(pu_b),
        label="PU B",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        production_unit_id=pu_b,
        area_total_ha=30.0,
        hectares_totais=24.0,
        horas_totais=20.0,
        quantidade_operacoes=4,
        quantidade_jornadas=3,
        quantidade_apontamentos=4,
        custo_operacional_total=75000.0,
        custo_operacional_por_hectare=2500.0,
        custo_operacional_por_operacao=18750.0,
        horas_por_hectare=0.8,
        hectares_por_jornada=12.0,
        resultado_operacional=18000.0,
        resultado_por_hectare=450.0,
        margem_pct=12.0,
        warnings_relevantes=["OPERACAO_CUSTO_FORA_CURVA"],
    )
    item_a.posicao = 1
    item_b.posicao = 2

    equipamento_a_item = EficienciaOperacionalItem(
        scope="EQUIPMENT",
        id=str(equipamento_a),
        label="Trator A",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        equipamento_id=equipamento_a,
        area_total_ha=20.0,
        hectares_totais=18.0,
        horas_totais=24.0,
        quantidade_operacoes=2,
        quantidade_jornadas=2,
        quantidade_apontamentos=2,
        custo_operacional_total=16000.0,
        custo_operacional_por_hectare=800.0,
        resultado_operacional=0.0,
        resultado_por_hectare=0.0,
        margem_pct=0.0,
        warnings_relevantes=["EQUIPAMENTO_CUSTO_ELEVADO"],
    )
    equipamento_b_item = EficienciaOperacionalItem(
        scope="EQUIPMENT",
        id=str(equipamento_b),
        label="Trator B",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        equipamento_id=equipamento_b,
        area_total_ha=30.0,
        hectares_totais=24.0,
        horas_totais=20.0,
        quantidade_operacoes=2,
        quantidade_jornadas=1,
        quantidade_apontamentos=2,
        custo_operacional_total=9000.0,
        custo_operacional_por_hectare=300.0,
        resultado_operacional=0.0,
        resultado_por_hectare=0.0,
        margem_pct=0.0,
        warnings_relevantes=[],
    )

    operacao_a = EficienciaOperacionalItem(
        scope="OPERATION",
        id="operacao-a",
        label="Pulverização",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        operacao_id=uuid.uuid4(),
        area_total_ha=20.0,
        hectares_totais=18.0,
        horas_totais=12.0,
        quantidade_operacoes=1,
        quantidade_jornadas=1,
        quantidade_apontamentos=1,
        custo_operacional_total=12000.0,
        custo_operacional_por_hectare=600.0,
        resultado_operacional=0.0,
        resultado_por_hectare=0.0,
        margem_pct=0.0,
        warnings_relevantes=["OPERACAO_CUSTO_FORA_CURVA"],
    )
    operacao_b = EficienciaOperacionalItem(
        scope="OPERATION",
        id="operacao-b",
        label="Plantio",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        operacao_id=uuid.uuid4(),
        area_total_ha=30.0,
        hectares_totais=24.0,
        horas_totais=20.0,
        quantidade_operacoes=1,
        quantidade_jornadas=1,
        quantidade_apontamentos=1,
        custo_operacional_total=6000.0,
        custo_operacional_por_hectare=200.0,
        resultado_operacional=0.0,
        resultado_por_hectare=0.0,
        margem_pct=0.0,
        warnings_relevantes=[],
    )

    safra = EficienciaOperacionalItem(
        scope="SAFRA",
        id=str(safra_id),
        label="SAFRA • SOJA",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=50.0,
        hectares_totais=42.0,
        horas_totais=44.0,
        quantidade_operacoes=7,
        quantidade_jornadas=5,
        quantidade_apontamentos=7,
        custo_operacional_total=81000.0,
        custo_operacional_por_hectare=1620.0,
        custo_operacional_por_operacao=11571.43,
        horas_por_hectare=0.88,
        hectares_por_jornada=8.4,
        resultado_operacional=30000.0,
        resultado_por_hectare=600.0,
        margem_pct=15.79,
        sujeito_reconciliacao=True,
        observacao_reconciliacao="diagnóstico sujeito à reconciliação.",
        warnings_relevantes=["JORNADA_BAIXA_PRODUTIVIDADE"],
    )

    return EficienciaOperacionalAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=safra,
        production_units=[item_a, item_b],
        equipamentos=[equipamento_a_item, equipamento_b_item],
        operacoes=[operacao_a, operacao_b],
        ranking=[item_a, item_b],
        warnings=[_warning("JORNADA_BAIXA_PRODUTIVIDADE", "eficiencia_v1")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="diagnóstico sujeito à reconciliação.",
    )


def _benchmark_response(
    *,
    tenant_id: uuid.UUID,
    safra_id: uuid.UUID,
    unidade_produtiva_id: uuid.UUID,
    pu_a: uuid.UUID,
    pu_b: uuid.UUID,
) -> BenchmarkAgricolaResponse:
    item_a = BenchmarkAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=pu_a,
        label="PU A",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=20.0,
        resultado_operacional=12000.0,
        margem_pct=18.0,
        receita_liquida_por_hectare=4000.0,
        resultado_por_hectare=600.0,
        custo_operacional_total=64000.0,
        custo_operacional_por_hectare=3200.0,
        custo_operacional_por_operacao=21333.33,
        horas_por_hectare=1.2,
        hectares_por_jornada=10.0,
        quantidade_operacoes=3,
        quantidade_jornadas=2,
        quantidade_apontamentos=3,
        warnings_relevantes=["CUSTO_HECTARE_ACIMA_MEDIA", "JORNADA_BAIXA_PRODUTIVIDADE"],
        posicao=1,
    )
    item_b = BenchmarkAgricolaItem(
        scope="PRODUCTION_UNIT",
        id=pu_b,
        label="PU B",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=30.0,
        resultado_operacional=18000.0,
        margem_pct=12.0,
        receita_liquida_por_hectare=3600.0,
        resultado_por_hectare=450.0,
        custo_operacional_total=75000.0,
        custo_operacional_por_hectare=2500.0,
        custo_operacional_por_operacao=18750.0,
        horas_por_hectare=0.8,
        hectares_por_jornada=12.0,
        quantidade_operacoes=4,
        quantidade_jornadas=3,
        quantidade_apontamentos=4,
        warnings_relevantes=["OPERACAO_CUSTO_FORA_CURVA"],
        posicao=2,
    )
    safra = BenchmarkAgricolaItem(
        scope="SAFRA",
        id=safra_id,
        label="SAFRA • SOJA",
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        area_total_ha=50.0,
        resultado_operacional=30000.0,
        margem_pct=15.79,
        receita_liquida_por_hectare=3800.0,
        resultado_por_hectare=600.0,
        custo_operacional_total=81000.0,
        custo_operacional_por_hectare=1620.0,
        custo_operacional_por_operacao=11571.43,
        horas_por_hectare=0.88,
        hectares_por_jornada=8.4,
        quantidade_operacoes=7,
        quantidade_jornadas=5,
        quantidade_apontamentos=7,
        sujeito_reconciliacao=True,
        observacao_reconciliacao="diagnóstico sujeito à reconciliação.",
        warnings_relevantes=["CUSTO_HECTARE_ACIMA_MEDIA"],
    )

    return BenchmarkAgricolaResponse(
        tenant_id=tenant_id,
        gerado_em=datetime.now(timezone.utc),
        safra_id=safra_id,
        unidade_produtiva_id=unidade_produtiva_id,
        safra=safra,
        production_units=[item_a, item_b],
        ranking=[item_a, item_b],
        destaques=BenchmarkAgricolaDestaques(melhor=item_a, referencia=item_b, ponto_atencao=item_b),
        warnings=[_warning("CUSTO_HECTARE_ACIMA_MEDIA", "benchmark"), _warning("JORNADA_BAIXA_PRODUTIVIDADE", "benchmark")],
        sujeito_reconciliacao=True,
        observacao_reconciliacao="diagnóstico sujeito à reconciliação.",
    )


@pytest.mark.asyncio
async def test_diagnostico_v1_service_detecta_desvios_rankings_e_tenant_isolation():
    tenant_id = uuid.uuid4()
    safra_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    pu_a = uuid.uuid4()
    pu_b = uuid.uuid4()
    equipamento_a = uuid.uuid4()
    equipamento_b = uuid.uuid4()
    session = AsyncMock()
    captured = {}

    class FakeDreService:
        def __init__(self, session, tenant_id):
            captured.setdefault("tenant_ids", []).append(tenant_id)

        async def gerar(self, **kwargs):
            captured["dre_kwargs"] = kwargs
            return _dre_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                warnings=[_warning("CUSTO_HECTARE_ACIMA_MEDIA", "dre_v1")],
            )

    class FakeRentabilidadeService:
        def __init__(self, session, tenant_id):
            captured.setdefault("tenant_ids", []).append(tenant_id)

        async def gerar(self, **kwargs):
            captured["rentabilidade_kwargs"] = kwargs
            return _rentabilidade_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_a=pu_a,
                pu_b=pu_b,
            )

    class FakeEficienciaService:
        def __init__(self, session, tenant_id):
            captured.setdefault("tenant_ids", []).append(tenant_id)

        async def gerar(self, **kwargs):
            captured["eficiencia_kwargs"] = kwargs
            return _eficiencia_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_a=pu_a,
                pu_b=pu_b,
                equipamento_a=equipamento_a,
                equipamento_b=equipamento_b,
            )

    class FakeBenchmarkService:
        def __init__(self, session, tenant_id):
            captured.setdefault("tenant_ids", []).append(tenant_id)

        async def gerar(self, **kwargs):
            captured["benchmark_kwargs"] = kwargs
            return _benchmark_response(
                tenant_id=tenant_id,
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                pu_a=pu_a,
                pu_b=pu_b,
            )

    class FakeAlertasService:
        def __init__(self, session, tenant_id):
            captured.setdefault("tenant_ids", []).append(tenant_id)

        async def detectar_inconsistencias_operacionais(self):
            return [
                SimpleNamespace(
                    codigo="OPERACAO_CUSTO_FORA_CURVA",
                    titulo="Operação com custo fora da curva",
                    severidade="INCONSISTENCIA_MODERADA",
                    origem="operacoes_agricolas",
                    total=2,
                    mensagem="Operação com custo elevado.",
                    amostras=["op-1"],
                    meta={},
                ),
                SimpleNamespace(
                    codigo="JORNADA_BAIXA_PRODUTIVIDADE",
                    titulo="Baixa produtividade por jornada",
                    severidade="INCONSISTENCIA_MODERADA",
                    origem="jornadas",
                    total=2,
                    mensagem="Baixa produtividade por jornada.",
                    amostras=["jo-1"],
                    meta={},
                ),
            ]

        async def detectar_inconsistencias_reconciliacao_economica(self):
            return [
                SimpleNamespace(
                    codigo="CUSTO_HECTARE_ACIMA_MEDIA",
                    titulo="Custo/ha acima da média",
                    severidade="RISCO_ECONOMICO",
                    origem="dre_v1",
                    total=2,
                    mensagem="Custo elevado.",
                    amostras=["ec-1"],
                    meta={},
                ),
            ]

    with (
        patch("agricola.diagnostico.service.DREAgricolaV1Service", FakeDreService),
        patch("agricola.diagnostico.service.RentabilidadeAgricolaV1Service", FakeRentabilidadeService),
        patch("agricola.diagnostico.service.EficienciaOperacionalAgricolaV1Service", FakeEficienciaService),
        patch("agricola.diagnostico.service.BenchmarkAgricolaV1Service", FakeBenchmarkService),
        patch("agricola.diagnostico.service.AlertasAgricolasService", FakeAlertasService),
    ):
        service = DiagnosticoOperacionalEconomicoAgricolaV1Service(session, tenant_id)
        response = await service.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=pu_a,
            data_inicio=datetime(2026, 1, 1).date(),
            data_fim=datetime(2026, 1, 31).date(),
        )

    assert response.tenant_id == tenant_id
    assert response.safra_id == safra_id
    assert response.production_unit_id == pu_a
    assert response.unidade_produtiva_id == unidade_produtiva_id
    assert response.sujeito_reconciliacao is True
    assert response.resumo.total == len(response.diagnosticos)
    assert response.resumo.risco_economico >= 1
    assert response.resumo.risco_operacional >= 1
    assert any(item.codigo == "RECORRENCIA_WARNING_ECONOMICO" for item in response.diagnosticos)
    assert any(item.codigo == "RECORRENCIA_INCONSISTENCIA_OPERACIONAL" for item in response.diagnosticos)
    assert any(item.codigo == "PRODUCTION_UNIT_BAIXA_EFICIENCIA" and item.scope == "PRODUCTION_UNIT" for item in response.diagnosticos)
    assert any(item.codigo == "EQUIPAMENTO_CUSTO_ELEVADO" for item in response.diagnosticos)
    assert any(item.codigo == "OPERACAO_CUSTO_FORA_CURVA" for item in response.diagnosticos)
    assert response.warnings
    assert any(warning.codigo == "CUSTO_HECTARE_ACIMA_MEDIA" for warning in response.warnings)
    assert len(captured["tenant_ids"]) >= 5
    assert captured["dre_kwargs"]["safra_id"] == safra_id
    assert captured["rentabilidade_kwargs"]["production_unit_id"] == pu_a
    assert captured["eficiencia_kwargs"]["unidade_produtiva_id"] == unidade_produtiva_id
    assert captured["benchmark_kwargs"]["data_inicio"].isoformat() == "2026-01-01"

