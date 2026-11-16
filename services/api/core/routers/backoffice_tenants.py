"""
Router para gestão de tenants pelo backoffice.

Permite admins SaaS criarem e gerenciarem tenants (assinantes).
"""
from typing import Optional
from uuid import UUID
import uuid as uuid_module
import secrets
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from core.database import async_session_maker
from core.dependencies import get_current_admin, require_permission
from core.models.tenant import Tenant
from core.models.billing import PlanoAssinatura, AssinaturaTenant, Fatura
from core.models.auth import Usuario, PerfilAcesso, TenantUsuario, UnidadeProdutivaUsuario
from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
# grupos_fazendas removed
from core.models.crm import LeadCRM
from core.services.plan_pricing_service import PlanoPricingService
from core.services.asaas_service import AsaasService
from core.exceptions import BusinessRuleError, EntityNotFoundError
from pydantic import BaseModel, EmailStr, Field
from loguru import logger

router = APIRouter(prefix="/backoffice/tenants", tags=["Backoffice - Gestão de Tenants"])


# ============================================================================
# SCHEMAS
# ============================================================================

class CriarTenantRequest(BaseModel):
    """Request para criar novo tenant."""
    # Dados do tenant
    nome_tenant: str = Field(..., min_length=3, max_length=150)
    documento: str = Field(..., description="CPF ou CNPJ")
    email_responsavel: EmailStr
    telefone_responsavel: Optional[str] = None

    # Dados do usuário owner
    nome_completo: str = Field(..., min_length=3)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    senha: str = Field(..., min_length=6)

    # Dados da primeira fazenda
    nome_fazenda: str = Field(..., min_length=3)

    # Assinatura
    plano_id: UUID
    usuarios_contratados: int = Field(1, ge=1, description="Quantidade de usuários simultâneos")
    ciclo_pagamento: str = Field("MENSAL", description="MENSAL ou ANUAL")
    extensoes_contratadas: list[str] = Field(default_factory=list, description="Lista de extensões opcionais (ex: EXT_IOT, EXT_ERP)")

    # Trial
    com_trial: bool = Field(True, description="Iniciar com período de trial")
    dias_trial: Optional[int] = Field(None, ge=1, le=90)


class TenantResponse(BaseModel):
    """Response com dados do tenant."""
    id: UUID
    nome: str
    documento: str
    email_responsavel: Optional[str]
    telefone_responsavel: Optional[str]
    ativo: bool
    storage_usado_mb: int
    storage_limite_mb: int
    data_ultimo_acesso: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Dados da assinatura
    assinatura: Optional[dict] = None

    model_config = {"from_attributes": True}


class AtivarDesativarTenantRequest(BaseModel):
    """Request para ativar/desativar tenant."""
    motivo: str = Field(..., min_length=10)


class ConversaoFazenda(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)


class ConvertLeadRequest(BaseModel):
    """Request para conversão de lead em assinante."""
    # Dados confirmados/sobrescritos pelo admin (pré-preenchidos do lead)
    nome_tenant: str = Field(..., min_length=3, max_length=150)
    documento: str = Field(..., description="CPF ou CNPJ")
    email_responsavel: EmailStr
    nome_completo: str = Field(..., min_length=3, description="Nome do responsável")
    telefone_responsavel: Optional[str] = None

    # Plano e assinatura
    plano_id: UUID
    ciclo_pagamento: str = Field("MENSAL", description="MENSAL ou ANUAL")
    usuarios_contratados: int = Field(5, ge=1)

    # Fazendas — pelo menos uma obrigatória
    fazendas: list[ConversaoFazenda] = Field(..., min_length=1)


class ConvertLeadResponse(BaseModel):
    tenant_id: UUID
    assinatura_id: UUID
    activation_token: str
    activation_expires_at: datetime
    message: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar novo assinante",
    description="Cria tenant completo: usuário owner, fazenda, assinatura e cobrança",
    dependencies=[Depends(require_permission("backoffice:tenants:create"))]
)
async def criar_tenant(
    request: CriarTenantRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Cria novo tenant (assinante) no sistema.

    **Processo:**
    1. Cria usuário owner
    2. Cria tenant
    3. Cria perfil de acesso (Proprietário)
    4. Vincula usuário ao tenant
    5. Cria primeira fazenda
    6. Vincula usuário à fazenda
    7. Cria assinatura
    8. Calcula valor e cria cobrança no Asaas (se não for trial)

    **Trial:**
    - Se `com_trial=true`, assinatura inicia em trial (sem cobrança)
    - Trial padrão é conforme configurado no plano
    - Após trial, gera cobrança automaticamente
    """
    async with async_session_maker() as session:
        try:
            # 1. Verificar se email/username já existe
            stmt = select(Usuario).where(
                (Usuario.email == request.email) |
                (Usuario.username == request.username)
            )
            result = await session.execute(stmt)
            usuario_existente = result.scalar_one_or_none()

            if usuario_existente:
                raise BusinessRuleError("Email ou username já cadastrado no sistema")

            # 2. Verificar se documento já existe
            stmt = select(Tenant).where(Tenant.documento == request.documento)
            result = await session.execute(stmt)
            tenant_existente = result.scalar_one_or_none()

            if tenant_existente:
                raise BusinessRuleError(f"Documento {request.documento} já cadastrado")

            # 3. Buscar plano
            stmt = select(PlanoAssinatura).where(PlanoAssinatura.id == request.plano_id)
            result = await session.execute(stmt)
            plano = result.scalar_one_or_none()

            if not plano or not plano.ativo:
                raise EntityNotFoundError("Plano indisponível ou inativo.")

            # 3.1. Validar e filtrar extensões solicitadas
            from core.constants import (
                ModuloMetadata,
                TABELA_EXTENSOES_A_PARTE,
                carregar_overrides_catalogo_modulos,
            )
            overrides_catalogo = await carregar_overrides_catalogo_modulos(session)
            extensoes_validas: list[str] = []
            for ext in request.extensoes_contratadas:
                if ext not in TABELA_EXTENSOES_A_PARTE:
                    continue
                if not ModuloMetadata.is_modulo_ativo(ext, overrides_catalogo):
                    nome_ext = TABELA_EXTENSOES_A_PARTE[ext].get("nome", ext)
                    raise BusinessRuleError(f"A extensão '{nome_ext}' está inativa no catálogo e não pode ser contratada.")
                extensoes_validas.append(ext)

            # 4. Validar quantidade de usuários
            pricing_service = PlanoPricingService(session)
            await pricing_service.validar_quantidade_usuarios(plano.id, request.usuarios_contratados)

            # 5. Criar usuário owner
            from core.services.auth_service import AuthService
            auth_service = AuthService(session)
            senha_hash = auth_service.get_password_hash(request.senha)

            usuario = Usuario(
                email=request.email,
                username=request.username,
                nome_completo=request.nome_completo,
                senha_hash=senha_hash
            )
            session.add(usuario)
            await session.flush()

            # 6. Criar tenant
            tenant = Tenant(
                nome=request.nome_tenant,
                documento=request.documento,
                email_responsavel=request.email_responsavel,
                telefone_responsavel=request.telefone_responsavel,
                ativo=True,
                branding={"extensoes_contratadas": extensoes_validas} if extensoes_validas else None,
            )
            session.add(tenant)
            await session.flush()

            # 7. Criar perfil de acesso "Proprietário"
            perfil = PerfilAcesso(
                tenant_id=tenant.id,
                nome="Proprietário",
                is_custom=True,
                permissoes={"global": "owner"}
            )
            session.add(perfil)
            await session.flush()

            # 8. Vincular usuário ao tenant como owner
            tenant_usuario = TenantUsuario(
                tenant_id=tenant.id,
                usuario_id=usuario.id,
                perfil_id=perfil.id,
                is_owner=True
            )
            session.add(tenant_usuario)

            # 9. Criar primeira unidade produtiva
            fazenda = Fazenda(
                tenant_id=tenant.id,
                nome=request.nome_fazenda,
                ativo=True
            )
            session.add(fazenda)
            await session.flush()

            # 11. Vincular usuário à fazenda
            fazenda_usuario = UnidadeProdutivaUsuario(
                tenant_id=tenant.id,
                usuario_id=usuario.id,
                unidade_produtiva_id=fazenda.id
            )
            session.add(fazenda_usuario)

            # 12. Criar assinatura vinculada ao grupo
            data_inicio = datetime.now(timezone.utc)

            if request.com_trial:
                dias_trial = request.dias_trial or plano.dias_trial
                data_proxima_renovacao = data_inicio + timedelta(days=dias_trial)
                status_assinatura = "TRIAL"
            else:
                dias_ciclo = 365 if request.ciclo_pagamento == "ANUAL" else 30
                data_proxima_renovacao = data_inicio + timedelta(days=dias_ciclo)
                status_assinatura = "PENDENTE"

            assinatura = AssinaturaTenant(
                tenant_id=tenant.id,
                plano_id=plano.id,
                tipo_assinatura="TENANT",
                ciclo_pagamento=request.ciclo_pagamento,
                usuarios_contratados=request.usuarios_contratados,
                status=status_assinatura,
                data_inicio=data_inicio,
                data_proxima_renovacao=data_proxima_renovacao
            )
            session.add(assinatura)
            await session.flush()

            # 13. Calcular valor da fatura inicial (incluindo usuários adicionais e extensões ativas)
            usuarios_inclusos = max(1, int(getattr(plano, "limite_usuarios_minimo", 1) or 1))
            if not plano.is_free:
                if request.usuarios_contratados > usuarios_inclusos:
                    valor_fatura, _ = await pricing_service._calcular_preco_instancia_plano(
                        plano, request.usuarios_contratados, request.ciclo_pagamento
                    )
                else:
                    valor_fatura = (
                        Decimal(str(plano.preco_anual))
                        if request.ciclo_pagamento == "ANUAL"
                        else Decimal(str(plano.preco_mensal))
                    )

                if extensoes_validas:
                    extensoes_info = {
                        e["id"]: e for e in ModuloMetadata.obter_extensoes_a_parte(overrides_catalogo)
                    }
                    chave_preco_ext = "preco_anual" if request.ciclo_pagamento == "ANUAL" else "preco_mensal"
                    valor_extensoes = sum(
                        Decimal(str(extensoes_info.get(ext, {}).get(chave_preco_ext, TABELA_EXTENSOES_A_PARTE[ext][chave_preco_ext])))
                        for ext in extensoes_validas
                    )
                    valor_fatura = (valor_fatura + valor_extensoes).quantize(Decimal("0.01"))

                # Data de vencimento da fatura
                if request.com_trial:
                    vencimento_dt = data_proxima_renovacao + timedelta(days=1)
                else:
                    vencimento_dt = data_inicio + timedelta(days=3)

                fatura = Fatura(
                    tenant_id=tenant.id,
                    assinatura_id=assinatura.id,
                    valor=valor_fatura,
                    data_vencimento=vencimento_dt,
                    status="ABERTA",
                )
                session.add(fatura)
                logger.info(
                    f"Fatura criada: R$ {valor_fatura} vence em {vencimento_dt} para {tenant.nome}"
                )

            await session.commit()
            await session.refresh(tenant)
            await session.refresh(assinatura)

            logger.info(
                f"Tenant criado: {tenant.nome} (ID: {tenant.id}) - "
                f"Plano: {plano.nome}, Usuários: {request.usuarios_contratados}, "
                f"Extensões: {extensoes_validas}, Status: {status_assinatura}"
            )

            # Preparar response
            tenant_data = TenantResponse.model_validate(tenant)
            tenant_data.assinatura = {
                "id": str(assinatura.id),
                "plano": plano.nome,
                "plano_id": str(plano.id),
                "status": assinatura.status,
                "usuarios_contratados": assinatura.usuarios_contratados,
                "ciclo_pagamento": assinatura.ciclo_pagamento,
                "data_proxima_renovacao": assinatura.data_proxima_renovacao,
                "extensoes_contratadas": extensoes_validas,
            }

            return tenant_data

        except BusinessRuleError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except EntityNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Erro ao criar tenant: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erro ao criar tenant")


@router.get(
    "",
    response_model=list[TenantResponse],
    summary="Listar tenants",
    dependencies=[Depends(require_permission("backoffice:tenants:view"))]
)
async def listar_tenants(
    ativo: Optional[bool] = Query(None, description="Filtrar por status ativo"),
    search: Optional[str] = Query(None, description="Buscar por nome ou documento"),
    limit: int = Query(50, le=100),
    offset: int = 0,
    current_admin: dict = Depends(get_current_admin)
):
    """Lista todos os tenants do sistema."""
    async with async_session_maker() as session:
        stmt = select(Tenant)

        if ativo is not None:
            stmt = stmt.where(Tenant.ativo == ativo)

        if search:
            stmt = stmt.where(
                (Tenant.nome.ilike(f"%{search}%")) |
                (Tenant.documento.ilike(f"%{search}%"))
            )

        stmt = stmt.order_by(Tenant.created_at.desc()).limit(limit).offset(offset)

        result = await session.execute(stmt)
        tenants = result.scalars().all()

        # Buscar assinaturas
        tenant_ids = [t.id for t in tenants]
        stmt_assinaturas = select(AssinaturaTenant).where(
            AssinaturaTenant.tenant_id.in_(tenant_ids),
            AssinaturaTenant.tipo_assinatura == "TENANT"
        )
        result = await session.execute(stmt_assinaturas)
        assinaturas = {a.tenant_id: a for a in result.scalars().all()}

        # Buscar planos
        plano_ids = [a.plano_id for a in assinaturas.values()]
        stmt_planos = select(PlanoAssinatura).where(PlanoAssinatura.id.in_(plano_ids))
        result = await session.execute(stmt_planos)
        planos = {p.id: p for p in result.scalars().all()}

        # Montar response
        response = []
        for tenant in tenants:
            tenant_data = TenantResponse.model_validate(tenant)

            assinatura = assinaturas.get(tenant.id)
            if assinatura:
                plano = planos.get(assinatura.plano_id)
                tenant_data.assinatura = {
                    "id": str(assinatura.id),
                    "plano": plano.nome if plano else "N/A",
                    "plano_id": str(assinatura.plano_id),
                    "status": assinatura.status,
                    "usuarios_contratados": assinatura.usuarios_contratados,
                    "ciclo_pagamento": assinatura.ciclo_pagamento,
                    "data_proxima_renovacao": assinatura.data_proxima_renovacao,
                    "extensoes_contratadas": (tenant.branding or {}).get("extensoes_contratadas", []) if isinstance(tenant.branding, dict) else [],
                }

            response.append(tenant_data)

        return response


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Detalhes do tenant",
    dependencies=[Depends(require_permission("backoffice:tenants:view"))]
)
async def obter_tenant(
    tenant_id: UUID,
    current_admin: dict = Depends(get_current_admin)
):
    """Obtém detalhes completos de um tenant."""
    async with async_session_maker() as session:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        # Buscar assinatura principal
        stmt = select(AssinaturaTenant).where(
            AssinaturaTenant.tenant_id == tenant_id,
            AssinaturaTenant.tipo_assinatura == "TENANT"
        )
        result = await session.execute(stmt)
        assinatura = result.scalar_one_or_none()

        tenant_data = TenantResponse.model_validate(tenant)

        if assinatura:
            # Buscar plano
            plano = await session.get(PlanoAssinatura, assinatura.plano_id)
            tenant_data.assinatura = {
                "id": str(assinatura.id),
                "plano": plano.nome if plano else "N/A",
                "plano_id": str(assinatura.plano_id),
                "status": assinatura.status,
                "usuarios_contratados": assinatura.usuarios_contratados,
                "ciclo_pagamento": assinatura.ciclo_pagamento,
                "data_inicio": assinatura.data_inicio,
                "data_proxima_renovacao": assinatura.data_proxima_renovacao,
                "created_at": assinatura.created_at,
                "extensoes_contratadas": (tenant.branding or {}).get("extensoes_contratadas", []) if isinstance(tenant.branding, dict) else [],
            }

        return tenant_data


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Garante datetime timezone-aware em UTC para comparações seguras."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@router.patch(
    "/{tenant_id}/desativar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desativar tenant",
    dependencies=[Depends(require_permission("backoffice:tenants:manage"))]
)
async def desativar_tenant(
    tenant_id: UUID,
    request: AtivarDesativarTenantRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """Desativa tenant (soft delete)."""
    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_id)

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        tenant.ativo = False
        await session.commit()

        logger.warning(
            f"Tenant {tenant.nome} (ID: {tenant_id}) desativado por admin "
            f"{current_admin['admin_id']}. Motivo: {request.motivo}"
        )

        return None


@router.patch(
    "/{tenant_id}/ativar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Ativar tenant",
    dependencies=[Depends(require_permission("backoffice:tenants:manage"))]
)
async def ativar_tenant(
    tenant_id: UUID,
    current_admin: dict = Depends(get_current_admin)
):
    """Ativa tenant anteriormente desativado."""
    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_id)

        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        tenant.ativo = True
        await session.commit()

        logger.info(
            f"Tenant {tenant.nome} (ID: {tenant_id}) reativado por admin "
            f"{current_admin['admin_id']}"
        )

        return None


@router.post(
    "/leads/{lead_id}/converter",
    response_model=ConvertLeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Converter lead em assinante",
    description=(
        "Converte um lead aprovado em tenant. Cria tenant, assinatura (PENDENTE_PAGAMENTO), "
        "usuário admin e fazendas. Retorna token de ativação para envio ao assinante."
    ),
    dependencies=[Depends(require_permission("backoffice:tenants:create"))]
)
async def converter_lead(
    lead_id: UUID,
    request: ConvertLeadRequest,
    current_admin: dict = Depends(get_current_admin)
):
    """
    Fluxo de conversão de lead:

    1. Valida que o lead está com status 'aprovado'
    2. Cria Tenant (ativo=False — pendente de pagamento)
    3. Cria AssinaturaTenant (status=PENDENTE_PAGAMENTO)
    4. Cria Usuário owner com senha temporária aleatória
    5. Cria Fazenda(s) conforme informado
    6. Gera token de ativação (48h) armazenado no Tenant
    7. Vincula lead ao tenant criado
    8. Lead status permanece 'aprovado' — muda para 'convertido' somente após pagamento (webhook Stripe)
    """
    async with async_session_maker() as session:
        try:
            # 1. Buscar e validar lead
            lead = await session.get(LeadCRM, lead_id)
            if not lead:
                raise HTTPException(status_code=404, detail="Lead não encontrado")
            if lead.status in ("convertido", "perdido"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Lead com status '{lead.status}' não pode ser convertido."
                )
            if lead.tenant_convertido_id:
                raise HTTPException(status_code=422, detail="Lead já foi convertido anteriormente")

            # 2. Verificar documento único
            stmt = select(Tenant).where(Tenant.documento == request.documento)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                raise BusinessRuleError(f"Documento {request.documento} já cadastrado")

            # 3. Verificar email único
            stmt = select(Usuario).where(Usuario.email == request.email_responsavel)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                raise BusinessRuleError(f"Email {request.email_responsavel} já cadastrado")

            # 4. Buscar plano (deve estar disponível no CRM)
            plano = await session.get(PlanoAssinatura, request.plano_id)
            if not plano or not plano.ativo:
                raise EntityNotFoundError("Plano indisponível ou inativo.")
            if not plano.disponivel_crm:
                raise BusinessRuleError("Este plano não está disponível para comercialização via CRM")

            # 5. Validar quantidade de usuários
            pricing_service = PlanoPricingService(session)
            await pricing_service.validar_quantidade_usuarios(plano.id, request.usuarios_contratados)

            # 6. Criar usuário owner com senha temporária
            from core.services.auth_service import AuthService
            auth_service = AuthService(session)
            senha_temporaria = secrets.token_urlsafe(12)
            senha_hash = auth_service.get_password_hash(senha_temporaria)

            # Gerar username a partir do email
            username_base = request.email_responsavel.split("@")[0].lower().replace(".", "_")
            username = username_base
            contador = 1
            while True:
                stmt = select(Usuario).where(Usuario.username == username)
                result = await session.execute(stmt)
                if not result.scalar_one_or_none():
                    break
                username = f"{username_base}_{contador}"
                contador += 1

            usuario = Usuario(
                email=request.email_responsavel,
                username=username,
                nome_completo=request.nome_completo,
                senha_hash=senha_hash
            )
            session.add(usuario)
            await session.flush()

            # 7. Criar tenant (inativo — ativa somente após pagamento)
            activation_token = secrets.token_urlsafe(32)
            activation_expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

            tenant = Tenant(
                nome=request.nome_tenant,
                documento=request.documento,
                email_responsavel=request.email_responsavel,
                telefone_responsavel=request.telefone_responsavel,
                ativo=False,
                activation_token=activation_token,
                activation_expires_at=activation_expires_at
            )
            session.add(tenant)
            await session.flush()

            # 8. Criar perfil de acesso "Proprietário"
            perfil = PerfilAcesso(
                tenant_id=tenant.id,
                nome="Proprietário",
                is_custom=True,
                permissoes={"global": "owner"}
            )
            session.add(perfil)
            await session.flush()

            # 9. Vincular usuário ao tenant como owner
            tenant_usuario = TenantUsuario(
                tenant_id=tenant.id,
                usuario_id=usuario.id,
                perfil_id=perfil.id,
                is_owner=True
            )
            session.add(tenant_usuario)

            # 10. Criar unidades produtivas
            for fazenda_data in request.fazendas:
                fazenda = Fazenda(
                    tenant_id=tenant.id,
                    nome=fazenda_data.nome,
                    ativo=True
                )
                session.add(fazenda)
                await session.flush()

                fazenda_usuario = UnidadeProdutivaUsuario(
                    tenant_id=tenant.id,
                    usuario_id=usuario.id,
                    unidade_produtiva_id=fazenda.id
                )
                session.add(fazenda_usuario)

            # 11. Criar assinatura
            data_inicio = datetime.now(timezone.utc)
            dias_ciclo = 365 if request.ciclo_pagamento == "ANUAL" else 30
            data_proxima_renovacao = data_inicio + timedelta(days=dias_ciclo)

            assinatura = AssinaturaTenant(
                tenant_id=tenant.id,
                plano_id=plano.id,
                tipo_assinatura="TENANT",
                ciclo_pagamento=request.ciclo_pagamento,
                usuarios_contratados=request.usuarios_contratados,
                status="PENDENTE_PAGAMENTO",
                data_inicio=data_inicio,
                data_proxima_renovacao=data_proxima_renovacao
            )
            session.add(assinatura)
            await session.flush()

            # 12. Criar fatura ABERTA no backoffice financeiro (compondo pacote base + acessos simultâneos extras)
            valor_fatura, _ = await pricing_service.calcular_preco_total(
                plano_id=plano.id,
                quantidade_usuarios=request.usuarios_contratados,
                ciclo=request.ciclo_pagamento,
            )
            fatura = Fatura(
                assinatura_id=assinatura.id,
                tenant_id=tenant.id,
                valor=valor_fatura,
                data_vencimento=data_proxima_renovacao,
                status="ABERTA",
            )
            session.add(fatura)

            # 13. Vincular lead ao tenant
            lead.tenant_convertido_id = tenant.id

            await session.commit()

            logger.info(
                f"Lead {lead_id} convertido → Tenant {tenant.id} ({tenant.nome}) "
                f"por admin {current_admin.get('sub', 'unknown')}. "
                f"Plano: {plano.nome}, Fazendas: {len(request.fazendas)}"
            )

            return ConvertLeadResponse(
                tenant_id=tenant.id,
                assinatura_id=assinatura.id,
                activation_token=activation_token,
                activation_expires_at=activation_expires_at,
                message=(
                    f"Tenant criado com sucesso. Envie o link de ativação para {request.email_responsavel}. "
                    f"Token expira em 48 horas."
                )
            )

        except BusinessRuleError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except EntityNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro ao converter lead {lead_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Erro ao converter lead")


class AddDiasCortesiaRequest(BaseModel):
    """Payload para adicionar dias de cortesia/extensão de trial ao tenant."""
    dias: int = Field(..., ge=1, le=365)


class TrocarPlanoTenantRequest(BaseModel):
    """Payload para troca administrativa de plano de um tenant."""
    plano_id: UUID


@router.patch(
    "/{tenant_id}/add-dias",
    summary="Adicionar dias de cortesia / estender trial",
    dependencies=[Depends(require_permission("backoffice:tenants:manage"))],
)
async def adicionar_dias_cortesia(
    tenant_id: UUID,
    request: AddDiasCortesiaRequest,
    current_admin: dict = Depends(get_current_admin),
):
    """Estende o período de trial/vigência da assinatura e prorroga fatura em aberto."""
    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        assinatura = (
            await session.execute(
                select(AssinaturaTenant)
                .where(
                    AssinaturaTenant.tenant_id == tenant_id,
                    AssinaturaTenant.tipo_assinatura == "TENANT",
                )
                .order_by(AssinaturaTenant.data_inicio.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if not assinatura:
            raise HTTPException(status_code=404, detail="Assinatura do tenant não encontrada")

        agora = datetime.now(timezone.utc)
        delta = timedelta(days=request.dias)

        trial_atual = _as_utc(assinatura.trial_expires_at)
        base_trial = trial_atual if trial_atual and trial_atual > agora else agora
        if assinatura.status in ("TRIAL", "PENDENTE_PAGAMENTO", "SUSPENSA", "BLOQUEADA") or trial_atual is not None:
            assinatura.trial_expires_at = base_trial + delta

        renovacao_atual = _as_utc(assinatura.data_proxima_renovacao)
        base_renovacao = renovacao_atual if renovacao_atual and renovacao_atual > agora else agora
        assinatura.data_proxima_renovacao = base_renovacao + delta

        if assinatura.status in ("SUSPENSA", "BLOQUEADA"):
            assinatura.status = "TRIAL" if assinatura.trial_expires_at is not None else "ATIVA"
            assinatura.data_bloqueio = None
            tenant.ativo = True

        faturas_abertas = (
            await session.execute(
                select(Fatura).where(
                    Fatura.assinatura_id == assinatura.id,
                    Fatura.status == "ABERTA",
                )
            )
        ).scalars().all()
        for fatura in faturas_abertas:
            venc_atual = _as_utc(fatura.data_vencimento)
            base_venc = venc_atual if venc_atual and venc_atual > agora else agora
            fatura.data_vencimento = base_venc + delta

        await session.commit()
        logger.info(
            f"Cortesia de {request.dias} dias aplicada ao tenant {tenant_id} "
            f"por admin {current_admin.get('admin_id', current_admin.get('sub', 'unknown'))}"
        )
        return {
            "tenant_id": str(tenant_id),
            "dias_adicionados": request.dias,
            "status": assinatura.status,
            "trial_expires_at": assinatura.trial_expires_at,
            "data_proxima_renovacao": assinatura.data_proxima_renovacao,
        }


@router.patch(
    "/{tenant_id}/trocar-plano",
    summary="Trocar plano do tenant administrativamente",
    dependencies=[Depends(require_permission("backoffice:tenants:manage"))],
)
async def trocar_plano_tenant(
    tenant_id: UUID,
    request: TrocarPlanoTenantRequest,
    current_admin: dict = Depends(get_current_admin),
):
    """Altera o plano da assinatura do tenant pelo backoffice (inclusive para plano gratuito/isento)."""
    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant não encontrado")

        plano = await session.get(PlanoAssinatura, request.plano_id)
        if not plano or not plano.ativo:
            raise HTTPException(status_code=404, detail="Plano indisponível ou inativo")

        assinatura = (
            await session.execute(
                select(AssinaturaTenant)
                .where(
                    AssinaturaTenant.tenant_id == tenant_id,
                    AssinaturaTenant.tipo_assinatura == "TENANT",
                )
                .order_by(AssinaturaTenant.data_inicio.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if not assinatura:
            raise HTTPException(status_code=404, detail="Assinatura do tenant não encontrada")

        assinatura.plano_id = plano.id
        assinatura.usuarios_contratados = max(assinatura.usuarios_contratados or 1, plano.limite_usuarios_minimo or 1)

        faturas_abertas = (
            await session.execute(
                select(Fatura).where(
                    Fatura.assinatura_id == assinatura.id,
                    Fatura.status == "ABERTA",
                )
            )
        ).scalars().all()

        if plano.is_free:
            assinatura.status = "ATIVA"
            assinatura.trial_expires_at = None
            assinatura.data_bloqueio = None
            tenant.ativo = True
            for fatura in faturas_abertas:
                fatura.status = "CANCELADA"
        elif assinatura.status in ("TRIAL", "PENDENTE_PAGAMENTO"):
            preco_novo = Decimal(str(plano.preco_anual if assinatura.ciclo_pagamento == "ANUAL" else plano.preco_mensal or 0))
            for fatura in faturas_abertas:
                fatura.valor = preco_novo

        await session.commit()
        logger.info(
            f"Plano do tenant {tenant_id} alterado para {plano.nome} "
            f"por admin {current_admin.get('admin_id', current_admin.get('sub', 'unknown'))}"
        )
        return {
            "tenant_id": str(tenant_id),
            "plano_id": str(plano.id),
            "plano_nome": plano.nome,
            "status": assinatura.status,
        }
