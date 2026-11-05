"""Serviço de Impersonação de Tenant (Acesso Assistido para Administradores e Suporte).

Permite que operadores de Backoffice acessem o contexto de um tenant como se fossem o
proprietário (owner) sem consumir licenças simultâneas do cliente, com suporte a modo
Somente Leitura (Inspeção) e Modo Edição (Operação), devidamente auditado.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from fastapi import HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.models.admin_audit_log import AdminAuditLog
from core.models.admin_impersonation import AdminImpersonation
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.models.tenant import Tenant
from core.models.unidade_produtiva import UnidadeProdutiva as Fazenda
from core.services.admin_audit_service import resolve_admin_identity
from core.services.auth_service import AuthService

ImpersonationMode = Literal["READ_ONLY", "READ_WRITE"]


class ImpersonationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def start_impersonation(
        self,
        admin_claims: dict[str, Any],
        tenant_id: uuid.UUID,
        modo: ImpersonationMode = "READ_ONLY",
        motivo: str = "Atendimento de suporte técnico",
        categoria: str = "SUPORTE",
        unidade_produtiva_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Inicia uma sessão de impersonação de tenant e retorna o JWT temporário."""
        admin_uid, admin_email = await resolve_admin_identity(self.session, admin_claims)
        backoffice_role = admin_claims.get("backoffice_role") or admin_claims.get("role") or "admin"

        # 1. Validar existência e estado do Tenant
        tenant = await self.session.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant não encontrado.",
            )
        if not tenant.ativo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível impersonar um tenant inativo ou bloqueado.",
            )

        # 2. Obter plano, módulos contratados e limites reais do tenant
        plan_stmt = (
            select(
                PlanoAssinatura.modulos_inclusos,
                PlanoAssinatura.plan_tier,
                PlanoAssinatura.max_fazendas,
                AssinaturaTenant.usuarios_contratados,
            )
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant.id,
                AssinaturaTenant.status.in_(["ATIVA", "TRIAL", "PENDENTE_PAGAMENTO"]),
            )
            .order_by(AssinaturaTenant.created_at.desc())
        )
        plan_rows = (await self.session.execute(plan_stmt)).all()
        if plan_rows:
            tenant_modules = list({m for r in plan_rows if r[0] for m in r[0]})
            tenant_tier = plan_rows[0][1] or "BASICO"
            tenant_max_fazendas = max((r[2] or 1) for r in plan_rows)
            tenant_max_usuarios = max((r[3] or 2) for r in plan_rows)
        else:
            tenant_modules = ["CORE"]
            tenant_tier = "BASICO"
            tenant_max_fazendas = 1
            tenant_max_usuarios = 2

        # 3. Obter unidades produtivas do tenant
        faz_stmt = select(Fazenda.id, Fazenda.nome).where(
            Fazenda.tenant_id == tenant.id,
            Fazenda.ativo == True,
        )
        faz_rows = (await self.session.execute(faz_stmt)).all()
        all_fazendas = [{"id": str(r[0]), "nome": r[1]} for r in faz_rows]

        # Validar fazenda específica se fornecida
        if unidade_produtiva_id:
            if not any(f["id"] == str(unidade_produtiva_id) for f in all_fazendas):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A fazenda informada não pertence ao tenant selecionado.",
                )

        agora = datetime.now(timezone.utc)

        # 4. Registrar a impersonação no banco
        impersonation = AdminImpersonation(
            id=uuid.uuid4(),
            admin_user_id=admin_uid,
            tenant_id=tenant.id,
            unidade_produtiva_id=unidade_produtiva_id,
            motivo=motivo,
            categoria=categoria,
            inicio=agora,
            fim=None,
            ip_address=ip_address,
            user_agent=user_agent,
            acoes_realizadas=[{
                "timestamp": agora.isoformat(),
                "acao": "IMPERSONATION_STARTED",
                "modo": modo,
                "motivo": motivo,
            }],
            meta_info={
                "impersonation_mode": modo,
                "categoria": categoria,
                "admin_email": admin_email,
                "backoffice_role": backoffice_role,
            },
        )
        self.session.add(impersonation)

        # 5. Registrar no log de auditoria do Backoffice
        audit_log = AdminAuditLog(
            id=uuid.uuid4(),
            admin_user_id=admin_uid,
            admin_email=admin_email,
            acao="TENANT_IMPERSONATION_START",
            entidade="tenant",
            entidade_id=tenant.id,
            descricao=f"Operador iniciou acesso assistido ao tenant '{tenant.nome}' em modo {modo}. Motivo: {motivo}",
            dados_novos={
                "impersonation_id": str(impersonation.id),
                "modo": modo,
                "motivo": motivo,
                "categoria": categoria,
                "unidade_produtiva_id": str(unidade_produtiva_id) if unidade_produtiva_id else None,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=agora,
        )
        self.session.add(audit_log)
        await self.session.commit()

        # 6. Gerar o Token de Impersonação com Claims específicas
        auth_service = AuthService(self.session)
        expires_delta = timedelta(minutes=60)

        tenant_contexts = [{
            "id": str(tenant.id),
            "nome": tenant.nome,
            "modules": tenant_modules,
            "plan_tier": tenant_tier,
            "max_fazendas": tenant_max_fazendas,
            "max_usuarios": tenant_max_usuarios,
            "fazendas": all_fazendas,
        }]

        fazendas_auth = [{"id": f["id"], "role": "owner"} for f in all_fazendas]

        claims = {
            "sub": str(admin_claims.get("sub") or admin_uid),
            "tenant_id": str(tenant.id),
            "role": "owner",
            "modules": tenant_modules,
            "fazendas_auth": fazendas_auth,
            "tenant_contexts": tenant_contexts,
            "is_superuser": False,  # Isola a experiência para respeitar os módulos do assinante
            "plan_tier": tenant_tier,
            "session_required": False,  # Não consome licença simultânea do assinante
            "impersonating": True,
            "impersonation_id": str(impersonation.id),
            "impersonation_mode": modo,
            "impersonator_id": str(admin_uid),
            "impersonator_email": admin_email,
            "backoffice_role": backoffice_role,
            "account_type": "COMMERCIAL",
            "product_scope": ["saas", "agro:free", "backoffice"],
        }

        access_token = auth_service.create_access_token(data=claims, expires_delta=expires_delta)

        logger.info(
            f"Impersonação iniciada: admin={admin_email} tenant={tenant.nome} modo={modo} imp_id={impersonation.id}"
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "impersonation_id": str(impersonation.id),
            "modo": modo,
            "tenant": {
                "id": str(tenant.id),
                "nome": tenant.nome,
                "documento": tenant.documento,
                "plan_tier": tenant_tier,
                "modulos": tenant_modules,
            },
            "fazendas": all_fazendas,
            "expira_em": (agora + expires_delta).isoformat(),
        }

    async def switch_mode(
        self,
        claims: dict[str, Any],
        impersonation_id: uuid.UUID,
        novo_modo: ImpersonationMode,
        motivo: str = "Alteração de modo operacional",
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Alterna o modo da sessão de impersonação entre READ_ONLY e READ_WRITE."""
        impersonation = await self.session.get(AdminImpersonation, impersonation_id)
        if not impersonation or impersonation.fim is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sessão de impersonação não encontrada ou já encerrada.",
            )

        admin_uid, admin_email = await resolve_admin_identity(self.session, claims)
        modo_anterior = (impersonation.meta_info or {}).get("impersonation_mode", "READ_ONLY")

        agora = datetime.now(timezone.utc)

        # Atualiza histórico de ações da impersonação
        acoes = list(impersonation.acoes_realizadas or [])
        acoes.append({
            "timestamp": agora.isoformat(),
            "acao": "MODE_SWITCH",
            "modo_anterior": modo_anterior,
            "novo_modo": novo_modo,
            "motivo": motivo,
        })
        impersonation.acoes_realizadas = acoes

        meta = dict(impersonation.meta_info or {})
        meta["impersonation_mode"] = novo_modo
        impersonation.meta_info = meta

        # Registra em auditoria
        audit_log = AdminAuditLog(
            id=uuid.uuid4(),
            admin_user_id=admin_uid,
            admin_email=admin_email,
            acao="TENANT_IMPERSONATION_MODE_CHANGE",
            entidade="tenant",
            entidade_id=impersonation.tenant_id,
            descricao=f"Modo de acesso assistido alterado de {modo_anterior} para {novo_modo}. Motivo: {motivo}",
            dados_anteriores={"modo": modo_anterior},
            dados_novos={"modo": novo_modo, "motivo": motivo, "impersonation_id": str(impersonation.id)},
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=agora,
        )
        self.session.add(audit_log)
        await self.session.commit()

        # Reemite token com o modo novo
        new_claims = dict(claims)
        new_claims["impersonation_mode"] = novo_modo
        expires_delta = timedelta(minutes=60)

        auth_service = AuthService(self.session)
        access_token = auth_service.create_access_token(data=new_claims, expires_delta=expires_delta)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "impersonation_id": str(impersonation.id),
            "modo": novo_modo,
            "expira_em": (agora + expires_delta).isoformat(),
        }

    async def stop_impersonation(
        self,
        claims: dict[str, Any],
        impersonation_id: uuid.UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """Encerra a sessão de impersonação ativa."""
        impersonation = await self.session.get(AdminImpersonation, impersonation_id)
        if not impersonation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sessão de impersonação não encontrada.",
            )

        if impersonation.fim is None:
            agora = datetime.now(timezone.utc)
            impersonation.fim = agora

            admin_uid, admin_email = await resolve_admin_identity(self.session, claims)

            acoes = list(impersonation.acoes_realizadas or [])
            acoes.append({
                "timestamp": agora.isoformat(),
                "acao": "IMPERSONATION_STOPPED",
            })
            impersonation.acoes_realizadas = acoes

            audit_log = AdminAuditLog(
                id=uuid.uuid4(),
                admin_user_id=admin_uid,
                admin_email=admin_email,
                acao="TENANT_IMPERSONATION_STOP",
                entidade="tenant",
                entidade_id=impersonation.tenant_id,
                descricao="Operador encerrou sessão de acesso assistido ao tenant.",
                dados_novos={"impersonation_id": str(impersonation.id)},
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=agora,
            )
            self.session.add(audit_log)
            await self.session.commit()

        return {
            "sucesso": True,
            "mensagem": "Sessão de impersonação encerrada com sucesso.",
            "impersonation_id": str(impersonation.id),
        }

