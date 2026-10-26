"""Serviço utilitário para resolução de identidade administrativa e auditoria.

Garante que qualquer operador autenticado (seja via AdminUser nativo ou via
identidade global de Usuario com is_superuser) possua um admin_user_id válido
respeitando a restrição de integridade referencial 'admin_audit_log_admin_user_id_fkey'.
"""

import uuid
from typing import Any, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from datetime import datetime, timezone
from core.models.admin_audit_log import AdminAuditLog
from core.models.admin_user import AdminUser
from core.models.auth import Usuario


class AdminAuditService:
    """Serviço centralizado para emissão e persistência de logs de auditoria administrativa."""

    @classmethod
    async def log_action(
        cls,
        session: AsyncSession,
        admin_id: uuid.UUID,
        admin_email: str,
        acao: str,
        entidade: str,
        entidade_id: uuid.UUID | None = None,
        descricao: str | None = None,
        dados_anteriores: dict | None = None,
        dados_novos: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AdminAuditLog:
        """Cria e persiste uma entrada padronizada em admin_audit_log."""
        audit_entry = AdminAuditLog(
            id=uuid.uuid4(),
            admin_user_id=admin_id,
            admin_email=admin_email,
            acao=acao,
            entidade=entidade,
            entidade_id=entidade_id,
            descricao=descricao,
            dados_anteriores=dados_anteriores,
            dados_novos=dados_novos,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
        )
        session.add(audit_entry)
        await session.flush()
        return audit_entry


async def resolve_admin_identity(
    session: AsyncSession,
    claims_or_user: Any,
) -> tuple[uuid.UUID, str]:
    """Resolve o UUID e e-mail de um operador administrativo garantindo a chave estrangeira em admin_users.

    Busca preferencialmente pelo UUID em admin_users. Se o ID pertencer a um usuário global (tabela usuarios),
    localiza ou sincroniza o registro correspondente em admin_users para respeitar a integridade
    referencial de admin_audit_log.admin_user_id_fkey.

    Args:
        session: Sessão assíncrona do SQLAlchemy.
        claims_or_user: Claims do JWT (dict) ou modelo de usuário autenticado.

    Returns:
        Tupla contendo (admin_user_id válido em admin_users, admin_email).
    """
    admin_sub = None
    admin_email = None

    if isinstance(claims_or_user, dict):
        admin_sub = claims_or_user.get("sub") or claims_or_user.get("id")
        admin_email = claims_or_user.get("email") or claims_or_user.get("username")
    else:
        admin_sub = getattr(claims_or_user, "id", None)
        admin_email = getattr(claims_or_user, "email", None) or getattr(claims_or_user, "username", None)

    sub_uuid: Optional[uuid.UUID] = None
    if admin_sub:
        try:
            sub_uuid = uuid.UUID(str(admin_sub))
        except (ValueError, TypeError):
            sub_uuid = None

    try:
        # 1. Se sub_uuid já é um AdminUser existente no banco, retorna imediatamente
        if sub_uuid:
            row = (await session.execute(
                select(AdminUser.id, AdminUser.email).where(AdminUser.id == sub_uuid)
            )).first()
            if row:
                return row[0], row[1] or admin_email or "admin@deepfarms.com"

        # 2. Se não encontrou por ID, descobre o e-mail via tabela usuarios se necessário
        if not admin_email and sub_uuid:
            u_row = (await session.execute(
                select(Usuario.email).where(Usuario.id == sub_uuid)
            )).first()
            if u_row and u_row[0]:
                admin_email = u_row[0]

        # 3. Com o e-mail em mãos, busca se existe um AdminUser com esse e-mail
        if admin_email:
            normalized_email = str(admin_email).strip().lower()
            a_row = (await session.execute(
                select(AdminUser.id, AdminUser.email).where(func.lower(AdminUser.email) == normalized_email)
            )).first()
            if a_row:
                return a_row[0], a_row[1]

            # 4. Se o e-mail é de um usuário válido (ex: superuser em usuarios), provisiona o AdminUser
            # para garantir a integridade referencial com admin_audit_log
            try:
                async with session.begin_nested():
                    new_admin = AdminUser(
                        id=sub_uuid or uuid.uuid4(),
                        email=normalized_email,
                        nome=normalized_email.split("@")[0],
                        senha_hash="LINKED_TO_USUARIO",
                        role="super_admin" if (isinstance(claims_or_user, dict) and claims_or_user.get("is_superuser")) else "admin",
                        ativo=True,
                    )
                    session.add(new_admin)
                    await session.flush()
                    return new_admin.id, new_admin.email
            except Exception as exc:
                logger.warning(f"Não foi possível provisionar AdminUser para {normalized_email}: {exc}")
                a_row = (await session.execute(
                    select(AdminUser.id, AdminUser.email).where(func.lower(AdminUser.email) == normalized_email)
                )).first()
                if a_row:
                    return a_row[0], a_row[1]

        # 5. Fallback para o primeiro AdminUser ativo existente no sistema (ex: admin raiz)
        root_admin = (await session.execute(
            select(AdminUser.id, AdminUser.email).where(AdminUser.ativo == True).limit(1)
        )).first()
        if root_admin:
            return root_admin[0], admin_email or root_admin[1]

        # 6. Se a tabela admin_users estiver completamente vazia (ex: ambiente de teste sem seed), cria um admin padrão
        try:
            async with session.begin_nested():
                default_admin = AdminUser(
                    id=sub_uuid or uuid.uuid4(),
                    email=admin_email or "admin@deepfarms.com",
                    nome="Administrador do Sistema",
                    senha_hash="SYSTEM_GENERATED",
                    role="super_admin",
                    ativo=True,
                )
                session.add(default_admin)
                await session.flush()
                return default_admin.id, default_admin.email
        except Exception:
            fallback = (await session.execute(select(AdminUser.id, AdminUser.email).limit(1))).first()
            if fallback:
                return fallback[0], admin_email or fallback[1]

    except Exception as exc:
        logger.warning(f"Fallback gracioso em resolve_admin_identity: {exc}")
        return sub_uuid or uuid.uuid4(), admin_email or "admin@deepfarms.com"

    return sub_uuid or uuid.uuid4(), admin_email or "admin@deepfarms.com"
