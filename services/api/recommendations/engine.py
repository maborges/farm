from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from .lifecycle_service import RecommendationLifecycleService
from .provider import RecommendationProvider
from .registry import RecommendationProviderRegistry, recommendation_provider_registry
from .schemas import (
    OperationalContext,
    RecommendationCandidate,
    RecommendationResultResponse,
    RecommendationSignal,
)


class RecommendationEngineExecution(BaseModel):
    provider_name: str
    status: str
    candidate_count: int = 0
    created: int = 0
    updated: int = 0
    errors: int = 0
    duration_ms: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RecommendationEngineResult(BaseModel):
    run_id: UUID
    tenant_id: UUID
    unidade_produtiva_id: UUID | None = None
    dry_run: bool = False
    providers_executed: int = 0
    candidates_total: int = 0
    recommendations_created: int = 0
    recommendations_updated: int = 0
    errors: int = 0
    duration_ms: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    executions: list[RecommendationEngineExecution] = Field(default_factory=list)
    items: list[RecommendationResultResponse] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class RecommendationEngine:
    """Global engine that deduplicates and persists provider candidates."""

    def __init__(
        self,
        session: AsyncSession,
        tenant_id: UUID,
        registry: RecommendationProviderRegistry | None = None,
    ) -> None:
        self.session = session
        self.tenant_id = tenant_id
        self.registry = registry or recommendation_provider_registry
        self.lifecycle = RecommendationLifecycleService(session, tenant_id)

    async def generate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
        provider_names: list[str] | None = None,
        dry_run: bool = False,
    ) -> RecommendationEngineResult:
        """Evaluate registered providers and persist recommendation results."""
        started_at = datetime.now(timezone.utc)
        start = perf_counter()
        result = RecommendationEngineResult(
            run_id=uuid4(),
            tenant_id=self.tenant_id,
            unidade_produtiva_id=context.unidade_produtiva_id,
            dry_run=dry_run,
            started_at=started_at,
        )
        for provider_cls in self._resolve_providers(context, provider_names):
            execution, items = await self._execute_provider(
                provider_cls,
                context,
                signals,
                dry_run=dry_run,
            )
            result.providers_executed += 1
            result.candidates_total += execution.candidate_count
            result.recommendations_created += execution.created
            result.recommendations_updated += execution.updated
            result.errors += execution.errors
            result.executions.append(execution)
            result.items.extend(items)
        result.duration_ms = int((perf_counter() - start) * 1000)
        result.finished_at = datetime.now(timezone.utc)
        return result

    async def _execute_provider(
        self,
        provider_cls: type[RecommendationProvider],
        context: OperationalContext,
        signals: list[RecommendationSignal],
        dry_run: bool = False,
    ) -> tuple[RecommendationEngineExecution, list[RecommendationResultResponse]]:
        started_at = datetime.now(timezone.utc)
        start = perf_counter()
        provider = provider_cls(self.session)
        created = 0
        updated = 0
        items: list[RecommendationResultResponse] = []
        try:
            if dry_run:
                async with self.session.begin_nested() as nested:
                    try:
                        candidates = await provider.evaluate(context, signals)
                    finally:
                        await nested.rollback()
                        self.session.expire_all()
            else:
                candidates = await provider.evaluate(context, signals)
            candidate_count = len(candidates)
            if dry_run:
                execution = RecommendationEngineExecution(
                    provider_name=provider.provider_name,
                    status="dry_run",
                    candidate_count=candidate_count,
                    duration_ms=int((perf_counter() - start) * 1000),
                    metadata={"candidate_count": candidate_count, "dry_run": True},
                )
                return execution, []
            for candidate in candidates:
                existing = await self.lifecycle._find_active_recommendation(
                    candidate.dedupe_key
                )
                persisted = await self.lifecycle.create_or_update_recommendation(
                    candidate
                )
                if existing is None:
                    created += 1
                    await self._notify_recommendation_created(persisted)
                else:
                    updated += 1
                items.append(
                    RecommendationResultResponse.model_validate(
                        persisted,
                        from_attributes=True,
                    )
                )
            execution = RecommendationEngineExecution(
                provider_name=provider.provider_name,
                status="success",
                candidate_count=candidate_count,
                created=created,
                updated=updated,
                duration_ms=int((perf_counter() - start) * 1000),
                metadata={"candidate_count": candidate_count},
            )
            return execution, items
        except Exception as exc:
            execution = RecommendationEngineExecution(
                provider_name=getattr(provider, "provider_name", provider_cls.__name__),
                status="failed",
                errors=1,
                candidate_count=0,
                duration_ms=int(
                    (datetime.now(timezone.utc) - started_at).total_seconds() * 1000
                ),
                metadata={
                    "exception_type": exc.__class__.__name__,
                    "exception_message": str(exc),
                },
            )
            return execution, []

    async def _notify_recommendation_created(self, recommendation: Any) -> None:
        try:
            from .notification_bridge import RecommendationNotificationBridge

            bridge = RecommendationNotificationBridge()
            await bridge.notify(recommendation, was_created=True)
        except Exception as exc:  # pragma: no cover - defensive isolation
            logger.bind(
                component="recommendation_engine",
                recommendation_id=(
                    str(getattr(recommendation, "id", None))
                    if getattr(recommendation, "id", None) is not None
                    else None
                ),
                tenant_id=(
                    str(getattr(recommendation, "tenant_id", None))
                    if getattr(recommendation, "tenant_id", None) is not None
                    else None
                ),
                exception_type=exc.__class__.__name__,
            ).exception("recommendation_notification_bridge_failed")

    def _resolve_providers(
        self,
        context: OperationalContext,
        provider_names: list[str] | None,
    ) -> tuple[type[RecommendationProvider], ...]:
        if provider_names:
            providers = []
            for provider_name in provider_names:
                provider_cls = self.registry.get_provider(provider_name)
                if provider_cls is not None:
                    providers.append(provider_cls)
            return tuple(providers)
        return self.registry.find_by_domain(context.domain.value)
