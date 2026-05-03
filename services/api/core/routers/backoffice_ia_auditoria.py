"""
Auditoria financeira e gestão de solicitações de créditos de IA.

Restrito a admins com permissão backoffice:ia:view.
"""
import csv
import io
from datetime import datetime, date, timezone, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from collections import defaultdict
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, require_permission
from core.models.solicitacoes_comerciais import SolicitacaoComercial
from core.models.solicitacoes_historico import SolicitacaoHistorico
from core.models.tenant import Tenant

_STATUS_PERMITIDOS = {"ABERTA", "EM_ANALISE", "CONCLUIDA", "CANCELADA"}


def _calcular_prioridade(sol: SolicitacaoComercial) -> int:
    """
    Pontuação determinística 0–100 para priorização comercial.

    Base por status:  EM_ANALISE=+50, ABERTA=+20, CANCELADA=-20
    Valor estimado:   min(valor/10, 50)
    Follow-up:        atrasado=+40, dentro de 1h=+20
    """
    score = 0

    if sol.status == "EM_ANALISE":
        score += 50
    elif sol.status == "ABERTA":
        score += 20
    elif sol.status == "CANCELADA":
        score -= 20

    if sol.valor_estimado is not None:
        score += min(int(float(sol.valor_estimado) / 10), 50)

    if sol.proximo_followup_em is not None:
        now = datetime.now(timezone.utc)
        followup = sol.proximo_followup_em
        if followup.tzinfo is None:
            followup = followup.replace(tzinfo=timezone.utc)
        if followup < now:
            score += 40
        elif followup <= now + timedelta(hours=1):
            score += 20

    return max(0, min(100, score))


async def _registrar_historico(
    session: AsyncSession,
    solicitacao: SolicitacaoComercial,
    tipo_evento: str,
    valor_anterior: Optional[str],
    valor_novo: Optional[str],
    observacao: Optional[str] = None,
) -> None:
    import uuid as _uuid
    hist = SolicitacaoHistorico(
        id=_uuid.uuid4(),
        solicitacao_id=solicitacao.id,
        tenant_id=solicitacao.tenant_id,
        tipo_evento=tipo_evento,
        valor_anterior=valor_anterior,
        valor_novo=valor_novo,
        observacao=observacao,
    )
    session.add(hist)


router = APIRouter(
    prefix="/backoffice/ia",
    tags=["Backoffice — IA Auditoria"],
    dependencies=[Depends(require_permission("backoffice:ia:view"))],
)


class AuditoriaItemResponse(BaseModel):
    solicitacao_id: str
    tenant_id: str
    quantidade_creditos: Optional[int] = None
    valor_total: Optional[float] = None
    custo_estimado: Optional[float] = None
    margem_estimada: Optional[float] = None
    margem_percentual: Optional[float] = None
    status_pagamento: Optional[str] = None
    status: str
    created_at: datetime


class AuditoriaTotaisResponse(BaseModel):
    receita_total: float
    custo_total: float
    margem_total: float
    total_vendas: int
    total_creditos: int


class AuditoriaResponse(BaseModel):
    itens: list[AuditoriaItemResponse]
    totais: AuditoriaTotaisResponse


def _extrair_float(detalhes: dict | None, campo: str) -> Optional[float]:
    if not detalhes:
        return None
    v = detalhes.get(campo)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _extrair_int(detalhes: dict | None, campo: str) -> Optional[int]:
    if not detalhes:
        return None
    v = detalhes.get(campo)
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


_CSV_COLUNAS = [
    "solicitacao_id", "tenant_id", "quantidade_creditos",
    "valor_total", "custo_estimado", "margem_estimada",
    "margem_percentual", "status_pagamento", "created_at",
]


def _build_filtros(
    status_pagamento: Optional[str],
    data_inicio: Optional[date],
    data_fim: Optional[date],
) -> list:
    filtros = [SolicitacaoComercial.tipo == "CREDITOS_IA"]
    if status_pagamento:
        filtros.append(SolicitacaoComercial.status_pagamento == status_pagamento)
    if data_inicio:
        filtros.append(
            SolicitacaoComercial.created_at >= datetime(data_inicio.year, data_inicio.month, data_inicio.day, tzinfo=timezone.utc)
        )
    if data_fim:
        fim_dt = datetime(data_fim.year, data_fim.month, data_fim.day, tzinfo=timezone.utc) + timedelta(days=1)
        filtros.append(SolicitacaoComercial.created_at < fim_dt)
    return filtros


async def _fetch_rows(
    filtros: list,
    session: AsyncSession,
    skip: int = 0,
    limit: int = 500,
) -> list:
    stmt = (
        select(SolicitacaoComercial)
        .where(and_(*filtros))
        .order_by(SolicitacaoComercial.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())


def _row_to_item(r: SolicitacaoComercial) -> AuditoriaItemResponse:
    det = r.detalhes or {}
    qtd = _extrair_int(det, "quantidade") or _extrair_int(det, "quantidade_creditos")
    valor = _extrair_float(det, "valor_total") or (float(r.valor_estimado) if r.valor_estimado else None)
    return AuditoriaItemResponse(
        solicitacao_id=str(r.id),
        tenant_id=str(r.tenant_id),
        quantidade_creditos=qtd,
        valor_total=valor,
        custo_estimado=_extrair_float(det, "custo_estimado"),
        margem_estimada=_extrair_float(det, "margem_estimada"),
        margem_percentual=_extrair_float(det, "margem_percentual"),
        status_pagamento=r.status_pagamento,
        status=r.status,
        created_at=r.created_at,
    )


@router.get("/creditos/auditoria", response_model=AuditoriaResponse)
async def auditoria_creditos_ia(
    status_pagamento: Optional[str] = Query(None, description="PENDENTE | PAGO | EXPIRADO"),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    session: AsyncSession = Depends(get_session),
):
    """Lista e totaliza vendas de créditos de IA. Restrito a backoffice."""
    filtros = _build_filtros(status_pagamento, data_inicio, data_fim)
    rows = await _fetch_rows(filtros, session, skip, limit)

    itens = [_row_to_item(r) for r in rows]
    receita_total = sum(i.valor_total or 0.0 for i in itens if i.status_pagamento == "PAGO")
    custo_total = sum(i.custo_estimado or 0.0 for i in itens if i.status_pagamento == "PAGO")
    margem_total = sum(i.margem_estimada or 0.0 for i in itens if i.status_pagamento == "PAGO")
    total_creditos = sum(i.quantidade_creditos or 0 for i in itens if i.status_pagamento == "PAGO")

    return AuditoriaResponse(
        itens=itens,
        totais=AuditoriaTotaisResponse(
            receita_total=round(receita_total, 2),
            custo_total=round(custo_total, 2),
            margem_total=round(margem_total, 2),
            total_vendas=len([i for i in itens if i.status_pagamento == "PAGO"]),
            total_creditos=total_creditos,
        ),
    )


@router.get("/creditos/auditoria/export.csv", include_in_schema=True)
async def exportar_auditoria_csv(
    status_pagamento: Optional[str] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Exporta auditoria de créditos de IA em CSV. Restrito a backoffice."""
    filtros = _build_filtros(status_pagamento, data_inicio, data_fim)
    rows = await _fetch_rows(filtros, session, skip=0, limit=10000)
    itens = [_row_to_item(r) for r in rows]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=_CSV_COLUNAS, extrasaction="ignore")
    writer.writeheader()
    for item in itens:
        writer.writerow({
            "solicitacao_id": item.solicitacao_id,
            "tenant_id": item.tenant_id,
            "quantidade_creditos": item.quantidade_creditos if item.quantidade_creditos is not None else "",
            "valor_total": f"{item.valor_total:.2f}" if item.valor_total is not None else "",
            "custo_estimado": f"{item.custo_estimado:.2f}" if item.custo_estimado is not None else "",
            "margem_estimada": f"{item.margem_estimada:.2f}" if item.margem_estimada is not None else "",
            "margem_percentual": f"{item.margem_percentual:.2f}" if item.margem_percentual is not None else "",
            "status_pagamento": item.status_pagamento or "",
            "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else "",
        })

    output.seek(0)
    filename = "auditoria_creditos_ia.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class TopTenantItem(BaseModel):
    tenant_id: str
    tenant_nome: str
    receita_total: float
    creditos_comprados: int


class ResumoExecutivoResponse(BaseModel):
    receita_total: float
    custo_total: float
    margem_total: float
    margem_percentual_media: float
    creditos_vendidos: int
    quantidade_vendas: int
    ticket_medio: float
    top_tenants: list[TopTenantItem]


@router.get("/creditos/resumo-executivo", response_model=ResumoExecutivoResponse)
async def resumo_executivo_ia(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    top_n: int = Query(5, ge=1, le=20),
    session: AsyncSession = Depends(get_session),
):
    """KPIs executivos de monetização de IA. Restrito a backoffice."""
    filtros = _build_filtros("PAGO", data_inicio, data_fim)
    rows = await _fetch_rows(filtros, session, skip=0, limit=10000)
    itens = [_row_to_item(r) for r in rows]

    receita_total = sum(i.valor_total or 0.0 for i in itens)
    custo_total = sum(i.custo_estimado or 0.0 for i in itens)
    margem_total = sum(i.margem_estimada or 0.0 for i in itens)
    creditos_vendidos = sum(i.quantidade_creditos or 0 for i in itens)
    quantidade_vendas = len(itens)

    margens = [i.margem_percentual for i in itens if i.margem_percentual is not None]
    margem_pct_media = sum(margens) / len(margens) if margens else 0.0
    ticket_medio = receita_total / quantidade_vendas if quantidade_vendas else 0.0

    # Agrupa por tenant
    por_tenant: dict[str, dict] = defaultdict(lambda: {"receita": 0.0, "creditos": 0})
    for item in itens:
        por_tenant[item.tenant_id]["receita"] += item.valor_total or 0.0
        por_tenant[item.tenant_id]["creditos"] += item.quantidade_creditos or 0

    # Busca nomes dos top tenants
    top_ids = sorted(por_tenant, key=lambda t: por_tenant[t]["receita"], reverse=True)[:top_n]
    tenant_nomes: dict[str, str] = {}
    if top_ids:
        import uuid as _uuid
        stmt_t = select(Tenant.id, Tenant.nome).where(
            Tenant.id.in_([_uuid.UUID(t) for t in top_ids])
        )
        for row in (await session.execute(stmt_t)).all():
            tenant_nomes[str(row.id)] = row.nome

    top_tenants = [
        TopTenantItem(
            tenant_id=tid,
            tenant_nome=tenant_nomes.get(tid, tid[:8]),
            receita_total=round(por_tenant[tid]["receita"], 2),
            creditos_comprados=por_tenant[tid]["creditos"],
        )
        for tid in top_ids
    ]

    return ResumoExecutivoResponse(
        receita_total=round(receita_total, 2),
        custo_total=round(custo_total, 2),
        margem_total=round(margem_total, 2),
        margem_percentual_media=round(margem_pct_media, 2),
        creditos_vendidos=creditos_vendidos,
        quantidade_vendas=quantidade_vendas,
        ticket_medio=round(ticket_medio, 2),
        top_tenants=top_tenants,
    )


# ── Gestão de Solicitações ────────────────────────────────────────────────────

class SolicitacaoItemResponse(BaseModel):
    id: str
    tenant_id: str
    tenant_nome: str
    usuario_id: Optional[str] = None
    tipo: str
    quantidade_creditos: Optional[int] = None
    valor_estimado: Optional[float] = None
    status: str
    status_pagamento: Optional[str] = None
    observacao_comercial: Optional[str] = None
    responsavel_usuario_id: Optional[str] = None
    responsavel_nome: Optional[str] = None
    proximo_followup_em: Optional[datetime] = None
    followup_observacao: Optional[str] = None
    created_at: datetime
    prioridade: int = 0
    crm_sync_status: str = "NAO_ENVIADO"


class StatusUpdatePayload(BaseModel):
    status: str
    observacao_comercial: Optional[str] = None


@router.get("/creditos/solicitacoes", response_model=list[SolicitacaoItemResponse])
async def listar_solicitacoes(
    status: Optional[str] = Query(None, description="ABERTA | EM_ANALISE | CONCLUIDA | CANCELADA"),
    status_pagamento: Optional[str] = Query(None, description="PENDENTE | PAGO | EXPIRADO"),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    ordenar_por: Optional[str] = Query(None, description="prioridade"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=500),
    session: AsyncSession = Depends(get_session),
):
    """Lista solicitações comerciais de créditos de IA. Restrito a backoffice."""
    filtros: list = [SolicitacaoComercial.tipo == "CREDITOS_IA"]
    if status:
        filtros.append(SolicitacaoComercial.status == status)
    if status_pagamento:
        filtros.append(SolicitacaoComercial.status_pagamento == status_pagamento)
    if data_inicio:
        filtros.append(
            SolicitacaoComercial.created_at >= datetime(data_inicio.year, data_inicio.month, data_inicio.day, tzinfo=timezone.utc)
        )
    if data_fim:
        fim_dt = datetime(data_fim.year, data_fim.month, data_fim.day, tzinfo=timezone.utc) + timedelta(days=1)
        filtros.append(SolicitacaoComercial.created_at < fim_dt)

    stmt = (
        select(SolicitacaoComercial)
        .where(and_(*filtros))
        .order_by(SolicitacaoComercial.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = list((await session.execute(stmt)).scalars().all())

    # Busca nomes dos tenants em batch
    import uuid as _uuid
    from core.models.admin_user import AdminUser
    tenant_ids = list({r.tenant_id for r in rows})
    tenant_nomes: dict[str, str] = {}
    if tenant_ids:
        stmt_t = select(Tenant.id, Tenant.nome).where(Tenant.id.in_(tenant_ids))
        for row in (await session.execute(stmt_t)).all():
            tenant_nomes[str(row.id)] = row.nome

    # Busca nomes dos responsáveis em batch
    resp_ids = list({r.responsavel_usuario_id for r in rows if r.responsavel_usuario_id})
    resp_nomes: dict[str, str] = {}
    if resp_ids:
        stmt_r = select(AdminUser.id, AdminUser.nome).where(AdminUser.id.in_(resp_ids))
        for row in (await session.execute(stmt_r)).all():
            resp_nomes[str(row.id)] = row.nome

    itens = []
    for r in rows:
        det = r.detalhes or {}
        qtd = None
        for campo in ("quantidade", "quantidade_creditos"):
            v = det.get(campo)
            if v is not None:
                try:
                    qtd = int(v)
                    break
                except (TypeError, ValueError):
                    pass
        tid_str = str(r.tenant_id)
        resp_id_str = str(r.responsavel_usuario_id) if r.responsavel_usuario_id else None
        itens.append(SolicitacaoItemResponse(
            id=str(r.id),
            tenant_id=tid_str,
            tenant_nome=tenant_nomes.get(tid_str, tid_str[:8]),
            usuario_id=str(r.usuario_id) if r.usuario_id else None,
            tipo=r.tipo,
            quantidade_creditos=qtd,
            valor_estimado=float(r.valor_estimado) if r.valor_estimado is not None else None,
            status=r.status,
            status_pagamento=r.status_pagamento,
            observacao_comercial=r.observacao_comercial,
            responsavel_usuario_id=resp_id_str,
            responsavel_nome=resp_nomes.get(resp_id_str) if resp_id_str else None,
            proximo_followup_em=r.proximo_followup_em,
            followup_observacao=r.followup_observacao,
            created_at=r.created_at,
            prioridade=_calcular_prioridade(r),
            crm_sync_status=r.crm_sync_status or "NAO_ENVIADO",
        ))

    if ordenar_por == "prioridade":
        itens.sort(key=lambda x: x.prioridade, reverse=True)

    return itens


@router.get("/creditos/solicitacoes/fila-prioritaria", response_model=list[SolicitacaoItemResponse])
async def fila_prioritaria(
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Fila comercial: solicitações acionáveis ordenadas por prioridade desc."""
    stmt = (
        select(SolicitacaoComercial)
        .where(
            SolicitacaoComercial.tipo == "CREDITOS_IA",
            SolicitacaoComercial.status.notin_(["CONCLUIDA", "CANCELADA"]),
        )
        .order_by(SolicitacaoComercial.created_at.desc())
        .limit(limit * 3)  # busca mais para poder re-ordenar por prioridade
    )
    rows = list((await session.execute(stmt)).scalars().all())

    from core.models.admin_user import AdminUser
    tenant_ids = list({r.tenant_id for r in rows})
    tenant_nomes: dict[str, str] = {}
    if tenant_ids:
        for row in (await session.execute(select(Tenant.id, Tenant.nome).where(Tenant.id.in_(tenant_ids)))).all():
            tenant_nomes[str(row.id)] = row.nome

    resp_ids = list({r.responsavel_usuario_id for r in rows if r.responsavel_usuario_id})
    resp_nomes: dict[str, str] = {}
    if resp_ids:
        for row in (await session.execute(select(AdminUser.id, AdminUser.nome).where(AdminUser.id.in_(resp_ids)))).all():
            resp_nomes[str(row.id)] = row.nome

    itens = []
    for r in rows:
        det = r.detalhes or {}
        qtd = None
        for campo in ("quantidade", "quantidade_creditos"):
            v = det.get(campo)
            if v is not None:
                try:
                    qtd = int(v)
                    break
                except (TypeError, ValueError):
                    pass
        tid_str = str(r.tenant_id)
        resp_id_str = str(r.responsavel_usuario_id) if r.responsavel_usuario_id else None
        itens.append(SolicitacaoItemResponse(
            id=str(r.id),
            tenant_id=tid_str,
            tenant_nome=tenant_nomes.get(tid_str, tid_str[:8]),
            usuario_id=str(r.usuario_id) if r.usuario_id else None,
            tipo=r.tipo,
            quantidade_creditos=qtd,
            valor_estimado=float(r.valor_estimado) if r.valor_estimado is not None else None,
            status=r.status,
            status_pagamento=r.status_pagamento,
            observacao_comercial=r.observacao_comercial,
            responsavel_usuario_id=resp_id_str,
            responsavel_nome=resp_nomes.get(resp_id_str) if resp_id_str else None,
            proximo_followup_em=r.proximo_followup_em,
            followup_observacao=r.followup_observacao,
            created_at=r.created_at,
            prioridade=_calcular_prioridade(r),
            crm_sync_status=r.crm_sync_status or "NAO_ENVIADO",
        ))

    itens.sort(key=lambda x: x.prioridade, reverse=True)
    return itens[:limit]


# ── Resumo / Dashboard ────────────────────────────────────────────────────────

class ResumoPorResponsavel(BaseModel):
    responsavel_usuario_id: Optional[str] = None
    responsavel_nome: str
    total: int
    valor_estimado: float


class ResumoSolicitacoesResponse(BaseModel):
    total_abertas: int
    total_em_analise: int
    total_concluidas: int
    total_canceladas: int
    valor_pendente: float
    valor_concluido: float
    taxa_conversao: float
    por_responsavel: list[ResumoPorResponsavel]


@router.get("/creditos/solicitacoes/resumo", response_model=ResumoSolicitacoesResponse)
async def resumo_solicitacoes(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """KPIs do funil comercial de créditos de IA. Restrito a backoffice."""
    from core.models.admin_user import AdminUser

    filtros: list = [SolicitacaoComercial.tipo == "CREDITOS_IA"]
    if data_inicio:
        filtros.append(
            SolicitacaoComercial.created_at >= datetime(data_inicio.year, data_inicio.month, data_inicio.day, tzinfo=timezone.utc)
        )
    if data_fim:
        fim_dt = datetime(data_fim.year, data_fim.month, data_fim.day, tzinfo=timezone.utc) + timedelta(days=1)
        filtros.append(SolicitacaoComercial.created_at < fim_dt)

    rows = list((await session.execute(
        select(SolicitacaoComercial).where(and_(*filtros))
    )).scalars().all())

    total_abertas = sum(1 for r in rows if r.status == "ABERTA")
    total_em_analise = sum(1 for r in rows if r.status == "EM_ANALISE")
    total_concluidas = sum(1 for r in rows if r.status == "CONCLUIDA")
    total_canceladas = sum(1 for r in rows if r.status == "CANCELADA")

    pendentes = {"ABERTA", "EM_ANALISE"}
    valor_pendente = sum(float(r.valor_estimado or 0) for r in rows if r.status in pendentes)
    valor_concluido = sum(float(r.valor_estimado or 0) for r in rows if r.status == "CONCLUIDA")

    elegíveis = total_abertas + total_em_analise + total_concluidas
    taxa_conversao = round(total_concluidas / elegíveis * 100, 1) if elegíveis else 0.0

    # Agrupamento por responsável
    por_resp: dict[str, dict] = defaultdict(lambda: {"total": 0, "valor": 0.0, "nome": None})
    for r in rows:
        key = str(r.responsavel_usuario_id) if r.responsavel_usuario_id else "__sem_responsavel__"
        por_resp[key]["total"] += 1
        por_resp[key]["valor"] += float(r.valor_estimado or 0)

    # Busca nomes dos responsáveis
    resp_uuids = [r.responsavel_usuario_id for r in rows if r.responsavel_usuario_id]
    resp_nomes: dict[str, str] = {}
    if resp_uuids:
        for row in (await session.execute(
            select(AdminUser.id, AdminUser.nome).where(AdminUser.id.in_(resp_uuids))
        )).all():
            resp_nomes[str(row.id)] = row.nome

    por_responsavel = []
    for key, dados in sorted(por_resp.items(), key=lambda x: x[1]["total"], reverse=True):
        if key == "__sem_responsavel__":
            resp_id = None
            nome = "Sem responsável"
        else:
            resp_id = key
            nome = resp_nomes.get(key, key[:8])
        por_responsavel.append(ResumoPorResponsavel(
            responsavel_usuario_id=resp_id,
            responsavel_nome=nome,
            total=dados["total"],
            valor_estimado=round(dados["valor"], 2),
        ))

    return ResumoSolicitacoesResponse(
        total_abertas=total_abertas,
        total_em_analise=total_em_analise,
        total_concluidas=total_concluidas,
        total_canceladas=total_canceladas,
        valor_pendente=round(valor_pendente, 2),
        valor_concluido=round(valor_concluido, 2),
        taxa_conversao=taxa_conversao,
        por_responsavel=por_responsavel,
    )


async def _mock_enviar_crm(payload: dict) -> bool:
    """Mock de integração CRM. Retorna True (sucesso). Substituir por chamada real."""
    from loguru import logger
    logger.info(f"[crm_mock] Payload enviado ao CRM: {payload}")
    return True


@router.post("/creditos/solicitacoes/{solicitacao_id}/enviar-crm")
async def enviar_para_crm(
    solicitacao_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Exporta solicitação para o CRM externo e registra status de envio."""
    stmt = select(SolicitacaoComercial).where(
        SolicitacaoComercial.id == solicitacao_id,
        SolicitacaoComercial.tipo == "CREDITOS_IA",
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

    tenant = await session.get(Tenant, row.tenant_id)
    tenant_nome = tenant.nome if tenant else str(row.tenant_id)

    payload = {
        "solicitacao_id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "tenant_nome": tenant_nome,
        "valor_estimado": float(row.valor_estimado) if row.valor_estimado else None,
        "prioridade": _calcular_prioridade(row),
        "status": row.status,
        "observacao_comercial": row.observacao_comercial,
        "origem": row.origem,
        "created_at": row.created_at.isoformat(),
    }

    try:
        sucesso = await _mock_enviar_crm(payload)
        novo_status = "ENVIADO" if sucesso else "ERRO"
    except Exception:
        novo_status = "ERRO"

    await session.execute(
        update(SolicitacaoComercial)
        .where(SolicitacaoComercial.id == solicitacao_id)
        .values(
            crm_sync_status=novo_status,
            crm_sync_at=datetime.now(timezone.utc),
        )
    )
    await session.commit()

    await _registrar_historico(
        session, row, "CRM_ENVIADO",
        valor_anterior=row.crm_sync_status,
        valor_novo=novo_status,
    )
    await session.commit()

    return {"crm_sync_status": novo_status}


@router.patch("/creditos/solicitacoes/{solicitacao_id}/status")
async def atualizar_status_solicitacao(
    solicitacao_id: UUID,
    payload: StatusUpdatePayload,
    session: AsyncSession = Depends(get_session),
):
    """Atualiza status de uma solicitação. Restrito a backoffice."""
    if payload.status not in _STATUS_PERMITIDOS:
        raise HTTPException(
            status_code=422,
            detail=f"Status inválido. Permitidos: {sorted(_STATUS_PERMITIDOS)}",
        )

    stmt = select(SolicitacaoComercial).where(
        SolicitacaoComercial.id == solicitacao_id,
        SolicitacaoComercial.tipo == "CREDITOS_IA",
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

    status_anterior = row.status
    obs_anterior = row.observacao_comercial

    row.status = payload.status
    if payload.observacao_comercial is not None:
        row.observacao_comercial = payload.observacao_comercial

    if status_anterior != payload.status:
        await _registrar_historico(session, row, "STATUS_ALTERADO", status_anterior, payload.status)
    if payload.observacao_comercial is not None and obs_anterior != payload.observacao_comercial:
        await _registrar_historico(session, row, "OBSERVACAO_ALTERADA", obs_anterior, payload.observacao_comercial)

    await session.commit()
    await session.refresh(row)
    return {"id": str(row.id), "status": row.status, "observacao_comercial": row.observacao_comercial}


class ResponsavelPayload(BaseModel):
    responsavel_usuario_id: Optional[UUID] = None


@router.patch("/creditos/solicitacoes/{solicitacao_id}/responsavel")
async def atribuir_responsavel(
    solicitacao_id: UUID,
    payload: ResponsavelPayload,
    session: AsyncSession = Depends(get_session),
):
    """Atribui ou remove responsável de uma solicitação. Restrito a backoffice."""
    from core.models.admin_user import AdminUser

    stmt = select(SolicitacaoComercial).where(
        SolicitacaoComercial.id == solicitacao_id,
        SolicitacaoComercial.tipo == "CREDITOS_IA",
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

    resp_anterior = str(row.responsavel_usuario_id) if row.responsavel_usuario_id else None

    if payload.responsavel_usuario_id is not None:
        admin = (await session.execute(
            select(AdminUser).where(AdminUser.id == payload.responsavel_usuario_id)
        )).scalar_one_or_none()
        if admin is None:
            raise HTTPException(status_code=404, detail="Usuário responsável não encontrado.")
        row.responsavel_usuario_id = payload.responsavel_usuario_id
        responsavel_nome = admin.nome
        resp_novo = str(payload.responsavel_usuario_id)
    else:
        row.responsavel_usuario_id = None
        responsavel_nome = None
        resp_novo = None

    if resp_anterior != resp_novo:
        await _registrar_historico(session, row, "RESPONSAVEL_ALTERADO", resp_anterior, resp_novo)

    await session.commit()
    await session.refresh(row)
    return {
        "id": str(row.id),
        "responsavel_usuario_id": str(row.responsavel_usuario_id) if row.responsavel_usuario_id else None,
        "responsavel_nome": responsavel_nome,
    }


class FollowupPayload(BaseModel):
    proximo_followup_em: Optional[datetime] = None
    followup_observacao: Optional[str] = None


@router.patch("/creditos/solicitacoes/{solicitacao_id}/followup")
async def atualizar_followup(
    solicitacao_id: UUID,
    payload: FollowupPayload,
    session: AsyncSession = Depends(get_session),
):
    """Registra próximo follow-up. Restrito a backoffice."""
    stmt = select(SolicitacaoComercial).where(
        SolicitacaoComercial.id == solicitacao_id,
        SolicitacaoComercial.tipo == "CREDITOS_IA",
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

    dt_str_old = row.proximo_followup_em.isoformat() if row.proximo_followup_em else None
    dt_str_new = payload.proximo_followup_em.isoformat() if payload.proximo_followup_em else None

    row.proximo_followup_em = payload.proximo_followup_em
    row.followup_observacao = payload.followup_observacao

    await _registrar_historico(session, row, "FOLLOWUP_ALTERADO", dt_str_old, dt_str_new, payload.followup_observacao)

    await session.commit()
    await session.refresh(row)
    return {
        "id": str(row.id),
        "proximo_followup_em": row.proximo_followup_em.isoformat() if row.proximo_followup_em else None,
        "followup_observacao": row.followup_observacao,
    }


# ── Histórico ─────────────────────────────────────────────────────────────────

class HistoricoItemResponse(BaseModel):
    id: str
    tipo_evento: str
    valor_anterior: Optional[str] = None
    valor_novo: Optional[str] = None
    observacao: Optional[str] = None
    created_at: datetime


@router.get("/creditos/solicitacoes/{solicitacao_id}/historico", response_model=list[HistoricoItemResponse])
async def listar_historico(
    solicitacao_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Retorna histórico de eventos de uma solicitação. Restrito a backoffice."""
    sol = (await session.execute(
        select(SolicitacaoComercial).where(
            SolicitacaoComercial.id == solicitacao_id,
            SolicitacaoComercial.tipo == "CREDITOS_IA",
        )
    )).scalar_one_or_none()
    if sol is None:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

    stmt = (
        select(SolicitacaoHistorico)
        .where(SolicitacaoHistorico.solicitacao_id == solicitacao_id)
        .order_by(SolicitacaoHistorico.created_at.desc())
    )
    rows = list((await session.execute(stmt)).scalars().all())
    return [
        HistoricoItemResponse(
            id=str(r.id),
            tipo_evento=r.tipo_evento,
            valor_anterior=r.valor_anterior,
            valor_novo=r.valor_novo,
            observacao=r.observacao,
            created_at=r.created_at,
        )
        for r in rows
    ]
