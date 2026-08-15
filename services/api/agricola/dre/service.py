from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.alertas.service import AlertasAgricolasService
from agricola.custos.models import CostAllocation
from agricola.operacoes.models import OperacaoAgricola, OperacaoExecucao
from agricola.romaneios.models import RomaneioColheita
from agricola.safras.models import Safra
from agricola.production_units.models import ProductionUnit
from agricola.colheita.models import ProdutoColhido
from core.cadastros.equipamentos.alocacao_service import get_equipamento_unidade_operacional
from core.cadastros.propriedades.models import AreaRural
from financeiro.comercializacao.models import ComercializacaoCommodity
from financeiro.models.despesa import Despesa
from financeiro.models.lancamento import LancamentoFinanceiro
from financeiro.models.rateio import Rateio
from financeiro.models.receita import Receita
from operacional.models.abastecimento import Abastecimento
from operacional.models.estoque import EstoqueMovimento
from operacional.models.frota import OrdemServico
from core.base_service import BaseService
from core.services.analytics_request_cache import build_analytics_scope_key, build_analytics_value_key, get_analytics_request_cache
from core.services.analytics_request_cache import record_analytics_cache_hit, record_analytics_cache_miss, record_analytics_service_call

from .schemas import (
    DREAgricolaResponse,
    DREAgricolaSection,
    DRELoteMargem,
    DREReconcilacaoMeta,
    DRESourceItem,
    DREWarning,
)
from .kpis_service import AgricolaDreKpiService


@dataclass(slots=True)
class _ScopedProductionUnit:
    id: UUID
    safra_id: UUID
    cultura: str | None
    area_id: UUID
    unidade_produtiva_id: UUID
    area_ha: float


class DREAgricolaV1Service(BaseService[Safra]):
    """Serviço interno e somente leitura para DRE agrícola v1."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        super().__init__(Safra, session, tenant_id)

    async def gerar(
        self,
        *,
        safra_id: UUID | None = None,
        unidade_produtiva_id: UUID | None = None,
        production_unit_id: UUID | None = None,
        production_unit_ids: list[UUID] | None = None,
        cultura: str | None = None,
        unidade_operacional_id: UUID | None = None,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> DREAgricolaResponse:
        record_analytics_service_call("agricola.dre.v1")
        cache = get_analytics_request_cache()
        scope_variant = self._cache_variant(
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id,
            production_unit_id=production_unit_id,
            production_unit_ids=production_unit_ids,
            cultura=cultura,
            unidade_operacional_id=unidade_operacional_id,
        )
        scope_cache_key = build_analytics_value_key(
            "agricola.dre.scope.v1",
            build_analytics_scope_key(
                self.tenant_id,
                safra_id,
                production_unit_id,
                unidade_produtiva_id,
                None,
                None,
            ),
            scope_variant,
        )
        cache_key = build_analytics_value_key(
            "agricola.dre.v1",
            build_analytics_scope_key(
                self.tenant_id,
                safra_id,
                production_unit_id,
                unidade_produtiva_id,
                data_inicio,
                data_fim,
            ),
            scope_variant,
        )
        if cache_key in cache:
            record_analytics_cache_hit("agricola.dre.v1")
            return cache[cache_key]
        record_analytics_cache_miss("agricola.dre.v1")

        scope = cache.get(scope_cache_key)
        if scope is None:
            scope = await self._resolver_escopo(
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                production_unit_id=production_unit_id,
                production_unit_ids=production_unit_ids,
                cultura=cultura,
                unidade_operacional_id=unidade_operacional_id,
            )
            scope = dict(scope)
            cache[scope_cache_key] = scope
        else:
            scope = dict(scope)

        if not scope["production_units"] and any(
            value is not None
            for value in (safra_id, unidade_produtiva_id, production_unit_id, production_unit_ids, cultura, unidade_operacional_id)
        ):
            response = DREAgricolaResponse(
                tenant_id=self.tenant_id,
                gerado_em=datetime.now(timezone.utc),
                safra_id=safra_id,
                unidade_produtiva_id=unidade_produtiva_id,
                production_unit_id=production_unit_id,
                unidade_operacional_id=unidade_operacional_id,
                cultura=cultura,
                production_unit_ids=[],
            )
            cache[cache_key] = response
            return response

        scope["data_inicio"] = data_inicio
        scope["data_fim"] = data_fim

        receitas_section, deducoes, receitas_warnings, receitas_excluidas = await self._consolidar_receitas(
            scope,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        custos_diretos_section = await self._consolidar_costs(scope, direct=True, data_inicio=data_inicio, data_fim=data_fim)
        custos_operacionais_section = await self._consolidar_costs(scope, direct=False, data_inicio=data_inicio, data_fim=data_fim)
        despesas_section, despesas_excluidas = await self._consolidar_despesas(
            scope,
            custos_diretos_section,
            custos_operacionais_section,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        reconciliacao = await self._montar_reconciliacao(
            scope,
            receitas_excluidas,
            despesas_excluidas,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        margem_por_lote, lotes_sem_vinculo = await self._ratear_custos_por_lote(
            scope,
            receitas_section,
            custos_diretos_section,
            custos_operacionais_section,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

        receita_bruta = round(receitas_section.valor, 2)
        deducoes_valor = round(deducoes, 2)
        receita_liquida = round(receita_bruta - deducoes_valor, 2)
        custos_diretos = round(custos_diretos_section.valor, 2)
        custos_operacionais = round(custos_operacionais_section.valor, 2)
        margem_bruta = round(receita_liquida - custos_diretos, 2)
        despesas_operacionais = round(despesas_section.valor, 2)
        resultado_operacional = round(margem_bruta - custos_operacionais - despesas_operacionais, 2)

        warnings = await self._montar_warnings(
            scope,
            receitas_warnings,
            despesas_excluidas,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        if lotes_sem_vinculo > 0:
            warnings.append(
                DREWarning(
                    codigo="COMERCIALIZACAO_SEM_LOTE_VINCULADO",
                    titulo="Comercialização sem lote vinculado",
                    severidade="WARNING_LEVE",
                    mensagem="Há comercializações sem produto_colhido_id vinculado; elas não entram no detalhamento de margem por lote.",
                    origem="dre_agricola_v1",
                    amostras=[str(lotes_sem_vinculo)],
                    meta={"quantidade": lotes_sem_vinculo},
                )
            )
        base_response = DREAgricolaResponse(
            tenant_id=self.tenant_id,
            gerado_em=datetime.now(timezone.utc),
            safra_id=safra_id,
            unidade_produtiva_id=unidade_produtiva_id or scope["unidade_produtiva_id"],
            production_unit_id=production_unit_id,
            unidade_operacional_id=unidade_operacional_id,
            cultura=scope["cultura"],
            production_unit_ids=[pu.id for pu in scope["production_units"]],
            receita_bruta=receita_bruta,
            deducoes=deducoes_valor,
            receita_liquida=receita_liquida,
            custos_diretos=custos_diretos,
            custos_operacionais=custos_operacionais,
            margem_bruta=margem_bruta,
            despesas_operacionais=despesas_operacionais,
            resultado_operacional=resultado_operacional,
            receita=receitas_section,
            custos_diretos_detalhe=custos_diretos_section,
            custos_operacionais_detalhe=custos_operacionais_section,
            despesas_operacionais_detalhe=despesas_section,
            margem_por_lote=margem_por_lote,
            lotes_sem_vinculo=lotes_sem_vinculo,
            warnings=warnings,
            reconciliacao=reconciliacao,
        )
        area_total_ha = round(sum(float(pu.area_ha or 0) for pu in scope["production_units"]), 2)
        kpis = AgricolaDreKpiService.calcular(
            base_response,
            area_total_ha=area_total_ha,
            warnings=warnings,
        )

        response = base_response.model_copy(update={"kpis": kpis})
        cache[cache_key] = response
        return response

    @staticmethod
    def _cache_variant(
        *,
        safra_id: UUID | None,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
        production_unit_ids: list[UUID] | None,
        cultura: str | None,
        unidade_operacional_id: UUID | None,
    ) -> str | None:
        parts: list[str] = []
        if cultura:
            parts.append(f"cultura={cultura.strip().lower()}")
        if production_unit_ids:
            parts.append("production_unit_ids=" + ",".join(sorted(str(item) for item in production_unit_ids)))
        if unidade_operacional_id is not None:
            parts.append(f"unidade_operacional_id={unidade_operacional_id}")
        if not parts:
            return None
        return "|".join(parts)

    async def _resolver_escopo(
        self,
        *,
        safra_id: UUID | None,
        unidade_produtiva_id: UUID | None,
        production_unit_id: UUID | None,
        production_unit_ids: list[UUID] | None,
        cultura: str | None,
        unidade_operacional_id: UUID | None,
    ) -> dict:
        unidade_operacional_resolvida = None
        if unidade_operacional_id is not None:
            contexto = await get_equipamento_unidade_operacional(
                self.session,
                tenant_id=self.tenant_id,
                equipamento_id=unidade_operacional_id,
            )
            unidade_operacional_resolvida = contexto.unidade_produtiva_id
            if unidade_produtiva_id is None:
                unidade_produtiva_id = unidade_operacional_resolvida

        stmt = select(
            ProductionUnit.id,
            ProductionUnit.safra_id,
            Safra.cultura,
            ProductionUnit.area_id,
            ProductionUnit.area_ha,
            AreaRural.unidade_produtiva_id,
        ).join(
            Safra,
            and_(Safra.id == ProductionUnit.safra_id, Safra.tenant_id == self.tenant_id),
        ).join(
            AreaRural,
            and_(AreaRural.id == ProductionUnit.area_id, AreaRural.tenant_id == self.tenant_id),
        ).where(
            ProductionUnit.tenant_id == self.tenant_id,
            ProductionUnit.status != "CANCELADA",
        )

        if safra_id is not None:
            stmt = stmt.where(ProductionUnit.safra_id == safra_id)
        if unidade_produtiva_id is not None:
            stmt = stmt.where(AreaRural.unidade_produtiva_id == unidade_produtiva_id)
        if cultura:
            stmt = stmt.where(func.lower(func.coalesce(Safra.cultura, "")) == cultura.strip().lower())
        if production_unit_id is not None:
            stmt = stmt.where(ProductionUnit.id == production_unit_id)
        if production_unit_ids:
            stmt = stmt.where(ProductionUnit.id.in_(production_unit_ids))

        rows = (await self.session.execute(stmt.order_by(ProductionUnit.id))).all()
        production_units = [
            _ScopedProductionUnit(
                id=row.id,
                safra_id=row.safra_id,
                cultura=row.cultura,
                area_id=row.area_id,
                unidade_produtiva_id=row.unidade_produtiva_id,
                area_ha=float(row.area_ha or 0),
            )
            for row in rows
        ]
        production_unit_lookup = {
            (pu.safra_id, pu.area_id): pu.id
            for pu in production_units
        }

        if not production_units and production_unit_id is not None:
            # Mantém o retorno estável mesmo quando o filtro aponta para uma PU inexistente.
            production_units = []

        safra_obj = None
        if safra_id is not None:
            safra_obj = await self.session.get(Safra, safra_id)

        return {
            "production_units": production_units,
            "production_unit_ids": [pu.id for pu in production_units],
            "safra_id": safra_id,
            "safra": safra_obj,
            "cultura": cultura or (safra_obj.cultura if safra_obj else None),
            "unidade_produtiva_id": unidade_produtiva_id,
            "unidade_operacional_id": unidade_operacional_id,
            "unidade_operacional_resolvida": unidade_operacional_resolvida,
            "production_unit_lookup": production_unit_lookup,
        }

    async def _consolidar_receitas(
        self,
        scope: dict,
        *,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> tuple[DREAgricolaSection, float, list[DREWarning], int]:
        pu_ids = [pu.id for pu in scope["production_units"]]
        receitas_items: list[DRESourceItem] = []
        warnings: list[DREWarning] = []
        receita_excluida_total = 0
        deducoes = 0.0
        romaneios_lookup_por_pu: dict[UUID, dict[UUID, RomaneioColheita]] = defaultdict(dict)
        quantidade_comercializada: dict[UUID, float] = defaultdict(float)
        produtos_por_romaneio: dict[UUID, dict[UUID, float]] = defaultdict(dict)

        # Receita de comercialização tem precedência sobre romaneio na mesma PU.
        stmt_comm = (
            select(Receita, ComercializacaoCommodity, ProdutoColhido, ProductionUnit)
            .join(ComercializacaoCommodity, Receita.origem_id == ComercializacaoCommodity.id)
            .join(ProdutoColhido, ComercializacaoCommodity.produto_colhido_id == ProdutoColhido.id)
            .join(
                ProductionUnit,
                and_(
                    ProductionUnit.tenant_id == self.tenant_id,
                    ProductionUnit.safra_id == ProdutoColhido.safra_id,
                    ProductionUnit.area_id == ProdutoColhido.talhao_id,
                ),
            )
            .where(
                Receita.tenant_id == self.tenant_id,
                Receita.ativo == True,
                Receita.origem_tipo == "COMERCIALIZACAO",
            )
        )
        stmt_comm = stmt_comm.where(
            self._periodo_clause(func.coalesce(Receita.competencia, Receita.data_emissao), data_inicio=data_inicio, data_fim=data_fim)
        )
        if pu_ids:
            stmt_comm = stmt_comm.where(ProductionUnit.id.in_(pu_ids))

        comm_rows = (
            await self.session.execute(
                stmt_comm.order_by(func.coalesce(Receita.competencia, Receita.data_emissao), Receita.created_at)
            )
        ).all()

        comm_por_pu: dict[UUID, list[DRESourceItem]] = defaultdict(list)
        for receita, comercializacao, produto_colhido, pu in comm_rows:
            if produto_colhido.romaneio_id is not None:
                quantidade_comercializada[produto_colhido.romaneio_id] += float(comercializacao.quantidade or 0)
                produtos_por_romaneio[produto_colhido.romaneio_id][produto_colhido.id] = float(produto_colhido.quantidade or 0)
            item = DRESourceItem(
                natureza="RECEITA_OPERACIONAL",
                fonte_oficial="Receita",
                origem_tipo="COMERCIALIZACAO",
                origem_id=receita.origem_id,
                production_unit_id=pu.id,
                unidade_produtiva_id=scope["unidade_produtiva_id"],
                safra_id=produto_colhido.safra_id,
                valor=float(receita.valor_total or 0),
                meta={
                    "receita_id": str(receita.id),
                    "comercializacao_id": str(comercializacao.id),
                    "produto_colhido_id": str(produto_colhido.id),
                    "romaneio_id": str(produto_colhido.romaneio_id) if produto_colhido.romaneio_id else None,
                    "quantidade": float(comercializacao.quantidade or 0),
                    "unidade": comercializacao.unidade,
                    "data_economica": str(receita.competencia or receita.data_emissao),
                    "data_economica_fonte": "competencia" if receita.competencia else "data_emissao",
                },
            )
            comm_por_pu[pu.id].append(item)

        stmt_rom = (
            select(Receita, RomaneioColheita, ProductionUnit, ProdutoColhido)
            .join(RomaneioColheita, Receita.origem_id == RomaneioColheita.id)
            .outerjoin(ProdutoColhido, ProdutoColhido.romaneio_id == RomaneioColheita.id)
            .outerjoin(
                ProductionUnit,
                and_(
                    ProductionUnit.tenant_id == self.tenant_id,
                    or_(
                        ProductionUnit.id == RomaneioColheita.production_unit_id,
                        and_(
                            ProductionUnit.safra_id == RomaneioColheita.safra_id,
                            ProductionUnit.area_id == RomaneioColheita.talhao_id,
                        ),
                    ),
                ),
            )
            .where(
                Receita.tenant_id == self.tenant_id,
                Receita.ativo == True,
                Receita.origem_tipo == "ROMANEIO_COLHEITA",
            )
        )
        stmt_rom = stmt_rom.where(
            self._periodo_clause(func.coalesce(Receita.competencia, Receita.data_emissao), data_inicio=data_inicio, data_fim=data_fim)
        )
        if pu_ids:
            stmt_rom = stmt_rom.where(or_(ProductionUnit.id.in_(pu_ids), ProductionUnit.id.is_(None)))

        rom_rows = (
            await self.session.execute(
                stmt_rom.order_by(func.coalesce(Receita.competencia, Receita.data_emissao), Receita.created_at)
            )
        ).all()
        rom_por_pu: dict[UUID, list[DRESourceItem]] = defaultdict(list)
        romaneios_por_pu: dict[UUID, list[RomaneioColheita]] = defaultdict(list)
        for receita, romaneio, pu, produto_colhido in rom_rows:
            pu_id = pu.id if pu else None
            if pu_id is None and pu_ids:
                continue
            if pu_id is None:
                continue

            romaneios_por_pu[pu_id].append(romaneio)
            romaneios_lookup_por_pu[pu_id][romaneio.id] = romaneio
            if produto_colhido is not None:
                produtos_por_romaneio[romaneio.id][produto_colhido.id] = float(produto_colhido.quantidade or 0)
            item = DRESourceItem(
                natureza="RECEITA_OPERACIONAL",
                fonte_oficial="Receita",
                origem_tipo="ROMANEIO_COLHEITA",
                origem_id=receita.origem_id,
                production_unit_id=pu_id,
                unidade_produtiva_id=scope["unidade_produtiva_id"],
                safra_id=romaneio.safra_id,
                valor=float(receita.valor_total or 0),
                meta={
                    "receita_id": str(receita.id),
                    "romaneio_id": str(romaneio.id),
                    "produto_colhido_id": str(produto_colhido.id) if produto_colhido else None,
                    "data_economica": str(receita.competencia or receita.data_emissao),
                    "data_economica_fonte": "competencia" if receita.competencia else "data_emissao",
                },
            )
            rom_por_pu[pu_id].append(item)

        for items in comm_por_pu.values():
            receitas_items.extend(items)

        romaneios_processados: set[UUID] = set()
        for pu_id, items in rom_por_pu.items():
            for item in items:
                romaneio_id = item.meta.get("romaneio_id")
                romaneio = None
                if romaneio_id is not None:
                    try:
                        romaneio_uuid = UUID(str(romaneio_id))
                    except Exception:
                        romaneio_uuid = None
                    if romaneio_uuid is not None:
                        romaneio = romaneios_lookup_por_pu.get(pu_id, {}).get(romaneio_uuid)
                if romaneio is None or romaneio.id in romaneios_processados:
                    continue
                romaneios_processados.add(romaneio.id)
                quantidade_produzida = sum(produtos_por_romaneio[romaneio.id].values())
                quantidade_vendida = quantidade_comercializada[romaneio.id]
                item, excluida, warning = self._calcular_saldo_romaneio(
                    item,
                    romaneio,
                    quantidade_produzida,
                    quantidade_vendida,
                    pu_id,
                )
                receitas_items.append(item)
                receita_excluida_total += excluida
                if warning:
                    warnings.append(warning)
                if romaneio.preco_saca and romaneio.sacas_60kg is not None:
                    saldo_percentual = item.meta.get("saldo_percentual", 1.0)
                    bruto_est = (
                        float(romaneio.peso_liquido_kg or 0)
                        / 60.0
                        * float(romaneio.preco_saca or 0)
                        * float(saldo_percentual)
                    )
                    deducoes += max(bruto_est - float(item.valor), 0.0)

        receitas_items = [item for item in receitas_items if item.valor > 0]

        valor_total = round(sum(item.valor for item in receitas_items), 2)
        fontes = defaultdict(float)
        for item in receitas_items:
            fontes[item.origem_tipo or "OUTRO"] += item.valor

        section = DREAgricolaSection(
            valor=valor_total,
            itens=receitas_items,
            total_registros=len(receitas_items),
            fontes={k: round(v, 2) for k, v in sorted(fontes.items())},
        )
        return section, deducoes, warnings, receita_excluida_total

    @staticmethod
    def _calcular_saldo_romaneio(
        item: DRESourceItem,
        romaneio: RomaneioColheita,
        quantidade_produzida: float,
        quantidade_vendida: float,
        production_unit_id: UUID,
    ) -> tuple[DRESourceItem, int, DREWarning | None]:
        """Mantém no romaneio somente a parcela da produção ainda não comercializada."""
        if quantidade_vendida <= 0:
            return item, 0, None
        if quantidade_produzida <= 0:
            return item.model_copy(update={"valor": 0.0}), 1, DREWarning(
                codigo="ROMANEIO_SEM_QUANTIDADE_PARA_RECONCILIAR_VENDA",
                titulo="Romaneio sem quantidade para calcular saldo comercial",
                severidade="WARNING_LEVE",
                mensagem="A receita comercializada foi considerada, mas o saldo estimado do romaneio foi excluído por não haver quantidade produzida rastreável.",
                origem="dre_agricola_v1",
                amostras=[romaneio.numero_romaneio or f"Romaneio {str(romaneio.id)[:8]}"],
                meta={"production_unit_id": str(production_unit_id)},
            )
        saldo_percentual = max(quantidade_produzida - quantidade_vendida, 0.0) / quantidade_produzida
        saldo_valor = round(item.valor * saldo_percentual, 2)
        meta = {**item.meta, "quantidade_produzida": quantidade_produzida, "quantidade_comercializada": quantidade_vendida, "saldo_percentual": saldo_percentual}
        return item.model_copy(update={"valor": saldo_valor, "meta": meta}), int(saldo_valor == 0), None

    async def _consolidar_costs(
        self,
        scope: dict,
        *,
        direct: bool,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> DREAgricolaSection:
        pu_ids = [pu.id for pu in scope["production_units"]]
        if not pu_ids:
            return DREAgricolaSection()

        source_direct = {"OPERATION_EXECUTION", "INVENTORY_MOVEMENT", "ESTOQUE"}
        stmt = select(CostAllocation).where(
            CostAllocation.tenant_id == self.tenant_id,
            CostAllocation.production_unit_id.in_(pu_ids),
        )
        stmt = stmt.where(self._periodo_clause(CostAllocation.allocation_date, data_inicio=data_inicio, data_fim=data_fim))
        rows = list((await self.session.execute(stmt.order_by(CostAllocation.allocation_date, CostAllocation.created_at))).scalars().all())
        scope["_cost_allocations_rows"] = rows
        scope["_cost_allocation_ids"] = {
            alloc.inventory_movement_id
            for alloc in rows
            if alloc.inventory_movement_id is not None
        }
        scope["_cost_allocations_total"] = len(rows)

        items: list[DRESourceItem] = []
        fontes = defaultdict(float)
        total = 0.0

        for alloc in rows:
            is_direct = alloc.source in source_direct
            if direct != is_direct:
                continue
            valor = float(alloc.amount or 0)
            total += valor
            fontes[alloc.source] += valor
            items.append(
                DRESourceItem(
                    natureza="CUSTO_DIRETO" if direct else "CUSTO_OPERACIONAL",
                    fonte_oficial="CostAllocation",
                    origem_tipo=alloc.source,
                    origem_id=alloc.source_id,
                    production_unit_id=alloc.production_unit_id,
                    safra_id=scope["safra_id"],
                    valor=valor,
                    meta={
                        "cost_allocation_id": str(alloc.id),
                        "cost_category": alloc.cost_category,
                        "allocation_method": alloc.allocation_method,
                        "allocation_date": str(alloc.allocation_date),
                        "data_economica": str(alloc.allocation_date),
                        "data_economica_fonte": "allocation_date",
                    },
                )
            )

        return DREAgricolaSection(
            valor=round(total, 2),
            itens=items,
            total_registros=len(items),
            fontes={k: round(v, 2) for k, v in sorted(fontes.items())},
        )

    async def _ratear_custos_por_lote(
        self,
        scope: dict,
        receitas_section: DREAgricolaSection,
        custos_diretos_section: DREAgricolaSection,
        custos_operacionais_section: DREAgricolaSection,
        *,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> tuple[list[DRELoteMargem], int]:
        """Rateia o custo de cada PU entre os lotes vendidos, proporcional à quantidade."""
        lotes: dict[UUID, dict] = {}
        for item in receitas_section.itens:
            produto_colhido_id_raw = item.meta.get("produto_colhido_id")
            if not produto_colhido_id_raw or item.production_unit_id is None:
                continue
            lote_id = UUID(str(produto_colhido_id_raw))
            entry = lotes.setdefault(
                lote_id,
                {
                    "production_unit_id": item.production_unit_id,
                    "quantidade": 0.0,
                    "unidade": item.meta.get("unidade"),
                    "receita_total": 0.0,
                },
            )
            entry["quantidade"] += float(item.meta.get("quantidade") or 0)
            entry["receita_total"] += item.valor

        custo_total_por_pu: dict[UUID, float] = defaultdict(float)
        for item in custos_diretos_section.itens:
            if item.production_unit_id is not None:
                custo_total_por_pu[item.production_unit_id] += item.valor
        for item in custos_operacionais_section.itens:
            if item.production_unit_id is not None:
                custo_total_por_pu[item.production_unit_id] += item.valor

        quantidade_total_por_pu: dict[UUID, float] = defaultdict(float)
        for lote in lotes.values():
            quantidade_total_por_pu[lote["production_unit_id"]] += lote["quantidade"]

        margens: list[DRELoteMargem] = []
        for lote_id, lote in sorted(lotes.items(), key=lambda kv: str(kv[0])):
            pu_id = lote["production_unit_id"]
            quantidade_total_pu = quantidade_total_por_pu.get(pu_id, 0.0)
            custo_total_pu = custo_total_por_pu.get(pu_id, 0.0)
            if quantidade_total_pu > 0:
                custo_rateado = round(custo_total_pu * (lote["quantidade"] / quantidade_total_pu), 2)
            else:
                custo_rateado = 0.0
            receita_total = round(lote["receita_total"], 2)
            margem = round(receita_total - custo_rateado, 2)
            margens.append(
                DRELoteMargem(
                    produto_colhido_id=lote_id,
                    production_unit_id=pu_id,
                    quantidade=lote["quantidade"],
                    unidade=lote["unidade"],
                    receita_total=receita_total,
                    custo_rateado=custo_rateado,
                    margem=margem,
                    margem_percentual=round(margem / receita_total * 100, 2) if receita_total else None,
                )
            )

        pu_ids = [pu.id for pu in scope["production_units"]]
        lotes_sem_vinculo = 0
        if pu_ids:
            stmt_sem_vinculo = (
                select(func.count(ComercializacaoCommodity.id))
                .select_from(Receita)
                .join(ComercializacaoCommodity, Receita.origem_id == ComercializacaoCommodity.id)
                .where(
                    Receita.tenant_id == self.tenant_id,
                    Receita.ativo == True,
                    Receita.origem_tipo == "COMERCIALIZACAO",
                    ComercializacaoCommodity.produto_colhido_id.is_(None),
                    self._periodo_clause(
                        func.coalesce(Receita.competencia, Receita.data_emissao),
                        data_inicio=data_inicio,
                        data_fim=data_fim,
                    ),
                )
            )
            lotes_sem_vinculo = (await self.session.execute(stmt_sem_vinculo)).scalar_one() or 0

        return margens, lotes_sem_vinculo

    async def _consolidar_despesas(
        self,
        scope: dict,
        custos_diretos_section: DREAgricolaSection,
        custos_operacionais_section: DREAgricolaSection,
        *,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> tuple[DREAgricolaSection, int]:
        """Consolida despesas somente quando não há camada superior equivalente."""
        pu_ids = [pu.id for pu in scope["production_units"]]
        if not pu_ids and scope["unidade_produtiva_id"] is None:
            return DREAgricolaSection(), 0

        # Origens que já possuem apropriação econômica oficial.
        alloc_op_ids = set(
            row[0]
            for row in (
                await self.session.execute(
                    select(func.distinct(OperacaoExecucao.operacao_id))
                    .join(CostAllocation, CostAllocation.operation_execution_id == OperacaoExecucao.id)
                    .where(
                        CostAllocation.tenant_id == self.tenant_id,
                        CostAllocation.production_unit_id.in_(pu_ids),
                        self._periodo_clause(CostAllocation.allocation_date, data_inicio=data_inicio, data_fim=data_fim),
                    )
                )
            ).all()
            if row[0] is not None
        )
        alloc_mov_origin_ids = set(
            row[0]
            for row in (
                await self.session.execute(
                    select(func.distinct(EstoqueMovimento.origem_id))
                    .join(CostAllocation, CostAllocation.inventory_movement_id == EstoqueMovimento.id)
                    .where(
                        CostAllocation.tenant_id == self.tenant_id,
                        CostAllocation.production_unit_id.in_(pu_ids),
                        self._periodo_clause(CostAllocation.allocation_date, data_inicio=data_inicio, data_fim=data_fim),
                    )
                )
            ).all()
            if row[0] is not None
        )
        alloc_rateio_ids = set(
            row[0]
            for row in (
                await self.session.execute(
                    select(func.distinct(CostAllocation.fin_rateio_id)).where(
                        CostAllocation.tenant_id == self.tenant_id,
                        CostAllocation.production_unit_id.in_(pu_ids),
                        CostAllocation.fin_rateio_id.isnot(None),
                        self._periodo_clause(CostAllocation.allocation_date, data_inicio=data_inicio, data_fim=data_fim),
                    )
                )
            ).all()
            if row[0] is not None
        )
        alloc_source_ids: dict[str, set[UUID]] = defaultdict(set)
        for allocation in scope.get("_cost_allocations_rows", []):
            if allocation.source_id is not None:
                alloc_source_ids[allocation.source].add(allocation.source_id)

        desp_stmt = select(Despesa).where(Despesa.tenant_id == self.tenant_id, Despesa.ativo == True)
        if scope["unidade_produtiva_id"] is not None:
            desp_stmt = desp_stmt.where(Despesa.unidade_produtiva_id == scope["unidade_produtiva_id"])
        desp_stmt = desp_stmt.where(
            self._periodo_clause(func.coalesce(Despesa.competencia, Despesa.data_emissao), data_inicio=data_inicio, data_fim=data_fim)
        )

        despesas = list(
            (
                await self.session.execute(
                    desp_stmt.order_by(func.coalesce(Despesa.competencia, Despesa.data_emissao), Despesa.created_at)
                )
            ).scalars().all()
        )
        if not despesas:
            return DREAgricolaSection(), 0

        op_ids = [d.origem_id for d in despesas if d.origem_tipo == "OPERACAO_AGRICOLA" and d.origem_id is not None]
        os_ids = [d.origem_id for d in despesas if d.origem_tipo == "ORDEM_SERVICO" and d.origem_id is not None]
        ab_ids = [d.origem_id for d in despesas if d.origem_tipo == "ABASTECIMENTO" and d.origem_id is not None]
        rateio_despesa_ids = [d.id for d in despesas]

        operacoes_map = {
            row.id: row
            for row in (await self.session.execute(select(OperacaoAgricola).where(OperacaoAgricola.id.in_(op_ids)))).scalars().all()
        }
        os_map = {
            row.id: row
            for row in (await self.session.execute(select(OrdemServico).where(OrdemServico.id.in_(os_ids)))).scalars().all()
        }
        abastecimentos_map = {
            row.id: row
            for row in (await self.session.execute(select(Abastecimento).where(Abastecimento.id.in_(ab_ids)))).scalars().all()
        }
        rateios_map = {
            row.id: row
            for row in (await self.session.execute(select(Rateio).where(Rateio.despesa_id.in_(rateio_despesa_ids)))).scalars().all()
        }
        rateios_por_despesa: dict[UUID, list[Rateio]] = defaultdict(list)
        for rateio in rateios_map.values():
            rateios_por_despesa[rateio.despesa_id].append(rateio)

        items: list[DRESourceItem] = []
        total = 0.0
        excluidas = 0

        for despesa in despesas:
            rateios_da_despesa = rateios_por_despesa.get(despesa.id, [])
            rateios_da_safra = [
                rateio for rateio in rateios_da_despesa if rateio.safra_id == scope["safra_id"]
            ]

            # Um rateio pertence somente à safra informada. Nunca atribuir a outra safra
            # pelo simples fato de a despesa estar vinculada à mesma unidade produtiva.
            if rateios_da_despesa and not rateios_da_safra:
                continue

            # Compras representam aquisição financeira de estoque.
            # O custo agrícola é reconhecido pelo consumo via CostAllocation.
            if despesa.origem_tipo == "COMPRA":
                excluidas += 1
                continue
            if despesa.origem_tipo == "OPERACAO_AGRICOLA" and despesa.origem_id in alloc_op_ids:
                excluidas += 1
                continue
            if despesa.origem_tipo in {"ORDEM_SERVICO", "ABASTECIMENTO"} and despesa.origem_id in alloc_mov_origin_ids:
                excluidas += 1
                continue
            if any(rateio.id in alloc_rateio_ids for rateio in rateios_da_safra):
                excluidas += 1
                continue
            if self._despesa_tem_allocation_canonica(despesa, alloc_source_ids):
                excluidas += 1
                continue

            pu_id = None
            if despesa.origem_tipo == "OPERACAO_AGRICOLA" and despesa.origem_id in operacoes_map:
                pu_id = operacoes_map[despesa.origem_id].production_unit_id
            elif despesa.origem_tipo == "ORDEM_SERVICO" and despesa.origem_id in os_map:
                os_obj = os_map[despesa.origem_id]
                pu_id = scope["production_unit_lookup"].get((os_obj.safra_id, os_obj.talhao_id))
            elif despesa.origem_tipo == "ABASTECIMENTO" and despesa.origem_id in abastecimentos_map:
                ab_obj = abastecimentos_map[despesa.origem_id]
                pu_id = scope["production_unit_lookup"].get((ab_obj.safra_id, ab_obj.talhao_id))
            elif rateios_da_safra:
                rateio = rateios_da_safra[0]
                pu_id = scope["production_unit_lookup"].get((rateio.safra_id, rateio.talhao_id))

            if pu_ids and pu_id is not None and pu_id not in pu_ids:
                continue
            if pu_ids and pu_id is None and scope["unidade_produtiva_id"] is None:
                # Sem como atribuir ao PU escolhido, não entra na DRE filtrada por PU.
                continue

            valor = (
                sum(float(rateio.valor_rateado or 0) for rateio in rateios_da_safra)
                if rateios_da_safra
                else float(despesa.valor_total or 0)
            )
            total += valor
            items.append(
                DRESourceItem(
                    natureza="DESPESA_OPERACIONAL",
                    fonte_oficial="Despesa",
                    origem_tipo=despesa.origem_tipo,
                    origem_id=despesa.origem_id,
                    production_unit_id=pu_id,
                    unidade_produtiva_id=despesa.unidade_produtiva_id,
                    safra_id=scope["safra_id"],
                    valor=valor,
                    meta={
                        "despesa_id": str(despesa.id),
                        "status": despesa.status,
                        "data_emissao": str(despesa.data_emissao),
                        "data_economica": str(despesa.competencia or despesa.data_emissao),
                        "data_economica_fonte": "competencia" if despesa.competencia else "data_emissao",
                        "plano_conta_id": str(despesa.plano_conta_id),
                    },
                )
            )

        return DREAgricolaSection(
            valor=round(total, 2),
            itens=items,
            total_registros=len(items),
            fontes={"DESPESA": round(total, 2)},
        ), excluidas

    @staticmethod
    def _despesa_tem_allocation_canonica(
        despesa: Despesa,
        alloc_source_ids: dict[str, set[UUID]],
    ) -> bool:
        """Aplica precedência econômica para novas origens operacionais canônicas."""
        if despesa.origem_id is None:
            return False
        source_map = {
            "ABASTECIMENTO": {"FROTA_COMBUSTIVEL"},
            "ORDEM_SERVICO": {"FROTA_PECAS", "FROTA_MANUTENCAO"},
            "RH_DIARIA": {"RH_DIARIA"},
            "RH_EMPREITADA": {"RH_EMPREITADA"},
        }
        fontes = source_map.get(despesa.origem_tipo or "", set())
        return any(despesa.origem_id in alloc_source_ids.get(source, set()) for source in fontes)

    async def _resolver_pu_por_safra_talhao(
        self,
        safra_id: UUID | None,
        talhao_id: UUID | None,
        scope_pu_ids: list[UUID],
    ) -> UUID | None:
        if safra_id is None or talhao_id is None:
            return None
        stmt = select(ProductionUnit.id).where(
            ProductionUnit.tenant_id == self.tenant_id,
            ProductionUnit.safra_id == safra_id,
            ProductionUnit.area_id == talhao_id,
        )
        if scope_pu_ids:
            stmt = stmt.where(ProductionUnit.id.in_(scope_pu_ids))
        return (await self.session.execute(stmt.limit(1))).scalar_one_or_none()

    async def _montar_reconciliacao(
        self,
        scope: dict,
        receitas_excluidas: int,
        despesas_excluidas: int,
        *,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> DREReconcilacaoMeta:
        pu_ids = [pu.id for pu in scope["production_units"]]
        contexto = await self._carregar_contexto_reconciliacao(
            scope,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        lancamentos = contexto["lancamentos"]
        lanc_receita = sum(float(l.valor or 0) for l in lancamentos if l.tipo == "RECEITA")
        lanc_custo = sum(float(l.valor or 0) for l in lancamentos if l.tipo == "CUSTO")
        movimentos = contexto["movimentos"]
        movimentos_com_custo = sum(1 for mov in movimentos if float(mov.custo_total or 0) > 0)
        allocations_total = int(contexto["allocations_total"])

        return DREReconcilacaoMeta(
            lancamentos_financeiros_receita=round(lanc_receita, 2),
            lancamentos_financeiros_custo=round(lanc_custo, 2),
            lancamentos_financeiros_total=round(lanc_receita - lanc_custo, 2),
            estoque_movimentos_com_custo=movimentos_com_custo,
            cost_allocations_total=allocations_total,
            despesas_excluidas_por_precedencia=despesas_excluidas,
            receitas_excluidas_por_precedencia=receitas_excluidas,
            observacao=(
                "LancamentoFinanceiro e EstoqueMovimento foram usados apenas como reconciliação. "
                "A consolidação de DRE respeita a precedencia economica oficial."
            ),
            detalhes={
                "production_unit_ids": [str(pu_id) for pu_id in pu_ids],
                "lancamentos_financeiros": len(lancamentos),
                "estoque_movimentos": len(movimentos),
                "periodo": {
                    "data_inicio": str(data_inicio) if data_inicio else None,
                    "data_fim": str(data_fim) if data_fim else None,
                },
            },
        )

    async def _montar_warnings(
        self,
        scope: dict,
        receitas_warnings: list[DREWarning],
        despesas_excluidas: int,
        *,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> list[DREWarning]:
        warnings: list[DREWarning] = list(receitas_warnings)
        if data_inicio is None and data_fim is None:
            alertas = AlertasAgricolasService(self.session, self.tenant_id)
            findings = await alertas.detectar_inconsistencias_reconciliacao_economica()
            for finding in findings:
                warnings.append(
                    DREWarning(
                        codigo=finding.codigo,
                        titulo=finding.titulo,
                        severidade=finding.severidade,
                        mensagem=finding.mensagem,
                        origem=finding.origem,
                        amostras=[str(sample) for sample in finding.amostras],
                        meta=finding.meta,
                    )
                )

        if despesas_excluidas > 0:
            warnings.append(
                DREWarning(
                    codigo="DESPESA_SUPRIMIDA_POR_PRECEDENCIA",
                    titulo="Despesa excluída por camada econômica superior",
                    severidade="WARNING_LEVE",
                    mensagem="Algumas despesas foram excluídas da DRE porque já estavam representadas por apropriação de custo (rateio) ou outra camada econômica superior.",
                    origem="dre_agricola_v1",
                    amostras=[str(despesas_excluidas)],
                    meta={"quantidade_excluida": despesas_excluidas},
                )
            )

        pu_ids = [pu.id for pu in scope["production_units"]]
        if pu_ids and not any(w.codigo == "MOVIMENTO_COM_CUSTO_SEM_ALLOCATION" for w in warnings):
            contexto = await self._carregar_contexto_reconciliacao(
                scope,
                data_inicio=data_inicio,
                data_fim=data_fim,
            )
            movimentos = contexto["movimentos"]
            if movimentos:
                allocation_ids = contexto["allocation_ids"]
                sem_alloc = [m for m in movimentos if m.id not in allocation_ids]
                if sem_alloc:
                    warnings.append(
                        DREWarning(
                            codigo="MOVIMENTO_COM_CUSTO_SEM_ALLOCATION",
                            titulo="Movimento de estoque com custo sem apropriação",
                            severidade="RISCO_ECONOMICO",
                            mensagem="Há movimento de estoque com custo e sem apropriação (rateio de custo) na unidade filtrada.",
                            origem="estoque_movimentos",
                            amostras=[
                                f"Movimento {m.tipo_movimento}"
                                f"{' — lote ' + m.numero_lote if m.numero_lote else ''}"
                                f" ({m.data_movimento.strftime('%d/%m/%Y')}) · custo R$ {float(m.custo_total or 0):.2f}"
                                for m in sem_alloc[:5]
                            ],
                            meta={"quantidade": len(sem_alloc)},
                            )
                    )
        return warnings

    async def _carregar_contexto_reconciliacao(
        self,
        scope: dict,
        *,
        data_inicio: date | None = None,
        data_fim: date | None = None,
    ) -> dict[str, object]:
        cache_key = build_analytics_value_key(
            "agricola.dre.reconciliacao.context.v1",
            build_analytics_scope_key(
                self.tenant_id,
                scope.get("safra_id"),
                None,
                scope.get("unidade_produtiva_id"),
                data_inicio,
                data_fim,
            ),
        )
        cache = get_analytics_request_cache()
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        pu_ids = [pu.id for pu in scope["production_units"]]
        lancamentos = list(
            (
                await self.session.execute(
                    select(LancamentoFinanceiro).where(
                        LancamentoFinanceiro.tenant_id == self.tenant_id,
                        LancamentoFinanceiro.safra_id == scope["safra_id"] if scope["safra_id"] is not None else True,
                        self._periodo_clause(LancamentoFinanceiro.data, data_inicio=data_inicio, data_fim=data_fim),
                    )
                )
            ).scalars().all()
        )
        movimentos = list(
            (
                await self.session.execute(
                    select(EstoqueMovimento).where(
                        EstoqueMovimento.tenant_id == self.tenant_id,
                        EstoqueMovimento.production_unit_id.in_(pu_ids) if pu_ids else True,
                        self._periodo_clause(EstoqueMovimento.data_movimento, data_inicio=data_inicio, data_fim=data_fim),
                    )
                )
            ).scalars().all()
        )
        allocation_ids = set(scope.get("_cost_allocation_ids") or [])
        allocations_total = int(scope.get("_cost_allocations_total") or 0)
        contexto = {
            "lancamentos": lancamentos,
            "movimentos": movimentos,
            "allocation_ids": allocation_ids,
            "allocations_total": allocations_total,
        }
        cache[cache_key] = contexto
        return contexto

    @staticmethod
    def _normalizar_data(valor: date | datetime | None) -> date | None:
        if valor is None:
            return None
        return valor.date() if isinstance(valor, datetime) else valor

    @classmethod
    def _periodo_clause(
        cls,
        coluna,
        *,
        data_inicio: date | None,
        data_fim: date | None,
    ):
        clausulas = []
        if data_inicio is not None:
            clausulas.append(coluna >= data_inicio)
        if data_fim is not None:
            clausulas.append(coluna <= data_fim)
        if not clausulas:
            return True
        return and_(*clausulas)
