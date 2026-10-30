from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import TenantPermissions
from core.models.auth import FazendaUsuario, PerfilAcesso, TenantUsuario

from .models import RecommendationResult


@dataclass(frozen=True, slots=True)
class RecommendationAccessScope:
    """Authorized recommendation scope resolved from the canonical IAM model."""

    unit_ids: tuple[UUID, ...]
    allow_tenant_wide: bool
    allow_all_units: bool = False


class RecommendationAuthorizationService:
    """Authorize human recommendation actions with tenant and unit scope."""

    def __init__(self, session: AsyncSession, tenant_id: UUID, user_id: UUID) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.user_id = user_id

    async def read_scope(self) -> RecommendationAccessScope:
        """Return the visible unit and tenant-wide scope for the authenticated user."""

        membership, profile = await self._membership()
        if membership.is_owner:
            return RecommendationAccessScope((), True, allow_all_units=True)
        self._require_permission(profile, "recommendations:view")
        units = await self._authorized_units("recommendations:view", profile)
        return RecommendationAccessScope(
            units,
            self._has_permission(profile, "recommendations:admin"),
        )

    async def authorize(self, recommendation_id: UUID, action: str) -> RecommendationResult:
        """Authorize one lifecycle action against the recommendation's real scope."""

        recommendation = await self._recommendation(recommendation_id)
        membership, profile = await self._membership()
        if membership.is_owner:
            return recommendation
        if recommendation.unidade_produtiva_id is None:
            self._require_permission(profile, "recommendations:admin")
            return recommendation
        await self._authorize_unit_action(recommendation.unidade_produtiva_id, action, profile)
        return recommendation

    async def pode_executar(self, recommendation_id: UUID, action: str) -> bool:
        """Versão não-exceção de `authorize`, para filtrar ações visíveis sem interromper o fluxo."""
        try:
            await self.authorize(recommendation_id, action)
            return True
        except HTTPException:
            return False

    async def authorize_metrics(self) -> None:
        """Restrict aggregate metrics to tenant-wide recommendation administrators."""

        membership, profile = await self._membership()
        if not membership.is_owner:
            self._require_permission(profile, "recommendations:admin")

    async def _membership(self) -> tuple[TenantUsuario, PerfilAcesso | None]:
        await self._set_rls_context()
        stmt = (
            select(TenantUsuario, PerfilAcesso)
            .outerjoin(PerfilAcesso, TenantUsuario.perfil_id == PerfilAcesso.id)
            .where(
                TenantUsuario.tenant_id == self.tenant_id,
                TenantUsuario.usuario_id == self.user_id,
                TenantUsuario.status == "ATIVO",
            )
        )
        row = (await self.session.execute(stmt)).first()
        if row is None:
            raise HTTPException(status_code=403, detail="Usuário não tem acesso a este tenant")
        return row

    async def _authorized_units(
        self,
        permission: str,
        tenant_profile: PerfilAcesso | None,
    ) -> tuple[UUID, ...]:
        stmt = (
            select(FazendaUsuario, PerfilAcesso)
            .outerjoin(PerfilAcesso, FazendaUsuario.perfil_fazenda_id == PerfilAcesso.id)
            .where(
                FazendaUsuario.tenant_id == self.tenant_id,
                FazendaUsuario.usuario_id == self.user_id,
            )
        )
        rows = (await self.session.execute(stmt)).all()
        return tuple(
            link.unidade_produtiva_id
            for link, profile in rows
            if self._is_current(link)
            and self._has_permission(profile or tenant_profile, permission)
        )

    async def _authorize_unit_action(
        self,
        unit_id: UUID,
        action: str,
        tenant_profile: PerfilAcesso | None,
    ) -> None:
        stmt = (
            select(FazendaUsuario, PerfilAcesso)
            .outerjoin(PerfilAcesso, FazendaUsuario.perfil_fazenda_id == PerfilAcesso.id)
            .where(
                FazendaUsuario.tenant_id == self.tenant_id,
                FazendaUsuario.usuario_id == self.user_id,
                FazendaUsuario.unidade_produtiva_id == unit_id,
            )
        )
        row = (await self.session.execute(stmt)).first()
        if row is None or not self._is_current(row[0]):
            raise HTTPException(
                status_code=403,
                detail="Acesso negado à unidade produtiva da recomendação",
            )
        self._require_permission(row[1] or tenant_profile, f"recommendations:{action}")

    async def _recommendation(self, recommendation_id: UUID) -> RecommendationResult:
        await self._set_rls_context()
        stmt = select(RecommendationResult).where(
            RecommendationResult.id == recommendation_id,
            RecommendationResult.tenant_id == self.tenant_id,
        )
        recommendation = (await self.session.execute(stmt)).scalar_one_or_none()
        if recommendation is None:
            raise HTTPException(status_code=404, detail="Recomendação não encontrada")
        return recommendation

    async def _set_rls_context(self) -> None:
        await self.session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(self.tenant_id)},
        )

    @staticmethod
    def _is_current(link: FazendaUsuario) -> bool:
        today = date.today()
        return not (link.vigencia_inicio and link.vigencia_inicio > today) and not (
            link.vigencia_fim and link.vigencia_fim < today
        )

    @staticmethod
    def _has_permission(profile: PerfilAcesso | None, permission: str) -> bool:
        if profile is None:
            return False
        return TenantPermissions.has_permission(profile.nome, permission, profile.permissoes)

    def _require_permission(self, profile: PerfilAcesso | None, permission: str) -> None:
        if not self._has_permission(profile, permission):
            raise HTTPException(status_code=403, detail=f"Permissão negada: {permission}")
