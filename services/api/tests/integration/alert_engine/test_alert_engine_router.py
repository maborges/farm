from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from alert_engine.models import AlertStatus, Category, Domain, Priority, Severity
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService
from core.models.tenant import Tenant
from core.services.auth_service import AuthService


pytestmark = pytest.mark.asyncio

ADMIN_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")


async def _ensure_tenant(session, tenant_id: uuid.UUID) -> None:
    if await session.get(Tenant, tenant_id):
        return
    session.add(
        Tenant(
            id=tenant_id,
            nome=f"Tenant {tenant_id.hex[:8]}",
            documento=tenant_id.hex[:11],
            ativo=True,
        )
    )
    await session.commit()


def _headers_for_tenant(tenant_id: uuid.UUID) -> dict[str, str]:
    token = AuthService(MagicMock()).create_access_token(
        {
            "sub": str(ADMIN_USER_ID),
            "tenant_id": str(tenant_id),
            "modules": ["CORE"],
            "fazendas_auth": [{"id": str(uuid.uuid4()), "role": "admin"}],
            "is_superuser": False,
            "plan_tier": "PROFISSIONAL",
        },
        expires_delta=timedelta(hours=1),
    )
    return {"Authorization": f"Bearer {token}"}


def _payload(
    tenant_id: uuid.UUID,
    *,
    domain: Domain,
    category: Category,
    severity: Severity,
    priority: Priority,
    dedupe_key: str,
    source_type: str,
    source_id: str,
    title: str,
    message: str,
) -> OperationalAlertCreate:
    return OperationalAlertCreate(
        tenant_id=tenant_id,
        domain=domain,
        category=category,
        title=title,
        message=message,
        severity=severity,
        priority=priority,
        status=AlertStatus.OPEN,
        confidence=0.9,
        trigger_type="RULE",
        source_type=source_type,
        source_id=source_id,
        source_event_ids=[uuid.uuid4()],
        source_indicator_ids=[uuid.uuid4()],
        dedupe_key=dedupe_key,
    )


async def _create_alert(
    session,
    tenant_id: uuid.UUID,
    *,
    domain: Domain,
    category: Category,
    severity: Severity,
    priority: Priority,
    dedupe_key: str,
    source_type: str,
    source_id: str,
    title: str,
    message: str,
) -> object:
    service = AlertLifecycleService(session, tenant_id)
    alert = await service.create_or_update_alert(
        _payload(
            tenant_id,
            domain=domain,
            category=category,
            severity=severity,
            priority=priority,
            dedupe_key=dedupe_key,
            source_type=source_type,
            source_id=source_id,
            title=title,
            message=message,
        )
    )
    await session.commit()
    return alert


async def _set_created_at(session, tenant_id: uuid.UUID, alert_id: uuid.UUID, when: datetime) -> None:
    await session.execute(text(f"SET LOCAL app.current_tenant_id = '{tenant_id}';"))
    await session.execute(
        text("UPDATE operational_alerts SET created_at = :when WHERE id = :id AND tenant_id = :tenant_id"),
        {"when": when, "id": str(alert_id), "tenant_id": str(tenant_id)},
    )
    await session.commit()


@pytest.mark.asyncio
async def test_get_alerts_empty_and_summary_empty(client: AsyncClient, session) -> None:
    tenant_id = uuid.uuid4()
    await _ensure_tenant(session, tenant_id)
    headers = _headers_for_tenant(tenant_id)

    response = await client.get("/api/v1/alerts", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}

    summary = await client.get("/api/v1/alerts/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["total_open"] == 0
    assert body["max_severity"] is None
    assert body["max_priority"] is None
    assert body["most_critical_domain"] is None
    assert len(body["top_alerts"]) == 0


@pytest.mark.asyncio
async def test_get_alerts_filters_pagination_and_tenant_query_ignored(client: AsyncClient, session) -> None:
    tenant_id = uuid.uuid4()
    outro_tenant_id = uuid.uuid4()
    await _ensure_tenant(session, tenant_id)
    await _ensure_tenant(session, outro_tenant_id)
    headers = _headers_for_tenant(tenant_id)
    other_headers = _headers_for_tenant(outro_tenant_id)

    alert_a = await _create_alert(
        session,
        tenant_id,
        domain=Domain.LIVESTOCK,
        category=Category.SANITARIO,
        severity=Severity.CRITICAL,
        priority=Priority.URGENT,
        dedupe_key="a",
        source_type="pecuaria.vacinacao",
        source_id="vac-1",
        title="A",
        message="A",
    )
    alert_b = await _create_alert(
        session,
        tenant_id,
        domain=Domain.LIVESTOCK,
        category=Category.PRODUCAO,
        severity=Severity.CRITICAL,
        priority=Priority.HIGH,
        dedupe_key="b",
        source_type="pecuaria.pesagem",
        source_id="pes-1",
        title="B",
        message="B",
    )
    alert_c = await _create_alert(
        session,
        tenant_id,
        domain=Domain.FINANCE,
        category=Category.FINANCEIRO,
        severity=Severity.WARNING,
        priority=Priority.NORMAL,
        dedupe_key="c",
        source_type="financeiro.caixa",
        source_id="cash-1",
        title="C",
        message="C",
    )
    other_alert = await _create_alert(
        session,
        outro_tenant_id,
        domain=Domain.SYSTEM,
        category=Category.GOVERNANCA,
        severity=Severity.INFO,
        priority=Priority.LOW,
        dedupe_key="other",
        source_type="system.rule",
        source_id="sys-1",
        title="Outro",
        message="Outro",
    )

    now = datetime.now(timezone.utc)
    await _set_created_at(session, tenant_id, alert_a.id, now - timedelta(days=3))
    await _set_created_at(session, tenant_id, alert_b.id, now - timedelta(days=2))
    await _set_created_at(session, tenant_id, alert_c.id, now - timedelta(days=1))
    await _set_created_at(session, outro_tenant_id, other_alert.id, now)

    service = AlertLifecycleService(session, tenant_id)
    await service.acknowledge_alert(alert_b.id, ADMIN_USER_ID, comment="triado")
    await session.commit()

    response = await client.get("/api/v1/alerts", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    assert [item["id"] for item in body["items"]] == [str(alert_a.id), str(alert_b.id), str(alert_c.id)]

    domain_result = await client.get("/api/v1/alerts", headers=headers, params={"domain": "LIVESTOCK"})
    assert domain_result.status_code == 200, domain_result.text
    assert domain_result.json()["total"] == 2

    status_result = await client.get("/api/v1/alerts", headers=headers, params={"status": "ACKNOWLEDGED"})
    assert status_result.status_code == 200, status_result.text
    assert [item["id"] for item in status_result.json()["items"]] == [str(alert_b.id)]

    severity_result = await client.get("/api/v1/alerts", headers=headers, params={"severity": "CRITICAL"})
    assert severity_result.status_code == 200, severity_result.text
    assert {item["id"] for item in severity_result.json()["items"]} == {str(alert_a.id), str(alert_b.id)}

    source_result = await client.get(
        "/api/v1/alerts",
        headers=headers,
        params={"source_type": "pecuaria.vacinacao", "source_id": "vac-1"},
    )
    assert source_result.status_code == 200, source_result.text
    assert [item["id"] for item in source_result.json()["items"]] == [str(alert_a.id)]

    page_result = await client.get("/api/v1/alerts", headers=headers, params={"limit": 1, "offset": 1})
    assert page_result.status_code == 200, page_result.text
    assert page_result.json()["total"] == 3
    assert len(page_result.json()["items"]) == 1
    assert page_result.json()["items"][0]["id"] == str(alert_b.id)

    ignored = await client.get(
        "/api/v1/alerts",
        headers=headers,
        params={"tenant_id": str(outro_tenant_id)},
    )
    assert ignored.status_code == 200, ignored.text
    assert {item["id"] for item in ignored.json()["items"]} == {str(alert_a.id), str(alert_b.id), str(alert_c.id)}

    other_tenant = await client.get("/api/v1/alerts", headers=other_headers)
    assert other_tenant.status_code == 200, other_tenant.text
    assert other_tenant.json()["total"] == 1
    assert other_tenant.json()["items"][0]["id"] == str(other_alert.id)


@pytest.mark.asyncio
async def test_get_alert_summary_counts_active_only_and_respects_limit(client: AsyncClient, session) -> None:
    tenant_id = uuid.uuid4()
    await _ensure_tenant(session, tenant_id)
    headers = _headers_for_tenant(tenant_id)

    active_1 = await _create_alert(
        session,
        tenant_id,
        domain=Domain.FINANCE,
        category=Category.FINANCEIRO,
        severity=Severity.CRITICAL,
        priority=Priority.URGENT,
        dedupe_key="active-1",
        source_type="financeiro.caixa",
        source_id="cash-crit",
        title="Caixa crítico",
        message="Caixa crítico",
    )
    active_2 = await _create_alert(
        session,
        tenant_id,
        domain=Domain.FINANCE,
        category=Category.ECONOMICO,
        severity=Severity.WARNING,
        priority=Priority.HIGH,
        dedupe_key="active-2",
        source_type="financeiro.risco",
        source_id="risk-high",
        title="Risco",
        message="Risco",
    )
    active_3 = await _create_alert(
        session,
        tenant_id,
        domain=Domain.LIVESTOCK,
        category=Category.SANITARIO,
        severity=Severity.WARNING,
        priority=Priority.NORMAL,
        dedupe_key="active-3",
        source_type="pecuaria.vacinacao",
        source_id="vac-warn",
        title="Vacinação",
        message="Vacinação",
    )
    resolved = await _create_alert(
        session,
        tenant_id,
        domain=Domain.AGRICULTURE,
        category=Category.PRODUCAO,
        severity=Severity.EMERGENCY,
        priority=Priority.URGENT,
        dedupe_key="resolved-1",
        source_type="agricola.producao",
        source_id="ag-1",
        title="Produção",
        message="Produção",
    )
    await AlertLifecycleService(session, tenant_id).resolve_alert(resolved.id, ADMIN_USER_ID, resolution_note="encerrado")
    await session.commit()

    cancelled = await _create_alert(
        session,
        tenant_id,
        domain=Domain.OPERATIONS,
        category=Category.OPERACIONAL,
        severity=Severity.CRITICAL,
        priority=Priority.URGENT,
        dedupe_key="cancelled-1",
        source_type="operacional.tarefa",
        source_id="task-1",
        title="Tarefa",
        message="Tarefa",
    )
    await AlertLifecycleService(session, tenant_id).dismiss_alert(cancelled.id, ADMIN_USER_ID, reason="duplicado")
    await session.commit()

    expired = await _create_alert(
        session,
        tenant_id,
        domain=Domain.SYSTEM,
        category=Category.GOVERNANCA,
        severity=Severity.EMERGENCY,
        priority=Priority.URGENT,
        dedupe_key="expired-1",
        source_type="system.rule",
        source_id="sys-exp",
        title="Expirado",
        message="Expirado",
    )
    await AlertLifecycleService(session, tenant_id)._set_rls_context()
    await session.execute(
        text(
            "UPDATE operational_alerts SET status = 'EXPIRED', updated_at = now() "
            "WHERE id = :id AND tenant_id = :tenant_id"
        ),
        {"id": str(expired.id), "tenant_id": str(tenant_id)},
    )
    await session.commit()

    summary = await client.get("/api/v1/alerts/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["total_open"] == 3
    assert body["max_severity"] == "CRITICAL"
    assert body["max_priority"] == "URGENT"
    assert body["most_critical_domain"] == "FINANCE"
    assert body["by_domain"]["FINANCE"] == {"open": 2, "critical": 1, "urgent": 1}
    assert body["by_domain"]["LIVESTOCK"] == {"open": 1, "critical": 0, "urgent": 0}
    assert body["by_domain"]["AGRICULTURE"] == {"open": 0, "critical": 0, "urgent": 0}
    assert body["by_domain"]["OPERATIONS"] == {"open": 0, "critical": 0, "urgent": 0}
    assert [item["id"] for item in body["top_alerts"]] == [str(active_1.id), str(active_2.id), str(active_3.id)]

    filtered = await client.get("/api/v1/alerts/summary", headers=headers, params={"domain": "FINANCE"})
    assert filtered.status_code == 200, filtered.text
    filtered_body = filtered.json()
    assert filtered_body["total_open"] == 2
    assert filtered_body["by_domain"]["FINANCE"] == {"open": 2, "critical": 1, "urgent": 1}

    limited = await client.get("/api/v1/alerts/summary", headers=headers, params={"limit": 2})
    assert limited.status_code == 200, limited.text
    assert len(limited.json()["top_alerts"]) == 2
