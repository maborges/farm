# ruff: noqa: S106
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import core.dependencies as core_dependencies
import integracoes.erp.router as erp_router_module
import integracoes.sankhya.routers as sankhya_router_module
from integracoes.models import (
    IntegrationFeature,
    IntegrationJob,
    MarketplaceIntegracao,
)
from integracoes.sankhya.models import SankhyaSyncLog
from integracoes.sankhya.services.sync_service import SankhyaSyncService

UTC = timezone.utc  # noqa: UP017


@pytest.fixture(autouse=True)
def _stub_canonical_events(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_publish(*args: Any, **kwargs: Any) -> None:
        return None

    monkeypatch.setattr(
        "integracoes.sankhya.services.canonical_adapter.publish_domain_event_safe",
        fake_publish,
    )


async def _seed_sankhya_provider(session: AsyncSession) -> None:
    existing = await session.execute(
        select(MarketplaceIntegracao).where(MarketplaceIntegracao.slug == "sankhya")
    )
    if existing.scalar_one_or_none() is not None:
        return

    session.add(
        MarketplaceIntegracao(
            id=2,
            nome="Sankhya",
            slug="sankhya",
            provider_type="ERP",
            ativa=True,
            oficial=True,
            provider_definition={
                "provider_code": "sankhya",
                "provider_name": "Sankhya",
                "display_name": "Sankhya ERP",
                "supported_scopes": ["TENANT"],
                "authentication_models": ["gateway_oauth_client_credentials"],
                "supported_versions": ["v1"],
            },
            connection_schema={},
            credential_schema={},
            feature_schema={"capability_matrix": []},
            sync_schema={},
            health_schema={},
        )
    )
    await session.commit()


def _override_permission_dependencies(app: FastAPI) -> None:
    for route in app.routes:
        dependant = getattr(route, "dependant", None)
        if dependant is None:
            continue
        for dependency in dependant.dependencies:
            call = getattr(dependency, "call", None)
            if call is None:
                continue
            if call.__module__ == "core.dependencies" and call.__name__ == "_dependency":
                app.dependency_overrides[call] = lambda: True


def _build_client(session: AsyncSession, tenant_id: uuid.UUID) -> AsyncClient:
    app = FastAPI()
    app.include_router(erp_router_module.router, prefix="/api/v1/integracoes")
    app.include_router(sankhya_router_module.router, prefix="/api/v1/integracoes")
    app.dependency_overrides[core_dependencies.get_session] = lambda: session
    app.dependency_overrides[erp_router_module.get_session] = lambda: session
    app.dependency_overrides[sankhya_router_module.get_session] = lambda: session
    app.dependency_overrides[core_dependencies.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[erp_router_module.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[sankhya_router_module.get_tenant_id] = lambda: tenant_id
    app.dependency_overrides[core_dependencies.get_token] = lambda: "fake"
    app.dependency_overrides[core_dependencies.get_current_user] = lambda: SimpleNamespace(
        id=uuid.uuid4(),
        perfil=SimpleNamespace(codigo="OWNER"),
    )
    _override_permission_dependencies(app)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _materialize_mixed_runtime(
    session: AsyncSession,
    tenant_id: uuid.UUID,
) -> tuple[SankhyaSyncService, IntegrationFeature]:
    await _seed_sankhya_provider(session)
    service = SankhyaSyncService(session)
    await service.criar_config(
        tenant_id=str(tenant_id),
        auth_model="gateway_oauth_client_credentials",
        sankhya_environment="producao",
        sankhya_api_base_url="https://gateway.example/api",
        sankhya_auth_url="https://gateway.example/authenticate",
        sankhya_client_id="client-123",
        sankhya_client_secret="client-secret",
        sankhya_x_token="x-token",
        sync_interval=900,
    )

    canonical_config = await service._get_canonical_config(str(tenant_id))
    assert canonical_config is not None

    feature = (
        await session.execute(
            select(IntegrationFeature)
            .where(IntegrationFeature.config_id == canonical_config.id)
            .order_by(IntegrationFeature.id.asc())
        )
    ).scalars().first()
    assert feature is not None

    health = await service._get_canonical_health(canonical_config.id)
    assert health is not None
    health.status = "DEGRADED"
    health.summary = "Saude com mistura de timestamps"
    health.checked_at = datetime(2026, 7, 14, 15, 0, tzinfo=UTC)
    health.last_success_at = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
    health.last_failure_at = datetime(2026, 7, 14, 11, 30, tzinfo=UTC)

    session.add(
        IntegrationJob(
            tenant_id=str(tenant_id),
            config_id=canonical_config.id,
            feature_id=feature.id,
            provider_id=canonical_config.integracao_id,
            status="SUCCESS",
            trigger_type="MANUAL",
            started_at=datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
            finished_at=datetime(2026, 7, 14, 15, 5, tzinfo=UTC),
            processados=10,
            sucessos=10,
            erros=0,
            request_payload={},
            result_payload={"ok": True},
        )
    )
    session.add(
        IntegrationJob(
            tenant_id=str(tenant_id),
            config_id=canonical_config.id,
            feature_id=feature.id,
            provider_id=canonical_config.integracao_id,
            status="PENDING",
            trigger_type="SCHEDULED",
            started_at=datetime(2026, 7, 14, 16, 0, tzinfo=UTC),
            finished_at=None,
            processados=0,
            sucessos=0,
            erros=0,
            request_payload={},
        )
    )
    session.add(
        SankhyaSyncLog(
            id=501,
            tenant_id=str(tenant_id),
            config_id=1,
            tipo=feature.codigo,
            operacao="import",
            status="sucesso",
            registros_processados=8,
            registros_sucesso=8,
            registros_erro=0,
            created_at=datetime(2026, 7, 14, 14, 29),
            started_at=datetime(2026, 7, 14, 14, 30),
            completed_at=datetime(2026, 7, 14, 14, 45),
        )
    )
    session.add(
        SankhyaSyncLog(
            id=502,
            tenant_id=str(tenant_id),
            config_id=1,
            tipo=feature.codigo,
            operacao="import",
            status="erro",
            registros_processados=3,
            registros_sucesso=1,
            registros_erro=2,
            erro_mensagem="falha externa",
            created_at=datetime(2026, 7, 14, 10, 0),
            started_at=datetime(2026, 7, 14, 10, 5),
            completed_at=datetime(2026, 7, 14, 10, 15),
        )
    )
    await session.commit()
    return service, feature


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (
            datetime(2026, 7, 14, 12, 0),
            datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
        ),
        (
            datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
            datetime(2026, 7, 14, 12, 0, tzinfo=UTC),
        ),
        (
            datetime(2026, 7, 14, 12, 0, tzinfo=timezone(timedelta(hours=-3))),
            datetime(2026, 7, 14, 15, 0, tzinfo=UTC),
        ),
    ],
)
def test_normaliza_timestamps_para_utc_aware(
    value: datetime | None,
    expected: datetime | None,
) -> None:
    normalized = SankhyaSyncService._normalize_utc_datetime(value)
    assert normalized == expected


def test_resolve_latest_timestamp_tolera_lista_mista() -> None:
    latest = SankhyaSyncService._resolve_latest_timestamp(
        [
            None,
            datetime(2026, 7, 10, 10, 0),
            datetime(2026, 7, 10, 11, 0, tzinfo=UTC),
            datetime(2026, 7, 10, 9, 30, tzinfo=timezone(timedelta(hours=-3))),
        ]
    )

    assert latest == datetime(2026, 7, 10, 12, 30, tzinfo=UTC)


@pytest.mark.asyncio
async def test_diagnostico_operacional_normaliza_naive_e_aware(
    session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    service, feature = await _materialize_mixed_runtime(session, tenant_id)

    diagnostico = await service.obter_diagnostico_operacional(str(tenant_id))

    assert diagnostico["health_atual"] == "DEGRADED"
    assert diagnostico["feature_mais_problematica"] == feature.codigo
    assert diagnostico["jobs_pendentes"] == 1
    assert diagnostico["jobs_falhos"] == 0
    assert diagnostico["ultimo_sucesso_at"] == datetime(
        2026,
        7,
        14,
        15,
        5,
        tzinfo=UTC,
    )
    assert diagnostico["ultima_falha_at"] == datetime(
        2026,
        7,
        14,
        11,
        30,
        tzinfo=UTC,
    )


@pytest.mark.asyncio
async def test_timeline_operacional_ordena_e_serializa_timestamps_mistos(
    session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    service, _ = await _materialize_mixed_runtime(session, tenant_id)

    timeline = await service.listar_timeline_operacional(str(tenant_id), limit=20)

    assert timeline
    occurred_at = [item["occurred_at"] for item in timeline]
    assert all(isinstance(item, datetime) for item in occurred_at)
    assert all(item.tzinfo is not None for item in occurred_at)
    assert occurred_at == sorted(occurred_at, reverse=True)

    log_entry = next(item for item in timeline if item["tipo_registro"] == "legacy_log")
    assert log_entry["duracao_ms"] == 15 * 60 * 1000


@pytest.mark.asyncio
async def test_endpoint_diagnostico_retorna_200_com_dados_mistos(
    session: AsyncSession,
) -> None:
    tenant_id = uuid.uuid4()
    _, feature = await _materialize_mixed_runtime(session, tenant_id)

    async with _build_client(session, tenant_id) as client:
        response = await client.get("/api/v1/integracoes/erp/diagnostico")

    assert response.status_code == 200
    payload = response.json()
    assert payload["health_atual"] == "DEGRADED"
    assert payload["feature_mais_problematica"] == feature.codigo
    assert payload["ultimo_sucesso_at"] == "2026-07-14T15:05:00Z"
    assert payload["ultima_falha_at"] == "2026-07-14T11:30:00Z"
