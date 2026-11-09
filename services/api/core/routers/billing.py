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
from core.schemas.billing_schemas import (
    FaturaResponse,
    LandingPlanoResponse,
    PlanoAssinaturaResponse,
    SimulacaoOrcamentoPublicoRequest,
)
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
        valor_anual_composto = float(plano.preco_anual or (plano.preco_mensal * 10))
        economia_anual_prevista = 0.0
        detalhamento_preco = []
        capacidade_equivalente = None
        try:
            from core.services.plan_pricing_service import PlanoPricingService
            pricing_svc = PlanoPricingService(session)
            total_dec, detalhamento_preco = await pricing_svc.calcular_preco_total(
                plano_id=plano.id,
                quantidade_usuarios=max_usuarios,
                ciclo=ciclo,
            )
            valor_composto = float(total_dec)
            mensal_dec, _ = await pricing_svc.calcular_preco_total(
                plano_id=plano.id,
                quantidade_usuarios=max_usuarios,
                ciclo="MENSAL",
            )
            anual_dec, _ = await pricing_svc.calcular_preco_total(
                plano_id=plano.id,
                quantidade_usuarios=max_usuarios,
                ciclo="ANUAL",
            )
            valor_anual_composto = float(anual_dec)
            economia_anual_prevista = float((mensal_dec * 12) - anual_dec)
            capacidade_equivalente = await pricing_svc.calcular_consumo_capacidade_tenant(tenant.id)
        except Exception:
            valor_composto = valor_base

        assinatura_data = {
            "plano": plano.nome,
            "plano_id": str(plano.id),
            "valor": valor_composto,
            "valor_base": float(plano.preco_mensal),
            "valor_anual_composto": valor_anual_composto,
            "economia_anual_prevista": economia_anual_prevista,
            "ciclo_pagamento": ciclo,
            "status": assinatura.status,
            "data_inicio": assinatura.data_inicio,
            "proximo_vencimento": assinatura.data_proxima_renovacao,
            "max_categorias_plano": max_categorias_plano,
            "limite_hectares": float(plano.limite_hectares) if plano.limite_hectares is not None else None,
            "usuarios_inclusos": plano.limite_usuarios_minimo or 1,
            "usuarios_contratados": max_usuarios,
            "detalhamento_preco": detalhamento_preco,
            "capacidade_equivalente": capacidade_equivalente,
        }
        from core.constants import ModuloMetadata, carregar_overrides_catalogo_modulos
        overrides = await carregar_overrides_catalogo_modulos(session)
        modulos_ativos = ModuloMetadata.filtrar_modulos_ativos(
            plano.modulos_inclusos or ["CORE"], overrides
        )

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
        valor_anual_composto = float(plano.preco_anual or (plano.preco_mensal * 10))
        economia_anual_prevista = 0.0
        detalhamento_preco = []
        capacidade_equivalente = None
        try:
            from core.services.plan_pricing_service import PlanoPricingService
            pricing_svc = PlanoPricingService(session)
            total_dec, detalhamento_preco = await pricing_svc.calcular_preco_total(
                plano_id=plano.id,
                quantidade_usuarios=max_usuarios,
                ciclo=ciclo,
            )
            valor_composto = float(total_dec)
            mensal_dec, _ = await pricing_svc.calcular_preco_total(
                plano_id=plano.id,
                quantidade_usuarios=max_usuarios,
                ciclo="MENSAL",
            )
            anual_dec, _ = await pricing_svc.calcular_preco_total(
                plano_id=plano.id,
                quantidade_usuarios=max_usuarios,
                ciclo="ANUAL",
            )
            valor_anual_composto = float(anual_dec)
            economia_anual_prevista = float((mensal_dec * 12) - anual_dec)
            capacidade_equivalente = await pricing_svc.calcular_consumo_capacidade_tenant(tenant.id)
        except Exception:
            valor_composto = valor_base

        assinatura_data = {
            "plano": plano.nome,
            "plano_id": str(plano.id),
            "valor": valor_composto,
            "valor_base": float(plano.preco_mensal),
            "valor_anual_composto": valor_anual_composto,
            "economia_anual_prevista": economia_anual_prevista,
            "ciclo_pagamento": ciclo,
            "status": assinatura.status,
            "data_inicio": assinatura.data_inicio,
            "proximo_vencimento": assinatura.data_proxima_renovacao,
            "max_categorias_plano": max_categorias_plano,
            "limite_hectares": float(plano.limite_hectares) if plano.limite_hectares is not None else None,
            "usuarios_inclusos": plano.limite_usuarios_minimo or 1,
            "usuarios_contratados": max_usuarios,
            "detalhamento_preco": detalhamento_preco,
            "capacidade_equivalente": capacidade_equivalente,
        }
        from core.constants import ModuloMetadata, carregar_overrides_catalogo_modulos
        overrides = await carregar_overrides_catalogo_modulos(session)
        modulos_ativos = ModuloMetadata.filtrar_modulos_ativos(
            plano.modulos_inclusos or ["CORE"], overrides
        )

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


@router.post("/invoices/{invoice_id}/checkout-stripe")
async def create_invoice_stripe_checkout(
    invoice_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    """Gera sessão de pagamento no Stripe Checkout com line_items compostos para fatura em aberto."""
    from core.services.plan_pricing_service import PlanoPricingService
    from core.services.stripe_service import StripeService

    fatura = await session.get(Fatura, invoice_id)
    if not fatura or fatura.tenant_id != tenant.id:
        raise HTTPException(status_code=404, detail="Fatura indisponível ou não encontrada.")

    if fatura.status == "PAGA":
        raise HTTPException(status_code=400, detail="Esta fatura já está paga.")

    assinatura = await session.get(AssinaturaTenant, fatura.assinatura_id) if fatura.assinatura_id else None
    if not assinatura:
        stmt_ass = (
            select(AssinaturaTenant)
            .where(AssinaturaTenant.tenant_id == tenant.id)
            .order_by(AssinaturaTenant.data_inicio.desc())
            .limit(1)
        )
        assinatura = (await session.execute(stmt_ass)).scalar_one_or_none()

    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura vinculada não encontrada.")

    from core.constants import ModuloMetadata, carregar_overrides_catalogo_modulos

    overrides = await carregar_overrides_catalogo_modulos(session)
    plano = await session.get(PlanoAssinatura, assinatura.plano_id)
    ciclo = getattr(assinatura, "ciclo_pagamento", "MENSAL") or "MENSAL"
    qtd_usuarios = assinatura.usuarios_contratados or (plano.limite_usuarios_minimo if plano else 1) or 1
    extensoes_contratadas = [
        ext
        for ext in list((tenant.branding or {}).get("extensoes_contratadas") or [])
        if ModuloMetadata.is_modulo_ativo(ext, overrides)
    ]

    detalhamento_preco: list[dict] | None = None
    if plano:
        try:
            pricing_svc = PlanoPricingService(session)
            _, detalhamento_preco = await pricing_svc.calcular_preco_total(
                plano_id=plano.id,
                quantidade_usuarios=qtd_usuarios,
                ciclo=ciclo,
            )
        except Exception:
            detalhamento_preco = None

    stripe_svc = StripeService()
    try:
        checkout_url = await stripe_svc.criar_checkout_assinatura(
            tenant_id=str(tenant.id),
            assinatura_id=str(assinatura.id),
            email=tenant.email_responsavel or "financeiro@deepfarms.com.br",
            plano_id=str(assinatura.plano_id),
            ciclo=ciclo,
            detalhamento_preco=detalhamento_preco,
            nome_plano=plano.nome if plano else "DeepFarms",
            usuarios_contratados=qtd_usuarios,
            extensoes_contratadas=extensoes_contratadas,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"checkout_url": checkout_url}

@router.get("/modules/catalog")
async def get_public_modules_catalog(session: AsyncSession = Depends(get_session)):
    """
    Retorna o status público de ativação dos módulos nativos e das extensões contratadas à parte (`EXT_IOT`, `EXT_ERP`).
    Módulos inativos não são exibidos nos pacotes e extensões inativas não podem ser selecionadas.
    """
    from core.constants import (
        EXTENSOES_CONTRATADAS_A_PARTE,
        ModuloMetadata,
        carregar_overrides_catalogo_modulos,
    )

    overrides = await carregar_overrides_catalogo_modulos(session)
    modulos_nativos: list[dict[str, object]] = []
    modulos_ativos: list[str] = []
    modulos_inativos: list[str] = []

    for mod_id, meta in ModuloMetadata.CATALOGO.items():
        ativo = ModuloMetadata.is_modulo_ativo(mod_id, overrides)
        if ativo:
            if mod_id not in EXTENSOES_CONTRATADAS_A_PARTE:
                modulos_ativos.append(mod_id)
        else:
            modulos_inativos.append(mod_id)

        if mod_id not in EXTENSOES_CONTRATADAS_A_PARTE:
            override_mod = overrides.get(mod_id, {})
            modulos_nativos.append({
                "id": mod_id,
                "nome": override_mod.get("nome", meta.get("nome", mod_id)),
                "descricao": override_mod.get("descricao", meta.get("descricao", "")),
                "categoria": override_mod.get("categoria", meta.get("categoria", "")),
                "obrigatorio": bool(override_mod.get("obrigatorio", meta.get("obrigatorio", False))),
                "ativo": ativo,
            })

    extensoes = ModuloMetadata.obter_extensoes_a_parte(overrides)
    return {
        "modulos_ativos": modulos_ativos,
        "modulos_inativos": modulos_inativos,
        "modulos_nativos": modulos_nativos,
        "extensoes": extensoes,
    }


@router.get("/plans", response_model=List[PlanoAssinaturaResponse])
async def list_available_plans(session: AsyncSession = Depends(get_session)):
    """Lista todos os pacotes de assinatura ativos filtrando módulos inativos."""
    from core.constants import ModuloMetadata, carregar_overrides_catalogo_modulos

    overrides = await carregar_overrides_catalogo_modulos(session)
    stmt = select(PlanoAssinatura).where(PlanoAssinatura.ativo == True).order_by(PlanoAssinatura.ordem.asc(), PlanoAssinatura.preco_mensal.asc())
    result = await session.execute(stmt)
    planos = list(result.scalars().all())

    nomes_atuais = {(p.nome or "").strip().lower() for p in planos}
    if len(planos) < 5 or any(n in nomes_atuais for n in ("básico", "basico", "profissional", "empresa")):
        try:
            from scripts.initial_load.seed_plans import seed_plans_with_session
            from scripts.seed_plan_pricing import seed_plan_pricing_with_session

            changed = await seed_plans_with_session(session)
            if changed:
                await seed_plan_pricing_with_session(session)
                result = await session.execute(stmt)
                planos = list(result.scalars().all())
        except Exception:
            pass

    for plano in planos:
        plano.modulos_inclusos = ModuloMetadata.filtrar_modulos_ativos(
            plano.modulos_inclusos or [], overrides
        )

    return planos


@router.get("/plans/landing", response_model=List[LandingPlanoResponse])
async def list_landing_plans(session: AsyncSession = Depends(get_session)):
    """Lista somente planos ativos e explicitamente publicados no site, filtrando módulos inativos."""
    from core.constants import ModuloMetadata, carregar_overrides_catalogo_modulos

    overrides = await carregar_overrides_catalogo_modulos(session)
    stmt = (
        select(PlanoAssinatura)
        .where(
            PlanoAssinatura.ativo.is_(True),
            PlanoAssinatura.disponivel_site.is_(True),
        )
        .order_by(PlanoAssinatura.ordem.asc(), PlanoAssinatura.preco_mensal.asc())
    )
    result = await session.execute(stmt)
    planos = list(result.scalars().all())

    nomes_atuais = {(p.nome or "").strip().lower() for p in planos}
    if len(planos) < 5 or any(n in nomes_atuais for n in ("básico", "basico", "profissional", "empresa")):
        try:
            from scripts.initial_load.seed_plans import seed_plans_with_session
            from scripts.seed_plan_pricing import seed_plan_pricing_with_session

            changed = await seed_plans_with_session(session)
            if changed:
                await seed_plan_pricing_with_session(session)
                result = await session.execute(stmt)
                planos = list(result.scalars().all())
        except Exception:
            pass

    for plano in planos:
        plano.modulos_inclusos = ModuloMetadata.filtrar_modulos_ativos(
            plano.modulos_inclusos or [], overrides
        )

    return planos


@router.post("/plans/simular")
async def simular_orcamento_publico(
    payload: SimulacaoOrcamentoPublicoRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Simulador transparente público (Landing Page, Cadastro e Painel de Assinatura).
    Calcula Hectares Equivalentes (isenta APP/Reserva Legal, pondera culturas/safrinha/consórcio e ILP),
    recomenda o pacote ideal entre os 5 perfis (100% dos módulos inclusos) e detalha
    o valor mensal e anual (2 meses grátis no pacote + 20% OFF nas licenças adicionais).
    """
    from core.services.plan_pricing_service import PlanoPricingService

    pricing_svc = PlanoPricingService(session)
    return await pricing_svc.simular_orcamento_publico(payload.model_dump())

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

    capacidade_eq = {}
    try:
        from core.services.plan_pricing_service import PlanoPricingService
        capacidade_eq = await PlanoPricingService(session).calcular_consumo_capacidade_tenant(tenant_id)
    except Exception:
        capacidade_eq = {}

    hectares_efetivos = float(capacidade_eq.get("hectares_equivalentes_total", hectares_atual))
    hectares_porcentagem = (hectares_efetivos / hectares_limite * 100) if hectares_limite and hectares_limite > 0 else 0.0

    return {
        "max_fazendas": {
            "atual": fazendas_atual,
            "limite": fazendas_limite,
            "porcentagem": round(fazendas_porcentagem, 2),
            "atingido": fazendas_atual >= fazendas_limite if fazendas_limite else False,
        },
        "limite_hectares": {
            "atual": round(hectares_efetivos, 2),
            "hectares_fisicos": round(hectares_atual, 2),
            "hectares_ambientais_isentos": round(float(capacidade_eq.get("hectares_ambientais_isentos", 0.0)), 2),
            "hectares_equivalentes": round(hectares_efetivos, 2),
            "cabecas_pecuaria_ativas": int(capacidade_eq.get("cabecas_pecuaria_total", 0)),
            "limite": hectares_limite,
            "porcentagem": round(hectares_porcentagem, 2),
            "atingido": hectares_efetivos >= hectares_limite if hectares_limite else False,
        },
        "max_usuarios": {
            "atual": sessoes_ativas,
            "limite": usuarios_limite,
            "usuarios_cadastrados": usuarios_cadastrados,
            "dispositivos_campo_ativos_isentos": int(capacidade_eq.get("dispositivos_campo_ativos_isentos", 0)),
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
