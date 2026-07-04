from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from recommendations.enums import (
    RecommendationActionType,
    RecommendationDomain,
    RecommendationPriority,
    RecommendationSourceType,
    RecommendationStatus,
)
from recommendations.models import RecommendationLifecycleEvent, RecommendationResult
from recommendations.schemas import (
    OperationalContext,
    RecommendationCandidate,
    RecommendationLifecycleEventCreate,
    RecommendationResultCreate,
    RecommendationSignal,
)


def test_models_import_and_tablenames() -> None:
    assert RecommendationResult.__tablename__ == "recommendation_results"
    assert RecommendationLifecycleEvent.__tablename__ == "recommendation_lifecycle_events"


def test_model_columns_cover_core_contracts() -> None:
    assert {
        "tenant_id",
        "domain",
        "status",
        "priority",
        "dedupe_key",
        "source_signal_ids",
    }.issubset(RecommendationResult.__table__.columns.keys())
    assert {"recommendation_id", "action_type", "previous_status", "new_status"}.issubset(
        RecommendationLifecycleEvent.__table__.columns.keys()
    )


def test_operational_context_valid() -> None:
    context = OperationalContext(
        tenant_id=uuid4(),
        unidade_produtiva_id=uuid4(),
        domain=RecommendationDomain.AGRICULTURE,
        scope_type="SAFRA",
        scope_id="safra-1",
        source_signal_ids=[uuid4()],
        generated_at=datetime.now(timezone.utc),
    )
    assert context.scope_type == "SAFRA"


def test_signal_valid() -> None:
    signal = RecommendationSignal(
        signal_id=uuid4(),
        tenant_id=uuid4(),
        domain=RecommendationDomain.FINANCE,
        source_type=RecommendationSourceType.EVENT,
        key="financeiro.fluxo_caixa_critico",
        occurred_at=datetime.now(timezone.utc),
        payload={"saldo": -1000},
    )
    assert signal.payload["saldo"] == -1000


def test_candidate_requires_action_target_when_action_is_not_none() -> None:
    with pytest.raises(ValidationError):
        RecommendationCandidate(
            tenant_id=uuid4(),
            domain=RecommendationDomain.AGRICULTURE,
            priority=RecommendationPriority.HIGH,
            source_type=RecommendationSourceType.SIGNAL,
            action_type=RecommendationActionType.OPEN_ROUTE,
            provider_name="fake",
            rule_code="RULE_1",
            scope_type="SAFRA",
            scope_id="safra-1",
            title="Revisar safra",
            summary="Resumo",
            rationale="Racional",
            dedupe_key="tenant:safra-1:rule-1",
        )


def test_candidate_valid_with_action_target() -> None:
    candidate = RecommendationCandidate(
        tenant_id=uuid4(),
        unidade_produtiva_id=uuid4(),
        domain=RecommendationDomain.OPERATIONS,
        priority=RecommendationPriority.URGENT,
        source_type=RecommendationSourceType.INDICATOR,
        action_type=RecommendationActionType.OPEN_ROUTE,
        provider_name="fake",
        rule_code="RULE_2",
        scope_type="EQUIPMENT",
        scope_id="eq-1",
        title="Inspecionar equipamento",
        summary="Resumo",
        rationale="Racional",
        dedupe_key="tenant:eq-1:rule-2",
        source_signal_ids=[uuid4()],
        confidence=Decimal("0.8"),
        action_target="/dashboard/operacional/frota/eq-1",
    )
    assert candidate.confidence == Decimal("0.8")


def test_result_create_valid() -> None:
    result = RecommendationResultCreate(
        tenant_id=uuid4(),
        domain=RecommendationDomain.FIELD,
        status=RecommendationStatus.CREATED,
        priority=RecommendationPriority.NORMAL,
        source_type=RecommendationSourceType.SIGNAL,
        action_type=RecommendationActionType.REVIEW,
        provider_name="fake",
        rule_code="RULE_3",
        scope_type="TASK",
        scope_id="task-1",
        title="Revisar tarefa",
        summary="Resumo",
        rationale="Racional",
        dedupe_key="tenant:task-1:rule-3",
        source_signal_ids=[uuid4()],
        action_target="task-1",
    )
    assert result.status == RecommendationStatus.CREATED


def test_lifecycle_event_create_valid() -> None:
    event = RecommendationLifecycleEventCreate(
        tenant_id=uuid4(),
        recommendation_id=uuid4(),
        action_type="CREATE",
        previous_status="CREATED",
        new_status="CREATED",
        source_channel="ENGINE",
    )
    assert event.source_channel == "ENGINE"
