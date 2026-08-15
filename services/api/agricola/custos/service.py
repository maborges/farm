from datetime import date
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from core.exceptions import BusinessRuleError

from agricola.cultivos.models import Cultivo  # noqa: F401 - registers relationship target
from agricola.safras.models import Safra, SafraTalhao
from agricola.production_units.models import ProductionUnit
from agricola.custos.models import CostAllocation
from agricola.a1_planejamento.models import ItemOrcamentoSafra
from agricola.custos.schemas import ReumoCustosSafraResponse, CustoBreakdown


async def calcular_custo_unitario_snapshot(
    session: AsyncSession,
    tenant_id: UUID,
    safra_id: UUID,
    talhao_id: UUID,
    quantidade_lote: float,
    data_referencia: date,
) -> float | None:
    """Snapshot de custo unitário (Alternativa B do OPERATIONS-GAP-01):
    custo acumulado do PU até a data / quantidade acumulada do PU até a data
    (incluindo o próprio lote sendo criado). Retorna None quando o PU do
    par safra+talhão é ambíguo/inexistente ou não há base de rateio."""
    from agricola.colheita.models import ProdutoColhido

    pu_ids = (
        (
            await session.execute(
                select(ProductionUnit.id).where(
                    ProductionUnit.tenant_id == tenant_id,
                    ProductionUnit.safra_id == safra_id,
                    ProductionUnit.area_id == talhao_id,
                    ProductionUnit.status != "CANCELADA",
                )
            )
        )
        .scalars()
        .all()
    )
    if len(pu_ids) != 1:
        return None
    pu_id = pu_ids[0]

    custo_acumulado = (
        await session.execute(
            select(func.coalesce(func.sum(CostAllocation.amount), 0)).where(
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.production_unit_id == pu_id,
                CostAllocation.allocation_date <= data_referencia,
            )
        )
    ).scalar_one()

    quantidade_anterior = (
        await session.execute(
            select(func.coalesce(func.sum(ProdutoColhido.quantidade), 0)).where(
                ProdutoColhido.tenant_id == tenant_id,
                ProdutoColhido.safra_id == safra_id,
                ProdutoColhido.talhao_id == talhao_id,
                ProdutoColhido.data_entrada <= data_referencia,
            )
        )
    ).scalar_one()

    quantidade_total = float(quantidade_anterior or 0) + float(quantidade_lote or 0)
    if quantidade_total <= 0:
        return None

    return round(float(custo_acumulado or 0) / quantidade_total, 4)


class CustosService:
    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    async def get_resumo_safra(self, safra_id: UUID, talhao_id: UUID | None = None) -> ReumoCustosSafraResponse:
        # Busca a Safra para ter a area
        stmt_safra = select(Safra).filter_by(id=safra_id, tenant_id=self.tenant_id)
        result_safra = await self.session.execute(stmt_safra)
        safra = result_safra.scalar_one_or_none()
        
        if not safra:
            raise BusinessRuleError("Safra não encontrada.")
            
        stmt_area_pu = select(func.coalesce(func.sum(ProductionUnit.area_ha), 0)).where(
            ProductionUnit.tenant_id == self.tenant_id,
            ProductionUnit.safra_id == safra_id,
            ProductionUnit.status != "CANCELADA",
        )
        if talhao_id:
            stmt_area_pu = stmt_area_pu.where(ProductionUnit.area_id == talhao_id)
        area_pu = (await self.session.execute(stmt_area_pu)).scalar_one()

        area_talhoes = 0
        if not talhao_id:
            area_talhoes = (await self.session.execute(
                select(func.coalesce(func.sum(SafraTalhao.area_ha), 0)).where(
                    SafraTalhao.tenant_id == self.tenant_id,
                    SafraTalhao.safra_id == safra_id,
                )
            )).scalar_one()
        area_ha = float(area_pu or area_talhoes or 1.0)
        
        breakdowns = []
        custo_total = 0.0
        fonte_apuracao = "COST_ALLOCATION"
        usou_fallback_operacional = False

        stmt_alloc = (
            select(
                CostAllocation.cost_category.label("categoria"),
                func.sum(CostAllocation.amount).label("total"),
            )
            .join(ProductionUnit, ProductionUnit.id == CostAllocation.production_unit_id)
            .where(
                CostAllocation.tenant_id == self.tenant_id,
                ProductionUnit.safra_id == safra_id,
            )
            .group_by(CostAllocation.cost_category)
        )
        if talhao_id:
            stmt_alloc = stmt_alloc.where(ProductionUnit.area_id == talhao_id)
        items = (await self.session.execute(stmt_alloc)).all()

        for row in items:
            valor = float(row.total or 0)
            custo_total += valor
            breakdowns.append({
                "categoria": row.categoria,
                "valor_total": valor,
                "valor_por_ha": valor / float(area_ha),
                "percentual": 0 # calculado no proximo step
            })
            
        # Atualiza percentuais
        for b in breakdowns:
            if custo_total > 0:
                b["percentual"] = round((b["valor_total"] / custo_total) * 100, 2)
            
        orcamento = None
        desvio = None
        fonte_orcamento_previsto = "ORCAMENTO_SAFRA"
        usou_fallback_orcamento = False
        stmt_orcamento = select(
            func.coalesce(func.sum(ItemOrcamentoSafra.custo_total), 0)
        ).where(
            ItemOrcamentoSafra.tenant_id == self.tenant_id,
            ItemOrcamentoSafra.safra_id == safra_id,
        )
        orcamento_total = float((await self.session.execute(stmt_orcamento)).scalar_one() or 0)
        if orcamento_total > 0:
            orcamento = orcamento_total
        else:
            custo_previsto_ha = getattr(safra, "custo_previsto_ha", None)
            if custo_previsto_ha:
                usou_fallback_orcamento = True
                fonte_orcamento_previsto = "SAFRA_CUSTO_PREVISTO_HA_FALLBACK"
                orcamento = float(custo_previsto_ha * area_ha)
        if orcamento is not None and orcamento > 0:
            desvio = round(((custo_total - orcamento) / orcamento) * 100, 2)
                
        return ReumoCustosSafraResponse(
            safra_id=safra_id,
            area_total_ha=float(area_ha),
            custo_total_realizado=custo_total,
            custo_realizado_por_ha=custo_total / float(area_ha),
            orcamento_previsto_total=orcamento,
            desvio_orcamento_pct=desvio,
            fonte_orcamento_previsto=fonte_orcamento_previsto,
            usou_fallback_orcamento=usou_fallback_orcamento,
            fonte_apuracao=fonte_apuracao,
            usou_fallback_operacional=usou_fallback_operacional,
            breakdown=breakdowns
        )
