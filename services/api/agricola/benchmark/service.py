from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from agricola.dre import AgricolaDreKpiService, DREAgricolaV1Service
from agricola.dre.schemas import DREWarning
from agricola.eficiencia import EficienciaOperacionalAgricolaV1Service
from agricola.rentabilidade import RentabilidadeAgricolaV1Service
from agricola.safras.models import Safra
from core.base_service import BaseService
from core.services.analytics_request_cache import (
    build_analytics_scope_key,
    build_analytics_value_key,
    get_analytics_request_cache,
)

from .schemas import BenchmarkAgricolaDestaques, BenchmarkAgricolaItem, BenchmarkAgricolaResponse


class BenchmarkAgricolaV1Service(BaseService[Safra]):
    """Camada oficial de benchmark agrícola derivada apenas dos serviços oficiais consolidados."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(Safra, session, tenant_id)

    async def gerar(
        self,
        *,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None = None,
        production_unit_id: UUID | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> BenchmarkAgricolaResponse:
        cache_key = build_analytics_value_key(
            "agricola.benchmark.v1",
            build_analytics_scope_key(
                self.tenant_id,
                safra_id,
                production_unit_id,
                unidade_produtiva_id,
                data_inicio,
                data_fim,
            ),
        )
        cache = get_analytics_request_cache()
        if cache_key in cache:
            return cache[cache_key]

        dre = await DREAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        kpis = dre.kpis or AgricolaDreKpiService.calcular(
            dre,
            area_total_ha=self._area_total(dre),
            warnings=dre.warnings,
        )
        rentabilidade = await RentabilidadeAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        eficiencia = await EficienciaOperacionalAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        safra_item = self._montar_item_safra(
            dre,
            kpis=kpis,
            rentabilidade_item=rentabilidade.safra,
            eficiencia_item=eficiencia.safra,
            safra_id=safra_id,
        )

        merged_units = self._mesclar_unidades(
            rentabilidade_items=rentabilidade.production_units,
            eficiencia_items=eficiencia.production_units,
            safra_id=safra_id,
        )
        ranking = self._rankear(merged_units)
        destaques = self._montar_destaques(ranking)

        source_warnings = [*dre.warnings, *rentabilidade.warnings, *eficiencia.warnings]
        source_codes = {warning.codigo for warning in source_warnings}
        extra_warning_codes = sorted(
            {
                code
                for item in merged_units
                for code in item.warnings_relevantes
                if code not in source_codes
            }
        )
        extra_warnings = [
            DREWarning(
                codigo=code,
                titulo=code.replace("_", " ").title(),
                severidade="INCONSISTENCIA_MODERADA",
                mensagem="Indicador oficial sujeito à reconciliação.",
                origem="benchmark",
            )
            for code in extra_warning_codes
        ]
        warnings = self._dedupe_warnings([
            *source_warnings,
            *extra_warnings,
        ])
        sujeito_reconciliacao = bool(
            safra_item.sujeito_reconciliacao
            or any(item.sujeito_reconciliacao for item in merged_units)
            or warnings
        )
        observacao = "benchmark sujeito à reconciliação." if sujeito_reconciliacao else None

        response = BenchmarkAgricolaResponse(
            tenant_id=self.tenant_id,
            gerado_em=datetime.now(timezone.utc),
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            safra=safra_item,
            production_units=merged_units,
            ranking=ranking,
            destaques=destaques,
            warnings=warnings,
            sujeito_reconciliacao=sujeito_reconciliacao,
            observacao_reconciliacao=observacao,
        )
        cache[cache_key] = response
        return response

    def _montar_item_safra(
        self,
        dre,
        *,
        kpis,
        rentabilidade_item,
        eficiencia_item,
        safra_id: UUID,
    ) -> BenchmarkAgricolaItem:
        warnings = self._merge_warning_codes(
            rentabilidade_item.warnings_relevantes if rentabilidade_item else [],
            eficiencia_item.warnings_relevantes if eficiencia_item else [],
            dre.warnings,
        )
        return BenchmarkAgricolaItem(
            scope="SAFRA",
            id=safra_id,
            label=rentabilidade_item.label if rentabilidade_item else (eficiencia_item.label if eficiencia_item else self._build_label("SAFRA", dre.cultura, None)),
            safra_id=safra_id,
            production_unit_id=rentabilidade_item.production_unit_id if rentabilidade_item else None,
            unidade_produtiva_id=rentabilidade_item.unidade_produtiva_id if rentabilidade_item else eficiencia_item.unidade_produtiva_id if eficiencia_item else None,
            area_total_ha=float(kpis.area_total_ha or 0.0),
            resultado_operacional=float(kpis.resultado_operacional or 0.0),
            margem_pct=kpis.margem_pct,
            receita_liquida_por_hectare=kpis.receita_por_hectare,
            resultado_por_hectare=kpis.resultado_por_hectare,
            custo_operacional_total=float(kpis.custo_operacional_total or 0.0),
            custo_operacional_por_hectare=kpis.custo_por_hectare,
            custo_operacional_por_operacao=eficiencia_item.custo_operacional_por_operacao if eficiencia_item else None,
            horas_por_hectare=eficiencia_item.horas_por_hectare if eficiencia_item else None,
            hectares_por_jornada=eficiencia_item.hectares_por_jornada if eficiencia_item else None,
            quantidade_operacoes=eficiencia_item.quantidade_operacoes if eficiencia_item else 0,
            quantidade_jornadas=eficiencia_item.quantidade_jornadas if eficiencia_item else 0,
            quantidade_apontamentos=eficiencia_item.quantidade_apontamentos if eficiencia_item else 0,
            sujeito_reconciliacao=bool(kpis.sujeito_reconciliacao or warnings),
            observacao_reconciliacao="benchmark sujeito à reconciliação." if warnings or kpis.sujeito_reconciliacao else None,
            warnings_relevantes=warnings,
        )

    def _mesclar_unidades(
        self,
        *,
        rentabilidade_items,
        eficiencia_items,
        safra_id: UUID,
    ) -> list[BenchmarkAgricolaItem]:
        rent_by_id = {self._item_key(item): item for item in rentabilidade_items}
        eff_by_id = {self._item_key(item): item for item in eficiencia_items}
        merged: list[BenchmarkAgricolaItem] = []
        all_ids = sorted(set(rent_by_id) | set(eff_by_id), key=lambda item_id: (
            rent_by_id.get(item_id).label if rent_by_id.get(item_id) else eff_by_id.get(item_id).label,
        ))

        for item_id in all_ids:
            rent_item = rent_by_id.get(item_id)
            eff_item = eff_by_id.get(item_id)
            merged.append(self._merge_item(rent_item, eff_item, safra_id=safra_id))
        return merged

    def _merge_item(self, rent_item, eff_item, *, safra_id: UUID) -> BenchmarkAgricolaItem:
        warnings = self._merge_warning_codes(
            rent_item.warnings_relevantes if rent_item else [],
            eff_item.warnings_relevantes if eff_item else [],
        )
        area_total_ha = float((rent_item.area_total_ha if rent_item else eff_item.area_total_ha if eff_item else 0.0) or 0.0)
        custo_operacional_total = float(eff_item.custo_operacional_total if eff_item else 0.0)
        resultado_operacional = float(rent_item.resultado_operacional if rent_item else eff_item.resultado_operacional if eff_item else 0.0)
        return BenchmarkAgricolaItem(
            scope="PRODUCTION_UNIT",
            id=rent_item.id if rent_item else UUID(str(eff_item.id)),
            label=rent_item.label if rent_item else eff_item.label,
            safra_id=safra_id,
            production_unit_id=rent_item.production_unit_id if rent_item else eff_item.production_unit_id,
            unidade_produtiva_id=rent_item.unidade_produtiva_id if rent_item else eff_item.unidade_produtiva_id,
            area_total_ha=area_total_ha,
            resultado_operacional=resultado_operacional,
            margem_pct=rent_item.margem_pct if rent_item else eff_item.margem_pct,
            receita_liquida_por_hectare=rent_item.receita_liquida_por_hectare if rent_item else None,
            resultado_por_hectare=rent_item.resultado_por_hectare if rent_item else eff_item.resultado_por_hectare,
            custo_operacional_total=custo_operacional_total,
            custo_operacional_por_hectare=eff_item.custo_operacional_por_hectare if eff_item else None,
            custo_operacional_por_operacao=eff_item.custo_operacional_por_operacao if eff_item else None,
            horas_por_hectare=eff_item.horas_por_hectare if eff_item else None,
            hectares_por_jornada=eff_item.hectares_por_jornada if eff_item else None,
            quantidade_operacoes=eff_item.quantidade_operacoes if eff_item else 0,
            quantidade_jornadas=eff_item.quantidade_jornadas if eff_item else 0,
            quantidade_apontamentos=eff_item.quantidade_apontamentos if eff_item else 0,
            sujeito_reconciliacao=bool((rent_item.sujeito_reconciliacao if rent_item else False) or (eff_item.sujeito_reconciliacao if eff_item else False) or warnings),
            observacao_reconciliacao="benchmark sujeito à reconciliação." if warnings or (rent_item and rent_item.sujeito_reconciliacao) or (eff_item and eff_item.sujeito_reconciliacao) else None,
            warnings_relevantes=warnings,
        )

    def _rankear(self, items: list[BenchmarkAgricolaItem]) -> list[BenchmarkAgricolaItem]:
        ranked = sorted(
            items,
            key=lambda item: (
                self._desc(item.resultado_por_hectare),
                self._desc(item.margem_pct),
                self._desc(item.receita_liquida_por_hectare),
                self._asc(item.custo_operacional_por_hectare),
                self._asc(item.horas_por_hectare),
                item.label,
            ),
        )
        for index, item in enumerate(ranked, start=1):
            item.posicao = index
        return ranked

    def _montar_destaques(self, ranking: list[BenchmarkAgricolaItem]) -> BenchmarkAgricolaDestaques:
        if not ranking:
            return BenchmarkAgricolaDestaques()
        melhor = ranking[0]
        melhor.destaque = "MELHOR"
        ponto_atencao = ranking[-1]
        if ponto_atencao is not melhor:
            ponto_atencao.destaque = "PONTO_ATENCAO"
        referencia = ranking[len(ranking) // 2]
        if referencia is not melhor and referencia is not ponto_atencao:
            referencia.destaque = "REFERENCIA"
        return BenchmarkAgricolaDestaques(
            melhor=melhor,
            referencia=referencia,
            ponto_atencao=ponto_atencao,
        )

    @staticmethod
    def _dedupe_warnings(warnings: list[DREWarning]) -> list[DREWarning]:
        deduped: dict[tuple[str, str], DREWarning] = {}
        for warning in warnings:
            deduped[(warning.codigo, warning.origem)] = warning
        return list(deduped.values())

    @staticmethod
    def _merge_warning_codes(*groups) -> list[str]:
        values: list[str] = []
        for group in groups:
            if not group:
                continue
            for item in group:
                if not item:
                    continue
                codigo = getattr(item, "codigo", None)
                values.append(str(codigo) if codigo else str(item))
        return sorted(set(values))

    @staticmethod
    def _area_total(dre) -> float:
        if dre.kpis and dre.kpis.area_total_ha:
            return float(dre.kpis.area_total_ha)
        return 0.0

    @staticmethod
    def _build_label(prefix: str, cultura: str | None, sufixo: str | None) -> str:
        parts = [prefix]
        if cultura:
            parts.append(cultura)
        if sufixo:
            parts.append(sufixo)
        return " • ".join(parts)

    @staticmethod
    def _item_key(item) -> UUID:
        if getattr(item, "production_unit_id", None):
            return item.production_unit_id
        return item.id if isinstance(item.id, UUID) else UUID(str(item.id))

    @staticmethod
    def _asc(value: float | None) -> float:
        return value if value is not None else float("inf")

    @staticmethod
    def _desc(value: float | None) -> float:
        return -value if value is not None else float("inf")
