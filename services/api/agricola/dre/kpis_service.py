from __future__ import annotations

from dataclasses import dataclass

from core.services.analytics_taxonomy import normalizar_severidade
from core.services.analytics_request_cache import (
    build_dre_kpi_cache_key,
    get_analytics_request_cache,
    record_analytics_cache_hit,
    record_analytics_cache_miss,
    record_analytics_service_call,
)

from .schemas import DREAgricolaKpis, DREAgricolaResponse, DREWarning


@dataclass(slots=True)
class AgricolaDreKpiService:
    """Deriva KPIs financeiros agrícolas diretamente da DRE v1 consolidada."""

    @staticmethod
    def calcular(
        dre: DREAgricolaResponse,
        *,
        area_total_ha: float,
        warnings: list[DREWarning],
    ) -> DREAgricolaKpis:
        record_analytics_service_call("agricola.dre.kpi.v1")
        cache_key = build_dre_kpi_cache_key(dre, area_total_ha=area_total_ha, warnings=warnings)
        cache = get_analytics_request_cache()
        if cache_key in cache:
            record_analytics_cache_hit("agricola.dre.kpi.v1")
            return cache[cache_key]
        record_analytics_cache_miss("agricola.dre.kpi.v1")

        custo_operacional_total = round(
            float(dre.custos_diretos or 0)
            + float(dre.custos_operacionais or 0)
            + float(dre.despesas_operacionais or 0),
            2,
        )
        margem_pct = (
            round((float(dre.resultado_operacional or 0) / float(dre.receita_liquida or 0)) * 100, 2)
            if float(dre.receita_liquida or 0) > 0
            else None
        )
        receita_por_hectare = round(float(dre.receita_liquida or 0) / area_total_ha, 2) if area_total_ha > 0 else None
        custo_por_hectare = round(custo_operacional_total / area_total_ha, 2) if area_total_ha > 0 else None
        resultado_por_hectare = (
            round(float(dre.resultado_operacional or 0) / area_total_ha, 2) if area_total_ha > 0 else None
        )
        warnings_relevantes = [
            warning.codigo
            for warning in warnings
            if normalizar_severidade(warning.severidade) in {"ATENCAO", "RISCO_ECONOMICO"}
        ]
        sujeito_reconciliacao = bool(warnings_relevantes)

        kpis = DREAgricolaKpis(
            area_total_ha=round(area_total_ha, 2),
            receita_liquida=round(float(dre.receita_liquida or 0), 2),
            custo_operacional_total=custo_operacional_total,
            margem_bruta=round(float(dre.margem_bruta or 0), 2),
            resultado_operacional=round(float(dre.resultado_operacional or 0), 2),
            margem_pct=margem_pct,
            custo_por_hectare=custo_por_hectare,
            receita_por_hectare=receita_por_hectare,
            resultado_por_hectare=resultado_por_hectare,
            sujeito_reconciliacao=sujeito_reconciliacao,
            observacao_reconciliacao="Valores sujeitos à reconciliação." if sujeito_reconciliacao else None,
            warnings_relevantes=warnings_relevantes,
        )
        cache[cache_key] = kpis
        return kpis
