"""Depreciação linear de ativos patrimoniais (OPERATIONS-GAP-01 §21.34).

Gera lançamentos de `CostAllocation` (source=DEPRECIACAO_EQUIPAMENTO /
DEPRECIACAO_BENFEITORIA) para Equipamentos e Benfeitorias depreciáveis,
usando o método linear simples: (valor_aquisicao - valor_residual) / (vida_util_anos * 12).

Job mensal, idempotente por (source, source_id, mês/ano de allocation_date).

LIMITAÇÃO CONHECIDA (ver adendo 21.34 da auditoria): `CostAllocation.production_unit_id`
é FK NOT NULL para `production_units` (unidade econômica safra+cultivo+área do módulo
agrícola) — uma entidade DIFERENTE de `unidades_produtivas` (propriedade/fazenda,
`core/models/unidade_produtiva.py`), que é o que `Equipamento.unidade_produtiva_id` e
`Benfeitoria.unidade_produtiva_id` referenciam. Não existe hoje um `ProductionUnit`
correspondente a "propriedade inteira" — depreciação de patrimônio fixo é overhead de
fazenda, não de safra/cultivo/área específica. Por isso o lançamento é **pulado com log**
(nunca quebra o job) sempre que não houver um `ProductionUnit` explicitamente resolvível
para o ativo. Fechar esse gap requer decisão de produto (criar ProductionUnit "overhead"
por unidade produtiva, ou trocar a FK para aceitar ambas as tabelas) — fora do escopo
desta implementação.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from agricola.custos.constants import DEPRECIACAO_BENFEITORIA, DEPRECIACAO_EQUIPAMENTO
from agricola.custos.models import CostAllocation
from agricola.production_units.models import ProductionUnit
from core.cadastros.equipamentos.models import CategoriaPatrimonial, Equipamento
from core.cadastros.propriedades.models import AreaRural
from imoveis.models.imovel import Benfeitoria, ImovelRural


def calcular_valor_mensal(
    valor_aquisicao,
    valor_residual,
    vida_util_anos: int | None,
) -> Decimal:
    """Depreciação linear mensal. Nunca retorna valor negativo."""
    if not vida_util_anos or vida_util_anos <= 0:
        return Decimal("0")
    if valor_aquisicao is None:
        return Decimal("0")

    aquisicao = Decimal(str(valor_aquisicao))
    residual = Decimal(str(valor_residual)) if valor_residual is not None else Decimal("0")

    base = aquisicao - residual
    if base <= 0:
        return Decimal("0")

    return base / Decimal(str(vida_util_anos * 12))


def _primeiro_dia_mes_corrente() -> date:
    hoje = datetime.now(timezone.utc).date()
    return hoje.replace(day=1)


async def _resolver_production_unit(
    session: AsyncSession, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID
) -> uuid.UUID | None:
    """Resolve um ProductionUnit (safra+cultivo+área) qualquer pertencente à
    UnidadeProdutiva (propriedade/fazenda) informada, via AreaRural.unidade_produtiva_id.

    Ver limitação documentada no topo do módulo: não há relação 1:1, então
    escolhemos o ProductionUnit mais recente da propriedade como destino do
    custo de depreciação (overhead de fazenda). Retorna None se a propriedade
    não tiver nenhum ProductionUnit — o lançamento é pulado nesse caso."""
    stmt = (
        select(ProductionUnit.id)
        .join(AreaRural, AreaRural.id == ProductionUnit.area_id)
        .where(
            ProductionUnit.tenant_id == tenant_id,
            AreaRural.unidade_produtiva_id == unidade_produtiva_id,
        )
        .order_by(ProductionUnit.id.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _ja_lancado(session: AsyncSession, source: str, source_id: uuid.UUID, mes: date) -> bool:
    stmt = select(CostAllocation.id).where(
        CostAllocation.source == source,
        CostAllocation.source_id == source_id,
        extract("year", CostAllocation.allocation_date) == mes.year,
        extract("month", CostAllocation.allocation_date) == mes.month,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def lancar_depreciacao_mensal(session: AsyncSession, tenant_id: uuid.UUID | None = None) -> dict:
    """Lança CostAllocation de depreciação linear para Equipamentos e Benfeitorias
    depreciáveis do mês corrente. Idempotente."""
    mes = _primeiro_dia_mes_corrente()
    contadores = {
        "equipamentos_lancados": 0,
        "equipamentos_pulados": 0,
        "benfeitorias_lancadas": 0,
        "benfeitorias_puladas": 0,
        "sem_production_unit_mapeavel": 0,
    }

    # --- Equipamentos ---
    stmt_eq = select(Equipamento).where(
        Equipamento.categoria_patrimonial == CategoriaPatrimonial.ATIVO_DEPRECIAVEL.value,
        Equipamento.vida_util_anos.is_not(None),
        Equipamento.valor_aquisicao.is_not(None),
        Equipamento.unidade_produtiva_id.is_not(None),
    )
    if tenant_id is not None:
        stmt_eq = stmt_eq.where(Equipamento.tenant_id == tenant_id)

    equipamentos = (await session.execute(stmt_eq)).scalars().all()
    for eq in equipamentos:
        valor_mensal = calcular_valor_mensal(eq.valor_aquisicao, eq.valor_residual, eq.vida_util_anos)
        if valor_mensal <= 0:
            contadores["equipamentos_pulados"] += 1
            continue
        if await _ja_lancado(session, DEPRECIACAO_EQUIPAMENTO, eq.id, mes):
            contadores["equipamentos_pulados"] += 1
            continue
        production_unit_id = await _resolver_production_unit(session, eq.tenant_id, eq.unidade_produtiva_id)
        if production_unit_id is None:
            contadores["sem_production_unit_mapeavel"] += 1
            continue
        session.add(
            CostAllocation(
                id=uuid.uuid4(),
                tenant_id=eq.tenant_id,
                production_unit_id=production_unit_id,
                source=DEPRECIACAO_EQUIPAMENTO,
                source_id=eq.id,
                cost_category="OUTROS",
                amount=valor_mensal,
                allocation_date=mes,
                allocation_method="DIRECT",
            )
        )
        contadores["equipamentos_lancados"] += 1

    # --- Benfeitorias (tenant_id derivado via ImovelRural, pois Benfeitoria não tem tenant_id próprio) ---
    stmt_bf = (
        select(Benfeitoria, ImovelRural.tenant_id)
        .join(ImovelRural, ImovelRural.id == Benfeitoria.imovel_id)
        .where(
            Benfeitoria.vida_util_anos.is_not(None),
            Benfeitoria.unidade_produtiva_id.is_not(None),
        )
    )
    if tenant_id is not None:
        stmt_bf = stmt_bf.where(ImovelRural.tenant_id == tenant_id)

    for bf, bf_tenant_id in (await session.execute(stmt_bf)).all():
        valor_mensal = calcular_valor_mensal(bf.valor_estimado, bf.valor_residual, bf.vida_util_anos)
        if valor_mensal <= 0:
            contadores["benfeitorias_puladas"] += 1
            continue
        if await _ja_lancado(session, DEPRECIACAO_BENFEITORIA, bf.id, mes):
            contadores["benfeitorias_puladas"] += 1
            continue
        production_unit_id = await _resolver_production_unit(session, bf_tenant_id, bf.unidade_produtiva_id)
        if production_unit_id is None:
            contadores["sem_production_unit_mapeavel"] += 1
            continue
        session.add(
            CostAllocation(
                id=uuid.uuid4(),
                tenant_id=bf_tenant_id,
                production_unit_id=production_unit_id,
                source=DEPRECIACAO_BENFEITORIA,
                source_id=bf.id,
                cost_category="OUTROS",
                amount=valor_mensal,
                allocation_date=mes,
                allocation_method="DIRECT",
            )
        )
        contadores["benfeitorias_lancadas"] += 1

    await session.commit()
    return contadores
