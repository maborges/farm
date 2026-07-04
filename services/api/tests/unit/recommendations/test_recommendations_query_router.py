from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from core.exceptions import BusinessRuleError, EntityNotFoundError, TenantViolationError
from recommendations.lifecycle_service import RecommendationLifecycleService
from recommendations.schemas import RecommendationCandidate


ADMIN_USER_ID = uuid.UUID("eeeeeeee-0000-0000-0000-000000000005")
pytestmark = pytest.mark.integration
recommendations_router_module = importlib.import_module("recommendations.router")


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


async def _seed_recommendation(
    session,
    tenant_id: uuid.UUID,
    *,
    domain: str,
    priority: str,
    rule_code: str,
    scope_id: str,
    scope_type: str = "SAFRA",
    unidade_produtiva_id: uuid.UUID | None = None,
) -> object:
    service = RecommendationLifecycleService(session, tenant_id)
    candidate = RecommendationCandidate(
        tenant_id=tenant_id,
        unidade_produtiva_id=unidade_produtiva_id,
        domain=domain,
        priority=priority,
        source_type="SIGNAL",
        action_type="OPEN_ROUTE",
        provider_name="seed",
        rule_code=rule_code,
        scope_type=scope_type,
        scope_id=scope_id,
        title=f"{rule_code} title",
        summary=f"{rule_code} summary",
        rationale=f"{rule_code} rationale",
        dedupe_key=f"{tenant_id}:{scope_id}:{rule_code}",
        source_signal_ids=[uuid.uuid4()],
        action_target="/api/v1/recommendations",
    )
    recommendation = await service.create_or_update_recommendation(candidate)
    await session.commit()
    return recommendation


async def _set_created_at(session, recommendation_id: uuid.UUID, created_at: datetime) -> None:
    await session.execute(
        text(
            """
            UPDATE recommendation_results
            SET created_at = :created_at, updated_at = :created_at
            WHERE id = :id
            """
        ),
        {"id": str(recommendation_id), "created_at": created_at},
    )
    await session.commit()


async def _ensure_unidade_produtiva(session, tenant_id: uuid.UUID, unidade_produtiva_id: uuid.UUID) -> None:
    await session.execute(
        text(
            """
            INSERT INTO unidades_produtivas (
                id, tenant_id, nome, ativo, created_at, updated_at
            )
            VALUES (:id, :tenant_id, :nome, true, now(), now())
            ON CONFLICT DO NOTHING
            """
        ),
        {
            "id": str(unidade_produtiva_id),
            "tenant_id": str(tenant_id),
            "nome": f"Unidade {unidade_produtiva_id.hex[:8]}",
        },
    )
    await session.commit()


def _build_client(session, tenant_id: uuid.UUID, current_user_id: uuid.UUID = ADMIN_USER_ID) -> AsyncClient:
    app = FastAPI()
    app.include_router(recommendations_router_module.router, prefix="/api/v1")

    @app.exception_handler(EntityNotFoundError)
    async def _not_found(_, exc: EntityNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(TenantViolationError)
    async def _tenant_violation(_, exc: TenantViolationError):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(BusinessRuleError)
    async def _business_rule(_, exc: BusinessRuleError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    app.dependency_overrides[recommendations_router_module.get_session] = lambda: session
    app.dependency_overrides[recommendations_router_module.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[recommendations_router_module.get_current_user] = lambda: SimpleNamespace(
        id=current_user_id
    )
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_list_filters_by_tenant_domain_and_priority(session, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _ensure_tenant(session, tenant_a)
    await _ensure_tenant(session, tenant_b)
    high = await _seed_recommendation(
        session,
        tenant_a,
        domain="AGRICULTURE",
        priority="HIGH",
        rule_code="AGRI_HIGH",
        scope_id="safra-1",
    )
    await _seed_recommendation(
        session,
        tenant_a,
        domain="AGRICULTURE",
        priority="LOW",
        rule_code="AGRI_LOW",
        scope_id="safra-2",
    )
    await _seed_recommendation(
        session,
        tenant_b,
        domain="AGRICULTURE",
        priority="URGENT",
        rule_code="AGRI_OTHER",
        scope_id="safra-3",
    )

    async with _build_client(session, tenant_a) as client:
        response = await client.get("/api/v1/recommendations", params={"domain": "AGRICULTURE"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == body["total"]
    assert body["total"] == 2
    assert body["items"][0]["id"] == str(high.id)
    assert body["items"][0]["priority"] == "HIGH"
    assert body["items"][1]["priority"] == "LOW"


@pytest.mark.asyncio
async def test_list_filters_by_status_scope_and_unit(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    unidade_produtiva_id = uuid.uuid4()
    await _ensure_unidade_produtiva(session, tenant, unidade_produtiva_id)
    recommendation = await _seed_recommendation(
        session,
        tenant,
        domain="FINANCE",
        priority="NORMAL",
        rule_code="FIN_VIEWED",
        scope_id="safra-99",
        scope_type="SAFRA",
        unidade_produtiva_id=unidade_produtiva_id,
    )
    service = RecommendationLifecycleService(session, tenant)
    await service.mark_viewed(recommendation.id, ADMIN_USER_ID)
    await session.commit()

    async with _build_client(session, tenant) as client:
        response = await client.get(
            "/api/v1/recommendations",
            params={
                "status": "VIEWED",
                "priority": "NORMAL",
                "unidade_produtiva_id": str(unidade_produtiva_id),
                "scope_type": "SAFRA",
                "scope_id": "safra-99",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "VIEWED"
    assert body["items"][0]["scope_id"] == "safra-99"


@pytest.mark.asyncio
async def test_list_filters_by_period(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    recent = await _seed_recommendation(
        session,
        tenant,
        domain="SYSTEM",
        priority="NORMAL",
        rule_code="RECENT_RULE",
        scope_id="scope-recent",
    )
    old = await _seed_recommendation(
        session,
        tenant,
        domain="SYSTEM",
        priority="LOW",
        rule_code="OLD_RULE",
        scope_id="scope-old",
    )

    await _set_created_at(session, recent.id, datetime(2026, 6, 20, 10, 0, tzinfo=timezone.utc))
    await _set_created_at(session, old.id, datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc))

    async with _build_client(session, tenant) as client:
        response = await client.get(
            "/api/v1/recommendations",
            params={
                "start_date": "2026-06-01",
                "end_date": "2026-06-30",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(recent.id)


@pytest.mark.asyncio
async def test_get_by_id_blocks_cross_tenant(session, tenant_id: uuid.UUID, outro_tenant_id: uuid.UUID) -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    await _ensure_tenant(session, tenant_a)
    await _ensure_tenant(session, tenant_b)
    recommendation = await _seed_recommendation(
        session,
        tenant_b,
        domain="AGRICULTURE",
        priority="HIGH",
        rule_code="OTHER_TENANT",
        scope_id="safra-77",
    )

    async with _build_client(session, tenant_a) as client:
        response = await client.get(f"/api/v1/recommendations/{recommendation.id}")

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("route", "payload", "expected_status"),
    [
        ("/view", None, "VIEWED"),
        ("/accept", None, "ACCEPTED"),
        ("/dismiss", {"reason": "duplicada"}, "DISMISSED"),
        (
            "/postpone",
            {"until": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), "reason": "aguardar"},
            "POSTPONED",
        ),
        ("/execute", {"execution_note": "executado no campo"}, "EXECUTED"),
    ],
)
async def test_lifecycle_action_endpoints_update_status(
    session,
    tenant_id: uuid.UUID,
    route: str,
    payload: dict[str, object] | None,
    expected_status: str,
) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    recommendation = await _seed_recommendation(
        session,
        tenant,
        domain="AGRICULTURE",
        priority="HIGH",
        rule_code=f"RULE_{expected_status}",
        scope_id=f"safra-{expected_status.lower()}",
    )
    async with _build_client(session, tenant) as client:
        response = await client.post(f"/api/v1/recommendations/{recommendation.id}{route}", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == expected_status


@pytest.mark.asyncio
async def test_reopen_endpoint_reopens_dismissed_recommendation(session, tenant_id: uuid.UUID) -> None:
    tenant = uuid.uuid4()
    await _ensure_tenant(session, tenant)
    recommendation = await _seed_recommendation(
        session,
        tenant,
        domain="FINANCE",
        priority="HIGH",
        rule_code="RULE_REOPEN",
        scope_id="safra-reopen",
    )
    lifecycle = RecommendationLifecycleService(session, tenant)
    await lifecycle.dismiss(recommendation.id, ADMIN_USER_ID, reason="aguardar")
    await session.commit()

    async with _build_client(session, tenant) as client:
        response = await client.post(f"/api/v1/recommendations/{recommendation.id}/reopen")

    assert response.status_code == 200
    assert response.json()["status"] == "REOPENED"


def test_api_layer_does_not_import_frontend_alert_engine_or_providers() -> None:
    project_root = Path(__file__).resolve().parents[5]
    sources = [
        (project_root / "services/api/recommendations/router.py").read_text(encoding="utf-8"),
        (project_root / "services/api/recommendations/query_service.py").read_text(encoding="utf-8"),
    ]
    forbidden = ("frontend", "CampoPWA", "NotificationDispatcher", "alert_engine", "ClimaRecommendationService")

    for source in sources:
        lowered = source.lower()
        for needle in forbidden:
            assert needle.lower() not in lowered
