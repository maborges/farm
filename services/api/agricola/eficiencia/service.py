from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.dre import AgricolaDreKpiService, DREAgricolaV1Service
from agricola.dre.schemas import DREAgricolaKpis, DREAgricolaResponse, DREWarning
from agricola.operacoes.models import OperacaoAgricola
from agricola.production_units.models import ProductionUnit
from agricola.rentabilidade.service import RentabilidadeAgricolaV1Service
from agricola.safras.models import Safra
from core.base_service import BaseService
from core.cadastros.equipamentos.models import Equipamento
from core.cadastros.propriedades.models import AreaRural
from operacional.models.apontamento import ApontamentoUso
from operacional.models.frota import JornadaEquipamento

from .schemas import EficienciaOperacionalAgricolaResponse, EficienciaOperacionalItem


@dataclass(slots=True)
class _OperacaoAgg:
    key: str
    label: str
    operacao_id: UUID | None
    production_unit_id: UUID | None
    unidade_produtiva_id: UUID | None
    safra_id: UUID
    hectares_totais: float
    horas_totais: float
    custo_operacional_total: float
    quantidade_operacoes: int


@dataclass(slots=True)
class _ApontamentoAgg:
    equipamento_id: UUID
    equipamento_nome: str
    equipamento_tipo: str
    production_unit_id: UUID | None
    unidade_produtiva_id: UUID | None
    safra_id: UUID | None
    hectares_totais: float
    horas_totais: float
    custo_operacional_total: float
    quantidade_jornadas: int
    quantidade_apontamentos: int


class EficienciaOperacionalAgricolaV1Service(BaseService[Safra]):
    """Camada oficial de eficiência operacional derivada da DRE agrícola v1 e dos registros operacionais."""

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
    ) -> EficienciaOperacionalAgricolaResponse:
        rentabilidade_svc = RentabilidadeAgricolaV1Service(self.session, self.tenant_id)
        rentabilidade = await rentabilidade_svc.gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        dre_safra = await DREAgricolaV1Service(self.session, self.tenant_id).gerar(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        kpis_safra = dre_safra.kpis or AgricolaDreKpiService.calcular(
            dre_safra,
            area_total_ha=self._area_total(dre_safra),
            warnings=dre_safra.warnings,
        )

        jornadas = await self._buscar_jornadas(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        apontamentos = await self._buscar_apontamentos(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        operacoes = await self._buscar_operacoes(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        apontamentos_por_equipamento = self._agrupar_apontamentos_por_equipamento(apontamentos)
        apontamentos_por_pu = self._agrupar_apontamentos_por_production_unit(apontamentos)
        jornadas_por_equipamento = self._agrupar_jornadas_por_equipamento(jornadas)
        operacoes_por_tipo = self._agrupar_operacoes(operacoes)
        operacoes_por_pu = self._agrupar_operacoes_por_production_unit(operacoes)

        production_unit_items = [
            self._montar_item_production_unit(
                item,
                safra_id=safra_id,
                apontamentos=apontamentos_por_pu.get(item.id, []),
                operacoes=operacoes_por_pu.get(item.id, []),
            )
            for item in rentabilidade.production_units
        ]
        ranking = self._rankear(production_unit_items)

        equipamento_ids = sorted(set(apontamentos_por_equipamento.keys()) | set(jornadas_por_equipamento.keys()))
        equipamentos = await self._buscar_equipamentos(list(equipamento_ids))
        equipamento_items: list[EficienciaOperacionalItem] = []
        for equipamento_id in equipamento_ids:
            equipamento = equipamentos.get(equipamento_id)
            agg = apontamentos_por_equipamento.get(
                equipamento_id,
                _ApontamentoAgg(
                    equipamento_id=equipamento_id,
                    equipamento_nome=equipamento.nome if equipamento else str(equipamento_id),
                    equipamento_tipo=equipamento.tipo if equipamento else "—",
                    production_unit_id=None,
                    unidade_produtiva_id=None,
                    safra_id=safra_id,
                    hectares_totais=0.0,
                    horas_totais=0.0,
                    custo_operacional_total=0.0,
                    quantidade_jornadas=0,
                    quantidade_apontamentos=0,
                ),
            )
            equipamento_items.append(
                self._montar_item_equipamento(
                    agg,
                    equipamento=equipamento,
                    jornadas=jornadas_por_equipamento.get(equipamento_id, []),
                    safra_id=safra_id,
                )
            )

        operacao_items = [
            self._montar_item_operacao(agg)
            for agg in operacoes_por_tipo
        ]

        safra_item = self._montar_item_safra(
            dre_safra,
            kpis=kpis_safra,
            safra_id=safra_id,
            jornadas=jornadas,
            apontamentos=apontamentos,
            operacoes=operacoes,
        )

        warnings = self._dedupe_warnings([
            *dre_safra.warnings,
            *rentabilidade.warnings,
            *self._warning_operacional_desvio_total(safra_item.custo_operacional_total, apontamentos),
        ])

        sujeito_reconciliacao = bool(
            safra_item.sujeito_reconciliacao
            or any(item.sujeito_reconciliacao for item in production_unit_items)
            or warnings
        )
        observacao = "indicadores sujeitos à reconciliação." if sujeito_reconciliacao else None

        return EficienciaOperacionalAgricolaResponse(
            tenant_id=self.tenant_id,
            gerado_em=datetime.now(timezone.utc),
            safra_id=safra_id,
            production_unit_id=production_unit_id,
            unidade_produtiva_id=unidade_produtiva_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            safra=safra_item,
            production_units=production_unit_items,
            equipamentos=sorted(
                equipamento_items,
                key=lambda item: (
                    item.custo_operacional_por_hectare if item.custo_operacional_por_hectare is not None else float("inf"),
                    -(item.resultado_por_hectare or 0.0),
                    item.label,
                ),
            ),
            operacoes=sorted(
                operacao_items,
                key=lambda item: (
                    item.custo_operacional_por_hectare if item.custo_operacional_por_hectare is not None else float("inf"),
                    item.label,
                ),
            ),
            ranking=ranking,
            warnings=warnings,
            sujeito_reconciliacao=sujeito_reconciliacao,
            observacao_reconciliacao=observacao,
        )

    async def _buscar_jornadas(
        self,
        *,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
    ) -> list[JornadaEquipamento]:
        stmt = select(JornadaEquipamento).where(
            JornadaEquipamento.tenant_id == self.tenant_id,
            JornadaEquipamento.status == "FINALIZADA",
            JornadaEquipamento.safra_id == safra_id,
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(JornadaEquipamento.unidade_produtiva_id == unidade_produtiva_id)
        if production_unit_id is not None:
            stmt = stmt.where(
                JornadaEquipamento.equipamento_id.in_(
                    select(ApontamentoUso.equipamento_id).where(
                        ApontamentoUso.tenant_id == self.tenant_id,
                        ApontamentoUso.safra_id == safra_id,
                        ApontamentoUso.production_unit_id == production_unit_id,
                    )
                )
            )
        if data_inicio is not None:
            stmt = stmt.where(JornadaEquipamento.data_inicio >= datetime.combine(data_inicio, datetime.min.time(), tzinfo=timezone.utc))
        if data_fim is not None:
            stmt = stmt.where(JornadaEquipamento.data_inicio <= datetime.combine(data_fim, datetime.max.time(), tzinfo=timezone.utc))
        return list((await self.session.execute(stmt.order_by(JornadaEquipamento.data_inicio.asc()))).scalars().all())

    async def _buscar_apontamentos(
        self,
        *,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
    ) -> list[ApontamentoUso]:
        stmt = select(ApontamentoUso).where(
            ApontamentoUso.tenant_id == self.tenant_id,
            ApontamentoUso.safra_id == safra_id,
        )
        if unidade_produtiva_id is not None:
            stmt = stmt.where(ApontamentoUso.unidade_produtiva_id == unidade_produtiva_id)
        if production_unit_id is not None:
            stmt = stmt.where(ApontamentoUso.production_unit_id == production_unit_id)
        if data_inicio is not None:
            stmt = stmt.where(ApontamentoUso.data >= datetime.combine(data_inicio, datetime.min.time(), tzinfo=timezone.utc))
        if data_fim is not None:
            stmt = stmt.where(ApontamentoUso.data <= datetime.combine(data_fim, datetime.max.time(), tzinfo=timezone.utc))
        return list((await self.session.execute(stmt.order_by(ApontamentoUso.data.desc(), ApontamentoUso.created_at.desc()))).scalars().all())

    async def _buscar_operacoes(
        self,
        *,
        safra_id: UUID,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
    ) -> list[OperacaoAgricola]:
        stmt = select(OperacaoAgricola).where(
            OperacaoAgricola.tenant_id == self.tenant_id,
            OperacaoAgricola.safra_id == safra_id,
            OperacaoAgricola.status != "CANCELADA",
        )
        if production_unit_id is not None:
            stmt = stmt.where(OperacaoAgricola.production_unit_id == production_unit_id)
        elif unidade_produtiva_id is not None:
            stmt = (
                stmt.join(
                    ProductionUnit,
                    and_(
                        ProductionUnit.id == OperacaoAgricola.production_unit_id,
                        ProductionUnit.tenant_id == self.tenant_id,
                    ),
                )
                .join(
                    AreaRural,
                    and_(
                        AreaRural.id == ProductionUnit.area_id,
                        AreaRural.tenant_id == self.tenant_id,
                    ),
                )
                .where(AreaRural.unidade_produtiva_id == unidade_produtiva_id)
            )
        if data_inicio is not None:
            stmt = stmt.where(OperacaoAgricola.data_realizada >= data_inicio)
        if data_fim is not None:
            stmt = stmt.where(OperacaoAgricola.data_realizada <= data_fim)
        return list((await self.session.execute(stmt.order_by(OperacaoAgricola.data_realizada.desc(), OperacaoAgricola.created_at.desc()))).scalars().all())

    async def _buscar_equipamentos(self, equipamento_ids: list[UUID]) -> dict[UUID, Equipamento]:
        ids = [item for item in equipamento_ids if item]
        if not ids:
            return {}
        stmt = select(Equipamento).where(
            Equipamento.tenant_id == self.tenant_id,
            Equipamento.id.in_(ids),
        )
        equipamentos = list((await self.session.execute(stmt)).scalars().all())
        return {item.id: item for item in equipamentos}

    def _montar_item_safra(
        self,
        dre: DREAgricolaResponse,
        *,
        kpis: DREAgricolaKpis,
        safra_id: UUID,
        jornadas: list[JornadaEquipamento],
        apontamentos: list[ApontamentoUso],
        operacoes: list[OperacaoAgricola],
    ) -> EficienciaOperacionalItem:
        horas_totais = self._jornada_horas(jornadas)
        hectares_totais = self._apontamento_hectares(apontamentos)
        custo_operacional_total = float(kpis.custo_operacional_total or 0.0)
        quantidade_jornadas = len(jornadas)
        quantidade_apontamentos = len(apontamentos)
        quantidade_operacoes = len(operacoes)
        return EficienciaOperacionalItem(
            scope="SAFRA",
            id=str(safra_id),
            label=self._build_label("SAFRA", dre.cultura, None),
            safra_id=safra_id,
            area_total_ha=float(kpis.area_total_ha or 0.0),
            hectares_totais=hectares_totais,
            horas_totais=horas_totais,
            quantidade_operacoes=quantidade_operacoes,
            quantidade_jornadas=quantidade_jornadas,
            quantidade_apontamentos=quantidade_apontamentos,
            custo_operacional_total=custo_operacional_total,
            custo_operacional_por_hectare=kpis.custo_por_hectare,
            custo_operacional_por_operacao=round(custo_operacional_total / quantidade_operacoes, 2) if quantidade_operacoes > 0 else None,
            horas_por_hectare=round(horas_totais / hectares_totais, 2) if hectares_totais > 0 else None,
            hectares_por_jornada=round(hectares_totais / quantidade_jornadas, 2) if quantidade_jornadas > 0 else None,
            resultado_operacional=float(kpis.resultado_operacional or 0.0),
            resultado_por_hectare=kpis.resultado_por_hectare,
            margem_pct=kpis.margem_pct,
            sujeito_reconciliacao=kpis.sujeito_reconciliacao,
            observacao_reconciliacao=kpis.observacao_reconciliacao,
            warnings_relevantes=kpis.warnings_relevantes,
        )

    def _montar_item_production_unit(
        self,
        item,
        *,
        safra_id: UUID,
        apontamentos: list[ApontamentoUso],
        operacoes: list[_OperacaoAgg],
    ) -> EficienciaOperacionalItem:
        area_total_ha = float(item.area_total_ha or 0.0)
        hectares_totais = self._apontamento_hectares(apontamentos)
        horas_totais = self._apontamento_horas(apontamentos)
        quantidade_operacoes = len(operacoes)
        custo_operacional_apontamentos = round(sum(float(ap.custo_total or 0.0) for ap in apontamentos), 2)
        receita_liquida_total = float(item.receita_liquida_por_hectare or 0.0) * area_total_ha
        resultado_total = float(item.resultado_operacional or 0.0)
        custo_operacional_total = round(receita_liquida_total - resultado_total, 2) if area_total_ha > 0 else 0.0
        warnings = list(item.warnings_relevantes or [])
        if area_total_ha > 0 and custo_operacional_total > 0 and custo_operacional_apontamentos > 0:
            desvio_pct = self._diferenca_percentual(custo_operacional_total, custo_operacional_apontamentos)
            if desvio_pct >= 20:
                warnings.append("EFICIENCIA_OPERACIONAL_DESVIO_CUSTO")
        return EficienciaOperacionalItem(
            scope="PRODUCTION_UNIT",
            id=str(item.id),
            label=item.label,
            safra_id=safra_id,
            production_unit_id=item.id,
            unidade_produtiva_id=item.unidade_produtiva_id,
            area_total_ha=area_total_ha,
            hectares_totais=hectares_totais,
            horas_totais=horas_totais,
            quantidade_operacoes=quantidade_operacoes,
            quantidade_apontamentos=len(apontamentos),
            custo_operacional_total=custo_operacional_total,
            custo_operacional_por_hectare=round(custo_operacional_total / area_total_ha, 2) if area_total_ha > 0 else None,
            custo_operacional_por_operacao=round(custo_operacional_total / quantidade_operacoes, 2) if quantidade_operacoes > 0 else None,
            horas_por_hectare=round(horas_totais / hectares_totais, 2) if hectares_totais > 0 else None,
            hectares_por_jornada=None,
            resultado_operacional=resultado_total,
            resultado_por_hectare=item.resultado_por_hectare,
            margem_pct=item.margem_pct,
            sujeito_reconciliacao=item.sujeito_reconciliacao or bool(warnings),
            observacao_reconciliacao=item.observacao_reconciliacao,
            warnings_relevantes=warnings,
        )

    def _montar_item_equipamento(
        self,
        agg: _ApontamentoAgg,
        *,
        equipamento: Equipamento | None,
        jornadas: list[JornadaEquipamento],
        safra_id: UUID,
    ) -> EficienciaOperacionalItem:
        label = equipamento.nome if equipamento else agg.equipamento_nome
        area_total_ha = agg.hectares_totais
        horas_totais = self._jornada_horas(jornadas) or agg.horas_totais
        quantidade_jornadas = len(jornadas)
        return EficienciaOperacionalItem(
            scope="EQUIPMENT",
            id=str(agg.equipamento_id),
            label=label,
            safra_id=safra_id,
            equipamento_id=agg.equipamento_id,
            unidade_produtiva_id=agg.unidade_produtiva_id,
            area_total_ha=area_total_ha,
            hectares_totais=agg.hectares_totais,
            horas_totais=horas_totais,
            quantidade_jornadas=quantidade_jornadas,
            quantidade_apontamentos=agg.quantidade_apontamentos,
            custo_operacional_total=agg.custo_operacional_total,
            custo_operacional_por_hectare=round(agg.custo_operacional_total / area_total_ha, 2) if area_total_ha > 0 else None,
            custo_operacional_por_operacao=round(agg.custo_operacional_total / agg.quantidade_apontamentos, 2) if agg.quantidade_apontamentos > 0 else None,
            horas_por_hectare=round(horas_totais / area_total_ha, 2) if area_total_ha > 0 else None,
            hectares_por_jornada=round(area_total_ha / quantidade_jornadas, 2) if quantidade_jornadas > 0 else None,
        )

    def _montar_item_operacao(self, agg: _OperacaoAgg) -> EficienciaOperacionalItem:
        custo_operacional_total = agg.custo_operacional_total
        return EficienciaOperacionalItem(
            scope="OPERATION",
            id=agg.key,
            label=agg.label,
            safra_id=agg.safra_id,
            production_unit_id=agg.production_unit_id,
            unidade_produtiva_id=agg.unidade_produtiva_id,
            operacao_id=agg.operacao_id,
            area_total_ha=agg.hectares_totais,
            hectares_totais=agg.hectares_totais,
            horas_totais=agg.horas_totais,
            quantidade_operacoes=agg.quantidade_operacoes,
            custo_operacional_total=custo_operacional_total,
            custo_operacional_por_hectare=round(custo_operacional_total / agg.hectares_totais, 2) if agg.hectares_totais > 0 else None,
            custo_operacional_por_operacao=round(custo_operacional_total / agg.quantidade_operacoes, 2) if agg.quantidade_operacoes > 0 else None,
            horas_por_hectare=round(agg.horas_totais / agg.hectares_totais, 2) if agg.hectares_totais > 0 else None,
        )

    def _rankear(self, items: list[EficienciaOperacionalItem]) -> list[EficienciaOperacionalItem]:
        ranked = sorted(
            items,
            key=lambda item: (
                item.custo_operacional_por_hectare if item.custo_operacional_por_hectare is not None else float("inf"),
                item.horas_por_hectare if item.horas_por_hectare is not None else float("inf"),
                -(item.resultado_por_hectare or 0.0),
            ),
        )
        for index, item in enumerate(ranked, start=1):
            item.posicao = index
        return ranked

    @staticmethod
    def _apontamento_hectares(apontamentos: list[ApontamentoUso]) -> float:
        return round(sum(float(item.area_ha_trabalhada or 0.0) for item in apontamentos), 2)

    @staticmethod
    def _apontamento_horas(apontamentos: list[ApontamentoUso]) -> float:
        return round(sum(float(item.horimetro_fim or 0.0) - float(item.horimetro_inicio or 0.0) for item in apontamentos), 2)

    @staticmethod
    def _jornada_horas(jornadas: list[JornadaEquipamento]) -> float:
        total = 0.0
        for item in jornadas:
            if item.horimetro_inicial is None or item.horimetro_final is None:
                continue
            if float(item.horimetro_final) >= float(item.horimetro_inicial):
                total += float(item.horimetro_final) - float(item.horimetro_inicial)
        return round(total, 2)

    @staticmethod
    def _agrupar_apontamentos_por_equipamento(apontamentos: list[ApontamentoUso]) -> dict[UUID, _ApontamentoAgg]:
        grupos: dict[UUID, list[ApontamentoUso]] = defaultdict(list)
        for item in apontamentos:
            grupos[item.equipamento_id].append(item)
        resultado: dict[UUID, _ApontamentoAgg] = {}
        for equipamento_id, itens in grupos.items():
            first = itens[0]
            resultado[equipamento_id] = _ApontamentoAgg(
                equipamento_id=equipamento_id,
                equipamento_nome=str(equipamento_id),
                equipamento_tipo="—",
                production_unit_id=first.production_unit_id,
                unidade_produtiva_id=first.unidade_produtiva_id,
                safra_id=first.safra_id,
                hectares_totais=round(sum(float(item.area_ha_trabalhada or 0.0) for item in itens), 2),
                horas_totais=round(sum(float(item.horimetro_fim or 0.0) - float(item.horimetro_inicio or 0.0) for item in itens), 2),
                custo_operacional_total=round(sum(float(item.custo_total or 0.0) for item in itens), 2),
                quantidade_jornadas=len({item.jornada_id for item in itens if item.jornada_id}),
                quantidade_apontamentos=len(itens),
            )
        return resultado

    @staticmethod
    def _agrupar_apontamentos_por_production_unit(apontamentos: list[ApontamentoUso]) -> dict[UUID, list[ApontamentoUso]]:
        grupos: dict[UUID, list[ApontamentoUso]] = defaultdict(list)
        for item in apontamentos:
            if item.production_unit_id is not None:
                grupos[item.production_unit_id].append(item)
        return grupos

    @staticmethod
    def _agrupar_jornadas_por_equipamento(jornadas: list[JornadaEquipamento]) -> dict[UUID, list[JornadaEquipamento]]:
        grupos: dict[UUID, list[JornadaEquipamento]] = defaultdict(list)
        for item in jornadas:
            grupos[item.equipamento_id].append(item)
        return grupos

    @staticmethod
    def _agrupar_operacoes_por_production_unit(operacoes: list[OperacaoAgricola]) -> dict[UUID, list[_OperacaoAgg]]:
        grupos: dict[UUID, list[_OperacaoAgg]] = defaultdict(list)
        for op in operacoes:
            if op.production_unit_id is None:
                continue
            chave = f"{op.tipo}::{op.subtipo or 'GERAL'}"
            grupos[op.production_unit_id].append(
                _OperacaoAgg(
                    key=chave,
                    label=op.tipo if not op.subtipo else f"{op.tipo} • {op.subtipo}",
                    operacao_id=op.id,
                    production_unit_id=op.production_unit_id,
                    unidade_produtiva_id=None,
                    safra_id=op.safra_id,
                    hectares_totais=float(op.area_aplicada_ha or 0.0),
                    horas_totais=0.0,
                    custo_operacional_total=float(op.custo_total or 0.0),
                    quantidade_operacoes=1,
                )
            )
        return grupos

    def _agrupar_operacoes(self, operacoes: list[OperacaoAgricola]) -> list[_OperacaoAgg]:
        grupos: dict[str, list[OperacaoAgricola]] = defaultdict(list)
        for item in operacoes:
            chave = f"{item.tipo}::{item.subtipo or 'GERAL'}"
            grupos[chave].append(item)
        resultados: list[_OperacaoAgg] = []
        for chave, itens in grupos.items():
            first = itens[0]
            label = first.tipo if not first.subtipo else f"{first.tipo} • {first.subtipo}"
            horas_totais = 0.0
            for op in itens:
                if op.hora_inicio and op.hora_fim:
                    delta = (
                        datetime.combine(date.today(), op.hora_fim, tzinfo=timezone.utc)
                        - datetime.combine(date.today(), op.hora_inicio, tzinfo=timezone.utc)
                    ).total_seconds() / 3600.0
                    if delta > 0:
                        horas_totais += delta
            resultados.append(
                _OperacaoAgg(
                    key=chave,
                    label=label,
                    operacao_id=first.id,
                    production_unit_id=first.production_unit_id,
                    unidade_produtiva_id=None,
                    safra_id=first.safra_id,
                    hectares_totais=round(sum(float(item.area_aplicada_ha or 0.0) for item in itens), 2),
                    horas_totais=round(horas_totais, 2),
                    custo_operacional_total=round(sum(float(item.custo_total or 0.0) for item in itens), 2),
                    quantidade_operacoes=len(itens),
                )
            )
        return resultados

    @staticmethod
    def _build_label(prefix: str, cultura: str | None, sufixo: str | None) -> str:
        parts = [prefix]
        if cultura:
            parts.append(cultura)
        if sufixo:
            parts.append(sufixo)
        return " • ".join(parts)

    @staticmethod
    def _area_total(dre: DREAgricolaResponse) -> float:
        if dre.kpis and dre.kpis.area_total_ha:
            return float(dre.kpis.area_total_ha)
        return 0.0

    @staticmethod
    def _diferenca_percentual(base: float, referencia: float) -> float:
        if referencia <= 0:
            return 0.0
        return abs(base - referencia) / referencia * 100

    @staticmethod
    def _warning_operacional_desvio_total(
        custo_operacional_oficial: float,
        apontamentos: list[ApontamentoUso],
    ) -> list[DREWarning]:
        custo_operacional_apontamentos = round(sum(float(ap.custo_total or 0.0) for ap in apontamentos), 2)
        if custo_operacional_oficial <= 0 or custo_operacional_apontamentos <= 0:
            return []
        desvio_pct = abs(custo_operacional_oficial - custo_operacional_apontamentos) / custo_operacional_oficial * 100
        if desvio_pct < 20:
            return []
        return [
            DREWarning(
                codigo="EFICIENCIA_OPERACIONAL_DESVIO_CUSTO",
                titulo="Desvio entre custo oficial e operacional",
                severidade="INCONSISTENCIA_MODERADA",
                mensagem="Os indicadores operacionais divergem do custo oficial da DRE e ficam sujeitos à reconciliação.",
                origem="eficiencia_operacional_v1",
                amostras=[],
                meta={"desvio_pct": round(desvio_pct, 2)},
            )
        ]

    @staticmethod
    def _dedupe_warnings(warnings: list[DREWarning]) -> list[DREWarning]:
        deduped: dict[tuple[str, str], DREWarning] = {}
        for warning in warnings:
            deduped[(warning.codigo, warning.origem)] = warning
        return list(deduped.values())
