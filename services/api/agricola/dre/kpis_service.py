from __future__ import annotations

from dataclasses import dataclass

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
            if warning.severidade in {"INCONSISTENCIA_MODERADA", "RISCO_ECONOMICO"}
        ]
        sujeito_reconciliacao = bool(warnings_relevantes)

        return DREAgricolaKpis(
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
