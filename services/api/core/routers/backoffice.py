from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update
from sqlalchemy.orm import selectinload
from typing import Any, List
import uuid
from loguru import logger

from core.constants import DEMO_EXTENSION_TICKET_CATEGORY
from core.dependencies import get_session, get_current_admin, require_any_permission, require_permission
from core.models.tenant import Tenant
from core.models.auth import Usuario, TenantUsuario
from core.models.sessao import SessaoAtiva
from core.models.billing import AssinaturaTenant, PlanoAssinatura, Fatura
from core.models.support import ChamadoSuporte, MensagemChamado, TicketStatus
from core.models.admin_audit_log import AdminAuditLog
from core.services.admin_audit_service import resolve_admin_identity
from core.services.demo_access_service import (
    DemoExtensionApprovalInput,
    approve_demo_extension,
    is_demo_tenant,
)
from core.schemas.billing_schemas import (
    PlanoAssinaturaCreate, PlanoAssinaturaResponse, PlanoAssinaturaUpdate,
    FaturaResponse, ReviewInvoiceRequest
)
from core.schemas.support_schemas import (
    AprovarProrrogacaoDemoRequest,
    ChamadoSuporteResponse,
    ChamadoDetalheResponse,
    MensagemChamadoCreate,
    MensagemChamadoResponse,
)
from core.schemas.auth_schemas import LoginBloqueadoItem, LoginBloqueadosListaResponse
from core.services.email_service import email_service

router = APIRouter(prefix="/backoffice", tags=["Backoffice"])


def _extrair_admin_identity(claims_or_user: Any) -> tuple[uuid.UUID, str]:
    """Extrai UUID e e-mail do operador administrativo com tolerância a dict ou model."""
    if isinstance(claims_or_user, dict):
        admin_sub = claims_or_user.get("sub") or claims_or_user.get("id")
        admin_email = claims_or_user.get("email") or claims_or_user.get("username") or "admin@deepfarms.com"
    else:
        admin_sub = getattr(claims_or_user, "id", None)
        admin_email = getattr(claims_or_user, "email", None) or getattr(claims_or_user, "username", "admin@deepfarms.com")
    try:
        admin_uid = uuid.UUID(str(admin_sub))
    except (ValueError, TypeError):
        admin_uid = uuid.uuid4()
    return admin_uid, str(admin_email)


@router.get("/bi/stats", dependencies=[Depends(get_current_admin)])
async def get_bi_stats(session: AsyncSession = Depends(get_session)):
    """Visão analítica profunda (BI) sobre a saúde do SaaS."""
    # 1. Churn Rate (Simulado com base em assinaturas inativas)
    total_assinaturas = await session.execute(select(func.count(AssinaturaTenant.id)))
    num_total = total_assinaturas.scalar_one() or 1
    
    inativas = await session.execute(select(func.count(AssinaturaTenant.id)).where(AssinaturaTenant.status == "CANCELADA"))
    num_inativas = inativas.scalar_one() or 0
    
    churn_rate = (num_inativas / num_total) * 100
    
    # 2. LTV (Lifetime Value) - Média MRR / Churn Rate
    mrr_res = await session.execute(select(func.sum(PlanoAssinatura.preco_mensal)).join(AssinaturaTenant).where(AssinaturaTenant.status == "ATIVA"))
    mrr = mrr_res.scalar_one() or 0
    avg_ticket = mrr / (num_total - num_inativas) if (num_total - num_inativas) > 0 else 0
    
    ltv = avg_ticket / (churn_rate / 100) if churn_rate > 0 else avg_ticket * 24 # Assume 2 anos se churn zero
    
    # 3. Retenção por Coorte (Simulado)
    coortes = [
        {"periodo": "2025-Q4", "tamanho": 45, "retencao": 92.5},
        {"periodo": "2026-Q1", "tamanho": 62, "retencao": 88.2},
        {"periodo": "2026-Q2", "tamanho": 28, "retencao": 95.0},
    ]

    # 4. Distribuição por Plano (Real)
    plano_dist = await session.execute(
        select(PlanoAssinatura.nome, func.count(AssinaturaTenant.id), func.sum(PlanoAssinatura.preco_mensal))
        .join(AssinaturaTenant)
        .group_by(PlanoAssinatura.nome)
    )
    dist = []
    for r in plano_dist:
        dist.append({
            "plano": r[0],
            "clientes": r[1],
            "receita": float(r[2] or 0)
        })

    # 5. Engajamento (Simulado - Seria contagem de operações agrícolas/financeiras)
    engajamento = {
        "usuarios_ativos_dia": int((num_total - num_inativas) * 0.65),
        "operacoes_por_dia": 1240,
        "hectares_gerenciados": 15400.5
    }

    return {
        "churn_rate": round(churn_rate, 2),
        "ltv": float(ltv),
        "cac_simulado": 450.0, # Custo de aquisição médio
        "payback_meses": round(450 / avg_ticket, 1) if avg_ticket > 0 else 0,
        "coortes": coortes,
        "distribuicao_receita": dist,
        "engajamento": engajamento,
        "periodo_analise": "Março/2026"
    }

@router.get("/dashboard/stats", dependencies=[Depends(get_current_admin)])
async def get_backoffice_stats(session: AsyncSession = Depends(get_session)):
    """Métricas avançadas para o Dashboard Administrativo do SaaS."""
    
    # 1. Contagens Básicas
    total_tenants = (await session.execute(select(func.count(Tenant.id)))).scalar() or 0
    active_tenants = (await session.execute(select(func.count(Tenant.id)).where(Tenant.ativo == True))).scalar() or 0
    total_users = (await session.execute(select(func.count(Usuario.id)))).scalar() or 0

    # Total de usuários gratuitos vs comerciais
    commercial_users_stmt = select(func.count(func.distinct(TenantUsuario.usuario_id)))
    commercial_users = (await session.execute(commercial_users_stmt)).scalar() or 0
    free_users = max(0, total_users - commercial_users)
    
    # 2. Receita Mensal Recorrente (MRR) - Estimativa baseada em planos ativos
    # Seleciona soma dos preços mensais das assinaturas ATIVAS
    mrr_stmt = (
        select(func.sum(PlanoAssinatura.preco_mensal))
        .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
        .where(AssinaturaTenant.status == "ATIVA")
    )
    mrr_result = await session.execute(mrr_stmt)
    mrr_total = mrr_result.scalar() or 0.0

    # 3. Tendência de Faturamento (Mock para o gráfico por enquanto)
    # Em produção isso viria de um count/sum nas faturas agrupado por mês
    receita_trend = [
        {"mes": "Out", "valor": mrr_total * 0.7},
        {"mes": "Nov", "valor": mrr_total * 0.75},
        {"mes": "Dez", "valor": mrr_total * 0.82},
        {"mes": "Jan", "valor": mrr_total * 0.90},
        {"mes": "Fev", "valor": mrr_total * 0.95},
        {"mes": "Mar", "valor": mrr_total}
    ]

    # 4. Distribuição por Plano
    plano_dist_stmt = (
        select(PlanoAssinatura.nome, func.count(AssinaturaTenant.id))
        .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
        .group_by(PlanoAssinatura.nome)
    )
    plano_dist_result = await session.execute(plano_dist_stmt)
    distribuicao_planos = [{"name": r[0], "value": r[1]} for r in plano_dist_result]

    return {
        "resumo": {
            "mrr": float(mrr_total),
            "tenants_ativos": active_tenants,
            "tenants_total": total_tenants,
            "usuarios_total": total_users,
            "usuarios_gratuitos_total": free_users,
            "usuarios_comerciais_total": commercial_users,
        },
        "graficos": {
            "receita": receita_trend,
            "planos": distribuicao_planos
        },
        "plataforma": {
            "versao": "1.0.0-pro",
            "status": "online"
        }
    }

@router.get("/tenants", dependencies=[Depends(get_current_admin)])
async def list_tenants(session: AsyncSession = Depends(get_session)):
    """Lista todos os produtores e o status de suas assinaturas."""
    
    stmt = (
        select(Tenant, AssinaturaTenant, PlanoAssinatura)
        .outerjoin(AssinaturaTenant, Tenant.id == AssinaturaTenant.tenant_id)
        .outerjoin(PlanoAssinatura, AssinaturaTenant.plano_id == PlanoAssinatura.id)
        .order_by(Tenant.created_at.desc())
    )
    
    results = await session.execute(stmt)
    
    data = []
    for tenant, assinatura, plano in results:
        data.append({
            "id": tenant.id,
            "nome": tenant.nome,
            "documento": tenant.documento,
            "ativo": tenant.ativo,
            "modulos": plano.modulos_inclusos if plano else [],
            "data_cadastro": tenant.created_at,
            "assinatura": {
                "plano": plano.nome if plano else "Sem Plano",
                "plano_id": plano.id if plano else None,
                "status": assinatura.status if assinatura else "INATIVA",
                "ciclo": assinatura.ciclo_pagamento if assinatura else None
            }
        })
        
    return data

@router.post("/tenants/{tenant_id}/toggle-status", dependencies=[Depends(get_current_admin)])
async def toggle_tenant_status(tenant_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Bloqueia ou desbloqueia um Tenant (corte total de acesso)."""
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant indisponível ou não encontrado.")
    
    tenant.ativo = not tenant.ativo
    await session.commit()
    
    return {"id": tenant_id, "novo_status": tenant.ativo}

@router.get("/plans", response_model=List[PlanoAssinaturaResponse], dependencies=[Depends(get_current_admin)])
async def list_plans(session: AsyncSession = Depends(get_session)):
    """Lista todos os pacotes de assinatura filtrando módulos inativos."""
    from core.constants import ModuloMetadata, carregar_overrides_catalogo_modulos

    overrides = await carregar_overrides_catalogo_modulos(session)
    stmt = select(PlanoAssinatura).order_by(PlanoAssinatura.preco_mensal.asc())
    result = await session.execute(stmt)
    planos = list(result.scalars().all())
    for plano in planos:
        plano.modulos_inclusos = ModuloMetadata.filtrar_modulos_ativos(
            plano.modulos_inclusos or [], overrides
        )
    return planos

@router.post("/plans", response_model=PlanoAssinaturaResponse, dependencies=[Depends(get_current_admin)])
async def create_plan(plan_data: PlanoAssinaturaCreate, session: AsyncSession = Depends(get_session)):
    """Cria um novo plano/pacote comercial filtrando módulos inativos."""
    from core.constants import ModuloMetadata, carregar_overrides_catalogo_modulos

    overrides = await carregar_overrides_catalogo_modulos(session)
    # Se o novo plano for marcado como padrão, desmarcar todos os outros
    if plan_data.is_default:
        stmt = select(PlanoAssinatura).where(PlanoAssinatura.is_default == True)
        result = await session.execute(stmt)
        existing_default = result.scalar_one_or_none()
        if existing_default:
            existing_default.is_default = False
            logger.info(f"Plano {existing_default.id} deixou de ser o plano padrão")

    payload_dict = plan_data.model_dump()
    payload_dict["modulos_inclusos"] = ModuloMetadata.filtrar_modulos_ativos(
        payload_dict.get("modulos_inclusos") or [], overrides
    )
    new_plan = PlanoAssinatura(**payload_dict)
    session.add(new_plan)
    await session.commit()
    await session.refresh(new_plan)
    return new_plan

@router.patch("/plans/{plan_id}", response_model=PlanoAssinaturaResponse, dependencies=[Depends(get_current_admin)])
async def update_plan(plan_id: uuid.UUID, plan_data: PlanoAssinaturaUpdate, session: AsyncSession = Depends(get_session)):
    """Atualiza um plano/pacote comercial filtrando módulos inativos."""
    from core.constants import ModuloMetadata, carregar_overrides_catalogo_modulos

    plan = await session.get(PlanoAssinatura, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plano indisponível ou não encontrado.")

    overrides = await carregar_overrides_catalogo_modulos(session)

    # Se estão marcando este plano como padrão, desmarcar os outros
    if plan_data.is_default is True:
        stmt = select(PlanoAssinatura).where(
            PlanoAssinatura.is_default == True,
            PlanoAssinatura.id != plan_id
        )
        result = await session.execute(stmt)
        existing_default = result.scalar_one_or_none()
        if existing_default:
            existing_default.is_default = False
            logger.info(f"Plano {existing_default.id} deixou de ser o plano padrão")
    # Se estão desmarcando este plano como padrão e não há outro, impedir
    elif plan_data.is_default is False and plan.is_default:
        stmt = select(func.count(PlanoAssinatura.id)).where(
            PlanoAssinatura.is_default == True,
            PlanoAssinatura.id != plan_id
        )
        result = await session.execute(stmt)
        other_default_count = result.scalar_one() or 0
        if other_default_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Deve haver pelo menos um plano padrão. Marque outro plano como padrão antes de desmarcar este."
            )

    updates = plan_data.model_dump(exclude_unset=True)
    if "modulos_inclusos" in updates and updates["modulos_inclusos"] is not None:
        updates["modulos_inclusos"] = ModuloMetadata.filtrar_modulos_ativos(
            updates["modulos_inclusos"], overrides
        )
    for field, value in updates.items():
        setattr(plan, field, value)
    await session.commit()
    await session.refresh(plan)
    return plan

@router.post("/plans/{plan_id}/toggle-status", dependencies=[Depends(get_current_admin)])
async def toggle_plan_status(plan_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Ativa ou desativa um plano comercial."""
    plan = await session.get(PlanoAssinatura, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plano indisponível ou não encontrado.")
    
    plan.ativo = not plan.ativo
    await session.commit()
    return {"id": plan_id, "novo_status": plan.ativo}

@router.get("/modules", dependencies=[Depends(get_current_admin)])
async def list_modules(session: AsyncSession = Depends(get_session)):
    """Retorna o catálogo completo de módulos disponíveis com metadados e status ativo."""
    from core.constants import ModuloMetadata, carregar_overrides_catalogo_modulos

    overrides = await carregar_overrides_catalogo_modulos(session)
    resultado = []
    for modulo_id, meta in ModuloMetadata.CATALOGO.items():
        resultado.append({
            "id": modulo_id,
            "nome": meta.get("nome", modulo_id),
            "descricao": meta.get("descricao", ""),
            "categoria": meta.get("categoria", ""),
            "obrigatorio": meta.get("obrigatorio", False),
            "preco_base_mensal": meta.get("preco_base_mensal", 0.0),
            "dependencias": meta.get("dependencias", []),
            "ativo": ModuloMetadata.is_modulo_ativo(modulo_id, overrides),
            **overrides.get(modulo_id, {}),
        })
    return resultado


@router.put("/modules/{module_id}", dependencies=[Depends(get_current_admin)])
async def update_module(module_id: str, payload: dict[str, Any], session: AsyncSession = Depends(get_session)):
    """Atualiza os campos comerciais, descritivos e de ativação persistidos do módulo."""
    from core.constants import ModuloMetadata, Modulos
    from core.models.configuration import ConfiguracaoSaaS
    if module_id not in ModuloMetadata.CATALOGO:
        raise HTTPException(status_code=404, detail="Módulo não encontrado.")
    allowed = {"nome", "descricao", "categoria", "obrigatorio", "preco_base_mensal", "dependencias", "ativo"}
    if set(payload) - allowed or not payload:
        raise HTTPException(status_code=422, detail="Campos de edição inválidos.")
    if module_id == Modulos.CORE and payload.get("ativo") is False:
        raise HTTPException(status_code=422, detail="O módulo Núcleo (CORE) é obrigatório e não pode ser desativado.")
    if "preco_base_mensal" in payload and (not isinstance(payload["preco_base_mensal"], (int, float)) or payload["preco_base_mensal"] < 0):
        raise HTTPException(status_code=422, detail="O preço deve ser um número maior ou igual a zero.")
    dependencies = payload.get("dependencias")
    if dependencies is not None and (
        not isinstance(dependencies, list)
        or any(not isinstance(dependency, str) or dependency not in ModuloMetadata.CATALOGO or dependency == module_id for dependency in dependencies)
    ):
        raise HTTPException(status_code=422, detail="Selecione dependências válidas para o módulo.")
    config = await session.scalar(select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == "backoffice:module_catalog"))
    if config is None:
        config = ConfiguracaoSaaS(chave="backoffice:module_catalog", valor={}, descricao="Edições do catálogo de módulos")
        session.add(config)
    values = dict(config.valor or {})
    values[module_id] = {**values.get(module_id, {}), **payload}
    config.valor = values
    await session.commit()
    return {"id": module_id, **values[module_id]}


@router.post("/modules/{module_id}/toggle-status", dependencies=[Depends(get_current_admin)])
async def toggle_module_status(module_id: str, session: AsyncSession = Depends(get_session)):
    """Ativa ou desativa um módulo ou extensão (`EXT_IOT`, `EXT_ERP`, etc.) no catálogo da plataforma."""
    from core.constants import ModuloMetadata, Modulos, carregar_overrides_catalogo_modulos
    from core.models.configuration import ConfiguracaoSaaS

    if module_id not in ModuloMetadata.CATALOGO:
        raise HTTPException(status_code=404, detail="Módulo não encontrado.")
    if module_id == Modulos.CORE:
        raise HTTPException(status_code=422, detail="O módulo Núcleo (CORE) é obrigatório e não pode ser desativado.")

    overrides = await carregar_overrides_catalogo_modulos(session)
    ativo_atual = ModuloMetadata.is_modulo_ativo(module_id, overrides)
    novo_status = not ativo_atual

    config = await session.scalar(select(ConfiguracaoSaaS).where(ConfiguracaoSaaS.chave == "backoffice:module_catalog"))
    if config is None:
        config = ConfiguracaoSaaS(chave="backoffice:module_catalog", valor={}, descricao="Edições do catálogo de módulos")
        session.add(config)
    values = dict(config.valor or {})
    values[module_id] = {**values.get(module_id, {}), "ativo": novo_status}
    config.valor = values
    await session.commit()
    return {"id": module_id, "ativo": novo_status}


@router.post("/tenants/{tenant_id}/assign-plan/{plan_id}", dependencies=[Depends(get_current_admin)])
async def assign_plan_to_tenant(
    tenant_id: uuid.UUID, 
    plan_id: uuid.UUID, 
    session: AsyncSession = Depends(get_session)
):
    """Vincula um plano a um produtor e libera os módulos correspondentes."""
    tenant = await session.get(Tenant, tenant_id)
    plan = await session.get(PlanoAssinatura, plan_id)
    
    if not tenant or not plan:
        raise HTTPException(status_code=404, detail="Tenant ou plano indisponível ou não encontrado.")
    
    # Buscar assinatura atual
    stmt = select(AssinaturaTenant).where(AssinaturaTenant.tenant_id == tenant_id)
    result = await session.execute(stmt)
    assinatura = result.scalar_one_or_none()
    
    from datetime import datetime, timezone
    
    if not assinatura:
        assinatura = AssinaturaTenant(
            tenant_id=tenant_id,
            plano_id=plan_id,
            status="ATIVA",
            data_inicio=datetime.now(timezone.utc)
        )
        session.add(assinatura)
    else:
        assinatura.plano_id = plan_id
        assinatura.status = "ATIVA" # Garante Reativação se estivesse pendente
        
    await session.commit()

    return {
        "message": f"Plano {plan.nome} atribuído ao tenant {tenant.nome}",
        "modulos_liberados": plan.modulos_inclusos
    }

@router.get("/invoices", response_model=List[FaturaResponse], dependencies=[Depends(get_current_admin)])
async def list_invoices(session: AsyncSession = Depends(get_session)):
    """Lista todas as faturas para conferência financeira."""
    stmt = (
        select(Fatura, Tenant.nome.label("tenant_nome"), PlanoAssinatura.nome.label("plano_nome"))
        .join(Tenant, Fatura.tenant_id == Tenant.id)
        .join(AssinaturaTenant, Fatura.assinatura_id == AssinaturaTenant.id)
        .join(PlanoAssinatura, AssinaturaTenant.plano_id == PlanoAssinatura.id)
        .order_by(Fatura.created_at.desc())
    )
    result = await session.execute(stmt)
    
    invoices = []
    for row in result:
        fatura = row[0]
        invoices.append({
            "id": fatura.id,
            "tenant_id": fatura.tenant_id,
            "tenant_nome": row.tenant_nome,
            "plano_nome": row.plano_nome,
            "valor": float(fatura.valor),
            "data_vencimento": fatura.data_vencimento,
            "status": fatura.status,
            "url_comprovante": fatura.url_comprovante,
            "data_envio_comprovante": fatura.data_envio_comprovante,
            "justificativa_rejeicao": fatura.justificativa_rejeicao,
            "created_at": fatura.created_at
        })
    return invoices

@router.post("/invoices/{invoice_id}/review", dependencies=[Depends(get_current_admin)])
async def review_invoice(
    invoice_id: uuid.UUID,
    review: ReviewInvoiceRequest,
    admin_claims: dict = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Aprova ou Rejeita um pagamento enviado pelo produtor."""
    # Buscar fatura com dados do tenant e plano
    stmt = (
        select(Fatura, Tenant, PlanoAssinatura, Usuario.email, Usuario.nome_completo)
        .join(Tenant, Fatura.tenant_id == Tenant.id)
        .join(AssinaturaTenant, Fatura.assinatura_id == AssinaturaTenant.id)
        .join(PlanoAssinatura, AssinaturaTenant.plano_id == PlanoAssinatura.id)
        .join(TenantUsuario, Tenant.id == TenantUsuario.tenant_id)
        .join(Usuario, TenantUsuario.usuario_id == Usuario.id)
        .where(Fatura.id == invoice_id, TenantUsuario.is_owner == True)
    )
    result = await session.execute(stmt)
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Fatura ou proprietário indisponível ou não encontrado.")
    
    fatura, tenant, plano, owner_email, owner_nome = row

    admin_id, _ = _extrair_admin_identity(admin_claims)

    from datetime import datetime, timezone

    if review.aprovado:
        fatura.status = "PAGA"
        # Se houver mudança de plano/acessos pendente vinculada à assinatura desta fatura, aplicar imediatamente
        from core.models.plan_changes import MudancaPlano
        from core.services.mudanca_plano_service import MudancaPlanoService
        mudanca_stmt = (
            select(MudancaPlano)
            .where(
                MudancaPlano.assinatura_id == fatura.assinatura_id,
                MudancaPlano.status == "pendente_pagamento",
            )
            .order_by(MudancaPlano.created_at.desc())
            .limit(1)
        )
        mudanca_pendente = (await session.execute(mudanca_stmt)).scalar_one_or_none()
        if mudanca_pendente:
            mudanca_svc = MudancaPlanoService(session, fatura.tenant_id)
            await mudanca_svc._aplicar_mudanca(mudanca_pendente)
    else:
        fatura.status = "REJEITADA"
        fatura.justificativa_rejeicao = review.justificativa

    fatura.operador_revisao_id = admin_id
    fatura.data_aprovacao_rejeicao = datetime.now(timezone.utc)
    
    await session.commit()

    # Enviar Notificação por E-mail (Background / Fire and Forget for UX)
    # Em produção usaríamos Celery, aqui faremos async simples
    try:
        if review.aprovado:
            await email_service.send_invoice_approved(
                email=owner_email,
                nome=owner_nome or tenant.nome,
                plano=plano.nome,
                valor=float(fatura.valor)
            )
        else:
            await email_service.send_invoice_rejected(
                email=owner_email,
                nome=owner_nome or tenant.nome,
                justificativa=review.justificativa
            )
    except Exception as e:
        logger.error(f"Erro ao disparar e-mail de notificação: {e}")

    return {"id": invoice_id, "novo_status": fatura.status}

@router.get("/users", dependencies=[Depends(get_current_admin)])
async def list_global_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str | None = Query(None, description="Busca por nome, email ou username"),
    account_type: str | None = Query("all", description="Filtro por tipo de conta: all, free, commercial"),
    session: AsyncSession = Depends(get_session),
):
    """Lista todos os usuários da plataforma com seus vínculos, filtros e produtos contratados."""
    stmt = select(Usuario)
    if search:
        search_filter = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Usuario.nome_completo).like(search_filter),
                func.lower(Usuario.email).like(search_filter),
                func.lower(Usuario.username).like(search_filter),
            )
        )

    if account_type and account_type.lower() == "free":
        subq_tenants = select(TenantUsuario.usuario_id).distinct()
        stmt = stmt.where(Usuario.id.not_in(subq_tenants), Usuario.is_superuser == False)
    elif account_type and account_type.lower() == "commercial":
        subq_tenants = select(TenantUsuario.usuario_id).distinct()
        stmt = stmt.where(Usuario.id.in_(subq_tenants))

    stmt = stmt.order_by(Usuario.created_at.desc()).offset(skip).limit(limit)
    usuarios = (await session.execute(stmt)).scalars().all()

    if not usuarios:
        return []

    user_ids = [u.id for u in usuarios]
    stmt_tenants = (
        select(TenantUsuario.usuario_id, TenantUsuario.is_owner, Tenant.nome)
        .join(Tenant, TenantUsuario.tenant_id == Tenant.id)
        .where(TenantUsuario.usuario_id.in_(user_ids))
    )
    tenants_res = (await session.execute(stmt_tenants)).all()

    tenant_map: dict[uuid.UUID, list[str]] = {u.id: [] for u in usuarios}
    owner_map: dict[uuid.UUID, bool] = {u.id: False for u in usuarios}
    for uid, is_owner, t_nome in tenants_res:
        if t_nome:
            tenant_map[uid].append(t_nome)
        if is_owner:
            owner_map[uid] = True

    users = []
    for u in usuarios:
        u_tenants = tenant_map.get(u.id, [])
        is_owner = owner_map.get(u.id, False)

        if u.is_superuser:
            acc_type = "PLATFORM_ADMIN"
            produtos = ["Backoffice Global", "SaaS Comercial", "DeepFarms Agro"]
        elif u_tenants:
            acc_type = "COMMERCIAL"
            produtos = ["SaaS Comercial", "DeepFarms Agro"]
        else:
            acc_type = "INDIVIDUAL_FREE"
            produtos = ["DeepFarms Agro Gratuito"]

        users.append({
            "id": u.id,
            "nome": u.nome_completo,
            "email": u.email,
            "username": u.username,
            "is_superuser": u.is_superuser,
            "is_owner": is_owner,
            "ativo": u.ativo,
            "account_type": acc_type,
            "produtos": produtos,
            "data_cadastro": u.created_at,
            "tenants": u_tenants,
        })
    return users

@router.post("/users/{user_id}/toggle-status")
async def toggle_user_status(
    user_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict = Depends(get_current_admin),
):
    """Bloqueia ou desbloqueia um usuário globalmente, invalidando sessões ativas se bloqueado."""
    user = await session.get(Usuario, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário indisponível ou não encontrado.")

    if user.is_superuser:
        raise HTTPException(status_code=400, detail="Não é possível desativar um superusuário por aqui.")

    # Verifica se o usuário é owner de algum tenant
    stmt_owner = select(TenantUsuario).where(
        TenantUsuario.usuario_id == user_id,
        TenantUsuario.is_owner == True
    )
    result = await session.execute(stmt_owner)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Não é possível desativar o proprietário (owner) de um tenant."
        )

    anterior = user.ativo
    user.ativo = not user.ativo
    sessoes_revogadas = 0
    if not user.ativo:
        stmt_revoke = (
            update(SessaoAtiva)
            .where(
                SessaoAtiva.usuario_id == user_id,
                SessaoAtiva.status == "ATIVA",
            )
            .values(status="ENCERRADA")
        )
        res_revoke = await session.execute(stmt_revoke)
        sessoes_revogadas = res_revoke.rowcount or 0

    # Auditoria administrativa
    admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)

    audit_entry = AdminAuditLog(
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="USUARIO_BLOQUEADO" if not user.ativo else "USUARIO_DESBLOQUEADO",
        entidade="usuario",
        entidade_id=user.id,
        descricao=f"Usuário {user.email} {'bloqueado' if not user.ativo else 'desbloqueado'} via painel administrativo.",
        dados_anteriores={"ativo": anterior},
        dados_novos={"ativo": user.ativo, "sessoes_revogadas": sessoes_revogadas},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(audit_entry)
    await session.commit()
    return {"id": user_id, "novo_status": user.ativo}

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: uuid.UUID,
    request: Request,
    enviar_email: bool = True,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict = Depends(get_current_admin),
):
    """
    Reseta a senha de um usuário global e retorna a senha temporária.
    Opcionalmente envia a senha por e-mail.
    """
    import secrets
    import string
    from core.services.auth_service import hash_password

    user = await session.get(Usuario, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuário indisponível ou não encontrado.")

    if user.is_superuser:
        raise HTTPException(status_code=400, detail="Não é possível resetar senha de superusuário por aqui.")

    # Gerar senha aleatória segura (12 caracteres com símbolos)
    caracteres = string.ascii_letters + string.digits + "!@#$%&*"
    senha_temporaria = ''.join(secrets.choice(caracteres) for _ in range(12))

    user.senha_hash = hash_password(senha_temporaria)

    # Auditoria administrativa
    admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)

    audit_entry = AdminAuditLog(
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="USUARIO_RESET_SENHA",
        entidade="usuario",
        entidade_id=user.id,
        descricao=f"Senha do usuário {user.email} resetada pelo operador administrativo.",
        dados_novos={"enviar_email": enviar_email},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(audit_entry)
    await session.commit()

    # Enviar e-mail com a senha temporária
    if enviar_email and user.email:
        try:
            await email_service.send_email(
                to=user.email,
                subject="Redefinição de Senha - DeepFarms",
                html_content=f"""
                <h2>Olá {user.nome_completo or user.username},</h2>
                <p>Sua senha foi redefinida pelo administrador do sistema DeepFarms.</p>
                <p><strong>Senha temporária:</strong> <code>{senha_temporaria}</code></p>
                <p>Por segurança, recomendamos criar uma nova senha no próximo acesso.</p>
                """
            )
        except Exception as e:
            import logging
            logging.error(f"Erro ao enviar e-mail de reset: {e}")

    return {
        "success": True,
        "senha_temporaria": senha_temporaria if not enviar_email else "Enviada por e-mail",
        "email_enviado": enviar_email,
        "usuario_email": user.email
    }

@router.get("/tickets", response_model=List[dict], dependencies=[Depends(require_permission("backoffice:support:view"))])
async def list_all_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """Lista todos os chamados da plataforma para o administrador ou comercial."""
    stmt = (
        select(
            ChamadoSuporte,
            Tenant,
            Usuario.nome_completo.label("usuario_nome"),
            Usuario.email.label("usuario_email"),
            TenantUsuario.data_validade_acesso,
            TenantUsuario.demo_prorrogacoes_count,
        )
        .join(Tenant, ChamadoSuporte.tenant_id == Tenant.id)
        .join(Usuario, ChamadoSuporte.usuario_abertura_id == Usuario.id)
        .outerjoin(
            TenantUsuario,
            (TenantUsuario.tenant_id == ChamadoSuporte.tenant_id)
            & (TenantUsuario.usuario_id == ChamadoSuporte.usuario_abertura_id),
        )
        .order_by(ChamadoSuporte.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await session.execute(stmt)
    
    tickets = []
    for row in result:
        c = row.ChamadoSuporte
        t = row.Tenant
        tickets.append({
            "id": c.id,
            "tenant_id": str(c.tenant_id),
            "tenant_nome": t.nome,
            "usuario_nome": row.usuario_nome,
            "usuario_email": row.usuario_email,
            "assunto": c.assunto,
            "categoria": c.categoria,
            "status": c.status,
            "prioridade": c.prioridade,
            "is_demo_tenant": is_demo_tenant(t),
            "data_validade_acesso": row.data_validade_acesso.isoformat() if row.data_validade_acesso else None,
            "demo_prorrogacoes_count": int(row.demo_prorrogacoes_count or 0),
            "created_at": c.created_at
        })
    return tickets

@router.get("/tickets/{ticket_id}", response_model=ChamadoDetalheResponse, dependencies=[Depends(require_permission("backoffice:support:view"))])
async def get_admin_ticket_details(ticket_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Retorna detalhes de um chamado para o administrador ou comercial."""
    stmt = (
        select(ChamadoSuporte)
        .options(selectinload(ChamadoSuporte.mensagens))
        .where(ChamadoSuporte.id == ticket_id)
    )
    result = await session.execute(stmt)
    chamado = result.scalar_one_or_none()
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado indisponível ou não encontrado.")

    tenant = await session.get(Tenant, chamado.tenant_id)
    usuario = await session.get(Usuario, chamado.usuario_abertura_id)
    tu = (
        await session.execute(
            select(TenantUsuario).where(
                TenantUsuario.tenant_id == chamado.tenant_id,
                TenantUsuario.usuario_id == chamado.usuario_abertura_id,
            )
        )
    ).scalar_one_or_none()

    return ChamadoDetalheResponse(
        id=chamado.id,
        tenant_id=chamado.tenant_id,
        usuario_abertura_id=chamado.usuario_abertura_id,
        assunto=chamado.assunto,
        categoria=chamado.categoria,
        prioridade=chamado.prioridade,
        status=chamado.status,
        created_at=chamado.created_at,
        updated_at=chamado.updated_at,
        mensagens=[MensagemChamadoResponse.model_validate(m) for m in chamado.mensagens],
        tenant_nome=tenant.nome if tenant else None,
        usuario_nome=(usuario.nome_completo or usuario.username) if usuario else None,
        usuario_email=usuario.email if usuario else None,
        is_demo_tenant=is_demo_tenant(tenant),
        data_validade_acesso=(
            tu.data_validade_acesso.isoformat()
            if (tu and tu.data_validade_acesso)
            else None
        ),
        demo_prorrogacoes_count=int(getattr(tu, "demo_prorrogacoes_count", 0) or 0) if tu else 0,
    )

@router.post("/tickets/{ticket_id}/reply", response_model=MensagemChamadoResponse, dependencies=[Depends(require_permission("backoffice:support:update"))])
async def admin_reply_to_ticket(
    ticket_id: uuid.UUID,
    data: MensagemChamadoCreate,
    admin_claims: dict = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """Administrador responde a um chamado."""
    chamado = await session.get(ChamadoSuporte, ticket_id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado indisponível ou não encontrado.")

    admin_id, _ = _extrair_admin_identity(admin_claims)
    
    msg = MensagemChamado(
        chamado_id=ticket_id,
        usuario_id=admin_id,
        conteudo=data.conteudo,
        anexo_url=data.anexo_url,
        is_admin_reply=True
    )
    
    # Atualiza status quando admin responde
    chamado.status = TicketStatus.AGUARDANDO_CLIENTE
    
    session.add(msg)
    await session.commit()
    return msg

@router.post("/tickets/{ticket_id}/close", dependencies=[Depends(require_permission("backoffice:support:update"))])
async def close_ticket(ticket_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Finaliza um chamado de suporte."""
    chamado = await session.get(ChamadoSuporte, ticket_id)
    if not chamado:
        raise HTTPException(status_code=404, detail="Chamado indisponível ou não encontrado.")
    
    chamado.status = TicketStatus.CONCLUIDO
    await session.commit()
    return {"id": ticket_id, "status": "CONCLUIDO"}


@router.post(
    "/tickets/{ticket_id}/aprovar-prorrogacao-demo",
    dependencies=[Depends(require_permission("backoffice:support:update"))],
)
async def approve_ticket_demo_extension(
    ticket_id: uuid.UUID,
    request: Request,
    body: AprovarProrrogacaoDemoRequest | None = None,
    admin_claims: dict = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """Aprova prorrogação de acesso de demonstração (+15 dias por padrão) com auditoria obrigatória."""
    role = str(admin_claims.get("role") or "").lower()
    if not admin_claims.get("is_superuser") and role not in {"super_admin", "admin", "comercial"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Aprovação de prorrogação restrita ao time Comercial ou Administradores.",
        )

    admin_id, admin_email = await resolve_admin_identity(session, admin_claims)
    payload = DemoExtensionApprovalInput(
        ticket_id=ticket_id,
        admin_id=admin_id,
        admin_email=admin_email,
        dias=(body.dias if body and body.dias is not None else None),
        observacao=(body.observacao if body else None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return await approve_demo_extension(session, payload)


@router.post("/tenants/{tenant_id}/reset-password", dependencies=[Depends(get_current_admin)])
async def reset_tenant_password(
    tenant_id: uuid.UUID,
    enviar_email: bool = True,
    session: AsyncSession = Depends(get_session)
):
    """
    Reseta a senha do responsável pelo tenant e opcionalmente envia email.
    """
    import secrets
    import string
    from core.services.auth_service import hash_password

    # Buscar tenant
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant indisponível ou não encontrado.")

    # Gerar senha aleatória
    caracteres = string.ascii_letters + string.digits + "!@#$%&*"
    senha_temporaria = ''.join(secrets.choice(caracteres) for _ in range(12))

    # Buscar usuário principal do tenant (admin/owner)
    stmt = (
        select(Usuario)
        .join(TenantUsuario)
        .where(
            TenantUsuario.tenant_id == tenant_id,
            TenantUsuario.is_owner == True
        )
    )
    result = await session.execute(stmt)
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário responsável indisponível ou não encontrado.")

    # Atualizar senha
    usuario.senha_hash = hash_password(senha_temporaria)
    # usuario.force_password_change = True  # Ativar se o campo existir no modelo Usuario

    await session.commit()

    # Enviar email se solicitado
    if enviar_email:
        # Tenta enviar usando o email_service existente
        try:
            await email_service.send_email(
                to=usuario.email,
                subject="Redefinição de Senha - DeepFarms",
                html_content=f"""
                <h2>Olá {usuario.nome_completo or tenant.nome},</h2>
                <p>Sua senha foi redefinida pelo administrador do sistema.</p>
                <p><strong>Senha temporária:</strong> {senha_temporaria}</p>
                <p>Por segurança, recomendamos criar uma nova senha no próximo acesso.</p>
                <p><a href="https://app.agrosass.com">Acessar sistema</a></p>
                """
            )
        except Exception as e:
             # Log error but return success since password was reset
             import logging
             logging.error(f"Erro ao enviar email de reset: {e}")

    return {
        "success": True,
        "senha_temporaria": senha_temporaria if not enviar_email else "Enviada por e-mail",
        "email_enviado": enviar_email,
        "usuario_email": usuario.email
    }


@router.patch("/tenants/{tenant_id}/change-plan", dependencies=[Depends(get_current_admin)])
async def change_tenant_plan(
    tenant_id: uuid.UUID,
    novo_plano_id: uuid.UUID,
    admin_user: Any = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session)
):
    """
    Altera o plano de assinatura de um tenant.
    """
    # Buscar tenant
    tenant = await session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant indisponível ou não encontrado.")

    # Buscar novo plano
    novo_plano = await session.get(PlanoAssinatura, novo_plano_id)
    if not novo_plano or not novo_plano.ativo:
        raise HTTPException(
            status_code=404,
            detail="Plano indisponível ou inativo. Verifique se o cadastro do plano está ativo.",
        )

    # Buscar assinatura atual
    stmt = select(AssinaturaTenant).where(AssinaturaTenant.tenant_id == tenant_id)
    result = await session.execute(stmt)
    assinatura = result.scalar_one_or_none()

    if not assinatura:
        raise HTTPException(
            status_code=404,
            detail="Assinatura não localizada. Verifique se o tenant possui uma assinatura ativa.",
        )

    # Guardar dados antigos para audit log
    plano_anterior_id = assinatura.plano_id

    # Atualizar assinatura
    assinatura.plano_id = novo_plano_id

    # Registrar no audit log
    from core.models.admin_audit_log import AdminAuditLog
    admin_uid, admin_email = await resolve_admin_identity(session, admin_user)
    audit = AdminAuditLog(
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="tenant.change_plan",
        entidade="tenant",
        entidade_id=tenant_id,
        descricao=f"Alteração de plano de {plano_anterior_id} para {novo_plano_id}",
        dados_anteriores={"plano_id": str(plano_anterior_id)},
        dados_novos={"plano_id": str(novo_plano_id)}
    )
    session.add(audit)

    await session.commit()

    return {
        "success": True,
        "tenant_id": tenant_id,
        "plano_anterior_id": plano_anterior_id,
        "plano_novo_id": novo_plano_id,
        "plano_novo_nome": novo_plano.nome,
        "novos_modulos": novo_plano.modulos_inclusos
    }


@router.get("/tenants/{tenant_id}/details", dependencies=[Depends(get_current_admin)])
async def get_tenant_details(tenant_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """
    Retorna detalhes completos de um tenant incluindo:
    - Todas as assinaturas (múltiplas)
    - Usuários associados
    - Grupos de fazendas com suas fazendas
    - Usuários por fazenda com perfis
    """
    from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
    # grupos_fazendas removed
    from core.models.auth import FazendaUsuario, PerfilAcesso
    from datetime import datetime, timedelta, timezone
    from loguru import logger

    try:
        # Buscar tenant
        tenant = await session.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant indisponível ou não encontrado.")

        # Buscar TODAS as assinaturas do tenant
        stmt_assinaturas = (
            select(AssinaturaTenant, PlanoAssinatura)
            .join(PlanoAssinatura, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(AssinaturaTenant.tenant_id == tenant_id)
            .order_by(AssinaturaTenant.tipo_assinatura, AssinaturaTenant.created_at.desc())
        )
        result_assinaturas = await session.execute(stmt_assinaturas)

        assinaturas = []
        for assinatura, plano in result_assinaturas:
            # Calcular próxima renovação
            proxima_renovacao = None
            if assinatura.data_proxima_renovacao:
                proxima_renovacao = assinatura.data_proxima_renovacao
            elif assinatura.data_inicio and assinatura.status == "ATIVA":
                if assinatura.ciclo_pagamento == "MENSAL":
                    proxima_renovacao = assinatura.data_inicio + timedelta(days=30)
                elif assinatura.ciclo_pagamento == "ANUAL":
                    proxima_renovacao = assinatura.data_inicio + timedelta(days=365)

            assinaturas.append({
                "id": assinatura.id,
                "tipo": assinatura.tipo_assinatura,
                "plano": {
                    "id": plano.id,
                    "nome": plano.nome,
                    "preco_mensal": float(plano.preco_mensal),
                    "preco_anual": float(plano.preco_anual),
                    "modulos": plano.modulos_inclusos,
                    "limite_usuarios_maximo": plano.limite_usuarios_maximo
                },
                "status": assinatura.status,
                "ciclo_pagamento": assinatura.ciclo_pagamento,
                "data_inicio": assinatura.data_inicio,
                "data_proxima_renovacao": proxima_renovacao,
                "created_at": assinatura.created_at
            })

        # Buscar todos os usuários do tenant
        stmt_usuarios = (
            select(Usuario, TenantUsuario, PerfilAcesso)
            .join(TenantUsuario, Usuario.id == TenantUsuario.usuario_id)
            .join(PerfilAcesso, TenantUsuario.perfil_id == PerfilAcesso.id)
            .where(TenantUsuario.tenant_id == tenant_id, TenantUsuario.status == "ATIVO")
            .order_by(TenantUsuario.is_owner.desc(), Usuario.nome_completo)
        )
        result_usuarios = await session.execute(stmt_usuarios)

        usuarios = []
        for usuario, tenant_usuario, perfil in result_usuarios:
            usuarios.append({
                "id": usuario.id,
                "nome_completo": usuario.nome_completo,
                "email": usuario.email,
                "username": usuario.username,
                "is_owner": tenant_usuario.is_owner,
                "perfil": {
                    "id": perfil.id,
                    "nome": perfil.nome
                },
                "ativo": usuario.ativo,
                "created_at": usuario.created_at
            })

        # Estrutura de grupos removida no modelo atual. Mantemos resposta estável
        # para o frontend e concentramos as fazendas em "sem grupo".
        grupos_tree: list[dict] = []

        # O modelo atual não expõe a hierarquia antiga de grupos nesta rota.
        # Para manter o contrato do frontend, consideramos todas as fazendas do tenant
        # como parte de "fazendas_sem_grupo".
        stmt_fazendas_sem_grupo = (
            select(Fazenda)
            .where(Fazenda.tenant_id == tenant_id)
            .order_by(Fazenda.nome)
        )
        result_fazendas_sem_grupo = await session.execute(stmt_fazendas_sem_grupo)
        fazendas_sem_grupo = result_fazendas_sem_grupo.scalars().all()

        fazendas_sem_grupo_data = []
        for fazenda in fazendas_sem_grupo:
            # Buscar usuários da fazenda
            stmt_usuarios_fazenda = (
                select(Usuario, FazendaUsuario, PerfilAcesso)
                .join(FazendaUsuario, Usuario.id == FazendaUsuario.usuario_id)
                .outerjoin(PerfilAcesso, FazendaUsuario.perfil_fazenda_id == PerfilAcesso.id)
                .where(FazendaUsuario.unidade_produtiva_id == fazenda.id)
                .order_by(Usuario.nome_completo)
            )
            result_usuarios_fazenda = await session.execute(stmt_usuarios_fazenda)

            usuarios_fazenda = []
            for usuario_f, fazenda_usuario, perfil_f in result_usuarios_fazenda:
                usuarios_fazenda.append({
                    "id": usuario_f.id,
                    "nome_completo": usuario_f.nome_completo,
                    "email": usuario_f.email,
                    "perfil_fazenda": {
                        "id": perfil_f.id,
                        "nome": perfil_f.nome
                    } if perfil_f else None
                })

            fazendas_sem_grupo_data.append({
                "id": fazenda.id,
                "nome": fazenda.nome,
                "cpf_cnpj": fazenda.cpf_cnpj,
                "coordenadas_sede": fazenda.coordenadas_sede,
                "area_total_ha": float(fazenda.area_total_ha) if fazenda.area_total_ha else None,
                "usuarios": usuarios_fazenda
            })

        return {
            "tenant": {
                "id": tenant.id,
                "nome": tenant.nome,
                "documento": tenant.documento,
                "ativo": tenant.ativo,
                "modulos_ativos": list({m for a in assinaturas for m in (a.get("plano") or {}).get("modulos", [])}),
                "created_at": tenant.created_at
            },
            "assinaturas": assinaturas,
            "usuarios": usuarios,
            "estrutura": {
                "grupos": grupos_tree,
                "fazendas_sem_grupo": fazendas_sem_grupo_data
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar detalhes do tenant {tenant_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.get("/tenants/storage/alertas", dependencies=[Depends(get_current_admin)])
async def get_storage_alerts(
    limite_percentual: float = 80.0,
    session: AsyncSession = Depends(get_session)
):
    """
    Retorna tenants com storage próximo ao limite.
    """
    stmt = (
        select(Tenant)
        .where(
            Tenant.ativo == True,
            Tenant.storage_usado_mb > (Tenant.storage_limite_mb * (limite_percentual / 100))
        )
    )
    result = await session.execute(stmt)
    tenants = result.scalars().all()

    alertas = []
    for tenant in tenants:
        percentual = (tenant.storage_usado_mb / tenant.storage_limite_mb) * 100 if tenant.storage_limite_mb > 0 else 0
        alertas.append({
            "tenant_id": tenant.id,
            "tenant_nome": tenant.nome,
            "storage_usado_mb": tenant.storage_usado_mb,
            "storage_limite_mb": tenant.storage_limite_mb,
            "percentual_uso": round(percentual, 2),
            "alerta": "critico" if percentual >= 95 else "alto" if percentual >= 90 else "medio"
        })

    # Ordenar por percentual de uso decrescente
    alertas.sort(key=lambda x: x["percentual_uso"], reverse=True)

    return {
        "total_alertas": len(alertas),
        "tenants": alertas
    }


# ==================== LOGIN RATE LIMITING - DESBLOQUEIO ====================

from core.schemas.auth_schemas import (
    LoginDesbloqueioRequest, LoginDesbloqueioResponse,
    LoginTentativasInfoResponse, LoginBloqueadosListaResponse
)
from core.services.login_rate_limit_service import LoginRateLimitService

@router.post("/login/desbloquear", dependencies=[Depends(get_current_admin)])
async def backoffice_desbloquear_login(
    dados: LoginDesbloqueioRequest,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(get_current_admin)
):
    """
    Backoffice: Desbloqueia login de usuário por email.
    
    Admin do SaaS pode desbloquear qualquer usuário da plataforma.
    Útil quando usuário entra em contato relatando bloqueio acidental.
    """
    rate_limit_svc = LoginRateLimitService(session)
    
    # Verifica se há tentativas registradas
    info = await rate_limit_svc.get_tentativas_por_email(dados.email)
    
    if not info:
        return LoginDesbloqueioResponse(
            sucesso=False,
            mensagem=f"Nenhum registro de tentativas para {dados.email}",
            email=dados.email
        )
    
    if not info["bloqueado"]:
        return LoginDesbloqueioResponse(
            sucesso=False,
            mensagem=f"Usuário {dados.email} não está bloqueado no momento",
            email=dados.email
        )
    
    # Desbloqueia
    await rate_limit_svc.desbloquear_manual(dados.email)
    
    # Log de auditoria (opcional - pode ser expandido)
    logger.info(f"Backoffice desbloqueou login para {dados.email} por {admin.get('sub')}")
    
    return LoginDesbloqueioResponse(
        sucesso=True,
        mensagem=f"Usuário {dados.email} desbloqueado com sucesso. Pode tentar login imediatamente.",
        email=dados.email
    )


@router.get("/login/tentativas/{email}", dependencies=[Depends(get_current_admin)])
async def backoffice_ver_tentativas_login(
    email: str,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(get_current_admin)
):
    """
    Backoffice: Visualiza tentativas de login de um usuário.
    
    Retorna informações sobre bloqueio, contador de tentativas e histórico.
    """
    rate_limit_svc = LoginRateLimitService(session)
    info = await rate_limit_svc.get_tentativas_por_email(email)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nenhum registro de tentativas para {email}"
        )
    
    return LoginTentativasInfoResponse(**info)


@router.get("/login/bloqueados", dependencies=[Depends(get_current_admin)])
async def backoffice_listar_bloqueados(
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(get_current_admin)
):
    """
    Backoffice: Lista usuários bloqueados nas últimas 24 horas.
    
    Permite monitorar bloqueios em massa (possível ataque) ou identificar
    usuários que precisam de suporte.
    """
    rate_limit_svc = LoginRateLimitService(session)
    bloqueados = await rate_limit_svc.listar_bloqueados_recentes(limit)
    
    return LoginBloqueadosListaResponse(
        total=len(bloqueados),
        bloqueados=[LoginBloqueadoItem(**b) for b in bloqueados]
    )



# ── Telemetria de Módulos ─────────────────────────────────────────────────────

@router.get(
    "/tenants/{tenant_id}/module-usage",
    summary="Uso de módulos por tenant nos últimos N dias",
    dependencies=[Depends(get_current_admin)],
)
async def backoffice_module_usage(
    tenant_id: uuid.UUID,
    days: int = 30,
    session: AsyncSession = Depends(get_session),
):
    from core.services.module_usage_service import get_usage_by_module
    return await get_usage_by_module(session, tenant_id, days)


@router.get(
    "/tenants/{tenant_id}/module-usage/{module_id}",
    summary="Série temporal diária de uso de um módulo específico",
    dependencies=[Depends(get_current_admin)],
)
async def backoffice_module_usage_daily(
    tenant_id: uuid.UUID,
    module_id: str,
    days: int = 30,
    session: AsyncSession = Depends(get_session),
):
    from core.services.module_usage_service import get_daily_usage
    return await get_daily_usage(session, tenant_id, module_id, days)
