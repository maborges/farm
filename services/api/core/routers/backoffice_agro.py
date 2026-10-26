"""Router do Backoffice para administração de produtores DeepFarms Agro.

Gerencia o ciclo de vida operacional de contas gratuitas (INDIVIDUAL_FREE),
inspeção de credenciais de cotações BYOK com envelope encryption seguro (sem segredos),
sessões ativas, bloqueio/desbloqueio e registro estrito de auditoria em AdminAuditLog.
"""

from __future__ import annotations

import math
import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, require_permission
from core.models.admin_audit_log import AdminAuditLog
from core.services.admin_audit_service import resolve_admin_identity
from core.models.auth import TenantUsuario, Usuario
from core.models.tenant import Tenant
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.models.sessao import SessaoAtiva
from core.models.usuario_byok import UsuarioByokCredential
from core.services.auth_service import _slugify_tenant_name
from core.utils.cpf_cnpj import normalizar_documento_opcional, validar_cpf_ou_cnpj

router = APIRouter(
    prefix="/backoffice/agro",
    tags=["Backoffice — DeepFarms Agro"],
)


# ==============================================================================
# SCHEMAS DE RESPOSTA E CONTRATO
# ==============================================================================

class AgroByokMeta(BaseModel):
    """Metadados seguros de credencial BYOK (sem chaves nem cifras)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_slug: str
    mascara_chave: str
    key_version: int
    status: str
    ultimo_uso: datetime | None = None
    created_at: datetime


class AgroSessionItem(BaseModel):
    """Informações de sessão ativa do usuário."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    ip_address: str | None = None
    user_agent: str | None = None
    inicio: datetime
    ultimo_heartbeat: datetime
    expira_em: datetime


class AgroAuditLogItem(BaseModel):
    """Registro de auditoria administrativa sobre o usuário."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admin_email: str
    acao: str
    descricao: str | None = None
    created_at: datetime


class AgroUserListItem(BaseModel):
    """Item da listagem de produtores Agro."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    nome_completo: str | None = None
    cpf: str | None = None
    telefone: str | None = None
    ativo: bool
    account_type: str = "INDIVIDUAL_FREE"
    data_cadastro: datetime
    ultimo_acesso: datetime | None = None
    sessoes_ativas_count: int = 0
    byok_count: int = 0
    byok_providers: list[str] = []


class AgroUserListResponse(BaseModel):
    """Resposta paginada de produtores Agro."""
    items: list[AgroUserListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AgroUserDetailResponse(BaseModel):
    """Detalhes completos de um produtor Agro para governança operacional."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    username: str
    nome_completo: str | None = None
    cpf: str | None = None
    telefone: str | None = None
    apelido: str | None = None
    foto_perfil_url: str | None = None
    ativo: bool
    account_type: str
    is_superuser: bool
    data_cadastro: datetime
    updated_at: datetime | None = None
    sessoes_ativas: list[AgroSessionItem] = []
    credenciais_byok: list[AgroByokMeta] = []
    acoes_auditoria: list[AgroAuditLogItem] = []


class ToggleStatusResponse(BaseModel):
    id: uuid.UUID
    novo_status: bool
    sessoes_encerradas: int
    mensagem: str


class RevokeSessionsResponse(BaseModel):
    id: uuid.UUID
    sessoes_encerradas: int
    mensagem: str


class AgroPlanoOption(BaseModel):
    """Opção de plano comercial para conversão de produtor."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nome: str
    preco_mensal: float
    preco_anual: float
    tem_trial: bool
    dias_trial: int
    plan_tier: str


class AgroConverterComercialRequest(BaseModel):
    """Payload para conversão de conta individual Agro em Tenant comercial."""
    nome_fazenda: str
    plano_id: uuid.UUID
    ciclo: str = "MENSAL"
    documento: str | None = None


class AgroConverterComercialResponse(BaseModel):
    """Resultado da conversão de produtor para comercial."""
    usuario_id: uuid.UUID
    tenant_id: uuid.UUID
    nome_tenant: str
    slug: str
    plano_id: uuid.UUID
    plano_nome: str
    status_assinatura: str
    mensagem: str


# ==============================================================================
# HELPERS DE MINIMIZAÇÃO DE DADOS (LGPD) E AUDITORIA
# ==============================================================================

def mascarar_cpf(cpf: str | None) -> str | None:
    """Mascara CPF preservando apenas dígitos centrais para conferência (ex: ***.***.789-**).

    Aplica o princípio de menor privilégio e minimização de dados pessoais (LGPD).
    """
    if not cpf:
        return None
    nums = re.sub(r"\D", "", str(cpf))
    if len(nums) != 11:
        return "***"
    return f"***.***.{nums[6:9]}-**"


def mascarar_telefone(telefone: str | None) -> str | None:
    """Mascara telefone preservando DDD e dígitos finais (ex: (11) *****-1234).

    Aplica o princípio de menor privilégio e minimização de dados pessoais (LGPD).
    """
    if not telefone:
        return None
    nums = re.sub(r"\D", "", str(telefone))
    if len(nums) == 11:
        return f"({nums[:2]}) *****-{nums[7:]}"
    elif len(nums) == 10:
        return f"({nums[:2]}) ****-{nums[6:]}"
    elif len(nums) >= 4:
        return f"***-{nums[-4:]}"
    return "***"


def _extrair_admin_identity(claims_or_user: Any) -> tuple[uuid.UUID, str]:
    """Extrai UUID e e-mail do operador a partir dos claims JWT ou modelo de usuário.

    Args:
        claims_or_user: Dicionário de claims ou objeto de usuário autenticado.

    Returns:
        Tupla contendo (admin_uid, admin_email).
    """
    if isinstance(claims_or_user, dict):
        admin_sub = claims_or_user.get("sub") or claims_or_user.get("id")
        admin_email = claims_or_user.get("email") or claims_or_user.get("username") or "operador@deepfarms.com"
    else:
        admin_sub = getattr(claims_or_user, "id", None)
        admin_email = getattr(claims_or_user, "email", None) or getattr(claims_or_user, "username", "operador@deepfarms.com")
    try:
        admin_uid = uuid.UUID(str(admin_sub))
    except (ValueError, TypeError):
        admin_uid = uuid.uuid4()
    return admin_uid, str(admin_email)


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@router.get(
    "/usuarios",
    response_model=AgroUserListResponse,
    dependencies=[Depends(require_permission("backoffice:agro:view"))],
)
async def listar_produtores_agro(
    page: int = Query(1, ge=1, description="Número da página atual"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    search: str | None = Query(None, description="Busca por nome, e-mail, username ou CPF"),
    status: str | None = Query("all", description="Filtro: all, ativo, bloqueado"),
    has_byok: bool | None = Query(None, description="Filtrar produtores com chaves BYOK"),
    session: AsyncSession = Depends(get_session),
) -> AgroUserListResponse:
    """Lista produtores rurais gratuitos do DeepFarms Agro com paginação e busca.

    Args:
        page: Índice da página (base 1).
        page_size: Quantidade máxima de registros retornados.
        search: Termo opcional para busca textual.
        status: Situação cadastral ('all', 'ativo', 'bloqueado').
        has_byok: Booleano para filtrar por configuração de cotações BYOK.
        session: Sessão do SQLAlchemy assíncrono.

    Returns:
        Envelope paginado AgroUserListResponse.

    Raises:
        HTTPException: Se houver parâmetros inválidos ou falha de autorização.
    """
    subq_commercial = select(TenantUsuario.usuario_id).distinct()

    # Isola estritamente usuários individuais gratuitos
    base_stmt = select(Usuario).where(
        Usuario.is_superuser == False,
        Usuario.id.not_in(subq_commercial),
    )

    if search and search.strip():
        termo = f"%{search.strip().lower()}%"
        cpf_numeros = re.sub(r"\D", "", search.strip())
        condicoes = [
            func.lower(Usuario.nome_completo).like(termo),
            func.lower(Usuario.email).like(termo),
            func.lower(Usuario.username).like(termo),
        ]
        if cpf_numeros:
            condicoes.append(Usuario.cpf.like(f"%{cpf_numeros}%"))
        base_stmt = base_stmt.where(or_(*condicoes))

    if status and status.lower() == "ativo":
        base_stmt = base_stmt.where(Usuario.ativo == True)
    elif status and status.lower() == "bloqueado":
        base_stmt = base_stmt.where(Usuario.ativo == False)

    if has_byok is True:
        subq_byok = select(UsuarioByokCredential.usuario_id).distinct()
        base_stmt = base_stmt.where(Usuario.id.in_(subq_byok))
    elif has_byok is False:
        subq_byok = select(UsuarioByokCredential.usuario_id).distinct()
        base_stmt = base_stmt.where(Usuario.id.not_in(subq_byok))

    # Total geral para paginação
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_registros = (await session.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = base_stmt.order_by(Usuario.created_at.desc()).offset(offset).limit(page_size)
    usuarios = (await session.execute(stmt)).scalars().all()

    if not usuarios:
        return AgroUserListResponse(
            items=[],
            total=total_registros,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total_registros / page_size) if total_registros > 0 else 1,
        )

    user_ids = [u.id for u in usuarios]

    # Agregação em lote de sessões ativas
    stmt_sess = (
        select(
            SessaoAtiva.usuario_id,
            func.count(SessaoAtiva.id).label("total_ativas"),
            func.max(SessaoAtiva.ultimo_heartbeat).label("ultimo_acesso"),
        )
        .where(
            SessaoAtiva.usuario_id.in_(user_ids),
            SessaoAtiva.status == "ATIVA",
        )
        .group_by(SessaoAtiva.usuario_id)
    )
    sess_rows = (await session.execute(stmt_sess)).all()
    sess_map = {row.usuario_id: (row.total_ativas, row.ultimo_acesso) for row in sess_rows}

    # Agregação em lote de chaves BYOK
    stmt_byok = (
        select(
            UsuarioByokCredential.usuario_id,
            UsuarioByokCredential.provider_slug,
        )
        .where(UsuarioByokCredential.usuario_id.in_(user_ids))
    )
    byok_rows = (await session.execute(stmt_byok)).all()
    byok_map: dict[uuid.UUID, list[str]] = {uid: [] for uid in user_ids}
    for uid, prov in byok_rows:
        if prov not in byok_map[uid]:
            byok_map[uid].append(prov)

    items: list[AgroUserListItem] = []
    for u in usuarios:
        sess_info = sess_map.get(u.id, (0, None))
        provs = byok_map.get(u.id, [])
        items.append(
            AgroUserListItem(
                id=u.id,
                email=u.email,
                username=u.username,
                nome_completo=u.nome_completo,
                cpf=mascarar_cpf(u.cpf),
                telefone=mascarar_telefone(u.telefone),
                ativo=u.ativo,
                account_type="INDIVIDUAL_FREE",
                data_cadastro=u.created_at,
                ultimo_acesso=sess_info[1],
                sessoes_ativas_count=sess_info[0],
                byok_count=len(provs),
                byok_providers=provs,
            )
        )

    total_pages = math.ceil(total_registros / page_size) if total_registros > 0 else 1

    return AgroUserListResponse(
        items=items,
        total=total_registros,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/usuarios/{usuario_id}",
    response_model=AgroUserDetailResponse,
    dependencies=[Depends(require_permission("backoffice:agro:view"))],
)
async def obter_detalhes_produtor_agro(
    usuario_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> AgroUserDetailResponse:
    """Retorna detalhes cadastrais, metadados BYOK e sessões ativas do produtor.

    Args:
        usuario_id: Identificador único do usuário.
        session: Sessão assíncrona do SQLAlchemy.

    Returns:
        AgroUserDetailResponse com dados do usuário e relações operacionais.

    Raises:
        HTTPException: Se o usuário não existir (404).
    """
    user = await session.get(Usuario, usuario_id)
    if not user:
        raise HTTPException(status_code=404, detail="Produtor Agro não encontrado.")

    # Verifica o tipo de conta real
    subq_commercial = select(TenantUsuario.tenant_id).where(TenantUsuario.usuario_id == usuario_id)
    commercial_tenants = (await session.execute(subq_commercial)).scalars().all()

    if user.is_superuser:
        acc_type = "PLATFORM_ADMIN"
    elif commercial_tenants:
        acc_type = "COMMERCIAL"
    else:
        acc_type = "INDIVIDUAL_FREE"

    # Sessões ativas
    stmt_sess = (
        select(SessaoAtiva)
        .where(SessaoAtiva.usuario_id == usuario_id, SessaoAtiva.status == "ATIVA")
        .order_by(desc(SessaoAtiva.ultimo_heartbeat))
    )
    sessoes = (await session.execute(stmt_sess)).scalars().all()
    session_items = [AgroSessionItem.model_validate(s) for s in sessoes]

    # Metadados BYOK (estritamente omitindo ciphertext e segredos)
    stmt_byok = (
        select(UsuarioByokCredential)
        .where(UsuarioByokCredential.usuario_id == usuario_id)
        .order_by(desc(UsuarioByokCredential.created_at))
    )
    byoks = (await session.execute(stmt_byok)).scalars().all()
    byok_items = [
        AgroByokMeta(
            id=b.id,
            provider_slug=b.provider_slug,
            mascara_chave=b.mascara_chave,
            key_version=b.key_version,
            status=b.status,
            ultimo_uso=b.ultimo_uso,
            created_at=b.created_at,
        )
        for b in byoks
    ]

    # Histórico recente de auditoria administrativa sobre este usuário
    stmt_audit = (
        select(AdminAuditLog)
        .where(
            AdminAuditLog.entidade == "usuario",
            AdminAuditLog.entidade_id == usuario_id,
        )
        .order_by(desc(AdminAuditLog.created_at))
        .limit(10)
    )
    audits = (await session.execute(stmt_audit)).scalars().all()
    audit_items = [AgroAuditLogItem.model_validate(a) for a in audits]

    return AgroUserDetailResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        nome_completo=user.nome_completo,
        cpf=mascarar_cpf(user.cpf),
        telefone=mascarar_telefone(user.telefone),
        apelido=user.apelido,
        foto_perfil_url=user.foto_perfil_url,
        ativo=user.ativo,
        account_type=acc_type,
        is_superuser=user.is_superuser,
        data_cadastro=user.created_at,
        updated_at=user.updated_at,
        sessoes_ativas=session_items,
        credenciais_byok=byok_items,
        acoes_auditoria=audit_items,
    )


@router.post(
    "/usuarios/{usuario_id}/toggle-status",
    response_model=ToggleStatusResponse,
)
async def alternar_status_produtor_agro(
    usuario_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict = Depends(require_permission("backoffice:agro:users")),
) -> ToggleStatusResponse:
    """Bloqueia ou desbloqueia um produtor Agro, revogando sessões se bloqueado.

    Args:
        usuario_id: Identificador do produtor a ser modificado.
        request: Objeto de requisição FastAPI para captura de IP e User-Agent.
        session: Sessão assíncrona do SQLAlchemy.
        admin_claims: Claims autorizados do operador autenticado.

    Returns:
        ToggleStatusResponse com o novo status e total de sessões encerradas.

    Raises:
        HTTPException: Se o usuário não existir (404) ou for superusuário (400).
    """
    user = await session.get(Usuario, usuario_id)
    if not user:
        raise HTTPException(status_code=404, detail="Produtor Agro não encontrado.")

    if user.is_superuser:
        raise HTTPException(
            status_code=400,
            detail="Operação negada: não é permitido bloquear superusuários pelo módulo Agro.",
        )

    anterior = user.ativo
    user.ativo = not user.ativo
    sessoes_encerradas = 0

    if not user.ativo:
        stmt_revoke = (
            update(SessaoAtiva)
            .where(
                SessaoAtiva.usuario_id == usuario_id,
                SessaoAtiva.status == "ATIVA",
            )
            .values(status="ENCERRADA")
        )
        res_revoke = await session.execute(stmt_revoke)
        sessoes_encerradas = res_revoke.rowcount or 0

    admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)
    audit = AdminAuditLog(
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="AGRO_USUARIO_BLOQUEADO" if not user.ativo else "AGRO_USUARIO_DESBLOQUEADO",
        entidade="usuario",
        entidade_id=user.id,
        descricao=(
            f"Produtor Agro {user.email} {'bloqueado' if not user.ativo else 'desbloqueado'} "
            f"pelo operador {admin_email}. Sessões encerradas: {sessoes_encerradas}."
        ),
        dados_anteriores={"ativo": anterior},
        dados_novos={"ativo": user.ativo, "sessoes_encerradas": sessoes_encerradas},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(audit)
    await session.commit()

    acao_str = "bloqueado" if not user.ativo else "desbloqueado"
    return ToggleStatusResponse(
        id=user.id,
        novo_status=user.ativo,
        sessoes_encerradas=sessoes_encerradas,
        mensagem=f"Produtor Agro {acao_str} com sucesso.",
    )


@router.delete(
    "/usuarios/{usuario_id}/sessions",
    response_model=RevokeSessionsResponse,
)
async def revogar_sessoes_produtor_agro(
    usuario_id: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict = Depends(require_permission("backoffice:agro:users")),
) -> RevokeSessionsResponse:
    """Encerra todas as sessões ativas de um produtor sem alterar o status da conta.

    Args:
        usuario_id: Identificador do produtor.
        request: Objeto de requisição para auditoria.
        session: Sessão assíncrona do SQLAlchemy.
        admin_claims: Claims autorizados do operador.

    Returns:
        RevokeSessionsResponse com o total de sessões revogadas.

    Raises:
        HTTPException: Se o usuário não existir (404).
    """
    user = await session.get(Usuario, usuario_id)
    if not user:
        raise HTTPException(status_code=404, detail="Produtor Agro não encontrado.")

    stmt_revoke = (
        update(SessaoAtiva)
        .where(
            SessaoAtiva.usuario_id == usuario_id,
            SessaoAtiva.status == "ATIVA",
        )
        .values(status="ENCERRADA")
    )
    res_revoke = await session.execute(stmt_revoke)
    sessoes_encerradas = res_revoke.rowcount or 0

    admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)
    audit = AdminAuditLog(
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="AGRO_USUARIO_SESSOES_REVOGADAS",
        entidade="usuario",
        entidade_id=user.id,
        descricao=f"Revogadas {sessoes_encerradas} sessões ativas do produtor Agro {user.email}.",
        dados_anteriores={"sessoes_ativas": sessoes_encerradas},
        dados_novos={"status_sessoes": "ENCERRADA"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(audit)
    await session.commit()

    return RevokeSessionsResponse(
        id=user.id,
        sessoes_encerradas=sessoes_encerradas,
        mensagem=f"{sessoes_encerradas} sessão(ões) revogada(s) com sucesso.",
    )


@router.get(
    "/planos",
    response_model=list[AgroPlanoOption],
    dependencies=[Depends(require_permission("backoffice:agro:view"))],
)
async def listar_planos_para_conversao(
    session: AsyncSession = Depends(get_session),
) -> list[AgroPlanoOption]:
    """Lista planos comerciais ativos disponíveis para promoção de produtores Agro.

    Args:
        session: Sessão assíncrona do SQLAlchemy.

    Returns:
        Lista com as opções de planos comerciais.
    """
    stmt = (
        select(PlanoAssinatura)
        .where(PlanoAssinatura.ativo == True, PlanoAssinatura.is_free == False)
        .order_by(PlanoAssinatura.ordem.asc(), PlanoAssinatura.preco_mensal.asc())
    )
    planos = (await session.execute(stmt)).scalars().all()
    return [
        AgroPlanoOption(
            id=p.id,
            nome=p.nome,
            preco_mensal=float(p.preco_mensal or 0),
            preco_anual=float(p.preco_anual or 0),
            tem_trial=bool(p.tem_trial),
            dias_trial=int(p.dias_trial or 15),
            plan_tier=str(p.plan_tier or "BASICO"),
        )
        for p in planos
    ]


@router.post(
    "/usuarios/{usuario_id}/converter-comercial",
    response_model=AgroConverterComercialResponse,
    status_code=status.HTTP_403_FORBIDDEN,
    dependencies=[Depends(require_permission("backoffice:agro:users"))],
)
async def converter_produtor_agro_em_comercial(
    usuario_id: uuid.UUID,
    payload: AgroConverterComercialRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: Any = Depends(require_permission("backoffice:agro:users")),
) -> AgroConverterComercialResponse:
    """Conversão de produtor desabilitada por diretriz de segurança (AGRO-ADMIN-01D2).

    Garante que nenhuma chamada crie Tenant, assinatura ou faturas sem homologação
    da esteira comercial canônica completa. O código anterior é preservado abaixo
    para posterior auditoria e homologação formal.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "A conversão comercial de produtores Agro via Backoffice está temporariamente "
            "desabilitada por diretriz de segurança e governança (AGRO-ADMIN-01D2). "
            "A funcionalidade aguarda homologação da esteira comercial completa (faturamento e faturas canônicas)."
        ),
    )

    # ==========================================================================
    # CÓDIGO ANTERIOR PRESERVADO PARA FUTURA REVISÃO / ESTEIRA COMERCIAL CANÔNICA
    # ==========================================================================
    user = await session.get(Usuario, usuario_id)
    if not user:
        raise HTTPException(status_code=404, detail="Produtor Agro não encontrado.")

    if user.is_superuser:
        raise HTTPException(
            status_code=400,
            detail="Operação negada: não é permitido converter superusuários da plataforma.",
        )

    stmt_plano = select(PlanoAssinatura).where(
        PlanoAssinatura.id == payload.plano_id,
        PlanoAssinatura.ativo == True,
    )
    plano = (await session.execute(stmt_plano)).scalar_one_or_none()
    if not plano:
        raise HTTPException(
            status_code=404,
            detail="Plano comercial selecionado não encontrado ou inativo.",
        )

    doc_normalizado = normalizar_documento_opcional(payload.documento or user.cpf)
    if doc_normalizado and not validar_cpf_ou_cnpj(doc_normalizado):
        raise HTTPException(
            status_code=400,
            detail="Documento CPF/CNPJ fornecido é inválido.",
        )

    nome_fazenda = payload.nome_fazenda.strip()
    if not nome_fazenda:
        raise HTTPException(
            status_code=400,
            detail="O nome da propriedade/fazenda é obrigatório para conversão.",
        )

    slug_base = _slugify_tenant_name(nome_fazenda)
    slug = slug_base
    suffix = 2
    while (
        await session.execute(select(Tenant.id).where(Tenant.slug == slug))
    ).scalar_one_or_none():
        slug = f"{slug_base}-{suffix}"
        suffix += 1

    agora = datetime.now(timezone.utc)

    # 1. Criação do Tenant
    tenant = Tenant(
        nome=nome_fazenda,
        documento=doc_normalizado,
        slug=slug,
        ativo=True,
    )
    session.add(tenant)
    await session.flush()

    # 2. Vínculo como Owner do Tenant comercial
    tu = TenantUsuario(
        tenant_id=tenant.id,
        usuario_id=usuario_id,
        is_owner=True,
        status="ATIVO",
    )
    session.add(tu)

    # 3. Provisionamento da Assinatura
    is_trial = not plano.is_free and plano.tem_trial
    if plano.is_free:
        status_assin = "ATIVA"
        trial_expira_em = None
    else:
        status_assin = "TRIAL" if is_trial else "ATIVA"
        trial_expira_em = agora + timedelta(days=plano.dias_trial) if is_trial else None

    assin = AssinaturaTenant(
        tenant_id=tenant.id,
        plano_id=plano.id,
        tipo_assinatura="TENANT",
        ciclo_pagamento=payload.ciclo.upper() if payload.ciclo else "MENSAL",
        status=status_assin,
        data_inicio=agora,
        data_proxima_renovacao=trial_expira_em,
        trial_expires_at=trial_expira_em,
    )
    session.add(assin)
    await session.flush()

    # 4. Auditoria Administrativa
    admin_uid, admin_email = await resolve_admin_identity(session, admin_claims)
    audit = AdminAuditLog(
        admin_user_id=admin_uid,
        admin_email=admin_email,
        acao="AGRO_USUARIO_CONVERTIDO_COMERCIAL",
        entidade="usuario",
        entidade_id=user.id,
        descricao=(
            f"Produtor Agro {user.email} promovido a cliente comercial na propriedade '{tenant.nome}' "
            f"com o plano '{plano.nome}'. Operador: {admin_email}."
        ),
        dados_anteriores={"account_type": "INDIVIDUAL_FREE"},
        dados_novos={
            "tenant_id": str(tenant.id),
            "tenant_nome": tenant.nome,
            "tenant_slug": tenant.slug,
            "plano_id": str(plano.id),
            "plano_nome": plano.nome,
            "status_assinatura": status_assin,
            "is_owner": True,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(audit)
    await session.commit()

    return AgroConverterComercialResponse(
        usuario_id=user.id,
        tenant_id=tenant.id,
        nome_tenant=tenant.nome,
        slug=tenant.slug,
        plano_id=plano.id,
        plano_nome=plano.nome,
        status_assinatura=status_assin,
        mensagem=f"Produtor promovido com sucesso para a propriedade comercial '{tenant.nome}'.",
    )
