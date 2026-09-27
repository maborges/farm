"""Resolução canônica da identidade operacional para o fluxo de materiais.

Este módulo não implementa recebimento. Ele apenas fornece a regra que os
próximos comandos de Campo/Estoque devem reutilizar, sem inferência por
e-mail, CPF, nome ou igualdade acidental entre UUIDs.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import BusinessRuleError, EntityNotFoundError
from core.models.auth import TenantUsuario, Usuario
from core.cadastros.pessoas.models import PessoaUsuario
from operacional.models.estoque import RequisicaoMaterial, RequisicaoResponsabilidadeHistorico


class IdentidadeOperacionalService:
    """Resolve User → Pessoa no contexto de um Tenant."""

    @staticmethod
    async def resolver_pessoa_usuario(
        session: AsyncSession, tenant_id: UUID, usuario_id: UUID
    ) -> PessoaUsuario:
        stmt = (
            select(PessoaUsuario)
            .join(
                TenantUsuario,
                (TenantUsuario.tenant_id == PessoaUsuario.tenant_id)
                & (TenantUsuario.usuario_id == PessoaUsuario.usuario_id),
            )
            .join(Usuario, Usuario.id == PessoaUsuario.usuario_id)
            .where(
                PessoaUsuario.tenant_id == tenant_id,
                PessoaUsuario.usuario_id == usuario_id,
                PessoaUsuario.status == "ATIVO",
                PessoaUsuario.vigencia_inicio <= func.current_timestamp(),
                (
                    PessoaUsuario.vigencia_fim.is_(None)
                    | (PessoaUsuario.vigencia_fim > func.current_timestamp())
                ),
                TenantUsuario.status == "ATIVO",
                Usuario.ativo.is_(True),
            )
        )
        identidade = (await session.execute(stmt)).scalars().first()
        if identidade is None:
            raise EntityNotFoundError(
                "Usuário não possui identidade operacional ativa neste tenant."
            )
        return identidade

    @staticmethod
    async def validar_recebedor(
        session: AsyncSession,
        tenant_id: UUID,
        requisicao_id: UUID,
        usuario_id: UUID,
    ) -> PessoaUsuario:
        """Autoriza responsável direto ou delegado vigente.

        O responsável direto é a Pessoa da requisição. Delegações futuras
        precisam apontar para ``pessoa_usuario_id``; uma linha legada sem esse
        vínculo não é usada como prova de identidade.
        """
        identidade = await IdentidadeOperacionalService.resolver_pessoa_usuario(
            session, tenant_id, usuario_id
        )
        requisicao = (
            await session.execute(
                select(RequisicaoMaterial).where(
                    RequisicaoMaterial.tenant_id == tenant_id,
                    RequisicaoMaterial.id == requisicao_id,
                )
            )
        ).scalars().first()
        if requisicao is None:
            raise EntityNotFoundError("Requisição não encontrada neste tenant.")

        if requisicao.responsavel_pessoa_id == identidade.pessoa_id:
            return identidade

        delegado = (
            await session.execute(
                select(RequisicaoResponsabilidadeHistorico.id).where(
                    RequisicaoResponsabilidadeHistorico.tenant_id == tenant_id,
                    RequisicaoResponsabilidadeHistorico.requisicao_id == requisicao_id,
                    RequisicaoResponsabilidadeHistorico.usuario_id == usuario_id,
                    RequisicaoResponsabilidadeHistorico.pessoa_usuario_id == identidade.id,
                    RequisicaoResponsabilidadeHistorico.papel == "DELEGADO",
                    RequisicaoResponsabilidadeHistorico.vigencia_inicio
                    <= func.current_timestamp(),
                    (
                        RequisicaoResponsabilidadeHistorico.vigencia_fim.is_(None)
                        | (
                            RequisicaoResponsabilidadeHistorico.vigencia_fim
                            > func.current_timestamp()
                        )
                    ),
                )
            )
        ).scalar_one_or_none()
        if delegado is None:
            raise BusinessRuleError(
                "Usuário não é o responsável nem possui delegação vigente para receber a requisição."
            )
        return identidade
