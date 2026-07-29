from __future__ import annotations

import importlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from core.exceptions import EntityNotFoundError, TenantViolationError
from recommendations.lifecycle_service import RecommendationLifecycleService
from recommendations.schemas import RecommendationCandidate


ADMIN_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")
pytestmark = pytest.mark.integration
router_module = importlib.import_module("recommendations.router")
metrics_module = importlib.import_module("recommendations.metrics_service")


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
        {"id": str(tenant_id), "nome": f"Tenant {tenant_id.hex[:8]}", "documento": tenant_id.hex[:11]},
    )
    await session.commit()
    # A rota de métricas é uma ação humana governada pelo RBAC. A fixture
    # representa o owner autenticado usado por `_build_client`, não um bypass
    # de autorização.
    await RecommendationLifecycleService(session, tenant_id)._set_rls_context()
    await session.execute(
        text(
            "INSERT INTO tenant_usuarios (id, tenant_id, usuario_id, is_owner, status, created_at) "
            "SELECT :id, :tenant_id, :usuario_id, true, 'ATIVO', now() "
            "WHERE NOT EXISTS ("
            "SELECT 1 FROM tenant_usuarios WHERE tenant_id = :tenant_id AND usuario_id = :usuario_id"
            ")"
        ),
        {"id": str(uuid.uuid4()), "tenant_id": str(tenant_id), "usuario_id": str(ADMIN_USER_ID)},
    )
    await session.commit()


async def _seed_recommendation(
    session,
    tenant_id: uuid.UUID,
    *,
    domain: str,
    priority: str,
    rule_code: str,
    action: str,
    created_at: datetime,
    delta_minutes: int,
    dedupe_suffix: str | None = None,
    unidade_produtiva_id: uuid.UUID | None = None,
) -> uuid.UUID:
    service = RecommendationLifecycleService(session, tenant_id)
    candidate = RecommendationCandidate(
        tenant_id=tenant_id,
        domain=domain,
        priority=priority,
        source_type="SIGNAL",
        action_type="OPEN_ROUTE",
        provider_name=f"provider-{rule_code.lower()}",
        rule_code=rule_code,
        scope_type="SAFRA",
        scope_id=f"scope-{rule_code.lower()}",
        title=f"{rule_code} title",
        summary=f"{rule_code} summary",
        rationale=f"{rule_code} rationale",
        dedupe_key=f"{tenant_id}:{rule_code}:{dedupe_suffix or 'base'}",
        source_signal_ids=[uuid.uuid4()],
        action_target="/dashboard/recommendations",
        unidade_produtiva_id=unidade_produtiva_id,
    )
    recommendation = await service.create_or_update_recommendation(candidate)
    if action == "view":
        await service.mark_viewed(recommendation.id, ADMIN_USER_ID)
    elif action == "accept":
        await service.accept(recommendation.id, ADMIN_USER_ID)
    elif action == "dismiss":
        await service.dismiss(recommendation.id, ADMIN_USER_ID, reason="nao aplicavel")
    elif action == "execute":
        await service.execute(recommendation.id, ADMIN_USER_ID, execution_note="executado")
    elif action == "none":
        pass
    else:
        raise ValueError(f"Unsupported action {action}")
    await _set_result_timestamps(
        session,
        recommendation.id,
        created_at=created_at,
        delta_minutes=delta_minutes,
        action=action,
    )
    await session.commit()
    return recommendation.id


async def _set_result_timestamps(
    session,
    recommendation_id: uuid.UUID,
    *,
    created_at: datetime,
    delta_minutes: int,
    action: str,
) -> None:
    acted_at = created_at + timedelta(minutes=delta_minutes)
    values = {
        "id": str(recommendation_id),
        "created_at": created_at,
        "updated_at": acted_at,
        "viewed_at": acted_at if action == "view" else None,
        "accepted_at": acted_at if action == "accept" else None,
        "dismissed_at": acted_at if action == "dismiss" else None,
        "executed_at": acted_at if action == "execute" else None,
    }
    await session.execute(
        text(
            """
            UPDATE recommendation_results
            SET created_at = :created_at,
                updated_at = :updated_at,
                viewed_at = :viewed_at,
                accepted_at = :accepted_at,
                dismissed_at = :dismissed_at,
                executed_at = :executed_at
            WHERE id = :id
            """
        ),
        values,
    )


async def _ensure_unidade_produtiva(session, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (id, tenant_id, nome, ativo, created_at, updated_at)
            VALUES (:id, :tenant_id, :nome, true, now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {"id": str(unidade_produtiva_id), "tenant_id": str(tenant_id), "nome": "Unidade teste"},
    )
    await session.commit()


def _build_client(session, tenant_id: uuid.UUID) -> AsyncClient:
    app = FastAPI()
    app.include_router(router_module.router, prefix="/api/v1")

    @app.exception_handler(EntityNotFoundError)
    async def _not_found(_, exc: EntityNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TenantViolationError)
    async def _tenant_violation(_, exc: TenantViolationError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    app.dependency_overrides[router_module.get_session] = lambda: session
    app.dependency_overrides[router_module.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[router_module.get_current_user] = lambda: SimpleNamespace(id=ADMIN_USER_ID)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_metrics_summary_by_tenant_and_rates(session, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _ensure_tenant(session, tenant_a)
    await _ensure_tenant(session, tenant_b)
    base = datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc)
    await _seed_recommendation(session, tenant_a, domain="AGRICULTURE", priority="HIGH", rule_code="RULE_VIEW", action="view", created_at=base, delta_minutes=10)
    await _seed_recommendation(session, tenant_a, domain="AGRICULTURE", priority="HIGH", rule_code="RULE_ACCEPT", action="accept", created_at=base + timedelta(minutes=20), delta_minutes=15)
    await _seed_recommendation(session, tenant_a, domain="FINANCE", priority="LOW", rule_code="RULE_DISMISS", action="dismiss", created_at=base + timedelta(minutes=40), delta_minutes=5)
    await _seed_recommendation(session, tenant_a, domain="OPERATIONS", priority="URGENT", rule_code="RULE_EXECUTE", action="execute", created_at=base + timedelta(minutes=60), delta_minutes=8)
    await _seed_recommendation(session, tenant_b, domain="FINANCE", priority="HIGH", rule_code="RULE_OTHER", action="accept", created_at=base, delta_minutes=3)

    service = metrics_module.RecommendationMetricsService(session, tenant_a)
    summary = await service.summary()

    assert summary.tenant_id == tenant_a
    assert summary.total_recommendations == 4
    assert summary.by_domain == {"AGRICULTURE": 2, "FINANCE": 1, "OPERATIONS": 1}
    assert summary.by_status == {"ACCEPTED": 1, "DISMISSED": 1, "EXECUTED": 1, "VIEWED": 1}
    assert summary.by_priority == {"HIGH": 2, "LOW": 1, "URGENT": 1}
    assert summary.viewed_total == 1
    assert summary.accepted_total == 1
    assert summary.dismissed_total == 1
    assert summary.executed_total == 1
    assert summary.view_rate == 0.25
    assert summary.accept_rate == 0.25
    assert summary.dismiss_rate == 0.25
    assert summary.execute_rate == 0.25
    assert summary.avg_time_to_view_seconds == 600.0
    assert summary.avg_time_to_accept_seconds == 900.0
    assert summary.avg_time_to_execute_seconds == 480.0
    assert summary.filters.start_date is None
    assert summary.filters.end_date is None
    assert summary.generated_at is not None
    assert len(summary.timeline) == 1
    assert summary.timeline[0].period == base.date()
    assert summary.timeline[0].total_recommendations == 4
    assert summary.timeline[0].accept_rate == 0.25
    assert set(summary.model_dump().keys()) == {
        "filters",
        "generated_at",
        "tenant_id",
        "total_recommendations",
        "by_domain",
        "by_status",
        "by_priority",
        "viewed_total",
        "accepted_total",
        "dismissed_total",
        "executed_total",
        "expired_total",
        "superseded_total",
        "reopened_total",
        "view_rate",
        "accept_rate",
        "dismiss_rate",
        "execute_rate",
        "avg_time_to_view_seconds",
        "avg_time_to_accept_seconds",
        "avg_time_to_execute_seconds",
        "lifecycle_events_total",
        "timeline",
    }


@pytest.mark.asyncio
async def test_metrics_cross_tenant_and_domain_aggregation(session, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _ensure_tenant(session, tenant_a)
    await _ensure_tenant(session, tenant_b)
    base = datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc)
    await _seed_recommendation(session, tenant_a, domain="AGRICULTURE", priority="HIGH", rule_code="RULE_A1", action="view", created_at=base, delta_minutes=6)
    await _seed_recommendation(session, tenant_a, domain="AGRICULTURE", priority="LOW", rule_code="RULE_A2", action="none", created_at=base + timedelta(minutes=10), delta_minutes=0)
    await _seed_recommendation(session, tenant_a, domain="FINANCE", priority="NORMAL", rule_code="RULE_A3", action="accept", created_at=base + timedelta(minutes=20), delta_minutes=12)
    await _seed_recommendation(session, tenant_b, domain="AGRICULTURE", priority="URGENT", rule_code="RULE_B1", action="execute", created_at=base, delta_minutes=4)

    service = metrics_module.RecommendationMetricsService(session, tenant_a)
    by_domain = await service.by_domain()

    assert len(by_domain.items) == 2
    agriculture = next(item for item in by_domain.items if item.domain == "AGRICULTURE")
    finance = next(item for item in by_domain.items if item.domain == "FINANCE")
    assert agriculture.total == 2
    assert agriculture.by_priority == {"HIGH": 1, "LOW": 1}
    assert agriculture.viewed_total == 1
    assert finance.total == 1
    assert finance.accepted_total == 1
    assert by_domain.filters.domain is None
    assert by_domain.generated_at is not None
    assert set(by_domain.model_dump().keys()) == {"filters", "generated_at", "items"}


@pytest.mark.asyncio
async def test_metrics_by_rule_and_lifecycle(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    base = datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc)
    await _seed_recommendation(session, tenant, domain="AGRICULTURE", priority="HIGH", rule_code="RULE_ALPHA", action="accept", created_at=base, delta_minutes=5, dedupe_suffix="1")
    await _seed_recommendation(session, tenant, domain="AGRICULTURE", priority="HIGH", rule_code="RULE_ALPHA", action="accept", created_at=base + timedelta(minutes=10), delta_minutes=7, dedupe_suffix="2")
    await _seed_recommendation(session, tenant, domain="FINANCE", priority="NORMAL", rule_code="RULE_BETA", action="dismiss", created_at=base + timedelta(minutes=20), delta_minutes=4)
    await _seed_recommendation(session, tenant, domain="OPERATIONS", priority="URGENT", rule_code="RULE_GAMMA", action="execute", created_at=base + timedelta(minutes=30), delta_minutes=3)

    service = metrics_module.RecommendationMetricsService(session, tenant)
    by_rule = await service.by_rule()
    lifecycle = await service.lifecycle()

    assert by_rule.top_by_volume[0].rule_code == "RULE_ALPHA"
    assert by_rule.top_by_volume[0].total == 2
    assert by_rule.top_by_acceptance[0].rule_code == "RULE_ALPHA"
    assert by_rule.top_by_acceptance[0].accepted_total == 2
    assert by_rule.top_by_dismissal[0].rule_code == "RULE_BETA"
    assert by_rule.top_by_dismissal[0].dismissed_total == 1

    assert lifecycle.total_events == 8
    assert lifecycle.created_total == 4
    assert lifecycle.viewed_total == 0
    assert lifecycle.accepted_total == 2
    assert lifecycle.dismissed_total == 1
    assert lifecycle.executed_total == 1
    assert lifecycle.by_action["CREATE"] == 4
    assert lifecycle.by_action["ACCEPT"] == 2
    assert lifecycle.by_action["DISMISS"] == 1
    assert lifecycle.by_action["EXECUTE"] == 1
    assert lifecycle.by_transition["CREATED->CREATED"] == 4
    assert by_rule.filters.domain is None
    assert by_rule.generated_at is not None
    assert lifecycle.generated_at is not None
    assert len(lifecycle.timeline) == 1
    assert set(by_rule.model_dump().keys()) == {"filters", "generated_at", "top_by_volume", "top_by_acceptance", "top_by_dismissal"}
    assert set(lifecycle.model_dump().keys()) == {
        "filters",
        "generated_at",
        "tenant_id",
        "total_events",
        "by_action",
        "by_transition",
        "created_total",
        "viewed_total",
        "accepted_total",
        "dismissed_total",
        "executed_total",
        "expired_total",
        "superseded_total",
        "reopened_total",
        "timeline",
    }


@pytest.mark.asyncio
async def test_metrics_router_summary_and_cross_tenant(session, tenant_id: uuid.UUID) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _ensure_tenant(session, tenant_a)
    await _ensure_tenant(session, tenant_b)
    base = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
    await _seed_recommendation(session, tenant_a, domain="AGRICULTURE", priority="HIGH", rule_code="RULE_WEB", action="view", created_at=base, delta_minutes=9)
    await _seed_recommendation(session, tenant_b, domain="AGRICULTURE", priority="HIGH", rule_code="RULE_OTHER", action="accept", created_at=base, delta_minutes=2)

    async with _build_client(session, tenant_a) as client:
        response = await client.get("/api/v1/recommendations/metrics/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == str(tenant_a)
    assert body["total_recommendations"] == 1
    assert body["by_domain"] == {"AGRICULTURE": 1}
    assert body["view_rate"] == 1.0
    assert body["filters"]["domain"] is None
    assert body["timeline"][0]["period"] == "2026-04-01"


@pytest.mark.asyncio
async def test_metrics_support_period_domain_and_unit_filters(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    unidade_produtiva_id = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    await _ensure_unidade_produtiva(session, tenant, unidade_produtiva_id)
    base = datetime(2026, 5, 12, 7, 0, tzinfo=timezone.utc)
    await _seed_recommendation(
        session,
        tenant,
        domain="AGRICULTURE",
        priority="HIGH",
        rule_code="RULE_FILTERED",
        action="accept",
        created_at=base,
        delta_minutes=11,
        unidade_produtiva_id=unidade_produtiva_id,
    )
    await _seed_recommendation(
        session,
        tenant,
        domain="FINANCE",
        priority="LOW",
        rule_code="RULE_OUTSIDE",
        action="view",
        created_at=base + timedelta(days=2),
        delta_minutes=3,
    )

    async with _build_client(session, tenant) as client:
        response = await client.get(
            "/api/v1/recommendations/metrics/summary",
            params={
                "start_date": base.date().isoformat(),
                "end_date": base.date().isoformat(),
                "domain": "AGRICULTURE",
                "unidade_produtiva_id": str(unidade_produtiva_id),
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total_recommendations"] == 1
    assert body["by_domain"] == {"AGRICULTURE": 1}
    assert body["by_status"] == {"ACCEPTED": 1}
    assert body["filters"]["domain"] == "AGRICULTURE"
    assert body["filters"]["unidade_produtiva_id"] == str(unidade_produtiva_id)
    assert body["timeline"] == [
        {
            "period": base.date().isoformat(),
            "total_recommendations": 1,
            "viewed_total": 0,
            "accepted_total": 1,
            "dismissed_total": 0,
            "executed_total": 0,
            "accept_rate": 1.0,
            "dismissed_rate": 0.0,
            "executed_rate": 0.0,
        }
    ]


def test_metrics_module_does_not_reference_alert_or_notifications() -> None:
    project_root = Path(__file__).resolve().parents[5]
    source = (project_root / "services/api/recommendations/metrics_service.py").read_text(encoding="utf-8")
    forbidden = ("alert_engine", "notifications", "NotificationDispatcher", "provider_registry")
    assert all(token not in source for token in forbidden)
