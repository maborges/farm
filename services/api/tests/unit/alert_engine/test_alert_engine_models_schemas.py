from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from alert_engine.models import (
    AlertEvent,
    AlertIndicator,
    AlertInsight,
    AlertLifecycleEvent,
    Category,
    Domain,
    AlertStatus,
    OperationalAlert,
    Priority,
    Severity,
)
from alert_engine.schemas import (
    AlertEventCreate,
    AlertIndicatorCreate,
    AlertInsightCreate,
    AlertLifecycleEventCreate,
    OperationalAlertCreate,
    OperationalAlertStatusUpdate,
)


def test_models_import_and_tablenames() -> None:
    assert AlertEvent.__tablename__ == "alert_events"
    assert AlertIndicator.__tablename__ == "alert_indicators"
    assert OperationalAlert.__tablename__ == "operational_alerts"
    assert AlertInsight.__tablename__ == "alert_insights"
    assert AlertLifecycleEvent.__tablename__ == "alert_lifecycle_events"


def test_model_columns_cover_core_contracts() -> None:
    assert {"tenant_id", "domain", "category", "source", "payload", "created_at"}.issubset(
        AlertEvent.__table__.columns.keys()
    )
    assert {"value_numeric", "value_text", "value_bool", "calculation_version"}.issubset(
        AlertIndicator.__table__.columns.keys()
    )
    assert {"dedupe_key", "source_event_ids", "source_indicator_ids", "status"}.issubset(
        OperationalAlert.__table__.columns.keys()
    )
    assert {"generated_by", "evidence_event_ids", "evidence_alert_ids"}.issubset(
        AlertInsight.__table__.columns.keys()
    )
    assert {"alert_id", "action_type", "previous_status", "new_status"}.issubset(
        AlertLifecycleEvent.__table__.columns.keys()
    )


def test_alert_event_create_valid() -> None:
    payload = {"peso": 450.5, "lote": "A1"}
    schema = AlertEventCreate(
        tenant_id=uuid4(),
        domain=Domain.LIVESTOCK,
        category=Category.PRODUCAO,
        source="pecuaria.pesagem",
        source_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        ingested_at=datetime.now(timezone.utc),
        actor_id=uuid4(),
        entity_type="animal",
        entity_id=uuid4(),
        payload=payload,
        correlation_id=uuid4(),
        causation_id=uuid4(),
        metadata={"origin": "sensor"},
    )
    assert schema.payload == payload


def test_alert_event_create_rejects_empty_payload() -> None:
    with pytest.raises(ValidationError):
        AlertEventCreate(
            tenant_id=uuid4(),
            domain=Domain.LIVESTOCK,
            category=Category.PRODUCAO,
            source="pecuaria.pesagem",
            occurred_at=datetime.now(timezone.utc),
            ingested_at=datetime.now(timezone.utc),
            payload={},
        )


def test_alert_indicator_create_valid_numeric_and_without_value_is_allowed() -> None:
    numeric = AlertIndicatorCreate(
        tenant_id=uuid4(),
        domain=Domain.FINANCE,
        category=Category.FINANCEIRO,
        key="saldo_caixa",
        label="Saldo de caixa",
        value_numeric=Decimal("1234.567890"),
        computed_at=datetime.now(timezone.utc),
        inputs=["lancamento:1", "lancamento:2"],
        confidence=Decimal("0.875"),
        calculation_version="1.0.0",
    )
    assert numeric.value_numeric == Decimal("1234.567890")

    marker = AlertIndicatorCreate(
        tenant_id=uuid4(),
        domain=Domain.SYSTEM,
        category=Category.GOVERNANCA,
        key="sync_ok",
        label="Sincronização concluída",
        computed_at=datetime.now(timezone.utc),
        inputs=["event:sync-1"],
        calculation_version="1.0.0",
    )
    assert marker.value_numeric is None
    assert marker.value_text is None
    assert marker.value_bool is None


def test_alert_indicator_create_rejects_multiple_values() -> None:
    with pytest.raises(ValidationError):
        AlertIndicatorCreate(
            tenant_id=uuid4(),
            domain=Domain.FINANCE,
            category=Category.FINANCEIRO,
            key="saldo_caixa",
            label="Saldo de caixa",
            value_numeric=Decimal("10.0"),
            value_text="positivo",
            computed_at=datetime.now(timezone.utc),
            inputs=["lancamento:1"],
            calculation_version="1.0.0",
        )


@pytest.mark.parametrize(
    "confidence",
    [Decimal("-0.001"), Decimal("1.001")],
)
def test_confidence_out_of_range_is_rejected(confidence: Decimal) -> None:
    with pytest.raises(ValidationError):
        AlertIndicatorCreate(
            tenant_id=uuid4(),
            domain=Domain.FINANCE,
            category=Category.FINANCEIRO,
            key="saldo_caixa",
            label="Saldo de caixa",
            value_numeric=Decimal("10.0"),
            computed_at=datetime.now(timezone.utc),
            inputs=["lancamento:1"],
            confidence=confidence,
            calculation_version="1.0.0",
        )


def test_operational_alert_create_valid() -> None:
    schema = OperationalAlertCreate(
        tenant_id=uuid4(),
        unidade_produtiva_id=uuid4(),
        domain=Domain.LIVESTOCK,
        category=Category.SANITARIO,
        title="Vacinação atrasada",
        message="O lote 12 está com vacinação em atraso há 3 dias.",
        severity=Severity.CRITICAL,
        priority=Priority.URGENT,
        status="OPEN",
        confidence=Decimal("0.900"),
        trigger_type="RULE",
        source_type="pecuaria.vacinacao",
        source_id="rule-01",
        source_event_ids=[uuid4()],
        source_indicator_ids=[uuid4()],
        dedupe_key="tenant-1:lote-12:vacinacao-atrasada",
        action_label="Registrar vacinação",
        action_url="/dashboard/pecuaria/lotes/12/vacinacao",
        context={"lote": "12"},
        expires_at=datetime.now(timezone.utc),
    )
    assert schema.dedupe_key.startswith("tenant-1")


@pytest.mark.parametrize(
    "field_name,value",
    [
        ("severity", "SEVERE"),
        ("priority", "P0"),
        ("status", "DONE"),
    ],
)
def test_operational_alert_rejects_invalid_enums(field_name: str, value: str) -> None:
    base = dict(
        tenant_id=uuid4(),
        domain=Domain.LIVESTOCK,
        category=Category.SANITARIO,
        title="Vacinação atrasada",
        message="O lote 12 está com vacinação em atraso há 3 dias.",
        severity=Severity.WARNING,
        priority=Priority.NORMAL,
        status=AlertStatus.OPEN,  # type: ignore[name-defined]
        trigger_type="RULE",
        source_type="pecuaria.vacinacao",
        source_id="rule-01",
        source_event_ids=[uuid4()],
        source_indicator_ids=[uuid4()],
        dedupe_key="tenant-1:lote-12:vacinacao-atrasada",
    )
    base[field_name] = value
    with pytest.raises(ValidationError):
        OperationalAlertCreate(**base)


def test_alert_insight_create_valid() -> None:
    schema = AlertInsightCreate(
        tenant_id=uuid4(),
        domain=Domain.FINANCE,
        category=Category.FINANCEIRO,
        title="Fluxo de caixa crítico",
        summary="O caixa está abaixo do mínimo operacional.",
        narrative="A fazenda acumulou despesas superiores às entradas no período.",
        severity=Severity.CRITICAL,
        priority=Priority.URGENT,
        confidence=Decimal("0.812"),
        evidence_event_ids=[uuid4()],
        evidence_indicator_ids=[uuid4()],
        evidence_alert_ids=[uuid4()],
        generated_by="ANALYTICS",
        generated_at=datetime.now(timezone.utc),
        metadata={"narrative_version": "1.0.0"},
    )
    assert schema.generated_by == "ANALYTICS"


def test_alert_lifecycle_event_create_valid() -> None:
    schema = AlertLifecycleEventCreate(
        tenant_id=uuid4(),
        alert_id=uuid4(),
        actor_id=uuid4(),
        action_type="ACKNOWLEDGE",
        previous_status="OPEN",
        new_status="ACKNOWLEDGED",
        payload={"note": "triado no dashboard"},
        source_channel="dashboard",
    )
    assert schema.action_type == "ACKNOWLEDGE"


def test_alert_lifecycle_event_rejects_invalid_action_type() -> None:
    with pytest.raises(ValidationError):
        AlertLifecycleEventCreate(
            tenant_id=uuid4(),
            alert_id=uuid4(),
            action_type="APPROVE",
            previous_status="OPEN",
            new_status="ACKNOWLEDGED",
            source_channel="dashboard",
        )
