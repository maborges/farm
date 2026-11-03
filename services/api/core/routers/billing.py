from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
import uuid

from core.dependencies import get_session, get_current_user, get_current_tenant, get_current_user_claims, get_tenant_id
from core.models.tenant import Tenant
from core.models.billing import AssinaturaTenant, PlanoAssinatura, Fatura
from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
from core.models.auth import TenantUsuario
from core.schemas.billing_schemas import FaturaResponse, LandingPlanoResponse, PlanoAssinaturaResponse
from core.services.storage_service import StorageService, increment_storage
from core.services.tenant_branding import upload_tenant_logo

router = APIRouter(prefix="/billing", tags=["Billing / Conta"])

@router.post("/my-account/logo")
async def upload_my_account_logo(
    arquivo: UploadFile = File(..., description="Logo JPEG, PNG ou WebP. Máx 2MB."),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Args: imagem, conta autenticada e sessão. Return: URL. Raises: erro de upload."""
    return {"logo_url_grupo": await upload_tenant_logo(tenant, session, arquivo)}

@router.get("/my-account")
async def get_my_account(tenant: Tenant = Depends(get_current_tenant), session: AsyncSession = Depends(get_session)):
    """Retorna detalhes da conta/tenant logado."""
    # Buscar assinatura ativa/trial e plano (prefere GRUPO, fallback qualquer)
    stmt = (
        select(AssinaturaTenant, PlanoAssinatura)
        .join(PlanoAssinatura, AssinaturaTenant.plano_id == PlanoAssinatura.id)
        .where(
            AssinaturaTenant.tenant_id == tenant.id,
            AssinaturaTenant.status.in_(["ATIVA", "TRIAL", "PENDENTE_PAGAMENTO"]),
        )
        .order_by(AssinaturaTenant.data_inicio.desc())
    )
    result = await session.execute(stmt)
    row = result.first()

    assinatura_data = None
    modulos_ativos = ["CORE"]
    max_usuarios = 2
    max_categorias_plano = 0
    if row:
        assinatura, plano = row
        max_categorias_plano = plano.max_categorias_plano
        max_usuarios = assinatura.usuarios_contratados or plano.limite_usuarios_minimo or 2
        ciclo = getattr(assinatura, "ciclo_pagamento", "MENSAL") or "MENSAL"
        valor_base = float(plano.preco_anual if ciclo == "ANUAL" else plano.preco_mensal)
        valor_composto = valor_base
        detalhamento_preco = []
        try:
            from core.services.plan_pricing_service import PlanoPricingService
            pricing_svc = PlanoPricingService(session)
            total_dec, detalhamento_preco = await pricing_svc.calcular_preco_total(
                plano_id=plano.id,
                quantidade_usuarios=max_usuarios,
                ciclo=ciclo,
            )
            valor_composto = float(total_dec)
        except Exception:
            valor_composto = valor_base

        assinatura_data = {
            "plano": plano.nome,
            "plano_id": str(plano.id),
            "valor": valor_composto,
            "valor_base": float(plano.preco_mensal),
            "ciclo_pagamento": ciclo,
            "status": assinatura.status,
            "data_inicio": assinatura.data_inicio,
            "proximo_vencimento": assinatura.data_proxima_renovacao,
            "max_categorias_plano": max_categorias_plano,
            "limite_hectares": float(plano.limite_hectares) if plano.limite_hectares is not None else None,
            "usuarios_inclusos": plano.limite_usuarios_minimo or 1,
            "usuarios_contratados": max_usuarios,
            "detalhamento_preco": detalhamento_preco,
        }
        modulos_ativos = plano.modulos_inclusos or ["CORE"]

    return {
        "tenant": {
            "id": tenant.id,
            "nome": tenant.nome,
            "documento": tenant.documento,
            "ativo": tenant.ativo,
            "modulos_ativos": modulos_ativos,
            "max_usuarios": max_usuarios,
            "max_categorias_plano": max_categorias_plano,
            "created_at": tenant.created_at,
            "email_responsavel": tenant.email_responsavel,
            "telefone_responsavel": tenant.telefone_responsavel,
            "idioma_padrao": tenant.idioma_padrao,
            "logo_url_grupo": (tenant.branding or {}).get("logoUrl"),
        },
        "assinatura": assinatura_data
    }

@router.patch("/my-account")
async def update_my_account(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    dados: dict = Body(...),
):
    """Atualiza dados do produtor (nome, documento, email_responsavel, telefone_responsavel, idioma_padrao)."""
    campos_permitidos = {"nome", "documento", "email_responsavel", "telefone_responsavel", "idioma_padrao"}
    campos_obrigatorios = {"nome", "documento"}
    
    for campo, valor in dados.items():
        if campo in campos_permitidos:
            if campo in campos_obrigatorios and not (valor or "").strip():
                raise HTTPException(status_code=422, detail=f"Campo '{campo}' é obrigatório.")
            setattr(tenant, campo, (valor.strip() if isinstance(valor, str) else valor) or None)
    
    await session.commit()
    await session.refresh(tenant)
    
    # Buscar assinatura ativa para retornar estrutura completa
    stmt = (
        select(AssinaturaTenant, PlanoAssinatura)
        .join(PlanoAssinatura, AssinaturaTenant.plano_id == PlanoAssinatura.id)
        .where(
            AssinaturaTenant.tenant_id == tenant.id,
            AssinaturaTenant.status.in_(["ATIVA", "TRIAL", "PENDENTE_PAGAMENTO"]),
        )
        .order_by(AssinaturaTenant.data_inicio.desc())
    )
    result = await session.execute(stmt)
    row = result.first()

    assinatura_data = None
    modulos_ativos = ["CORE"]
    max_usuarios = 2
    max_categorias_plano = 0
    if row:
        assinatura, plano = row
        max_categorias_plano = plano.max_categorias_plano
        max_usuarios = assinatura.usuarios_contratados or plano.limite_usuarios_minimo or 2
        ciclo = getattr(assinatura, "ciclo_pagamento", "MENSAL") or "MENSAL"
        valor_base = float(plano.preco_anual if ciclo == "ANUAL" else plano.preco_mensal)
        valor_composto = valor_base
        detalhamento_preco = []
        try:
            from core.services.plan_pricing_service import PlanoPricingService
            pricing_svc = PlanoPricingService(session)
            total_dec, detalhamento_preco = await pricing_svc.calcular_preco_total(
                plano_id=plano.id,
                quantidade_usuarios=max_usuarios,
                ciclo=ciclo,
            )
            valor_composto = float(total_dec)
        except Exception:
            valor_composto = valor_base

        assinatura_data = {
            "plano": plano.nome,
            "plano_id": str(plano.id),
            "valor": valor_composto,
            "valor_base": float(plano.preco_mensal),
            "ciclo_pagamento": ciclo,
            "status": assinatura.status,
            "data_inicio": assinatura.data_inicio,
            "proximo_vencimento": assinatura.data_proxima_renovacao,
            "max_categorias_plano": max_categorias_plano,
            "limite_hectares": float(plano.limite_hectares) if plano.limite_hectares is not None else None,
            "usuarios_inclusos": plano.limite_usuarios_minimo or 1,
            "usuarios_contratados": max_usuarios,
            "detalhamento_preco": detalhamento_preco,
        }
        modulos_ativos = plano.modulos_inclusos or ["CORE"]

    # Retorna estrutura completa igual ao GET /my-account
    return {
        "tenant": {
            "id": tenant.id,
            "nome": tenant.nome,
            "documento": tenant.documento,
            "ativo": tenant.ativo,
            "modulos_ativos": modulos_ativos,
            "max_usuarios": max_usuarios,
            "max_categorias_plano": max_categorias_plano,
            "created_at": tenant.created_at,
            "email_responsavel": tenant.email_responsavel,
            "telefone_responsavel": tenant.telefone_responsavel,
            "idioma_padrao": tenant.idioma_padrao,
            "logo_url_grupo": (tenant.branding or {}).get("logoUrl"),
        },
        "assinatura": assinatura_data
    }

@router.get("/invoices", response_model=List[FaturaResponse])
async def list_my_invoices(tenant: Tenant = Depends(get_current_tenant), session: AsyncSession = Depends(get_session)):
    """Lista o histórico de faturas do cliente logado."""
    stmt = (
        select(Fatura, PlanoAssinatura.nome.label("plano_nome"))
        .join(AssinaturaTenant, Fatura.assinatura_id == AssinaturaTenant.id)
        .join(PlanoAssinatura, AssinaturaTenant.plano_id == PlanoAssinatura.id)
        .where(Fatura.tenant_id == tenant.id)
        .order_by(Fatura.created_at.desc())
    )
    result = await session.execute(stmt)
    
    invoices = []
    for row in result:
        f = row[0]
        invoices.append({
            "id": f.id,
            "tenant_id": f.tenant_id,
            "tenant_nome": tenant.nome, # Já sabemos quem é
            "plano_nome": row.plano_nome,
            "valor": float(f.valor),
            "data_vencimento": f.data_vencimento,
            "status": f.status,
            "url_comprovante": f.url_comprovante,
            "data_envio_comprovante": f.data_envio_comprovante,
            "justificativa_rejeicao": f.justificativa_rejeicao,
            "created_at": f.created_at
        })
    return invoices

@router.post("/invoices/{invoice_id}/pay")
async def register_payment_proof(
    invoice_id: uuid.UUID,
    arquivo: UploadFile = File(..., description="Comprovante de pagamento (PDF, JPEG ou PNG). Máx 5MB."),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """Envia o comprovante de pagamento (upload real via StorageService)."""
    fatura = await session.get(Fatura, invoice_id)
    if not fatura or fatura.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Fatura indisponível ou não encontrada.")

    if fatura.status == "PAGA":
        raise HTTPException(status_code=400, detail="Esta fatura já está paga.")

    allowed = {"application/pdf", "image/jpeg", "image/png"}
    if arquivo.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Tipo não suportado. Use: {', '.join(allowed)}")

    content = await arquivo.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Comprovante deve ter no máximo 5MB.")

    ext = {"application/pdf": ".pdf", "image/jpeg": ".jpg", "image/png": ".png"}.get(arquivo.content_type, ".pdf")
    filename = f"{uuid.uuid4().hex[:12]}{ext}"
    storage_path = f"static/comprovantes/{tenant.id}/{invoice_id}/{filename}"

    StorageService.save_blob(content, storage_path)
    await increment_storage(session, tenant.id, len(content))
    url_comprovante = StorageService.public_url(storage_path)

    from datetime import datetime, timezone

    fatura.url_comprovante = url_comprovante
    fatura.data_envio_comprovante = datetime.now(timezone.utc)
    fatura.status = "EM_ANALISE"

    await session.commit()
    return {"message": "Comprovante enviado para análise!", "url_comprovante": url_comprovante}

@router.get("/plans", response_model=List[PlanoAssinaturaResponse])
async def list_available_plans(session: AsyncSession = Depends(get_session)):
    """Lista todos os pacotes de assinatura ativos."""
    stmt = select(PlanoAssinatura).where(PlanoAssinatura.ativo == True).order_by(PlanoAssinatura.preco_mensal.asc())
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/plans/landing", response_model=List[LandingPlanoResponse])
async def list_landing_plans(session: AsyncSession = Depends(get_session)):
    """Lista somente planos ativos e explicitamente publicados no site."""
    stmt = (
        select(PlanoAssinatura)
        .where(
            PlanoAssinatura.ativo.is_(True),
            PlanoAssinatura.disponivel_site.is_(True),
        )
        .order_by(PlanoAssinatura.ordem.asc(), PlanoAssinatura.preco_mensal.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()

@router.post("/upgrade")
async def request_upgrade(
    plan_id: uuid.UUID = Body(..., embed=True),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session)
):
    """
    Solicita upgrade para um novo plano.
    Gera um chamado de suporte interno e uma fatura pendente (simulado).
    """
    plan = await session.get(PlanoAssinatura, plan_id)
    if not plan or not plan.ativo:
        raise HTTPException(
            status_code=404,
            detail="Plano indisponível ou inativo. Se necessário, escolha outro plano ou contate o suporte.",
        )
        
    # Verifica se já está nesse plano
    stmt = select(AssinaturaTenant).where(AssinaturaTenant.tenant_id == tenant.id)
    result = await session.execute(stmt)
    assinatura = result.scalar_one_or_none()
    
    if assinatura and assinatura.plano_id == plan_id:
        raise HTTPException(status_code=400, detail="Seu tenant já está nesse plano.")

    # Em uma implementação real, integraríamos com Stripe ou geraria fatura.
    # Aqui, vamos registrar a intenção e avisar o suporte.
    return {
        "message": f"Solicitação de upgrade para {plan.nome} recebida!",
        "instructions": "Nossa equipe entrará em contato em instantes para concluir a migração."
    }


@router.get("/limits")
async def get_tenant_limits(
    claims: dict = Depends(get_current_user_claims),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    """
    Retorna status dos limites do tenant ativo.
    """
    from core.models.billing import AssinaturaTenant, PlanoAssinatura

    # Buscar assinatura ativado tenant
    stmt = (
        select(PlanoAssinatura, AssinaturaTenant)
        .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
        .where(
            AssinaturaTenant.tenant_id == tenant_id,
            AssinaturaTenant.status.in_(["ATIVA", "TRIAL", "PENDENTE_PAGAMENTO"]),
            AssinaturaTenant.tipo_assinatura == "TENANT",
        )
    )
    stmt = stmt.limit(1)
    result = await session.execute(stmt)
    row = result.first()
    plano = row[0] if row else None
    assinatura = row[1] if row else None

    if not plano:
        return {
            "max_fazendas": {"atual": 0, "limite": 0, "porcentagem": 0.0, "atingido": False},
            "limite_hectares": {"atual": 0.0, "limite": None, "porcentagem": 0.0, "atingido": False},
            "max_usuarios": {"atual": 0, "limite": 0, "usuarios_cadastrados": 0, "porcentagem": 0.0, "atingido": False},
            "storage": {"atual": 0, "limite": 0, "porcentagem": 0.0, "atingido": False},
        }

    # Contar fazendas
    fazendas_count_stmt = select(func.count(Fazenda.id)).where(Fazenda.tenant_id == tenant_id, Fazenda.ativo == True)
    fazendas_result = await session.execute(fazendas_count_stmt)
    fazendas_atual = fazendas_result.scalar_one() or 0

    max_fazendas = plano.max_fazendas
    fazendas_limite = None if max_fazendas == -1 else max_fazendas
    fazendas_porcentagem = (fazendas_atual / fazendas_limite * 100) if fazendas_limite and fazendas_limite > 0 else 0.0

    # Somar hectares das propriedades ativas
    hectares_stmt = select(
        func.coalesce(
            func.sum(
                func.coalesce(Fazenda.area_total_calculada_ha, Fazenda.area_total_ha, 0)
            ),
            0,
        )
    ).where(Fazenda.tenant_id == tenant_id, Fazenda.ativo == True)
    hectares_atual = float((await session.execute(hectares_stmt)).scalar_one() or 0)
    hectares_limite = float(plano.limite_hectares) if plano.limite_hectares is not None else None
    hectares_porcentagem = (hectares_atual / hectares_limite * 100) if hectares_limite and hectares_limite > 0 else 0.0

    # Contar acessos simultâneos ativos e total de usuários cadastrados na equipe
    from core.models.sessao import SessaoAtiva
    from datetime import datetime, timezone
    agora = datetime.now(timezone.utc)
    sessoes_count_stmt = select(func.count(SessaoAtiva.id)).where(
        SessaoAtiva.tenant_id == tenant_id,
        SessaoAtiva.status == "ATIVA",
        SessaoAtiva.expira_em > agora,
    )
    sessoes_ativas = (await session.execute(sessoes_count_stmt)).scalar_one() or 0

    usuarios_count_stmt = select(func.count(TenantUsuario.id)).where(
        TenantUsuario.tenant_id == tenant_id,
        TenantUsuario.status == "ATIVO",
    )
    usuarios_cadastrados = (await session.execute(usuarios_count_stmt)).scalar_one() or 0

    usuarios_limite = (
        (assinatura.usuarios_contratados if assinatura else None)
        or plano.limite_usuarios_maximo
        or plano.limite_usuarios_minimo
    )
    usuarios_porcentagem = (sessoes_ativas / usuarios_limite * 100) if usuarios_limite and usuarios_limite > 0 else 0.0

    # Storage
    tenant = await session.get(Tenant, tenant_id)
    storage_atual = tenant.storage_usado_mb if tenant else 0
    storage_limite = tenant.storage_limite_mb if tenant else 0
    storage_porcentagem = (storage_atual / storage_limite * 100) if storage_limite > 0 else 0.0

    return {
        "max_fazendas": {
            "atual": fazendas_atual,
            "limite": fazendas_limite,
            "porcentagem": round(fazendas_porcentagem, 2),
            "atingido": fazendas_atual >= fazendas_limite if fazendas_limite else False,
        },
        "limite_hectares": {
            "atual": round(hectares_atual, 2),
            "limite": hectares_limite,
            "porcentagem": round(hectares_porcentagem, 2),
            "atingido": hectares_atual >= hectares_limite if hectares_limite else False,
        },
        "max_usuarios": {
            "atual": sessoes_ativas,
            "limite": usuarios_limite,
            "usuarios_cadastrados": usuarios_cadastrados,
            "porcentagem": round(usuarios_porcentagem, 2),
            "atingido": sessoes_ativas >= usuarios_limite if usuarios_limite else False,
        },
        "storage": {
            "atual": storage_atual,
            "limite": storage_limite,
            "porcentagem": round(storage_porcentagem, 2),
            "atingido": storage_atual >= storage_limite,
        },
    }
