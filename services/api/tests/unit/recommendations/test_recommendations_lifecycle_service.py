from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text

from core.exceptions import BusinessRuleError
from recommendations.models import RecommendationLifecycleEvent, RecommendationResult
from recommendations.schemas import RecommendationCandidate
from recommendations.lifecycle_service import RecommendationLifecycleService


ADMIN_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")
pytestmark = pytest.mark.integration


async def _ensure_tenant(session, tenant_id: uuid.UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO tenants (
                id, nome, documento, ativo, storage_usado_mb, storage_limite_mb,
                idioma_padrao, created_at, updated_at
            )
            VALUES (:id, :nome, :documento, true, 0, 10240, 'pt-BR', now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(tenant_id),
            "nome": f"Tenant {tenant_id.hex[:8]}",
            "documento": tenant_id.hex[:11],
        },
    )
    await session.commit()


def _candidate(tenant_id: uuid.UUID, *, dedupe_key: str = "tenant:safra-1:rule-1") -> RecommendationCandidate:
    return RecommendationCandidate(
        tenant_id=tenant_id,
        unidade_produtiva_id=None,
        domain="AGRICULTURE",
        priority="HIGH",
        source_type="SIGNAL",
        action_type="OPEN_ROUTE",
        provider_name="fake",
        rule_code="RULE_1",
        scope_type="SAFRA",
        scope_id="safra-1",
        title="Revisar custos",
        summary="Resumo",
        rationale="Racional",
        dedupe_key=dedupe_key,
        source_signal_ids=[uuid.uuid4()],
        action_target="/dashboard/agricola",
    )


async def _count_results(session, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count(RecommendationResult.id)).where(RecommendationResult.tenant_id == tenant_id)
    return int((await session.execute(stmt)).scalar_one() or 0)


async def _count_events(session, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count(RecommendationLifecycleEvent.id)).where(
        RecommendationLifecycleEvent.tenant_id == tenant_id
    )
    return int((await session.execute(stmt)).scalar_one() or 0)


@pytest.mark.asyncio
async def test_create_recommendation_and_lifecycle_event(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    service = RecommendationLifecycleService(session, tenant)

    recommendation = await service.create_or_update_recommendation(_candidate(tenant))

    assert recommendation.status == "CREATED"
    assert await _count_results(session, tenant) == 1
    assert await _count_events(session, tenant) == 1


@pytest.mark.asyncio
async def test_dedupe_updates_active_recommendation_without_duplication(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    service = RecommendationLifecycleService(session, tenant)

    first = await service.create_or_update_recommendation(_candidate(tenant))
    second = await service.create_or_update_recommendation(
        _candidate(tenant, dedupe_key="tenant:safra-1:rule-1")
    )

    assert first.id == second.id
    assert await _count_results(session, tenant) == 1
    assert await _count_events(session, tenant) == 1


@pytest.mark.asyncio
async def test_dedupe_creates_new_after_dismiss(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    service = RecommendationLifecycleService(session, tenant)

    first = await service.create_or_update_recommendation(_candidate(tenant))
    await service.dismiss(first.id, ADMIN_USER_ID, reason="duplicada")
    second = await service.create_or_update_recommendation(_candidate(tenant))

    assert first.id != second.id
    assert await _count_results(session, tenant) == 2


@pytest.mark.asyncio
async def test_lifecycle_transitions_work(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    service = RecommendationLifecycleService(session, tenant)

    recommendation = await service.create_or_update_recommendation(_candidate(tenant))
    recommendation = await service.mark_viewed(recommendation.id, ADMIN_USER_ID)
    assert recommendation.status == "VIEWED"

    recommendation = await service.accept(recommendation.id, ADMIN_USER_ID)
    assert recommendation.status == "ACCEPTED"

    recommendation = await service.execute(recommendation.id, ADMIN_USER_ID, execution_note="ok")
    assert recommendation.status == "EXECUTED"


@pytest.mark.asyncio
async def test_postpone_requires_future_datetime(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    service = RecommendationLifecycleService(session, tenant)
    recommendation = await service.create_or_update_recommendation(_candidate(tenant))

    with pytest.raises(BusinessRuleError):
        await service.postpone(
            recommendation.id,
            datetime.now(timezone.utc) - timedelta(minutes=1),
            ADMIN_USER_ID,
        )


@pytest.mark.asyncio
async def test_invalid_transition_fails(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    service = RecommendationLifecycleService(session, tenant)
    recommendation = await service.create_or_update_recommendation(_candidate(tenant))
    await service.execute(recommendation.id, ADMIN_USER_ID, execution_note="ok")

    with pytest.raises(BusinessRuleError):
        await service.accept(recommendation.id, ADMIN_USER_ID)
