from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import TenantViolationError
from core.models.unidade_produtiva import UnidadeProdutiva

from .engine import RecommendationEngine, RecommendationEngineResult
from .enums import RecommendationDomain
from .provider import RecommendationProvider
from .registry import RecommendationProviderRegistry, recommendation_provider_registry
from .schemas import OperationalContext, RecommendationSignal


@dataclass(slots=True)
class RecommendationExecutionScope:
    tenant_id: UUID
    unidade_produtiva_id: UUID | None
    domain: RecommendationDomain
    scope_type: str
    scope_id: str


class RecommendationExecutionRunner:
    """Small orchestration helper for controlled recommendation runs."""

    def __init__(
        self,
        session: AsyncSession,
        registry: RecommendationProviderRegistry | None = None,
    ) -> None:
        self.session = session
        self.registry = registry or recommendation_provider_registry

    def resolve_providers(
        self,
        domain: RecommendationDomain | None = None,
    ) -> tuple[type[RecommendationProvider], ...]:
        if domain is None:
            return self.registry.list_providers()
        return self.registry.find_by_domain(domain.value)

    async def build_context(
        self,
        *,
        tenant_id: UUID,
        provider_cls: type[RecommendationProvider],
        unidade_produtiva_id: UUID | None = None,
        domain: RecommendationDomain | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OperationalContext:
        resolved_domain = self._resolve_domain(provider_cls, domain)
        scope = await self._resolve_scope(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=resolved_domain,
        )
        return OperationalContext(
            tenant_id=tenant_id,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=resolved_domain,
            scope_type=scope.scope_type,
            scope_id=scope.scope_id,
            generated_at=self._now(),
            metadata=metadata or {},
        )

    async def run_provider(
        self,
        *,
        tenant_id: UUID,
        provider_cls: type[RecommendationProvider],
        signals: list[RecommendationSignal] | None = None,
        unidade_produtiva_id: UUID | None = None,
        domain: RecommendationDomain | None = None,
        dry_run: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> RecommendationEngineResult:
        context = await self.build_context(
            tenant_id=tenant_id,
            provider_cls=provider_cls,
            unidade_produtiva_id=unidade_produtiva_id,
            domain=domain,
            metadata=metadata,
        )
        engine = RecommendationEngine(self.session, tenant_id, registry=self.registry)
        return await engine.generate(
            context,
            signals or [],
            provider_names=[provider_cls.provider_name],
            dry_run=dry_run,
        )

    async def _resolve_scope(
        self,
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID | None,
        domain: RecommendationDomain,
    ) -> RecommendationExecutionScope:
        if unidade_produtiva_id is not None:
            await self._ensure_unidade_produtiva(tenant_id=tenant_id, unidade_produtiva_id=unidade_produtiva_id)
            return RecommendationExecutionScope(
                tenant_id=tenant_id,
                unidade_produtiva_id=unidade_produtiva_id,
                domain=domain,
                scope_type="UNIDADE_PRODUTIVA",
                scope_id=str(unidade_produtiva_id),
            )
        return RecommendationExecutionScope(
            tenant_id=tenant_id,
            unidade_produtiva_id=None,
            domain=domain,
            scope_type="TENANT",
            scope_id=str(tenant_id),
        )

    async def _ensure_unidade_produtiva(
        self,
        *,
        tenant_id: UUID,
        unidade_produtiva_id: UUID,
    ) -> None:
        stmt = select(UnidadeProdutiva.id).where(
            UnidadeProdutiva.id == unidade_produtiva_id,
            UnidadeProdutiva.tenant_id == tenant_id,
            UnidadeProdutiva.ativo.is_(True),
        )
        row = await self.session.execute(stmt)
        if row.scalar_one_or_none() is None:
            raise TenantViolationError(
                "Unidade produtiva não localizada ou fora do tenant informado.",
                tenant_id=tenant_id,
                resource="unidade_produtiva",
            )

    @staticmethod
    def _resolve_domain(
        provider_cls: type[RecommendationProvider],
        requested_domain: RecommendationDomain | None,
    ) -> RecommendationDomain:
        if requested_domain is not None:
            return requested_domain
        for value in getattr(provider_cls, "domains", ()):
            try:
                return RecommendationDomain(str(value).upper())
            except ValueError:
                continue
        return RecommendationDomain.SYSTEM

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)
