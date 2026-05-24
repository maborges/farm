from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.dre import AgricolaDreKpiService, DREAgricolaV1Service
from agricola.dre.schemas import DREAgricolaResponse, DREWarning
from agricola.production_units.models import ProductionUnit
from agricola.safras.models import Safra
from core.base_service import BaseService
from core.cadastros.propriedades.models import AreaRural
from core.services.analytics_request_cache import (
    build_analytics_scope_key,
    build_analytics_value_key,
    get_analytics_request_cache,
    record_analytics_cache_hit,
    record_analytics_cache_miss,
    record_analytics_service_call,
)

from .schemas import RentabilidadeAgricolaItem, RentabilidadeAgricolaResponse


@dataclass(slots=True)
class _ScopedProductionUnit:
    id: UUID
    safra_id: UUID
    area_id: UUID
    area_nome: str
    unidade_produtiva_id: UUID
    area_ha: float

    @property
    def label(self) -> str:
        return self.area_nome or str(self.id)


class RentabilidadeAgricolaV1Service(BaseService[Safra]):
    """Camada oficial de rentabilidade derivada exclusivamente da DRE agrícola v1."""

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
    ) -> RentabilidadeAgricolaResponse:
        record_analytics_service_call("agricola.rentabilidade.v1")
        cache_key = build_analytics_value_key(
            "agricola.rentabilidade.v1",
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
            record_analytics_cache_hit("agricola.rentabilidade.v1")
            return cache[cache_key]
        record_analytics_cache_miss("agricola.rentabilidade.v1")

        production_units = await self._listar_production_units(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
        )

        if not production_units:
            response = self._empty_response(
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                production_unit_id=production_unit_id,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )
            cache[cache_key] = response
            return response

        dre_service = DREAgricolaV1Service(self.session, self.tenant_id)
        dre_safra = await dre_service.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        safra_item = self._montar_item_safra(
            dre_safra,
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
        )

        production_unit_items: list[RentabilidadeAgricolaItem] = []
        production_unit_dres: list[DREAgricolaResponse] = []
        reuse_safra_response_for_unit = bool(
            production_unit_id is not None
            and len(production_units) == 1
            and production_units[0].id == production_unit_id
        )
        for scope_unit in production_units:
            if reuse_safra_response_for_unit:
                dre_unit = dre_safra
            else:
                dre_unit = await dre_service.gerar(
                    safra_id=safra_id,
                    unidade_produtiva_id=unidade_produtiva_id,
                    production_unit_id=scope_unit.id,
                    data_inicio=data_inicio,
                    data_fim=data_fim,
                )
            production_unit_dres.append(dre_unit)
            production_unit_items.append(
                self._montar_item_production_unit(
                    dre_unit,
                    scope_unit=scope_unit,
                    safra_id=safra_id,
                )
            )

        ranking = self._rankear(production_unit_items)
        warnings = self._unir_warnings([dre_safra, *production_unit_dres])
        sujeito_reconciliacao = bool(
            safra_item.sujeito_reconciliacao
            or any(item.sujeito_reconciliacao for item in production_unit_items)
            or warnings
        )
        observacao = "rentabilidade sujeita à reconciliação." if sujeito_reconciliacao else None

        response = RentabilidadeAgricolaResponse(
            tenant_id=self.tenant_id,
            gerado_em=datetime.now(timezone.utc),
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            safra=safra_item,
            production_units=production_unit_items,
            ranking=ranking,
            warnings=warnings,
            sujeito_reconciliacao=sujeito_reconciliacao,
            observacao_reconciliacao=observacao,
        )
        cache[cache_key] = response
        return response

    def _empty_response(
        self,
        *,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
    ) -> RentabilidadeAgricolaResponse:
        empty_item = RentabilidadeAgricolaItem(
            scope="SAFRA",
            id=safra_id,
            label=str(safra_id),
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
        )
        return RentabilidadeAgricolaResponse(
            tenant_id=self.tenant_id,
            gerado_em=datetime.now(timezone.utc),
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            safra=empty_item,
            production_units=[],
            ranking=[],
            warnings=[],
            sujeito_reconciliacao=False,
            observacao_reconciliacao=None,
        )

    async def _listar_production_units(
        self,
        *,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
    ) -> list[_ScopedProductionUnit]:
        stmt = (
            select(
                ProductionUnit.id,
                ProductionUnit.safra_id,
                ProductionUnit.area_id,
                ProductionUnit.area_ha,
                AreaRural.nome,
                AreaRural.unidade_produtiva_id,
            )
            .join(
                Safra,
                and_(Safra.id == ProductionUnit.safra_id, Safra.tenant_id == self.tenant_id),
            )
            .join(
                AreaRural,
                and_(AreaRural.id == ProductionUnit.area_id, AreaRural.tenant_id == self.tenant_id),
            )
            .where(
                ProductionUnit.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == safra_id,
                ProductionUnit.status != "CANCELADA",
            )
        )

        if unidade_produtiva_id is not None:
            stmt = stmt.where(AreaRural.unidade_produtiva_id == unidade_produtiva_id)
        if production_unit_id is not None:
            stmt = stmt.where(ProductionUnit.id == production_unit_id)

        rows = (await self.session.execute(stmt.order_by(AreaRural.nome.asc(), ProductionUnit.id.asc()))).all()
        return [
            _ScopedProductionUnit(
                id=row.id,
                safra_id=row.safra_id,
                area_id=row.area_id,
                area_nome=row.nome or str(row.id),
                unidade_produtiva_id=row.unidade_produtiva_id,
                area_ha=float(row.area_ha or 0),
            )
            for row in rows
        ]

    def _montar_item_safra(
        self,
        dre: DREAgricolaResponse,
        *,
        safra_id: UUID,
        production_unit_id: UUID | None,
        unidade_produtiva_id: UUID | None,
    ) -> RentabilidadeAgricolaItem:
        kpis = dre.kpis or AgricolaDreKpiService.calcular(
            dre,
            area_total_ha=self._area_total(dre),
            warnings=dre.warnings,
        )
        return RentabilidadeAgricolaItem(
            scope="SAFRA",
            id=safra_id,
            label=self._build_label("SAFRA", dre.cultura, None),
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            area_total_ha=kpis.area_total_ha,
            resultado_operacional=kpis.resultado_operacional,
            margem_pct=kpis.margem_pct,
            receita_liquida_por_hectare=kpis.receita_por_hectare,
            resultado_por_hectare=kpis.resultado_por_hectare,
            sujeito_reconciliacao=kpis.sujeito_reconciliacao,
            observacao_reconciliacao=kpis.observacao_reconciliacao,
            warnings_relevantes=kpis.warnings_relevantes,
        )

    def _montar_item_production_unit(
        self,
        dre: DREAgricolaResponse,
        *,
        scope_unit: _ScopedProductionUnit,
        safra_id: UUID,
    ) -> RentabilidadeAgricolaItem:
        kpis = dre.kpis or AgricolaDreKpiService.calcular(
            dre,
            area_total_ha=scope_unit.area_ha,
            warnings=dre.warnings,
        )
        return RentabilidadeAgricolaItem(
            scope="PRODUCTION_UNIT",
            id=scope_unit.id,
            label=scope_unit.label,
            safra_id=safra_id,
            production_unit_id=scope_unit.id,
            unidade_produtiva_id=scope_unit.unidade_produtiva_id,
            area_total_ha=kpis.area_total_ha,
            resultado_operacional=kpis.resultado_operacional,
            margem_pct=kpis.margem_pct,
            receita_liquida_por_hectare=kpis.receita_por_hectare,
            resultado_por_hectare=kpis.resultado_por_hectare,
            sujeito_reconciliacao=kpis.sujeito_reconciliacao,
            observacao_reconciliacao=kpis.observacao_reconciliacao,
            warnings_relevantes=kpis.warnings_relevantes,
        )

    def _rankear(self, items: list[RentabilidadeAgricolaItem]) -> list[RentabilidadeAgricolaItem]:
        ranked = sorted(
            items,
            key=lambda item: (
                item.resultado_por_hectare if item.resultado_por_hectare is not None else float("-inf"),
                item.resultado_operacional,
                item.area_total_ha,
            ),
            reverse=True,
        )
        for index, item in enumerate(ranked, start=1):
            item.posicao = index
        return ranked

    def _area_total(self, dre: DREAgricolaResponse) -> float:
        if dre.kpis and dre.kpis.area_total_ha:
            return float(dre.kpis.area_total_ha)
        return 0.0

    def _build_label(self, prefix: str, cultura: str | None, sufixo: str | None) -> str:
        parts = [prefix]
        if cultura:
            parts.append(cultura)
        if sufixo:
            parts.append(sufixo)
        return " • ".join(parts)

    def _unir_warnings(self, responses: list[DREAgricolaResponse]) -> list[DREWarning]:
        warnings: dict[tuple[str, str], DREWarning] = {}
        for response in responses:
            for warning in response.warnings:
                warnings[(warning.codigo, warning.origem)] = warning
        return list(warnings.values())
