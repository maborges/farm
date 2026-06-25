from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text

from alert_engine.models import AlertLifecycleEvent, AlertStatus, OperationalAlert
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService
from core.exceptions import BusinessRuleError, EntityNotFoundError


ADMIN_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


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


def _alert_payload(
    tenant_id: uuid.UUID,
    *,
    dedupe_key: str = "tenant:lote-12:vacinacao-atrasada",
    message: str = "O lote 12 está com vacinação em atraso há 3 dias.",
    severity: str = "CRITICAL",
    priority: str = "URGENT",
) -> OperationalAlertCreate:
    return OperationalAlertCreate(
        tenant_id=tenant_id,
        unidade_produtiva_id=None,
        domain="LIVESTOCK",
        category="SANITARIO",
        title="Vacinação atrasada",
        message=message,
        severity=severity,
        priority=priority,
        status="OPEN",
        confidence=0.9,
        trigger_type="RULE",
        source_type="pecuaria.vacinacao",
        source_id="rule-01",
        source_event_ids=[uuid.uuid4()],
        source_indicator_ids=[uuid.uuid4()],
        dedupe_key=dedupe_key,
        action_label="Registrar vacinação",
        action_url="/dashboard/pecuaria/lotes/12/vacinacao",
        context={"lote": "12"},
    )


async def _count_alerts(session, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count(OperationalAlert.id)).where(OperationalAlert.tenant_id == tenant_id)
    return int((await session.execute(stmt)).scalar_one() or 0)


async def _count_lifecycle_events(session, tenant_id: uuid.UUID) -> int:
    stmt = select(func.count(AlertLifecycleEvent.id)).where(AlertLifecycleEvent.tenant_id == tenant_id)
    return int((await session.execute(stmt)).scalar_one() or 0)


@pytest.mark.asyncio
async def test_create_alert_and_create_lifecycle_event(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    alert = await service.create_or_update_alert(_alert_payload(tenant_id))

    assert alert.status == AlertStatus.OPEN.value
    assert await _count_alerts(session, tenant_id) == 1
    assert await _count_lifecycle_events(session, tenant_id) == 1

    event = (
        await session.execute(
            select(AlertLifecycleEvent).where(AlertLifecycleEvent.alert_id == alert.id)
        )
    ).scalar_one()
    assert event.action_type == "CREATE"
    assert event.previous_status == "OPEN"
    assert event.new_status == "OPEN"
    assert event.source_channel == "ENGINE"
    assert event.payload["created_by"] == "ENGINE"


@pytest.mark.asyncio
async def test_dedupe_updates_active_alert_without_duplication(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    first = await service.create_or_update_alert(_alert_payload(tenant_id))
    second = await service.create_or_update_alert(
        _alert_payload(
            tenant_id,
            message="Vacinação ainda atrasada, com piora do cenário.",
            priority="HIGH",
        )
    )

    assert second.id == first.id
    assert second.message == "Vacinação ainda atrasada, com piora do cenário."
    assert second.priority == "HIGH"
    assert await _count_alerts(session, tenant_id) == 1
    assert await _count_lifecycle_events(session, tenant_id) == 1


@pytest.mark.asyncio
async def test_dedupe_creates_new_alert_after_resolution(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    first = await service.create_or_update_alert(_alert_payload(tenant_id))
    await service.resolve_alert(first.id, ADMIN_USER_ID, resolution_note="Concluído")
    second = await service.create_or_update_alert(_alert_payload(tenant_id))

    assert second.id != first.id
    assert await _count_alerts(session, tenant_id) == 2
    assert second.status == AlertStatus.OPEN.value


@pytest.mark.asyncio
async def test_acknowledge_changes_status_and_creates_lifecycle(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    alert = await service.create_or_update_alert(_alert_payload(tenant_id))
    updated = await service.acknowledge_alert(alert.id, ADMIN_USER_ID, comment="Triado")

    assert updated.status == AlertStatus.ACKNOWLEDGED.value
    assert updated.acknowledged_by == ADMIN_USER_ID
    assert updated.acknowledged_at is not None

    event = (
        await session.execute(
            select(AlertLifecycleEvent)
            .where(AlertLifecycleEvent.alert_id == alert.id)
            .order_by(AlertLifecycleEvent.created_at.desc())
        )
    ).scalars().first()
    assert event.action_type == "ACKNOWLEDGE"
    assert event.previous_status == "OPEN"
    assert event.new_status == "ACKNOWLEDGED"
    assert event.payload["comment"] == "Triado"


@pytest.mark.asyncio
async def test_snooze_changes_status_and_creates_lifecycle(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    alert = await service.create_or_update_alert(_alert_payload(tenant_id))
    until = datetime.now(timezone.utc) + timedelta(hours=2)
    updated = await service.snooze_alert(alert.id, ADMIN_USER_ID, until, reason="Aguardar inspeção")

    assert updated.status == AlertStatus.SNOOZED.value
    assert updated.expires_at == until

    event = (
        await session.execute(
            select(AlertLifecycleEvent)
            .where(AlertLifecycleEvent.alert_id == alert.id)
            .order_by(AlertLifecycleEvent.created_at.desc())
        )
    ).scalars().first()
    assert event.action_type == "SNOOZE"
    assert event.previous_status == "OPEN"
    assert event.new_status == "SNOOZED"
    assert event.payload["reason"] == "Aguardar inspeção"


@pytest.mark.asyncio
async def test_snooze_in_the_past_fails(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    alert = await service.create_or_update_alert(_alert_payload(tenant_id))
    with pytest.raises(BusinessRuleError):
        await service.snooze_alert(
            alert.id,
            ADMIN_USER_ID,
            datetime.now(timezone.utc) - timedelta(minutes=1),
            reason="inválido",
        )


@pytest.mark.asyncio
async def test_resolve_changes_status_and_creates_lifecycle(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    alert = await service.create_or_update_alert(_alert_payload(tenant_id))
    updated = await service.resolve_alert(alert.id, ADMIN_USER_ID, resolution_note="Ok")

    assert updated.status == AlertStatus.RESOLVED.value
    assert updated.resolved_by == ADMIN_USER_ID
    assert updated.resolved_at is not None

    event = (
        await session.execute(
            select(AlertLifecycleEvent)
            .where(AlertLifecycleEvent.alert_id == alert.id)
            .order_by(AlertLifecycleEvent.created_at.desc())
        )
    ).scalars().first()
    assert event.action_type == "RESOLVE"
    assert event.previous_status == "OPEN"
    assert event.new_status == "RESOLVED"


@pytest.mark.asyncio
async def test_dismiss_changes_status_and_creates_lifecycle(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    alert = await service.create_or_update_alert(_alert_payload(tenant_id))
    updated = await service.dismiss_alert(alert.id, ADMIN_USER_ID, reason="Duplicado")

    assert updated.status == AlertStatus.CANCELLED.value
    event = (
        await session.execute(
            select(AlertLifecycleEvent)
            .where(AlertLifecycleEvent.alert_id == alert.id)
            .order_by(AlertLifecycleEvent.created_at.desc())
        )
    ).scalars().first()
    assert event.action_type == "DISMISS"
    assert event.previous_status == "OPEN"
    assert event.new_status == "CANCELLED"
    assert event.payload["reason"] == "Duplicado"


@pytest.mark.asyncio
async def test_invalid_transition_fails(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    alert = await service.create_or_update_alert(_alert_payload(tenant_id))
    await service.resolve_alert(alert.id, ADMIN_USER_ID, resolution_note="Ok")

    with pytest.raises(BusinessRuleError):
        await service.acknowledge_alert(alert.id, ADMIN_USER_ID)


@pytest.mark.asyncio
async def test_other_tenant_is_not_found(session, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    await _ensure_tenant(session, outro_tenant_id)
    service_a = AlertLifecycleService(session, tenant_id)
    service_b = AlertLifecycleService(session, outro_tenant_id)

    alert = await service_a.create_or_update_alert(_alert_payload(tenant_id))

    with pytest.raises(EntityNotFoundError):
        await service_b.resolve_alert(alert.id, ADMIN_USER_ID, resolution_note="não pode")


@pytest.mark.asyncio
async def test_lifecycle_event_preserves_previous_and_new_status(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    alert = await service.create_or_update_alert(_alert_payload(tenant_id))
    until = datetime.now(timezone.utc) + timedelta(hours=1)
    await service.snooze_alert(alert.id, ADMIN_USER_ID, until, reason="aguardar")

    event = (
        await session.execute(
            select(AlertLifecycleEvent)
            .where(AlertLifecycleEvent.alert_id == alert.id)
            .order_by(AlertLifecycleEvent.created_at.desc())
        )
    ).scalars().first()
    assert event.previous_status == "OPEN"
    assert event.new_status == "SNOOZED"

