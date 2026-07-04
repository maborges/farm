from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest

from recommendations.engine import RecommendationEngineExecution, RecommendationEngineResult
from recommendations.enums import RecommendationActionType, RecommendationDomain, RecommendationPriority, RecommendationSourceType
from recommendations.provider import RecommendationProvider
from recommendations.registry import RecommendationProviderRegistry
from recommendations.runner import RecommendationExecutionRunner
from recommendations.scheduler import RecommendationSchedulerService
from recommendations.schemas import OperationalContext, RecommendationCandidate, RecommendationSignal


class TenantScopedProvider(RecommendationProvider):
    provider_name = "tenant_scoped"
    domains = ("AGRICULTURE",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        return [
            RecommendationCandidate(
                tenant_id=context.tenant_id,
                unidade_produtiva_id=context.unidade_produtiva_id,
                domain=context.domain,
                priority=RecommendationPriority.HIGH,
                source_type=RecommendationSourceType.SIGNAL,
                action_type=RecommendationActionType.OPEN_ROUTE,
                provider_name=self.provider_name,
                rule_code="RULE_TENANT",
                scope_type=context.scope_type,
                scope_id=context.scope_id,
                title="Revisar recomendação",
                summary="Resumo",
                rationale="Racional",
                dedupe_key=f"{context.tenant_id}:tenant_scoped:{context.scope_id}",
                source_signal_ids=[signal.signal_id for signal in signals],
                action_target="/api/v1/recommendations",
            )
        ]


class FinanceProvider(RecommendationProvider):
    provider_name = "finance_provider"
    domains = ("FINANCE",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        return [
            RecommendationCandidate(
                tenant_id=context.tenant_id,
                unidade_produtiva_id=context.unidade_produtiva_id,
                domain=context.domain,
                priority=RecommendationPriority.NORMAL,
                source_type=RecommendationSourceType.SIGNAL,
                action_type=RecommendationActionType.OPEN_ROUTE,
                provider_name=self.provider_name,
                rule_code="RULE_FINANCE",
                scope_type=context.scope_type,
                scope_id=context.scope_id,
                title="Analisar financeiro",
                summary="Resumo",
                rationale="Racional",
                dedupe_key=f"{context.tenant_id}:finance_provider:{context.scope_id}",
                source_signal_ids=[signal.signal_id for signal in signals],
                action_target="/api/v1/recommendations",
            )
        ]


class FailingProvider(RecommendationProvider):
    provider_name = "failing_provider"
    domains = ("AGRICULTURE",)

    async def evaluate(
        self,
        context: OperationalContext,
        signals: list[RecommendationSignal],
    ) -> list[RecommendationCandidate]:
        raise RuntimeError("boom")


def _build_registry(*provider_classes: type[RecommendationProvider]) -> RecommendationProviderRegistry:
    registry = RecommendationProviderRegistry()
    registry.register_many(provider_classes)
    return registry


def _signal(tenant_id: uuid.UUID) -> list[RecommendationSignal]:
    return [
        RecommendationSignal(
            signal_id=uuid.uuid4(),
            tenant_id=tenant_id,
            domain=RecommendationDomain.AGRICULTURE,
            source_type=RecommendationSourceType.SIGNAL,
            key="signal-1",
            occurred_at=datetime.now(timezone.utc),
        )
    ]


def _engine_result(
    provider_name: str,
    *,
    candidate_count: int,
    created: int = 0,
    updated: int = 0,
    errors: int = 0,
    status: str = "success",
) -> RecommendationEngineResult:
    return RecommendationEngineResult(
        run_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        dry_run=False,
        providers_executed=1,
        candidates_total=candidate_count,
        recommendations_created=created,
        recommendations_updated=updated,
        errors=errors,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        executions=[
            RecommendationEngineExecution(
                provider_name=provider_name,
                status=status,
                candidate_count=candidate_count,
                created=created,
                updated=updated,
                errors=errors,
                duration_ms=1,
            )
        ],
        items=[],
    )


@pytest.mark.asyncio
async def test_scheduler_executes_by_tenant_and_batches() -> None:
    tenant_id = uuid.uuid4()
    registry = _build_registry(TenantScopedProvider, FinanceProvider)
    session = SimpleNamespace()
    scheduler = RecommendationSchedulerService(session, registry=registry)
    scheduler.runner.run_provider = AsyncMock(
        side_effect=[
            _engine_result("tenant_scoped", candidate_count=1, created=1),
            _engine_result("finance_provider", candidate_count=1, created=1),
        ]
    )

    result = await scheduler.run_scheduled_recommendations(
        tenant_id=tenant_id,
        batch_size=1,
        signals=_signal(tenant_id),
    )

    assert result.tenant_id == tenant_id
    assert result.providers_requested == 2
    assert result.providers_executed == 2
    assert result.total_batches == 2
    assert result.candidates_total == 2
    assert result.recommendations_created == 2
    assert result.recommendations_updated == 0
    assert result.errors == 0
    assert result.provider_names == ["tenant_scoped", "finance_provider"]


@pytest.mark.asyncio
async def test_scheduler_executes_by_domain_only() -> None:
    tenant_id = uuid.uuid4()
    registry = _build_registry(TenantScopedProvider, FinanceProvider)
    session = SimpleNamespace()
    scheduler = RecommendationSchedulerService(session, registry=registry)
    scheduler.runner.run_provider = AsyncMock(return_value=_engine_result("tenant_scoped", candidate_count=1, created=1))

    result = await scheduler.run_scheduled_recommendations(
        tenant_id=tenant_id,
        domain=RecommendationDomain.AGRICULTURE,
        signals=_signal(tenant_id),
    )

    assert result.providers_requested == 1
    assert result.providers_executed == 1
    assert result.provider_names == ["tenant_scoped"]
    assert result.candidates_total == 1


@pytest.mark.asyncio
async def test_scheduler_executes_with_unidade_produtiva_and_persists_scope() -> None:
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    registry = _build_registry(TenantScopedProvider)
    session = SimpleNamespace()
    scheduler = RecommendationSchedulerService(session, registry=registry)
    scheduler.runner.run_provider = AsyncMock(return_value=_engine_result("tenant_scoped", candidate_count=1, created=1))

    result = await scheduler.run_scheduled_recommendations(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        signals=_signal(tenant_id),
    )

    assert result.providers_executed == 1
    assert result.unidade_produtiva_id == unidade_produtiva_id
    assert result.executions[0].batch_index == 1


@pytest.mark.asyncio
async def test_dry_run_does_not_persist() -> None:
    tenant_id = uuid.uuid4()
    registry = _build_registry(TenantScopedProvider)
    session = SimpleNamespace()
    scheduler = RecommendationSchedulerService(session, registry=registry)
    scheduler.runner.run_provider = AsyncMock(return_value=_engine_result("tenant_scoped", candidate_count=1, created=0))

    result = await scheduler.run_scheduled_recommendations(
        tenant_id=tenant_id,
        dry_run=True,
        signals=_signal(tenant_id),
    )

    assert result.dry_run is True
    assert result.providers_executed == 1
    assert result.candidates_total == 1
    assert result.recommendations_created == 0
    assert result.recommendations_updated == 0
    assert result.executions[0].status == "success"


@pytest.mark.asyncio
async def test_scheduler_isolates_provider_errors() -> None:
    tenant_id = uuid.uuid4()
    registry = _build_registry(FailingProvider, TenantScopedProvider)
    session = SimpleNamespace()
    scheduler = RecommendationSchedulerService(session, registry=registry)
    scheduler.runner.run_provider = AsyncMock(
        side_effect=[
            RuntimeError("boom"),
            _engine_result("tenant_scoped", candidate_count=1, created=1),
        ]
    )

    result = await scheduler.run_scheduled_recommendations(
        tenant_id=tenant_id,
        signals=_signal(tenant_id),
    )

    assert result.providers_executed == 2
    assert result.errors == 1
    assert result.recommendations_created == 1
    assert result.provider_names == ["failing_provider", "tenant_scoped"]
    assert any(execution.status == "failed" for execution in result.executions)


@pytest.mark.asyncio
async def test_scheduler_preserves_dedupe() -> None:
    tenant_id = uuid.uuid4()
    registry = _build_registry(TenantScopedProvider)
    session = SimpleNamespace()
    scheduler = RecommendationSchedulerService(session, registry=registry)
    scheduler.runner.run_provider = AsyncMock(
        side_effect=[
            _engine_result("tenant_scoped", candidate_count=1, created=1),
            _engine_result("tenant_scoped", candidate_count=1, created=0, updated=1),
        ]
    )

    first = await scheduler.run_scheduled_recommendations(
        tenant_id=tenant_id,
        signals=_signal(tenant_id),
    )
    second = await scheduler.run_scheduled_recommendations(
        tenant_id=tenant_id,
        signals=_signal(tenant_id),
    )

    assert first.recommendations_created == 1
    assert second.recommendations_created == 0
    assert second.recommendations_updated == 1


@pytest.mark.asyncio
async def test_runner_builds_tenant_safe_context() -> None:
    tenant_id = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()

    session = SimpleNamespace()
    session.execute = AsyncMock(return_value=SimpleNamespace(scalar_one_or_none=lambda: unidade_produtiva_id))
    runner = RecommendationExecutionRunner(session, registry=_build_registry(TenantScopedProvider))

    context = await runner.build_context(
        tenant_id=tenant_id,
        provider_cls=TenantScopedProvider,
        unidade_produtiva_id=unidade_produtiva_id,
    )

    assert context.tenant_id == tenant_id
    assert context.unidade_produtiva_id == unidade_produtiva_id
    assert context.scope_type == "UNIDADE_PRODUTIVA"
    assert context.scope_id == str(unidade_produtiva_id)
