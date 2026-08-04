import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import date

from core.constants import PlanTier
from core.dependencies import get_session, get_current_user, get_tenant_id, require_module, require_tier
from core.cadastros.propriedades.models import AreaRural
from agricola.safras.models import Safra
from agricola.cultivos.models import Cultivo, CultivoArea
from agricola.production_units.models import ProductionUnit
from agricola.custos.models import CostAllocation
from agricola.custos.service import CustosService
from agricola.a1_planejamento.models import ItemOrcamentoSafra
from agricola.tarefas.models import SafraTarefa
from agricola.services.talhao_service import AgricolaTalhaoService
from financeiro.comercializacao.service import ComercializacaoService

router = APIRouter(prefix="/reports", tags=["Relatórios"])

SAFRA_STATUS_ATIVA = ["PLANEJADA", "PREPARO_SOLO", "PLANTIO", "DESENVOLVIMENTO", "COLHEITA", "POS_COLHEITA"]

CATEGORIA_ROTULO = {
    "SEMENTE": "Sementes",
    "FERTILIZANTE": "Fertilizantes",
    "DEFENSIVO": "Defensivos",
}


@router.get("/agricola/summary")
async def get_agricola_summary_report(
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _module: None = Depends(require_module("A1_PLANEJAMENTO")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    """Consolidado de dados agrícolas para relatórios, com base em safras ativas do tenant."""
    stmt_safras_ativas = select(Safra.id).where(
        Safra.tenant_id == tenant_id,
        Safra.status.in_(SAFRA_STATUS_ATIVA),
    )
    safras_ativas_ids = list((await session.execute(stmt_safras_ativas)).scalars().all())
    safras_ativas = len(safras_ativas_ids)

    usando_fallback_ultima_safra = False
    if not safras_ativas_ids:
        # Sem safra em andamento: cai para a mais recente (mesmo ENCERRADA/CANCELADA)
        # para o resumo não ficar vazio logo após o fim do ciclo.
        stmt_ultima_safra = (
            select(Safra.id)
            .where(Safra.tenant_id == tenant_id)
            .order_by(Safra.created_at.desc())
            .limit(1)
        )
        ultima_id = (await session.execute(stmt_ultima_safra)).scalar_one_or_none()
        if ultima_id:
            safras_ativas_ids = [ultima_id]
            usando_fallback_ultima_safra = True

    total_hectares = 0.0
    custo_medio_ha = 0.0
    if safras_ativas_ids:
        total_hectares = float((await session.execute(
            select(func.coalesce(func.sum(ProductionUnit.area_ha), 0)).where(
                ProductionUnit.tenant_id == tenant_id,
                ProductionUnit.safra_id.in_(safras_ativas_ids),
                ProductionUnit.status != "CANCELADA",
            )
        )).scalar_one())

        custo_total = float((await session.execute(
            select(func.coalesce(func.sum(CostAllocation.amount), 0))
            .join(ProductionUnit, ProductionUnit.id == CostAllocation.production_unit_id)
            .where(
                CostAllocation.tenant_id == tenant_id,
                ProductionUnit.safra_id.in_(safras_ativas_ids),
            )
        )).scalar_one())
        if total_hectares > 0:
            custo_medio_ha = custo_total / total_hectares

    stmt_produtividade = (
        select(
            Cultivo.cultura,
            func.coalesce(func.sum(CultivoArea.area_ha), 0).label("area"),
            func.avg(Cultivo.produtividade_real_sc_ha).label("produtividade"),
        )
        .join(CultivoArea, CultivoArea.cultivo_id == Cultivo.id)
        .where(
            Cultivo.tenant_id == tenant_id,
            Cultivo.safra_id.in_(safras_ativas_ids) if safras_ativas_ids else False,
        )
        .group_by(Cultivo.cultura)
    )
    produtividade_por_cultura = []
    if safras_ativas_ids:
        for row in (await session.execute(stmt_produtividade)).all():
            produtividade_por_cultura.append({
                "cultura": row.cultura or "Não informado",
                "area": float(row.area or 0),
                "produtividade": float(row.produtividade) if row.produtividade is not None else 0.0,
                "unidade": "sc/ha",
            })

    uso_insumos = []
    if safras_ativas_ids:
        stmt_insumos = (
            select(
                ItemOrcamentoSafra.categoria,
                ItemOrcamentoSafra.descricao,
                ItemOrcamentoSafra.unidade,
                func.sum(ItemOrcamentoSafra.quantidade).label("quantidade"),
                func.sum(ItemOrcamentoSafra.custo_total).label("custo"),
            )
            .where(
                ItemOrcamentoSafra.tenant_id == tenant_id,
                ItemOrcamentoSafra.safra_id.in_(safras_ativas_ids),
                ItemOrcamentoSafra.categoria.in_(list(CATEGORIA_ROTULO.keys())),
            )
            .group_by(ItemOrcamentoSafra.categoria, ItemOrcamentoSafra.descricao, ItemOrcamentoSafra.unidade)
        )
        for row in (await session.execute(stmt_insumos)).all():
            uso_insumos.append({
                "insumo": row.descricao or CATEGORIA_ROTULO.get(row.categoria, row.categoria),
                "quantidade": float(row.quantidade or 0),
                "unidade": row.unidade or "",
                "custo": float(row.custo or 0),
            })

    cronograma_atividades = []
    if safras_ativas_ids:
        stmt_tarefas = (
            select(SafraTarefa.data_prevista, SafraTarefa.tipo, SafraTarefa.status)
            .where(
                SafraTarefa.tenant_id == tenant_id,
                SafraTarefa.safra_id.in_(safras_ativas_ids),
                SafraTarefa.status.notin_(["CANCELADA"]),
            )
            .order_by(SafraTarefa.data_prevista.asc())
            .limit(20)
        )
        for row in (await session.execute(stmt_tarefas)).all():
            cronograma_atividades.append({
                "data": row.data_prevista.isoformat() if row.data_prevista else None,
                "atividade": row.tipo,
                "status": row.status,
            })

    return {
        "resumo": {
            "total_hectares": round(total_hectares, 2),
            "safras_ativas": safras_ativas,
            "custo_medio_ha": round(custo_medio_ha, 2),
            "previsao_colheita_ton": 0,
            "usando_ultima_safra_encerrada": usando_fallback_ultima_safra,
        },
        "produtividade_por_cultura": produtividade_por_cultura,
        "uso_insumos": uso_insumos,
        "cronograma_atividades": cronograma_atividades,
    }


@router.get("/pecuaria/summary")
async def get_pecuaria_summary_report(
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
):
    """Consolidado de dados zootécnicos."""
    return {
        "rebanho": {
            "total_cabecas": 2450,
            "ua_total": 1850.5,  # Unidade Animal
            "gmd_medio": 0.850,  # Ganho Médio Diário (kg)
            "lotes_ativos": 12
        },
        "composicao_categorias": [
            {"categoria": "Bezerros", "quantidade": 850},
            {"categoria": "Novilhas", "quantidade": 600},
            {"categoria": "Touros", "quantidade": 50},
            {"categoria": "Vacas", "quantidade": 950}
        ],
        "sanitario_pendente": 145,
        "estoque_pastagem": {
            "disponivel_massa": 2500,
            "carga_animal": 1.5
        }
    }


@router.get("/agricola/talhoes")
async def get_agricola_talhoes_report(
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _module: None = Depends(require_module("A1_PLANEJAMENTO")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    """Lista resumida de talhões para seleção no relatório."""
    talhao_svc = AgricolaTalhaoService(session, tenant_id)
    talhoes = await talhao_svc.listar_talhoes_com_cultivo()
    return [
        {
            "id": str(t["id"]),
            "nome": t["nome"],
            "area": float(t["area_hectares"] or t["area_hectares_manual"] or 0),
            "cultura": (t["cultivo_atual"] or {}).get("cultura", "Sem cultivo ativo"),
        }
        for t in talhoes
    ]


@router.get("/agricola/profitability")
async def get_agricola_profitability_report(
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _module: None = Depends(require_module("A1_PLANEJAMENTO")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    """Rentabilidade por talhão, com base em custo real (rateio) e receita real (vendas confirmadas)."""
    custos_svc = CustosService(session, tenant_id)
    comerc_svc = ComercializacaoService(session, tenant_id)

    stmt_safras_ativas = select(Safra.id).where(
        Safra.tenant_id == tenant_id,
        Safra.status.in_(SAFRA_STATUS_ATIVA),
    )
    safras_ativas_ids = list((await session.execute(stmt_safras_ativas)).scalars().all())
    if not safras_ativas_ids:
        stmt_ultima_safra = (
            select(Safra.id)
            .where(Safra.tenant_id == tenant_id)
            .order_by(Safra.created_at.desc())
            .limit(1)
        )
        ultima_id = (await session.execute(stmt_ultima_safra)).scalar_one_or_none()
        if ultima_id:
            safras_ativas_ids = [ultima_id]

    talhao_svc = AgricolaTalhaoService(session, tenant_id)
    talhoes = await talhao_svc.listar_talhoes_com_cultivo()

    por_talhao = []
    receita_total = 0.0
    custo_total = 0.0
    lucro_por_cultura: dict[str, float] = {}

    for t in talhoes:
        cultivo_atual = t.get("cultivo_atual")
        if not cultivo_atual:
            continue
        stmt_safra_id = select(Cultivo.safra_id).where(Cultivo.id == cultivo_atual["id"])
        safra_id = (await session.execute(stmt_safra_id)).scalar_one_or_none()
        if not safra_id or safra_id not in safras_ativas_ids:
            continue

        resumo_custo = await custos_svc.get_resumo_safra(safra_id, talhao_id=t["id"])
        receita = await comerc_svc.get_receita_por_safra(safra_id, talhao_id=t["id"])
        custo = resumo_custo.custo_total_realizado
        lucro = receita - custo
        margem = round((lucro / receita) * 100, 2) if receita > 0 else 0.0

        por_talhao.append({
            "id": str(t["id"]),
            "nome": t["nome"],
            "receita": round(receita, 2),
            "custo": round(custo, 2),
            "lucro": round(lucro, 2),
            "margem": margem,
        })
        receita_total += receita
        custo_total += custo
        cultura = cultivo_atual["cultura"] or "Não informado"
        lucro_por_cultura[cultura] = lucro_por_cultura.get(cultura, 0.0) + lucro

    lucro_total = receita_total - custo_total
    margem_media = round((lucro_total / receita_total) * 100, 2) if receita_total > 0 else 0.0
    roi_geral = round(lucro_total / custo_total, 4) if custo_total > 0 else 0.0

    return {
        "roi_geral": roi_geral,
        "margem_media": margem_media,
        "receita_total": round(receita_total, 2),
        "lucro_total": round(lucro_total, 2),
        "por_talhao": por_talhao,
        "distribuicao_lucro_cultura": [
            {"name": cultura, "value": round(valor, 2)} for cultura, valor in lucro_por_cultura.items()
        ],
    }


@router.get("/agricola/talhao/{talhao_id}")
async def get_agricola_talhao_detail_report(
    talhao_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user=Depends(get_current_user),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    _module: None = Depends(require_module("A1_PLANEJAMENTO")),
    _tier: None = Depends(require_tier(PlanTier.PROFISSIONAL)),
):
    """Detalhe de um talhão: cultivo atual, histórico de produtividade, custos acumulados e apontamentos."""
    area = await session.get(AreaRural, talhao_id)
    if not area or area.tenant_id != tenant_id or area.tipo != "TALHAO":
        raise HTTPException(status_code=404, detail="Talhão não encontrado")

    stmt_cultivo_atual = (
        select(Cultivo, Safra.ano_safra)
        .join(CultivoArea, CultivoArea.cultivo_id == Cultivo.id)
        .join(Safra, Cultivo.safra_id == Safra.id)
        .where(
            CultivoArea.area_id == talhao_id,
            Cultivo.tenant_id == tenant_id,
            Cultivo.status.notin_(["CANCELADA", "ENCERRADA"]),
        )
        .order_by(Cultivo.created_at.desc())
        .limit(1)
    )
    row = (await session.execute(stmt_cultivo_atual)).first()
    cultivo_atual, ano_safra_atual = row if row else (None, None)

    stmt_historico = (
        select(Safra.ano_safra, Cultivo.produtividade_real_sc_ha)
        .join(Cultivo, Cultivo.safra_id == Safra.id)
        .join(CultivoArea, CultivoArea.cultivo_id == Cultivo.id)
        .where(
            CultivoArea.area_id == talhao_id,
            Cultivo.tenant_id == tenant_id,
            Cultivo.produtividade_real_sc_ha.isnot(None),
        )
        .order_by(Safra.ano_safra.asc())
    )
    historico_produtividade = [
        {"safra": r.ano_safra, "produtividade": float(r.produtividade_real_sc_ha)}
        for r in (await session.execute(stmt_historico)).all()
    ]

    custos_acumulados = {
        "preparo_solo": 0.0, "sementes": 0.0, "fertilizantes": 0.0,
        "defensivos": 0.0, "operacoes": 0.0, "total": 0.0, "por_ha": 0.0,
    }
    if cultivo_atual:
        custos_svc = CustosService(session, tenant_id)
        resumo = await custos_svc.get_resumo_safra(cultivo_atual.safra_id, talhao_id=talhao_id)
        campo_por_categoria = {
            "SEMENTE": "sementes", "FERTILIZANTE": "fertilizantes", "DEFENSIVO": "defensivos",
            "PREPARO_SOLO": "preparo_solo",
        }
        for b in resumo.breakdown:
            campo = campo_por_categoria.get(b.categoria, "operacoes")
            custos_acumulados[campo] += b.valor_total
        custos_acumulados["total"] = round(resumo.custo_total_realizado, 2)
        custos_acumulados["por_ha"] = round(resumo.custo_realizado_por_ha, 2)
        for k in ("preparo_solo", "sementes", "fertilizantes", "defensivos", "operacoes"):
            custos_acumulados[k] = round(custos_acumulados[k], 2)

    apontamentos_recentes = []
    if cultivo_atual:
        stmt_tarefas = (
            select(SafraTarefa.data_prevista, SafraTarefa.tipo, SafraTarefa.status)
            .where(
                SafraTarefa.tenant_id == tenant_id,
                SafraTarefa.safra_id == cultivo_atual.safra_id,
            )
            .order_by(SafraTarefa.data_prevista.desc())
            .limit(10)
        )
        for r in (await session.execute(stmt_tarefas)).all():
            apontamentos_recentes.append({
                "data": r.data_prevista.isoformat() if r.data_prevista else None,
                "tipo": r.tipo,
                "detalhe": r.status,
            })

    dias_ciclo = 0
    if cultivo_atual and cultivo_atual.data_plantio_real:
        dias_ciclo = (date.today() - cultivo_atual.data_plantio_real).days

    return {
        "id": str(area.id),
        "nome": area.nome,
        "area": float(area.area_hectares or area.area_hectares_manual or 0),
        "cultura_atual": cultivo_atual.cultura if cultivo_atual else "Sem cultivo ativo",
        "data_plantio": cultivo_atual.data_plantio_real.isoformat() if cultivo_atual and cultivo_atual.data_plantio_real else None,
        "dias_ciclo": dias_ciclo,
        "estagio_fenologico": cultivo_atual.status if cultivo_atual else "N/A",
        "historico_produtividade": historico_produtividade,
        "custos_acumulados": custos_acumulados,
        "apontamentos_recentes": apontamentos_recentes,
    }
