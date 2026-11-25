"""Serviço de governança do modo Demonstração (Somente Consulta, CRM e Prorrogação)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import logging
import secrets
import unicodedata
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import (
    DEMO_PROFILE_NAME,
    DEMO_READ_ONLY_PERMISSIONS,
    DEMO_TENANT_CANONICAL_NAME,
)
from core.models.admin_audit_log import AdminAuditLog
from core.models.auth import ConviteAcesso, PerfilAcesso, TenantUsuario, Usuario
from core.models.crm import AtividadeCRM, LeadCRM, PipelineEstagio
from core.models.support import ChamadoSuporte, MensagemChamado, TicketStatus
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
from core.services.demo_config_service import get_demo_saas_config
from core.services.email_service import email_service

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DemoLeadSyncInput:
    """Dados do usuário convidado para sincronização no CRM comercial."""

    email: str
    nome: str
    telefone: str | None = None
    empresa: str | None = None
    data_validade_acesso: date | None = None
    tenant_id: uuid.UUID | None = None


@dataclass(slots=True)
class DemoExtensionApprovalInput:
    """Parâmetros auditados para aprovação de prorrogação de acesso de demonstração."""

    ticket_id: uuid.UUID
    admin_id: uuid.UUID
    admin_email: str
    dias: int | None = None
    observacao: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


def _normalize_ascii_lower(value: str | None) -> str:
    """Normaliza string removendo acentos e espaços excedentes em minúsculas."""
    if not value:
        return ""
    raw = unicodedata.normalize("NFKD", str(value).strip())
    return raw.encode("ascii", "ignore").decode("ascii").lower()


def is_demo_tenant(tenant: Tenant | None) -> bool:
    """
    Indica se um tenant é o ambiente oficial de demonstração.

    Args:
        tenant: Instância de Tenant ou None.

    Return:
        True quando marcado com is_demo ou com nome canônico 'Produtor DeepFarms'.

    Raises:
        Nenhuma exceção é lançada.
    """
    if tenant is None:
        return False
    if bool(getattr(tenant, "is_demo", False)):
        return True
    return _normalize_ascii_lower(getattr(tenant, "nome", None)) == _normalize_ascii_lower(
        DEMO_TENANT_CANONICAL_NAME
    )


def is_read_only_profile(perfil: PerfilAcesso | None) -> bool:
    """
    Verifica se o perfil de acesso impõe modo estrito somente consulta.

    Args:
        perfil: Instância de PerfilAcesso ou None.

    Return:
        True quando is_read_only, is_demo_profile ou nome normalizado 'demonstracao'.

    Raises:
        Nenhuma exceção é lançada.
    """
    if perfil is None:
        return False
    if bool(getattr(perfil, "is_read_only", False)) or bool(
        getattr(perfil, "is_demo_profile", False)
    ):
        return True
    return _normalize_ascii_lower(getattr(perfil, "nome", None)) == "demonstracao"


async def ensure_demo_profile(session: AsyncSession) -> PerfilAcesso:
    """
    Obtém ou cria de forma idempotente o perfil global 'Demonstração'.

    Args:
        session: Sessão assíncrona ativa do SQLAlchemy.

    Return:
        Registro global de PerfilAcesso com flags read-only e permissões somente consulta.

    Raises:
        SQLAlchemyError: Em caso de falha de persistência.
    """
    stmt = select(PerfilAcesso).where(PerfilAcesso.tenant_id.is_(None))
    globais = (await session.execute(stmt)).scalars().all()
    for perfil in globais:
        if bool(getattr(perfil, "is_demo_profile", False)) or (
            _normalize_ascii_lower(perfil.nome) == "demonstracao"
        ):
            perfil.is_read_only = True
            perfil.is_demo_profile = True
            if not perfil.permissoes or not isinstance(perfil.permissoes.get("granted"), list):
                perfil.permissoes = {"granted": list(DEMO_READ_ONLY_PERMISSIONS)}
            return perfil

    perfil = PerfilAcesso(
        id=uuid.uuid4(),
        tenant_id=None,
        nome=DEMO_PROFILE_NAME,
        descricao="Visitante de demonstração (somente consulta, sem gravação ou alteração)",
        is_custom=False,
        is_read_only=True,
        is_demo_profile=True,
        permissoes={"granted": list(DEMO_READ_ONLY_PERMISSIONS)},
    )
    session.add(perfil)
    await session.flush()
    return perfil


async def ensure_demo_crm_stage(
    session: AsyncSession,
    stage_name: str | None = None,
) -> PipelineEstagio:
    """
    Obtém ou cria de forma idempotente o estágio de demonstração no pipeline CRM.

    Args:
        session: Sessão assíncrona ativa do SQLAlchemy.
        stage_name: Nome desejado do estágio; quando omitido usa `configuracoes_saas`.

    Return:
        Estágio PipelineEstagio correspondente ao ambiente de demonstração.

    Raises:
        SQLAlchemyError: Em caso de falha de persistência.
    """
    target_name = stage_name or (await get_demo_saas_config(session)).estagio_crm_nome
    target_norm = _normalize_ascii_lower(target_name)
    estagios = (
        await session.execute(select(PipelineEstagio).order_by(PipelineEstagio.ordem))
    ).scalars().all()
    for estagio in estagios:
        if _normalize_ascii_lower(estagio.nome) == target_norm:
            return estagio

    max_ordem = max((e.ordem for e in estagios), default=-1)
    novo = PipelineEstagio(
        id=uuid.uuid4(),
        nome=target_name,
        cor="#0ea5e9",
        ordem=max_ordem + 1,
        ativo=True,
    )
    session.add(novo)
    await session.flush()
    return novo


async def sync_demo_lead_to_crm(
    session: AsyncSession,
    payload: DemoLeadSyncInput,
) -> LeadCRM:
    """
    Cria ou atualiza lead comercial no estágio 'Demonstração' de forma idempotente por e-mail.

    Args:
        session: Sessão assíncrona ativa do SQLAlchemy.
        payload: Dados do usuário recém-cadastrado ou aceito no convite demo.

    Return:
        Instância de LeadCRM posicionada no estágio 'Demonstração'.

    Raises:
        SQLAlchemyError: Em caso de falha ao gravar lead ou atividade.
    """
    estagio = await ensure_demo_crm_stage(session)
    email_norm = payload.email.strip().lower()
    validade_str = (
        payload.data_validade_acesso.strftime("%d/%m/%Y")
        if payload.data_validade_acesso
        else "15 dias"
    )

    stmt = (
        select(LeadCRM)
        .where(func.lower(LeadCRM.email) == email_norm)
        .order_by(LeadCRM.created_at.desc())
        .limit(1)
    )
    lead = (await session.execute(stmt)).scalar_one_or_none()

    if lead is None:
        lead = LeadCRM(
            id=uuid.uuid4(),
            nome=payload.nome.strip() or email_norm.split("@")[0],
            email=email_norm,
            telefone=payload.telefone.strip() if payload.telefone else None,
            empresa=payload.empresa.strip() if payload.empresa else None,
            estagio_id=estagio.id,
            origem="demonstracao",
            status="ativo",
            notas=f"Acesso de demonstração iniciado (validade até {validade_str}).",
            tags={"demo": True, "somente_consulta": True},
        )
        session.add(lead)
        await session.flush()
        descricao_atv = (
            f"Cadastro via convite de demonstração concluído. "
            f"Acesso válido até {validade_str}."
        )
    else:
        lead.estagio_id = estagio.id
        if payload.telefone and not lead.telefone:
            lead.telefone = payload.telefone.strip()
        if payload.empresa and not lead.empresa:
            lead.empresa = payload.empresa.strip()
        if lead.status == "perdido":
            lead.status = "ativo"
        tags = dict(lead.tags or {})
        tags["demo"] = True
        tags["somente_consulta"] = True
        lead.tags = tags
        descricao_atv = (
            f"Lead movido automaticamente para Demonstração após aceite do convite "
            f"(validade até {validade_str})."
        )

    atividade = AtividadeCRM(
        id=uuid.uuid4(),
        lead_id=lead.id,
        tipo="nota",
        descricao=descricao_atv,
        concluida=True,
    )
    session.add(atividade)
    await session.flush()
    return lead


async def approve_demo_extension(
    session: AsyncSession,
    payload: DemoExtensionApprovalInput,
) -> dict:
    """
    Prorroga a validade do usuário em demonstração a partir de um chamado de suporte e audita.

    Args:
        session: Sessão assíncrona ativa do SQLAlchemy.
        payload: Identificação do chamado, operador comercial/admin e dias de prorrogação.

    Return:
        Dicionário com nova data de validade, contador de prorrogações e status do chamado.

    Raises:
        HTTPException: 404 se chamado ou vínculo não existirem; 400 se não for usuário de demo.
    """
    chamado = await session.get(ChamadoSuporte, payload.ticket_id)
    if not chamado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chamado indisponível ou não encontrado.",
        )

    row = (
        await session.execute(
            select(TenantUsuario, Tenant, PerfilAcesso, Usuario)
            .join(Tenant, Tenant.id == TenantUsuario.tenant_id)
            .join(Usuario, Usuario.id == TenantUsuario.usuario_id)
            .outerjoin(PerfilAcesso, PerfilAcesso.id == TenantUsuario.perfil_id)
            .where(
                TenantUsuario.tenant_id == chamado.tenant_id,
                TenantUsuario.usuario_id == chamado.usuario_abertura_id,
            )
        )
    ).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vínculo do usuário solicitante no tenant não encontrado.",
        )

    tu, tenant, perfil, usuario = row
    if tu.is_owner or not (is_demo_tenant(tenant) or is_read_only_profile(perfil)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este chamado não pertence a um usuário em período de demonstração.",
        )

    hoje = date.today()
    dias_adicionados = (
        payload.dias
        if payload.dias is not None
        else (await get_demo_saas_config(session)).dias_prorrogacao_padrao
    )
    validade_anterior = tu.data_validade_acesso
    base_data = max(hoje, validade_anterior) if validade_anterior else hoje
    nova_validade = base_data + timedelta(days=dias_adicionados)

    prorrogacoes_anteriores = int(getattr(tu, "demo_prorrogacoes_count", 0) or 0)
    tu.data_validade_acesso = nova_validade
    tu.demo_prorrogacoes_count = prorrogacoes_anteriores + 1
    if tu.status != "ATIVO":
        tu.status = "ATIVO"

    agora = datetime.now(timezone.utc)
    obs = f"\nObservação comercial: {payload.observacao.strip()}" if payload.observacao else ""
    msg = MensagemChamado(
        chamado_id=chamado.id,
        usuario_id=payload.admin_id,
        conteudo=(
            f"Prorrogação aprovada! Seu acesso ao ambiente de demonstração foi estendido por "
            f"mais {dias_adicionados} dias corridos (válido até {nova_validade.strftime('%d/%m/%Y')}).{obs}"
        ),
        is_admin_reply=True,
    )
    session.add(msg)

    chamado.status = TicketStatus.CONCLUIDO
    chamado.atendente_id = payload.admin_id
    chamado.data_resolucao = agora
    if not chamado.data_primeira_resposta:
        chamado.data_primeira_resposta = agora

    audit = AdminAuditLog(
        id=uuid.uuid4(),
        admin_user_id=payload.admin_id,
        admin_email=payload.admin_email,
        acao="DEMO_ACCESS_EXTENDED",
        entidade="tenant_usuario",
        entidade_id=tu.id,
        descricao=(
            f"Prorrogação de +{dias_adicionados} dias aprovada para {usuario.email} no tenant "
            f"'{tenant.nome}' (chamado {chamado.id})."
        ),
        dados_anteriores={
            "data_validade_acesso": validade_anterior.isoformat() if validade_anterior else None,
            "demo_prorrogacoes_count": prorrogacoes_anteriores,
        },
        dados_novos={
            "data_validade_acesso": nova_validade.isoformat(),
            "demo_prorrogacoes_count": tu.demo_prorrogacoes_count,
            "dias_adicionados": dias_adicionados,
            "ticket_id": str(chamado.id),
            "observacao": payload.observacao,
        },
        ip_address=payload.ip_address,
        user_agent=payload.user_agent,
        created_at=agora,
    )
    session.add(audit)

    # Atualiza trilha do lead no CRM caso exista para este e-mail
    lead = (
        await session.execute(
            select(LeadCRM)
            .where(func.lower(LeadCRM.email) == usuario.email.strip().lower())
            .order_by(LeadCRM.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if lead is not None:
        session.add(
            AtividadeCRM(
                id=uuid.uuid4(),
                lead_id=lead.id,
                tipo="nota",
                descricao=(
                    f"Prorrogação #{tu.demo_prorrogacoes_count} (+{dias_adicionados} dias) aprovada "
                    f"por {payload.admin_email}. Novo vencimento: {nova_validade.strftime('%d/%m/%Y')}."
                ),
                admin_user_id=payload.admin_id,
                admin_email=payload.admin_email,
                concluida=True,
            )
        )

    await session.commit()
    return {
        "sucesso": True,
        "ticket_id": str(chamado.id),
        "usuario_id": str(usuario.id),
        "usuario_email": usuario.email,
        "data_validade_acesso": nova_validade.isoformat(),
        "demo_prorrogacoes_count": tu.demo_prorrogacoes_count,
    }


@dataclass(slots=True)
class DemoRequestInput:
    """Dados informados pelo visitante na landing page para acesso à demonstração."""

    nome: str
    email: str
    telefone: str | None = None
    empresa: str | None = None


@dataclass(slots=True)
class DemoRequestResult:
    """Resultado do processamento de solicitação pública de demonstração."""

    ja_cadastrado: bool
    ja_vinculado_demo: bool
    convite_reenviado: bool
    dias_acesso: int
    mensagem: str


async def resolve_demo_tenant(session: AsyncSession) -> Tenant:
    """
    Resolve o tenant oficial de demonstração configurado na plataforma.

    Args:
        session: Sessão assíncrona ativa do SQLAlchemy.

    Return:
        Instância de Tenant configurada como ambiente de demonstração.

    Raises:
        HTTPException: 503 quando nenhum tenant de demonstração estiver disponível.
    """
    demo_cfg = await get_demo_saas_config(session)
    if demo_cfg.tenant_id:
        tenant = await session.get(Tenant, uuid.UUID(demo_cfg.tenant_id))
        if tenant and tenant.ativo:
            return tenant

    demo_tenant = (
        await session.execute(select(Tenant).where(Tenant.is_demo.is_(True), Tenant.ativo.is_(True)).limit(1))
    ).scalar_one_or_none()
    if demo_tenant:
        return demo_tenant

    canonical = _normalize_ascii_lower(DEMO_TENANT_CANONICAL_NAME)
    ativos = (await session.execute(select(Tenant).where(Tenant.ativo.is_(True)))).scalars().all()
    for tenant in ativos:
        if _normalize_ascii_lower(tenant.nome) == canonical:
            return tenant

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Ambiente de demonstração indisponível no momento.",
    )


async def _get_or_create_demo_invite(
    session: AsyncSession,
    tenant: Tenant,
    email_norm: str,
) -> tuple[ConviteAcesso, PerfilAcesso, bool]:
    """
    Obtém um convite pendente reutilizável ou cria novo convite para o tenant de demonstração.

    Args:
        session: Sessão assíncrona ativa do SQLAlchemy.
        tenant: Tenant de demonstração de destino.
        email_norm: E-mail normalizado em minúsculas.

    Return:
        Tupla `(convite, perfil_demo, convite_reenviado)`.

    Raises:
        SQLAlchemyError: Em falha de consulta ou persistência.
    """
    perfil = await ensure_demo_profile(session)
    fazendas_ids = [
        str(fid)
        for fid in (
            await session.execute(
                select(Fazenda.id).where(Fazenda.tenant_id == tenant.id, Fazenda.ativo.is_(True))
            )
        ).scalars().all()
    ]
    agora = datetime.now(timezone.utc)
    nova_expiracao = agora + timedelta(days=7)

    existente = (
        await session.execute(
            select(ConviteAcesso)
            .where(
                ConviteAcesso.tenant_id == tenant.id,
                func.lower(ConviteAcesso.email_convidado) == email_norm,
                ConviteAcesso.status == "PENDENTE",
            )
            .order_by(ConviteAcesso.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if existente:
        exp = (
            existente.data_expiracao.replace(tzinfo=timezone.utc)
            if existente.data_expiracao.tzinfo is None
            else existente.data_expiracao
        )
        if exp >= agora:
            existente.data_expiracao = nova_expiracao
            existente.perfil_id = perfil.id
            existente.unidades_produtivas_ids = fazendas_ids
            return existente, perfil, True
        existente.status = "EXPIRADO"

    convite = ConviteAcesso(
        tenant_id=tenant.id,
        email_convidado=email_norm,
        perfil_id=perfil.id,
        unidades_produtivas_ids=fazendas_ids,
        token_convite=secrets.token_urlsafe(32),
        status="PENDENTE",
        data_expiracao=nova_expiracao,
        data_validade_acesso=None,
    )
    session.add(convite)
    await session.flush()
    return convite, perfil, False


async def _send_demo_invite_email(
    email_norm: str,
    tenant: Tenant,
    perfil_nome: str,
    token: str,
) -> None:
    """Dispara o e-mail de convite/confirmação da demonstração sem propagar falhas SMTP."""
    try:
        await email_service.send_invite(
            email=email_norm,
            remetente="Equipe DeepFarms",
            tenant_nome=tenant.nome,
            perfil_nome=perfil_nome,
            token=token,
            tenant_id=tenant.id,
        )
    except Exception:
        logger.warning("Falha ao enviar e-mail de demonstração para o tenant %s.", tenant.id)


async def solicitar_acesso_demonstracao(
    session: AsyncSession,
    payload: DemoRequestInput,
) -> DemoRequestResult:
    """
    Processa solicitação pública de acesso à demonstração pela landing page.

    Args:
        session: Sessão assíncrona ativa do SQLAlchemy.
        payload: Dados informados pelo visitante (nome, e-mail, telefone e empresa opcionais).

    Return:
        `DemoRequestResult` indicando se o usuário já possui conta, vínculo e orientação.

    Raises:
        HTTPException: 503 se o ambiente de demonstração não estiver configurado.
    """
    tenant = await resolve_demo_tenant(session)
    demo_cfg = await get_demo_saas_config(session)
    email_norm = payload.email.strip().lower()

    usuario = (
        await session.execute(select(Usuario).where(func.lower(Usuario.email) == email_norm))
    ).scalar_one_or_none()
    ja_cadastrado = usuario is not None

    ja_vinculado_demo = False
    if usuario is not None:
        vinculo = (
            await session.execute(
                select(TenantUsuario.id).where(
                    TenantUsuario.tenant_id == tenant.id,
                    TenantUsuario.usuario_id == usuario.id,
                )
            )
        ).scalar_one_or_none()
        ja_vinculado_demo = vinculo is not None

    validade_prevista = date.today() + timedelta(days=demo_cfg.duracao_inicial_dias)
    await sync_demo_lead_to_crm(
        session,
        DemoLeadSyncInput(
            email=email_norm,
            nome=payload.nome.strip(),
            telefone=payload.telefone,
            empresa=payload.empresa,
            data_validade_acesso=validade_prevista,
            tenant_id=tenant.id,
        ),
    )

    if ja_vinculado_demo:
        await session.commit()
        return DemoRequestResult(
            ja_cadastrado=True,
            ja_vinculado_demo=True,
            convite_reenviado=False,
            dias_acesso=demo_cfg.duracao_inicial_dias,
            mensagem=(
                "Você já está cadastrado na plataforma e já possui acesso ao ambiente de "
                "demonstração. Faça login com seu e-mail e senha para entrar."
            ),
        )

    convite, perfil, reenviado = await _get_or_create_demo_invite(session, tenant, email_norm)
    await session.commit()
    await _send_demo_invite_email(email_norm, tenant, perfil.nome, convite.token_convite)

    # TODO(security): Mensagem diferenciada para usuários já cadastrados é requisito explícito
    # de produto; o risco de enumeração de e-mail é mitigado por DemoRequestRateLimiter (5 req/15min por IP).
    if ja_cadastrado:
        mensagem = (
            "Você já está cadastrado na plataforma. Enviamos um e-mail de confirmação "
            "para liberar seu acesso ao ambiente de demonstração."
        )
    else:
        mensagem = (
            f"Enviamos um e-mail com o link para concluir seu cadastro e acessar o "
            f"ambiente de demonstração por {demo_cfg.duracao_inicial_dias} dias."
        )

    return DemoRequestResult(
        ja_cadastrado=ja_cadastrado,
        ja_vinculado_demo=False,
        convite_reenviado=reenviado,
        dias_acesso=demo_cfg.duracao_inicial_dias,
        mensagem=mensagem,
    )
