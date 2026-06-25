from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from alert_engine.models import AlertStatus, Domain, Priority, Severity, OperationalAlert
from alert_engine.service import AlertLifecycleService


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


def _payload(
    tenant_id: uuid.UUID,
    *,
    domain: str,
    category: str,
    severity: str,
    priority: str,
    status: str = "OPEN",
    source_type: str = "engine.rule",
    source_id: str = "rule-1",
    dedupe_key: str,
    title: str = "Alerta",
    message: str = "Mensagem",
):
    from alert_engine.schemas import OperationalAlertCreate

    return OperationalAlertCreate(
        tenant_id=tenant_id,
        domain=domain,
        category=category,
        title=title,
        message=message,
        severity=severity,
        priority=priority,
        status=status,
        confidence=0.9,
        trigger_type="RULE",
        source_type=source_type,
        source_id=source_id,
        source_event_ids=[uuid.uuid4()],
        source_indicator_ids=[uuid.uuid4()],
        dedupe_key=dedupe_key,
    )


async def _create_alert(service: AlertLifecycleService, payload) -> OperationalAlert:
    return await service.create_or_update_alert(payload)


async def _set_created_at(session, tenant_id: uuid.UUID, alert_id: uuid.UUID, when: datetime) -> None:
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))
    await session.execute(
        text("UPDATE operational_alerts SET created_at = :when WHERE id = :id AND tenant_id = :tenant_id"),
        {"when": when, "id": str(alert_id), "tenant_id": str(tenant_id)},
    )


@pytest.mark.asyncio
async def test_list_empty_and_summary_zeros(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    result = await service.list_alerts()
    summary = await service.get_alert_summary()

    assert result.total == 0
    assert result.alerts == []
    assert summary.total_open == 0
    assert summary.max_severity is None
    assert summary.max_priority is None
    assert summary.most_critical_domain is None
    assert set(summary.by_domain.keys()) == {
        "AGRICULTURE",
        "LIVESTOCK",
        "FINANCE",
        "OPERATIONS",
        "FIELD",
        "SYSTEM",
    }
    assert all(item.open == 0 and item.critical == 0 and item.urgent == 0 for item in summary.by_domain.values())
    assert summary.top_alerts == []


@pytest.mark.asyncio
async def test_list_filters_pagination_and_ordering(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    alert_a = await _create_alert(
        service,
        _payload(
            tenant_id,
            domain="LIVESTOCK",
            category="SANITARIO",
            severity="CRITICAL",
            priority="URGENT",
            source_type="pecuaria.vacinacao",
            source_id="vac-1",
            dedupe_key="a",
            title="A",
            message="A",
        ),
    )
    alert_b = await _create_alert(
        service,
        _payload(
            tenant_id,
            domain="LIVESTOCK",
            category="PRODUCAO",
            severity="CRITICAL",
            priority="HIGH",
            source_type="pecuaria.pesagem",
            source_id="pes-1",
            dedupe_key="b",
            title="B",
            message="B",
        ),
    )
    alert_c = await _create_alert(
        service,
        _payload(
            tenant_id,
            domain="FINANCE",
            category="FINANCEIRO",
            severity="WARNING",
            priority="NORMAL",
            source_type="financeiro.caixa",
            source_id="cash-1",
            dedupe_key="c",
            title="C",
            message="C",
        ),
    )
    past = datetime.now(timezone.utc) - timedelta(days=5)
    recent = datetime.now(timezone.utc) - timedelta(days=1)
    newest = datetime.now(timezone.utc)
    await _set_created_at(session, tenant_id, alert_a.id, past)
    await _set_created_at(session, tenant_id, alert_b.id, recent)
    await _set_created_at(session, tenant_id, alert_c.id, newest)
    await service.acknowledge_alert(alert_b.id, ADMIN_USER_ID, comment="triado")

    all_alerts = await service.list_alerts()
    assert all_alerts.total == 3
    assert [item.id for item in all_alerts.alerts] == [alert_a.id, alert_b.id, alert_c.id]

    domain_result = await service.list_alerts(domain="LIVESTOCK")
    assert domain_result.total == 2
    assert {item.id for item in domain_result.alerts} == {alert_a.id, alert_b.id}

    category_result = await service.list_alerts(category="FINANCEIRO")
    assert [item.id for item in category_result.alerts] == [alert_c.id]

    severity_result = await service.list_alerts(severity="CRITICAL")
    assert {item.id for item in severity_result.alerts} == {alert_a.id, alert_b.id}

    priority_result = await service.list_alerts(priority="URGENT")
    assert [item.id for item in priority_result.alerts] == [alert_a.id]

    status_result = await service.list_alerts(status=AlertStatus.ACKNOWLEDGED)
    assert [item.id for item in status_result.alerts] == [alert_b.id]

    source_result = await service.list_alerts(source_type="pecuaria.vacinacao", source_id="vac-1")
    assert [item.id for item in source_result.alerts] == [alert_a.id]

    date_result = await service.list_alerts(
        date_from=datetime.now(timezone.utc) - timedelta(days=2),
        date_to=datetime.now(timezone.utc) + timedelta(days=1),
    )
    assert {item.id for item in date_result.alerts} == {alert_b.id, alert_c.id}

    page_result = await service.list_alerts(limit=1, offset=1)
    assert page_result.total == 3
    assert len(page_result.alerts) == 1
    assert page_result.alerts[0].id == alert_b.id


@pytest.mark.asyncio
async def test_other_tenant_isolation(session, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    await _ensure_tenant(session, outro_tenant_id)
    service_a = AlertLifecycleService(session, tenant_id)
    service_b = AlertLifecycleService(session, outro_tenant_id)

    await _create_alert(
        service_a,
        _payload(
            tenant_id,
            domain="SYSTEM",
            category="GOVERNANCA",
            severity="INFO",
            priority="LOW",
            dedupe_key="tenant-a",
            source_type="system.rule",
            source_id="sys-1",
        ),
    )

    result = await service_b.list_alerts()
    summary = await service_b.get_alert_summary()

    assert result.total == 0
    assert summary.total_open == 0


@pytest.mark.asyncio
async def test_summary_counts_active_only_and_top_alerts_limit(session, tenant_id: uuid.UUID) -> None:
    await _ensure_tenant(session, tenant_id)
    service = AlertLifecycleService(session, tenant_id)

    active_1 = await _create_alert(
        service,
        _payload(
            tenant_id,
            domain="FINANCE",
            category="FINANCEIRO",
            severity="CRITICAL",
            priority="URGENT",
            dedupe_key="active-1",
            source_type="financeiro.caixa",
            source_id="cash-crit",
            title="Caixa crítico",
        ),
    )
    active_2 = await _create_alert(
        service,
        _payload(
            tenant_id,
            domain="FINANCE",
            category="ECONOMICO",
            severity="WARNING",
            priority="HIGH",
            dedupe_key="active-2",
            source_type="financeiro.risco",
            source_id="risk-high",
            title="Risco econômico",
        ),
    )
    active_3 = await _create_alert(
        service,
        _payload(
            tenant_id,
            domain="LIVESTOCK",
            category="SANITARIO",
            severity="WARNING",
            priority="NORMAL",
            dedupe_key="active-3",
            source_type="pecuaria.vacinacao",
            source_id="vac-warn",
            title="Vacinação",
        ),
    )
    active_4 = await _create_alert(
        service,
        _payload(
            tenant_id,
            domain="AGRICULTURE",
            category="PRODUCAO",
            severity="EMERGENCY",
            priority="URGENT",
            dedupe_key="resolved-1",
            source_type="agricola.producao",
            source_id="ag-1",
            title="Produção",
        ),
    )
    await service.resolve_alert(active_4.id, ADMIN_USER_ID, resolution_note="encerrado")

    cancelled = await _create_alert(
        service,
        _payload(
            tenant_id,
            domain="OPERATIONS",
            category="OPERACIONAL",
            severity="CRITICAL",
            priority="URGENT",
            dedupe_key="cancelled-1",
            source_type="operacional.tarefa",
            source_id="task-1",
            title="Tarefa",
        ),
    )
    await service.dismiss_alert(cancelled.id, ADMIN_USER_ID, reason="duplicado")

    expired = await _create_alert(
        service,
        _payload(
            tenant_id,
            domain="SYSTEM",
            category="GOVERNANCA",
            severity="EMERGENCY",
            priority="URGENT",
            dedupe_key="expired-1",
            source_type="system.rule",
            source_id="sys-exp",
            title="Expirado",
        ),
    )
    await service._set_rls_context()
    await session.execute(
        text(
            "UPDATE operational_alerts SET status = 'EXPIRED', updated_at = now() "
            "WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": str(expired.id), "tenant_id": str(tenant_id)},
    )

    summary = await service.get_alert_summary()

    assert summary.total_open == 3
    assert summary.max_severity == Severity.CRITICAL
    assert summary.max_priority == Priority.URGENT
    assert summary.most_critical_domain == Domain.FINANCE
    assert summary.by_domain["FINANCE"].open == 2
    assert summary.by_domain["FINANCE"].critical == 1
    assert summary.by_domain["FINANCE"].urgent == 1
    assert summary.by_domain["LIVESTOCK"].open == 1
    assert summary.by_domain["AGRICULTURE"].open == 0
    assert summary.by_domain["OPERATIONS"].open == 0
    assert len(summary.top_alerts) == 3
    assert [item.id for item in summary.top_alerts] == [active_1.id, active_2.id, active_3.id]

    limited = await service.get_alert_summary(top_limit=2)
    assert len(limited.top_alerts) == 2
