from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError, EntityNotFoundError
from agricola.colheita.models import ProdutoColhido
from agricola.custos.models import CostAllocation, ProdutoColhidoCostAllocation
from agricola.production_units.models import ProductionUnit


async def _resolver_pu_do_lote(session: AsyncSession, tenant_id: UUID, lote: ProdutoColhido) -> UUID:
    pu_ids = (
        (
            await session.execute(
                select(ProductionUnit.id).where(
                    ProductionUnit.tenant_id == tenant_id,
                    ProductionUnit.safra_id == lote.safra_id,
                    ProductionUnit.area_id == lote.talhao_id,
                    ProductionUnit.status != "CANCELADA",
                )
            )
        )
        .scalars()
        .all()
    )
    if len(pu_ids) != 1:
        raise BusinessRuleError(
            "Não foi possível resolver uma ProductionUnit única para safra+talhão do lote "
            f"({lote.safra_id}/{lote.talhao_id}) — reconciliação de custo requer PU não ambígua."
        )
    return pu_ids[0]


async def _obter_lote(session: AsyncSession, tenant_id: UUID, produto_colhido_id: UUID) -> ProdutoColhido:
    lote = (
        await session.execute(
            select(ProdutoColhido).where(
                ProdutoColhido.id == produto_colhido_id,
                ProdutoColhido.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()
    if lote is None:
        raise EntityNotFoundError("Produto colhido não encontrado")
    return lote


async def reconciliar_alocacoes_lote(
    session: AsyncSession, tenant_id: UUID, produto_colhido_id: UUID
) -> list[ProdutoColhidoCostAllocation]:
    """Recalcula o rateio AUTOMATICO de custo entre todos os lotes do PU do lote
    informado, proporcional à quantidade. Linhas MANUAL não são recriadas nem
    apagadas. Retorna as linhas resultantes do lote solicitado."""
    lote = await _obter_lote(session, tenant_id, produto_colhido_id)
    pu_id = await _resolver_pu_do_lote(session, tenant_id, lote)

    lotes_pu = (
        (
            await session.execute(
                select(ProdutoColhido).where(
                    ProdutoColhido.tenant_id == tenant_id,
                    ProdutoColhido.safra_id == lote.safra_id,
                    ProdutoColhido.talhao_id == lote.talhao_id,
                )
            )
        )
        .scalars()
        .all()
    )
    lote_ids = [l.id for l in lotes_pu]
    quantidade_total = sum(float(l.quantidade or 0) for l in lotes_pu)

    custo_allocations = (
        (
            await session.execute(
                select(CostAllocation).where(
                    CostAllocation.tenant_id == tenant_id,
                    CostAllocation.production_unit_id == pu_id,
                )
            )
        )
        .scalars()
        .all()
    )

    overrides_manuais = set(
        (row.produto_colhido_id, row.cost_allocation_id)
        for row in (
            await session.execute(
                select(ProdutoColhidoCostAllocation.produto_colhido_id, ProdutoColhidoCostAllocation.cost_allocation_id).where(
                    ProdutoColhidoCostAllocation.tenant_id == tenant_id,
                    ProdutoColhidoCostAllocation.produto_colhido_id.in_(lote_ids),
                    ProdutoColhidoCostAllocation.origem_calculo == "MANUAL",
                )
            )
        ).all()
    )

    await session.execute(
        delete(ProdutoColhidoCostAllocation).where(
            ProdutoColhidoCostAllocation.tenant_id == tenant_id,
            ProdutoColhidoCostAllocation.produto_colhido_id.in_(lote_ids),
            ProdutoColhidoCostAllocation.origem_calculo == "AUTOMATICO",
        )
    )

    if quantidade_total > 0:
        for alloc in custo_allocations:
            amount = float(alloc.amount or 0)
            for l in lotes_pu:
                if (l.id, alloc.id) in overrides_manuais:
                    continue
                fracao = float(l.quantidade or 0) / quantidade_total
                if fracao <= 0:
                    continue
                session.add(
                    ProdutoColhidoCostAllocation(
                        tenant_id=tenant_id,
                        produto_colhido_id=l.id,
                        cost_allocation_id=alloc.id,
                        valor_atribuido=round(amount * fracao, 2),
                        percentual_atribuido=round(fracao * 100, 4),
                        origem_calculo="AUTOMATICO",
                    )
                )
    await session.flush()

    return (
        (
            await session.execute(
                select(ProdutoColhidoCostAllocation).where(
                    ProdutoColhidoCostAllocation.tenant_id == tenant_id,
                    ProdutoColhidoCostAllocation.produto_colhido_id == produto_colhido_id,
                )
            )
        )
        .scalars()
        .all()
    )


async def aplicar_override_manual(
    session: AsyncSession,
    tenant_id: UUID,
    produto_colhido_id: UUID,
    cost_allocation_id: UUID,
    valor_atribuido: float,
    justificativa: str,
    usuario_id: UUID | None = None,
) -> ProdutoColhidoCostAllocation:
    if not justificativa or not justificativa.strip():
        raise BusinessRuleError("Override manual de custo de lote exige justificativa.")

    lote = await _obter_lote(session, tenant_id, produto_colhido_id)
    pu_id = await _resolver_pu_do_lote(session, tenant_id, lote)

    alloc = (
        await session.execute(
            select(CostAllocation).where(
                CostAllocation.id == cost_allocation_id,
                CostAllocation.tenant_id == tenant_id,
                CostAllocation.production_unit_id == pu_id,
            )
        )
    ).scalar_one_or_none()
    if alloc is None:
        raise EntityNotFoundError("CostAllocation não encontrado para o PU deste lote")

    percentual = round((float(valor_atribuido) / float(alloc.amount)) * 100, 4) if float(alloc.amount or 0) else 0.0

    stmt = (
        pg_insert(ProdutoColhidoCostAllocation)
        .values(
            tenant_id=tenant_id,
            produto_colhido_id=produto_colhido_id,
            cost_allocation_id=cost_allocation_id,
            valor_atribuido=round(float(valor_atribuido), 2),
            percentual_atribuido=percentual,
            origem_calculo="MANUAL",
            justificativa=justificativa,
        )
        .on_conflict_do_update(
            constraint="uq_produto_colhido_cost_allocation",
            set_={
                "valor_atribuido": round(float(valor_atribuido), 2),
                "percentual_atribuido": percentual,
                "origem_calculo": "MANUAL",
                "justificativa": justificativa,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        .returning(ProdutoColhidoCostAllocation)
    )
    row = (await session.execute(stmt)).scalar_one()
    await session.flush()
    return row


async def obter_custo_alocado(session: AsyncSession, tenant_id: UUID, produto_colhido_id: UUID) -> dict:
    await _obter_lote(session, tenant_id, produto_colhido_id)
    itens = (
        (
            await session.execute(
                select(ProdutoColhidoCostAllocation).where(
                    ProdutoColhidoCostAllocation.tenant_id == tenant_id,
                    ProdutoColhidoCostAllocation.produto_colhido_id == produto_colhido_id,
                )
            )
        )
        .scalars()
        .all()
    )
    total = sum(float(item.valor_atribuido or 0) for item in itens)
    return {"itens": itens, "total": round(total, 2)}
