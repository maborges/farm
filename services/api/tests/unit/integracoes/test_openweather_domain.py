from __future__ import annotations

# ruff: noqa: I001, E501

import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from alert_engine.models import Domain
from integracoes.models import (
    IntegrationCredential,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationHealthStatus,
    IntegrationJob,
    IntegrationJobStatus,
    IntegrationSyncMode,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.openweather.schemas import OpenWeatherConfigUpsert
from integracoes.openweather.services import OpenWeatherService
from integracoes.security import decrypt_integration_secret, is_integration_secret_encrypted

REPO_ROOT = Path(__file__).resolve().parents[5]
ROUTERS_FILE = REPO_ROOT / "services/api/integracoes/openweather/routers.py"
MAIN_FILE = REPO_ROOT / "services/api/main.py"
SIDEBAR_CONFIG_FILE = REPO_ROOT / "apps/web/src/lib/sidebar-config.ts"
CATALOG_FILE = REPO_ROOT / "apps/web/src/app/integracoes/page.tsx"


@pytest_asyncio.fixture()
async def tenant_id(session: AsyncSession) -> str:
    tid = str(uuid.uuid4())
    await session.execute(
        text(
            "INSERT INTO tenants (id, nome, documento, ativo, storage_usado_mb, "
            "storage_limite_mb, idioma_padrao, created_at, updated_at) "
            "VALUES (:id, :nome, :doc, true, 0, 10240, 'pt-BR', now(), now())"
        ),
        {"id": tid, "nome": "Tenant OpenWeather Teste", "doc": tid[:11]},
    )
    await session.execute(text(f"SET app.current_tenant_id = '{tid}'"))
    return tid


async def _save_config(session: AsyncSession, tenant_id: str) -> Any:
    service = OpenWeatherService(session)
    return await service.salvar_config(
        tenant_id,
        payload=OpenWeatherConfigUpsert(
            api_key="weather-secret",
            api_base_url="https://api.openweathermap.org",
            environment="production",
            location_query="Sao Paulo,BR",
            units="metric",
            language="pt_br",
            timeout_seconds=20,
            cache_ttl_seconds=1800,
        ),
    )


@pytest.mark.asyncio
async def test_salvar_config_materializa_provider_features_policies_e_credential_encriptada(
    session: AsyncSession,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[Any] = []

    async def fake_publish(event: Any, **_: Any) -> None:
        events.append(event)

    monkeypatch.setattr(
        "integracoes.openweather.services.publish_domain_event_safe",
        fake_publish,
    )

    config_response = await _save_config(session, tenant_id)

    provider = (
        await session.execute(
            select(MarketplaceIntegracao).where(MarketplaceIntegracao.slug == "openweather")
        )
    ).scalar_one()
    credential = (
        await session.execute(
            select(IntegrationCredential).where(IntegrationCredential.tenant_id == tenant_id)
        )
    ).scalar_one()
    config = (
        await session.execute(
            select(TenantIntegracao).where(TenantIntegracao.tenant_id == tenant_id)
        )
    ).scalar_one()
    features = list(
        (
            await session.execute(
                select(IntegrationFeature).where(IntegrationFeature.config_id == config.id)
            )
        ).scalars()
    )
    policies = list(
        (
            await session.execute(
                select(IntegrationSyncPolicy).where(IntegrationSyncPolicy.config_id == config.id)
            )
        ).scalars()
    )

    assert provider.provider_type == "CLIMA"
    assert config_response.api_key_configured is True
    assert config_response.api_key_mask == "••••••••"
    assert config_response.connection_payload["api_base_url"] == "https://api.openweathermap.org"
    assert is_integration_secret_encrypted(credential.segredo_criptografado)
    assert decrypt_integration_secret(credential.segredo_criptografado) == "weather-secret"
    assert {feature.codigo for feature in features} == {
        "current_weather",
        "forecast",
        "rainfall",
        "temperature",
        "humidity",
        "wind",
    }
    assert {policy.mode for policy in policies} == {IntegrationSyncMode.PULL.value}
    assert any(event.event_type == "integrations.configured" for event in events)
    assert any(event.event_type == "integrations.credential_rotated" for event in events)


@pytest.mark.asyncio
async def test_atualizacao_sem_nova_api_key_preserva_credencial_existente(
    session: AsyncSession,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr("integracoes.openweather.services.publish_domain_event_safe", fake_publish)

    await _save_config(session, tenant_id)
    service = OpenWeatherService(session)
    await service.salvar_config(
        tenant_id,
        payload=OpenWeatherConfigUpsert(
            api_key=None,
            api_base_url="https://api.openweathermap.org",
            environment="production",
            location_query="Campinas,BR",
            units="metric",
            language="pt_br",
            timeout_seconds=20,
            cache_ttl_seconds=1800,
        ),
    )

    credentials = list(
        (
            await session.execute(
                select(IntegrationCredential).where(
                    IntegrationCredential.tenant_id == tenant_id
                )
            )
        ).scalars()
    )

    assert len(credentials) == 1
    assert decrypt_integration_secret(credentials[0].segredo_criptografado) == "weather-secret"


@pytest.mark.asyncio
async def test_rotacao_de_api_key_cria_nova_credencial_e_desativa_a_anterior(
    session: AsyncSession,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    monkeypatch.setattr("integracoes.openweather.services.publish_domain_event_safe", fake_publish)

    await _save_config(session, tenant_id)
    service = OpenWeatherService(session)
    await service.salvar_config(
        tenant_id,
        payload=OpenWeatherConfigUpsert(
            api_key="weather-secret-rotated",
            api_base_url="https://api.openweathermap.org",
            environment="production",
            location_query="Sao Paulo,BR",
            units="metric",
            language="pt_br",
            timeout_seconds=20,
            cache_ttl_seconds=1800,
        ),
    )

    credentials = list(
        (
            await session.execute(
                select(IntegrationCredential)
                .where(IntegrationCredential.tenant_id == tenant_id)
                .order_by(IntegrationCredential.version_number.asc())
            )
        ).scalars()
    )

    assert len(credentials) == 2
    assert credentials[0].ativo is False
    assert credentials[1].ativo is True
    assert decrypt_integration_secret(credentials[1].segredo_criptografado) == "weather-secret-rotated"


@pytest.mark.asyncio
async def test_teste_de_conexao_cria_job_health_e_eventos_canonicos(
    session: AsyncSession,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[Any] = []
    alerts: list[Any] = []

    async def fake_publish(event: Any, **_: Any) -> None:
        events.append(event)

    async def fake_alert(self, payload: Any) -> Any:
        alerts.append(payload)
        return payload

    async def fake_fetch(self, location_query: str) -> dict[str, Any]:
        assert location_query == "Sao Paulo,BR"
        return {
            "name": "São Paulo",
            "dt": 1_720_000_000,
            "weather": [{"description": "céu limpo"}],
            "main": {"temp": 24.5, "humidity": 66},
            "wind": {"speed": 2.4},
            "rain": {"1h": 0.2},
        }

    monkeypatch.setattr("integracoes.openweather.services.publish_domain_event_safe", fake_publish)
    monkeypatch.setattr(
        "integracoes.openweather.services.AlertLifecycleService.create_or_update_alert",
        fake_alert,
    )
    monkeypatch.setattr("integracoes.openweather.services.OpenWeatherClient.fetch_current_weather", fake_fetch)

    await _save_config(session, tenant_id)
    service = OpenWeatherService(session)
    result = await service.testar_conexao(tenant_id)

    job = (
        await session.execute(select(IntegrationJob).order_by(IntegrationJob.created_at.desc()))
    ).scalar_one()
    health = (
        await session.execute(select(IntegrationHealth).order_by(IntegrationHealth.checked_at.desc()))
    ).scalar_one()

    assert result.sucesso is True
    assert result.weather is not None
    assert result.weather.location == "São Paulo"
    assert job.status == IntegrationJobStatus.SUCCESS.value
    assert health.status == IntegrationHealthStatus.CONNECTED.value
    assert health.consecutive_failures == 0
    assert any(event.event_type == "integrations.sync_started" for event in events)
    assert any(event.event_type == "integrations.sync_completed" for event in events)
    assert any(event.event_type == "integrations.health_changed" for event in events)
    assert alerts == []


@pytest.mark.asyncio
async def test_falha_de_conexao_cria_alerta_e_health_degradado(
    session: AsyncSession,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[Any] = []
    alerts: list[Any] = []

    async def fake_publish(event: Any, **_: Any) -> None:
        events.append(event)

    async def fake_alert(self, payload: Any) -> Any:
        alerts.append(payload)
        return payload

    async def fake_fetch(self, location_query: str) -> dict[str, Any]:
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("integracoes.openweather.services.publish_domain_event_safe", fake_publish)
    monkeypatch.setattr(
        "integracoes.openweather.services.AlertLifecycleService.create_or_update_alert",
        fake_alert,
    )
    monkeypatch.setattr("integracoes.openweather.services.OpenWeatherClient.fetch_current_weather", fake_fetch)

    await _save_config(session, tenant_id)
    service = OpenWeatherService(session)
    result = await service.testar_conexao(tenant_id)

    job = (
        await session.execute(select(IntegrationJob).order_by(IntegrationJob.created_at.desc()))
    ).scalar_one()
    health = (
        await session.execute(select(IntegrationHealth).order_by(IntegrationHealth.checked_at.desc()))
    ).scalar_one()

    assert result.sucesso is False
    assert "timeout" in result.mensagem.lower()
    assert job.status == IntegrationJobStatus.FAILED.value
    assert health.status == IntegrationHealthStatus.DEGRADED.value
    assert health.consecutive_failures == 1
    assert len(alerts) == 1
    assert getattr(alerts[0].domain, "value", alerts[0].domain) == Domain.INTEGRATIONS.value
    assert any(event.event_type == "integrations.sync_failed" for event in events)


@pytest.mark.asyncio
async def test_mapeamento_de_health_cobre_auth_error_e_rate_limited(
    session: AsyncSession,
) -> None:
    service = OpenWeatherService(session)

    assert (
        service.adapter._derive_health_status_from_sync(  # noqa: SLF001
            success=False,
            erros=1,
            error_message="API key inválida ou sem permissão para OpenWeather.",
        )
        == IntegrationHealthStatus.AUTH_ERROR.value
    )
    assert (
        service.adapter._derive_health_status_from_sync(  # noqa: SLF001
            success=False,
            erros=1,
            error_message="Limite de requisições atingido no OpenWeather.",
        )
        == IntegrationHealthStatus.RATE_LIMITED.value
    )


@pytest.mark.asyncio
async def test_status_timeline_e_diagnostico_consolidam_camadas_canonicas(
    session: AsyncSession,
    tenant_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_publish(event: Any, **_: Any) -> None:
        return None

    async def fake_alert(self, payload: Any) -> Any:
        return payload

    async def fake_fetch(self, location_query: str) -> dict[str, Any]:
        return {
            "name": "Ribeirão Preto",
            "dt": 1_720_000_100,
            "weather": [{"description": "nublado"}],
            "main": {"temp": 22.0, "humidity": 70},
            "wind": {"speed": 1.5},
            "rain": {},
        }

    monkeypatch.setattr("integracoes.openweather.services.publish_domain_event_safe", fake_publish)
    monkeypatch.setattr(
        "integracoes.openweather.services.AlertLifecycleService.create_or_update_alert",
        fake_alert,
    )
    monkeypatch.setattr("integracoes.openweather.services.OpenWeatherClient.fetch_current_weather", fake_fetch)

    await _save_config(session, tenant_id)
    service = OpenWeatherService(session)
    await service.testar_conexao(tenant_id)

    status = await service.obter_status_detalhado(tenant_id)
    health = await service.obter_health_detalhado(tenant_id)
    jobs = await service.listar_jobs(tenant_id)
    timeline = await service.listar_timeline_operacional(tenant_id)
    diagnosis = await service.obter_diagnostico_operacional(tenant_id)

    assert status["status_origem"] == "canonical"
    assert health["origem"] == "canonical"
    assert len(jobs) == 1
    assert jobs[0]["tenant_id"] == tenant_id
    assert any(item["tipo_registro"] == "canonical_job" for item in timeline)
    assert any(item["tipo_registro"] == "health_snapshot" for item in timeline)
    assert diagnosis["health_atual"] == "CONNECTED"
    assert diagnosis["jobs_falhos"] == 0


def test_rotas_e_menu_tenant_apontam_para_o_console_de_openweather() -> None:
    router_source = ROUTERS_FILE.read_text(encoding="utf-8")
    main_source = MAIN_FILE.read_text(encoding="utf-8")
    sidebar_config_source = SIDEBAR_CONFIG_FILE.read_text(encoding="utf-8")
    catalog_source = CATALOG_FILE.read_text(encoding="utf-8")

    assert "Depends(get_session)" in router_source
    assert "Depends(get_tenant_id)" in router_source
    assert "require_tenant_permission(\"integrations:view\")" in router_source
    assert "openweather_router" in main_source
    assert "app.include_router(openweather_router, prefix=\"/api/v1/integracoes\")" in main_source
    assert "/dashboard/settings/integracoes/clima/openweather" in sidebar_config_source
    assert "OpenWeather" in sidebar_config_source
    assert 'permission: \'integrations:view\'' in sidebar_config_source
    assert "/dashboard/settings/integracoes/clima/openweather" in catalog_source
