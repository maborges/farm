"""Services canônicos do provider OpenWeather."""

# ruff: noqa: B008, E501, F401, I001, UP017, UP038

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from alert_engine.models import Category, Domain, Priority, Severity, TriggerType
from alert_engine.schemas import OperationalAlertCreate
from alert_engine.service import AlertLifecycleService
from core.models.unidade_produtiva import UnidadeProdutiva
from events import publish_domain_event_safe
from integracoes.payload_masking import mask_sensitive_payload
from integracoes.events import (
    IntegrationConfigured,
    IntegrationCredentialRotated,
    IntegrationHealthChanged,
    IntegrationSyncCompleted,
    IntegrationSyncFailed,
    IntegrationSyncStarted,
)
from integracoes.models import (
    IntegrationCredential,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationHealthStatus,
    IntegrationJob,
    IntegrationJobStatus,
    IntegrationJobTrigger,
    IntegrationPolicyPriority,
    IntegrationScope,
    IntegrationStatus,
    IntegrationSyncMode,
    IntegrationSyncPolicy,
    IntegrationVersion,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.security import (
    decrypt_integration_secret,
    encrypt_integration_secret,
    mask_integration_secret,
)
from integracoes.openweather.schemas import (
    OpenWeatherConfigResponse,
    OpenWeatherConfigUpsert,
    OpenWeatherTestConnectionResponse,
    OpenWeatherWeatherSnapshotResponse,
)

_OPENWEATHER_SLUG = "openweather"
_OPENWEATHER_NAME = "OpenWeather"
_DEFAULT_API_BASE_URL = "https://api.openweathermap.org"
_DEFAULT_LOCATION_QUERY = "Sao Paulo,BR"
_DEFAULT_UNITS = "metric"
_DEFAULT_LANGUAGE = "pt_br"
_DEFAULT_TIMEOUT = 20
_DEFAULT_CACHE_TTL = 1800
_LOG_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "agrosaas:openweather:sync-log")

_FEATURE_DEFAULTS: dict[str, dict[str, Any]] = {
    "current_weather": {
        "nome": "Tempo Atual",
        "descricao": "Consulta atual de temperatura, umidade, chuva e vento.",
        "habilitada": True,
        "mode": IntegrationSyncMode.PULL,
        "prioridade": IntegrationPolicyPriority.HIGH,
        "settings_payload": {
            "supported_modes": ["PULL", "MANUAL"],
            "ttl_seconds": _DEFAULT_CACHE_TTL,
        },
    },
    "forecast": {
        "nome": "Previsão",
        "descricao": "Previsão climática futura.",
        "habilitada": False,
        "mode": IntegrationSyncMode.PULL,
        "prioridade": IntegrationPolicyPriority.NORMAL,
        "settings_payload": {
            "supported_modes": ["PULL"],
            "future": True,
        },
    },
    "rainfall": {
        "nome": "Chuva",
        "descricao": "Volume de precipitação disponível no provider.",
        "habilitada": False,
        "mode": IntegrationSyncMode.PULL,
        "prioridade": IntegrationPolicyPriority.NORMAL,
        "settings_payload": {
            "supported_modes": ["PULL"],
            "future": True,
        },
    },
    "temperature": {
        "nome": "Temperatura",
        "descricao": "Leitura de temperatura para dashboards e alertas.",
        "habilitada": False,
        "mode": IntegrationSyncMode.PULL,
        "prioridade": IntegrationPolicyPriority.NORMAL,
        "settings_payload": {"future": True},
    },
    "humidity": {
        "nome": "Umidade",
        "descricao": "Leitura de umidade relativa do ar.",
        "habilitada": False,
        "mode": IntegrationSyncMode.PULL,
        "prioridade": IntegrationPolicyPriority.NORMAL,
        "settings_payload": {"future": True},
    },
    "wind": {
        "nome": "Vento",
        "descricao": "Leitura de vento e rajadas.",
        "habilitada": False,
        "mode": IntegrationSyncMode.PULL,
        "prioridade": IntegrationPolicyPriority.NORMAL,
        "settings_payload": {"future": True},
    },
}


@dataclass(slots=True)
class OpenWeatherWeatherSnapshot:
    """Snapshot operacional do clima atual."""

    location: str | None
    temperature: float | None
    humidity: int | None
    rainfall_mm: float | None
    wind_speed: float | None
    condition: str | None
    units: str | None
    observed_at: datetime | None
    job_id: uuid.UUID | None = None

    def to_response(self) -> OpenWeatherWeatherSnapshotResponse:
        """Converte o snapshot para resposta de API."""

        return OpenWeatherWeatherSnapshotResponse(
            location=self.location,
            temperature=self.temperature,
            humidity=self.humidity,
            rainfall_mm=self.rainfall_mm,
            wind_speed=self.wind_speed,
            condition=self.condition,
            units=self.units,
            observed_at=self.observed_at,
            source="openweather",
            job_id=str(self.job_id) if self.job_id else None,
        )


class OpenWeatherClient:
    """Cliente HTTP mínimo para OpenWeather."""

    def __init__(
        self, api_base_url: str, api_key: str, timeout_seconds: int, units: str, language: str
    ) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.units = units
        self.language = language

    async def fetch_current_weather(
        self,
        location_query: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
    ) -> dict[str, Any]:
        """Consulta o tempo atual no OpenWeather."""

        params: dict[str, Any] = {
            "appid": self.api_key,
            "units": self.units,
            "lang": self.language,
        }

        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        else:
            params["q"] = location_query or _DEFAULT_LOCATION_QUERY

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.api_base_url}/data/2.5/weather", params=params)
            response.raise_for_status()
            return response.json()

    async def fetch_forecast_weather(
        self,
        location_query: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
    ) -> dict[str, Any]:
        """Consulta a previsão do tempo (5 dias / 3 horas) no OpenWeather."""

        params: dict[str, Any] = {
            "appid": self.api_key,
            "units": self.units,
            "lang": self.language,
        }

        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        else:
            params["q"] = location_query or _DEFAULT_LOCATION_QUERY

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(f"{self.api_base_url}/data/2.5/forecast", params=params)
            response.raise_for_status()
            return response.json()


class OpenWeatherCanonicalAdapter:
    """Conecta OpenWeather ao domínio canônico de Integrações."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sync_provider_config(
        self,
        tenant_id: str,
        payload: OpenWeatherConfigUpsert,
        *,
        reason: str,
        unidade_produtiva_id: str | None = None,
    ) -> TenantIntegracao:
        """Materializa provider, credential, config, features, policies e version."""

        # Garante contexto RLS antes de qualquer DML — necessário para a política de INSERT do Postgres
        await self.db.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )

        provider = await self._ensure_provider()
        credential, credential_changed = await self._ensure_credential(
            tenant_id,
            provider,
            payload,
        )
        config, config_changed = await self._ensure_config(
            tenant_id, provider, credential, payload, unidade_produtiva_id
        )
        await self._ensure_default_features_and_policies(config, provider)
        await self._ensure_initial_health(config, provider)
        await self._append_version(config, credential, payload, reason)

        if config_changed:
            await self._publish_configured_event(config)
        if credential_changed:
            await self._publish_credential_rotated_event(config, credential)

        await self.db.commit()
        await self.db.execute(
            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
            {"tid": str(tenant_id)},
        )
        await self.db.refresh(config)
        return config


    async def ensure_job_context(
        self,
        tenant_id: str,
        feature_code: str,
        trigger_type: IntegrationJobTrigger,
        request_payload: dict[str, Any] | None = None,
        config: TenantIntegracao | None = None,
    ) -> tuple[
        TenantIntegracao,
        MarketplaceIntegracao,
        IntegrationFeature,
        IntegrationSyncPolicy,
        IntegrationJob,
    ]:
        """Garante o contexto canônico para uma execução OpenWeather."""

        config = config or await self._get_or_create_config(tenant_id)
        provider = await self._get_provider_by_id(config.provider_id)
        assert provider is not None
        feature = await self._ensure_feature(config, provider, feature_code)
        policy = await self._ensure_policy(config, provider, feature)

        job = await self._start_job(
            config=config,
            provider=provider,
            feature=feature,
            policy=policy,
            trigger_type=trigger_type,
            request_payload=request_payload,
        )
        return config, provider, feature, policy, job

    async def finish_job(
        self,
        *,
        config: TenantIntegracao,
        provider: MarketplaceIntegracao,
        feature: IntegrationFeature,
        job: IntegrationJob,
        success: bool,
        processados: int,
        erros: int = 0,
        error_message: str | None = None,
        snapshot: OpenWeatherWeatherSnapshot | None = None,
        trigger_type: IntegrationJobTrigger,
    ) -> IntegrationJob:
        """Finaliza job, health, alertas e eventos do provider."""

        previous_health = await self._get_health_by_config_id(config.id)
        previous_status = previous_health.status if previous_health else None
        await self._finalize_job(
            job=job,
            success=success,
            processados=processados,
            erros=erros,
            error_message=error_message,
            snapshot=snapshot,
        )

        health_status = self._derive_health_status_from_sync(
            success=success,
            erros=erros,
            error_message=error_message,
        )
        health_summary = (
            "Consulta climática concluída com sucesso."
            if success
            else error_message or "Falha na consulta climática."
        )
        health = await self._upsert_health(
            config=config,
            provider=provider,
            status=health_status,
            summary=health_summary,
            details_payload={
                "feature_code": feature.codigo,
                "job_id": str(job.id),
                "trigger_type": trigger_type.value,
                "snapshot": self._snapshot_to_dict(snapshot),
                "error_message": error_message,
            },
            last_success=success,
            last_job_id=job.id,
        )

        if success:
            await self._publish_sync_completed_event(config, job, feature.codigo)
        else:
            await self._publish_sync_failed_event(config, job, feature.codigo, error_message)
            await self._create_operational_alert(
                config, job, feature.codigo, health_status, error_message
            )

        if previous_status != health.status:
            await self._publish_health_changed_event(config, previous_status, health.status)

        await self.db.commit()
        await self.db.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(config.tenant_id)},
        )
        await self.db.refresh(job)
        return job

    async def get_config(
        self, tenant_id: str, unidade_produtiva_id: str | None = None
    ) -> TenantIntegracao | None:
        """Obtém a configuração climática no escopo solicitado."""

        # Este adapter também é usado por workers e por fluxos que atravessam
        # commits intermediários. Reafirma o contexto transacional antes do
        # lookup para que o RLS não transforme uma configuração existente em
        # "não configurada".
        await self.db.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )

        scope_type = (
            IntegrationScope.UNIDADE_PRODUTIVA.value
            if unidade_produtiva_id
            else IntegrationScope.TENANT.value
        )

        stmt = (
            select(TenantIntegracao)
            .join(MarketplaceIntegracao, TenantIntegracao.integracao_id == MarketplaceIntegracao.id)
            .where(
                TenantIntegracao.tenant_id == tenant_id,
                TenantIntegracao.deleted_at.is_(None),
                TenantIntegracao.scope_type == scope_type,
                MarketplaceIntegracao.slug == _OPENWEATHER_SLUG,
            )
        )
        if unidade_produtiva_id:
            stmt = stmt.where(TenantIntegracao.scope_id == unidade_produtiva_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def materializar_config_unidade(
        self, tenant_id: str, unidade_produtiva_id: str
    ) -> TenantIntegracao | None:
        """Materializa configuração unitária a partir do legado do tenant."""

        config = await self.get_config(tenant_id, unidade_produtiva_id)
        if config:
            return config
        legado = await self.get_config(tenant_id)
        if not legado:
            return None
        config = TenantIntegracao(
            tenant_id=legado.tenant_id,
            integracao_id=legado.integracao_id,
            status=legado.status,
            configuracoes=legado.configuracoes,
            credenciais=legado.credenciais,
            webhook_url=legado.webhook_url,
            webhook_secret=legado.webhook_secret,
            ultima_sincronizacao=legado.ultima_sincronizacao,
            total_sincronizacoes=legado.total_sincronizacoes,
            installed_at=legado.installed_at,
            scope_type=IntegrationScope.UNIDADE_PRODUTIVA.value,
            scope_id=unidade_produtiva_id,
            lifecycle_state=legado.lifecycle_state,
            connection_payload=legado.connection_payload,
            credential_ref_id=legado.credential_ref_id,
        )
        self.db.add(config)
        await self.db.flush()
        return config

    async def get_provider(self) -> MarketplaceIntegracao:
        """Obtém ou cria o catálogo OpenWeather."""

        return await self._ensure_provider()

    async def obter_config_response(
        self, tenant_id: str, unidade_produtiva_id: str | None = None
    ) -> OpenWeatherConfigResponse | None:
        """Serializa a configuração OpenWeather do tenant."""

        config = await self.get_config(tenant_id, unidade_produtiva_id)
        if not config:
            return None
        credential = await self._get_credential_by_id(config.credential_ref_id)
        latest_job = await self._get_latest_job(config.id)
        return OpenWeatherConfigResponse(
            id=config.id,
            tenant_id=str(config.tenant_id),
            provider_id=config.provider_id,
            provider_slug=_OPENWEATHER_SLUG,
            status=config.status,
            ativo=config.status == "ativa",
            lifecycle_state=config.lifecycle_state,
            connection_payload=config.connection_payload or {},
            configuracoes=config.configuracoes or {},
            api_key_configured=bool(credential and credential.segredo_criptografado),
            api_key_mask=mask_integration_secret(credential.segredo_criptografado)
            if credential
            else None,
            credential_ref_id=config.credential_ref_id,
            last_synced_at=config.ultima_sincronizacao
            or (latest_job.finished_at if latest_job else None),
            created_at=config.installed_at,
            updated_at=config.updated_at,
            scope_type=config.scope_type,
            scope_id=config.scope_id,
        )

    async def obter_status_detalhado(
        self, tenant_id: str, unidade_produtiva_id: str | None = None
    ) -> dict[str, Any]:
        """Resume status, health, features e policies do provider."""

        config = await self.get_config(tenant_id, unidade_produtiva_id)
        config_id = config.id if config else None
        health = await self._get_canonical_health(config_id)
        features = await self._list_canonical_features(config_id)
        policies = await self._list_canonical_policies(config_id)
        latest_job = await self._get_latest_job(config_id) if config_id is not None else None
        latest_weather = self._snapshot_from_job(latest_job) if latest_job else None

        proximo_sync = None
        if config and config.ultima_sincronizacao:
            proximo_sync = config.ultima_sincronizacao + self._sync_delta(config)

        status_conexao = (
            "validado"
            if health and health.status == IntegrationHealthStatus.CONNECTED.value
            else "pendente_teste"
            if config
            else "nao_configurado"
        )

        return {
            "configurado": bool(config),
            "ativo": bool(config and config.status == "ativa"),
            "ultimo_sync": config.ultima_sincronizacao if config else None,
            "proximo_sync": proximo_sync,
            "status_conexao": status_conexao,
            "status_legado": None,
            "status_canonico": config.lifecycle_state if config else None,
            "status_origem": "canonical",
            "health_origem": "canonical",
            "config_id_canonico": config.id if config else None,
            "lifecycle_state": config.lifecycle_state if config else None,
            "health_status": health.status if health else None,
            "health_summary": health.summary if health else "Aguardando teste de conexão inicial.",
            "last_success_at": health.last_success_at if health else None,
            "last_failure_at": health.last_failure_at if health else None,
            "consecutive_failures": health.consecutive_failures if health else 0,
            "features_habilitadas": [feature.codigo for feature in features if feature.habilitada],
            "policies_resumidas": [
                {
                    "feature_code": feature.codigo,
                    "mode": policy.mode,
                    "ativa": policy.ativa,
                    "retry_limite": policy.retry_limite,
                    "trigger_expression": policy.trigger_expression,
                }
                for policy, feature in policies
            ],
            "latest_weather": latest_weather.to_response() if latest_weather else None,
        }

    async def obter_health_detalhado(
        self, tenant_id: str, unidade_produtiva_id: str | None = None
    ) -> dict[str, Any]:
        """Resume o snapshot operacional de health do provider."""

        config = await self.get_config(tenant_id, unidade_produtiva_id)
        health = await self._get_canonical_health(config.id if config else None)
        if not health:
            return {
                "configurado": bool(config),
                "origem": "canonical",
                "status": IntegrationHealthStatus.DISCONNECTED.value,
                "summary": "Integração ainda não testada.",
                "checked_at": None,
                "last_success_at": None,
                "last_failure_at": None,
                "consecutive_failures": 0,
                "details": None,
            }

        return {
            "configurado": True,
            "origem": "canonical",
            "status": health.status,
            "summary": health.summary,
            "checked_at": health.checked_at,
            "last_success_at": health.last_success_at,
            "last_failure_at": health.last_failure_at,
            "consecutive_failures": health.consecutive_failures,
            "details": mask_sensitive_payload(health.details_payload),
        }

    async def listar_jobs(
        self,
        tenant_id: str,
        *,
        limit: int = 20,
        unidade_produtiva_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista jobs canônicos do provider."""

        config = await self.get_config(tenant_id, unidade_produtiva_id)
        if not config:
            return []
        features = await self._list_canonical_features(config.id)
        feature_by_id = {feature.id: feature for feature in features}
        stmt = (
            select(IntegrationJob)
            .where(
                IntegrationJob.tenant_id == tenant_id,
                IntegrationJob.config_id == config.id,
            )
            .order_by(IntegrationJob.created_at.desc())
            .limit(limit)
        )
        jobs = list((await self.db.execute(stmt)).scalars().all())
        return [self._serialize_job(job, feature_by_id.get(job.feature_id)) for job in jobs]

    async def listar_timeline_operacional(
        self,
        tenant_id: str,
        *,
        limit: int = 50,
        status: str | None = None,
        feature_code: str | None = None,
        origem: str | None = None,
        unidade_produtiva_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Consolida timeline de jobs e health do provider."""

        jobs = await self.listar_jobs(
            tenant_id, limit=limit, unidade_produtiva_id=unidade_produtiva_id
        )
        health = await self.obter_health_detalhado(tenant_id, unidade_produtiva_id)
        timeline = [
            *self._build_job_timeline_entries(jobs),
            self._build_health_timeline_entry(health),
        ]
        filtered = self._filter_timeline_entries(
            timeline,
            status=status,
            feature_code=feature_code,
            origem=origem,
        )
        filtered.sort(key=lambda item: item["occurred_at"], reverse=True)
        return filtered[:limit]

    async def obter_diagnostico_operacional(
        self, tenant_id: str, unidade_produtiva_id: str | None = None
    ) -> dict[str, Any]:
        """Resume a saúde operacional do provider em linguagem de suporte."""

        status_payload = await self.obter_status_detalhado(tenant_id, unidade_produtiva_id)
        health_payload = await self.obter_health_detalhado(tenant_id, unidade_produtiva_id)
        jobs = await self.listar_jobs(
            tenant_id, limit=50, unidade_produtiva_id=unidade_produtiva_id
        )

        ultimo_sucesso_at = self._resolve_latest_timestamp(
            [status_payload.get("last_success_at")]
            + [job.get("finished_at") for job in jobs if job["job_status"] == "SUCCESS"]
        )
        ultima_falha_at = self._resolve_latest_timestamp(
            [status_payload.get("last_failure_at")]
            + [job.get("finished_at") for job in jobs if job["job_status"] == "FAILED"]
        )
        falhas_consecutivas = int(health_payload.get("consecutive_failures") or 0)
        jobs_pendentes = sum(
            1 for job in jobs if job["job_status"] in {"PENDING", "RUNNING", "RETRYING"}
        )
        jobs_falhos = sum(1 for job in jobs if job["job_status"] == "FAILED")
        feature_mais_problematica = self._resolve_problematic_feature(jobs)
        health_atual = str(health_payload.get("status") or "DISCONNECTED")

        return {
            "origem": health_payload.get("origem") or "canonical",
            "health_atual": health_atual,
            "status_degradacao": (
                "degradado"
                if health_atual in {"DEGRADED", "PARTIAL_FAILURE", "AUTH_ERROR", "CONFIG_ERROR"}
                else "estavel"
            ),
            "ultimo_sucesso_at": ultimo_sucesso_at,
            "ultima_falha_at": ultima_falha_at,
            "falhas_consecutivas": falhas_consecutivas,
            "feature_mais_problematica": feature_mais_problematica,
            "jobs_pendentes": jobs_pendentes,
            "jobs_falhos": jobs_falhos,
            "recomendacao_operacional": self._build_operational_recommendation(
                health_atual=health_atual,
                falhas_consecutivas=falhas_consecutivas,
                jobs_pendentes=jobs_pendentes,
                feature_mais_problematica=feature_mais_problematica,
            ),
        }

    async def _ensure_provider(self) -> MarketplaceIntegracao:
        stmt = select(MarketplaceIntegracao).where(MarketplaceIntegracao.slug == _OPENWEATHER_SLUG)
        provider = (await self.db.execute(stmt)).scalar_one_or_none()
        if provider is None:
            provider = MarketplaceIntegracao(
                nome=_OPENWEATHER_NAME,
                slug=_OPENWEATHER_SLUG,
                descricao="Provider climático canônico baseado em OpenWeather.",
                categoria="Clima",
                subcategoria="Meteorologia",
                fornecedor="OpenWeather",
                ativa=True,
                oficial=True,
                provider_type="CLIMA",
                provider_definition={
                    "provider": _OPENWEATHER_SLUG,
                    "version": 1,
                    "scope": "TENANT",
                    "transport": "REST",
                },
                connection_schema={
                    "required": ["api_key"],
                    "optional": [
                        "api_base_url",
                        "environment",
                        "location_query",
                        "units",
                        "language",
                        "timeout_seconds",
                        "cache_ttl_seconds",
                    ],
                },
                credential_schema={"required": ["api_key"]},
                feature_schema={"supported_features": list(_FEATURE_DEFAULTS.keys())},
                sync_schema={"default_trigger": "PULL", "default_interval_minutes": 30},
                health_schema={"states": [status.value for status in IntegrationHealthStatus]},
            )
            self.db.add(provider)
            await self.db.flush()
            return provider

        provider.provider_type = "CLIMA"
        provider.categoria = provider.categoria or "Clima"
        provider.subcategoria = provider.subcategoria or "Meteorologia"
        provider.ativa = True
        provider.oficial = True
        provider.provider_definition = provider.provider_definition or {
            "provider": _OPENWEATHER_SLUG,
            "version": 1,
        }
        return provider

    async def _ensure_credential(
        self,
        tenant_id: str,
        provider: MarketplaceIntegracao,
        payload: OpenWeatherConfigUpsert,
    ) -> tuple[IntegrationCredential, bool]:
        secret = payload.api_key or ""
        stmt = (
            select(IntegrationCredential)
            .where(
                IntegrationCredential.tenant_id == tenant_id,
                IntegrationCredential.provider_id == provider.id,
                IntegrationCredential.scope_type == IntegrationScope.TENANT.value,
                IntegrationCredential.ativo.is_(True),
            )
            .order_by(IntegrationCredential.version_number.desc())
        )
        current = (await self.db.execute(stmt)).scalars().first()
        if current is None:
            if not secret:
                raise ValueError("API key é obrigatória na criação da configuração.")
            credential = IntegrationCredential(
                tenant_id=tenant_id,
                provider_id=provider.id,
                scope_type=IntegrationScope.TENANT.value,
                segredo_criptografado=encrypt_integration_secret(secret),
                mask_metadata={"api_key_mask": mask_integration_secret(secret)},
                version_number=1,
                ativo=True,
                rotated_at=datetime.utcnow(),
            )
            self.db.add(credential)
            await self.db.flush()
            return credential, True

        if not secret:
            return current, False

        current_secret = current.segredo_criptografado
        rotated = self._canonical_secret(secret) != current_secret
        if not rotated:
            return current, False

        current.ativo = False
        self.db.add(current)
        await self.db.flush()
        credential = IntegrationCredential(
            tenant_id=tenant_id,
            provider_id=provider.id,
            scope_type=IntegrationScope.TENANT.value,
            segredo_criptografado=encrypt_integration_secret(secret),
            mask_metadata={"api_key_mask": mask_integration_secret(secret)},
            version_number=current.version_number + 1,
            ativo=True,
            rotated_at=datetime.utcnow(),
        )
        self.db.add(credential)
        await self.db.flush()
        return credential, True

    async def _ensure_config(
        self,
        tenant_id: str,
        provider: MarketplaceIntegracao,
        credential: IntegrationCredential,
        payload: OpenWeatherConfigUpsert,
        unidade_produtiva_id: str | None = None,
    ) -> tuple[TenantIntegracao, bool]:
        scope_type = (
            IntegrationScope.UNIDADE_PRODUTIVA.value
            if unidade_produtiva_id
            else IntegrationScope.TENANT.value
        )
        stmt = select(TenantIntegracao).where(
            TenantIntegracao.tenant_id == tenant_id,
            TenantIntegracao.integracao_id == provider.id,
            TenantIntegracao.scope_type == scope_type,
            TenantIntegracao.deleted_at.is_(None),
        )
        if unidade_produtiva_id:
            stmt = stmt.where(TenantIntegracao.scope_id == unidade_produtiva_id)
        config = (await self.db.execute(stmt)).scalar_one_or_none()
        connection_payload = self._connection_payload(payload)
        configuracoes = self._configuracoes_payload(payload)
        status = "ativa"
        lifecycle = IntegrationStatus.ACTIVE.value
        changed = False

        if config is None:
            config = TenantIntegracao(
                tenant_id=tenant_id,
                integracao_id=provider.id,
                status=status,
                configuracoes=configuracoes,
                scope_type=scope_type,
                scope_id=unidade_produtiva_id,
                lifecycle_state=lifecycle,
                connection_payload=connection_payload,
                credential_ref_id=credential.id,
            )
            self.db.add(config)
            await self.db.flush()
            return config, True

        if config.connection_payload != connection_payload:
            config.connection_payload = connection_payload
            changed = True
        if config.configuracoes != configuracoes:
            config.configuracoes = configuracoes
            changed = True
        if config.status != status:
            config.status = status
            changed = True
        if config.lifecycle_state != lifecycle:
            config.lifecycle_state = lifecycle
            changed = True
        if config.credential_ref_id != credential.id:
            config.credential_ref_id = credential.id
            changed = True

        self.db.add(config)
        await self.db.flush()
        return config, changed

    async def _ensure_default_features_and_policies(
        self,
        config: TenantIntegracao,
        provider: MarketplaceIntegracao,
    ) -> None:
        for feature_code in _FEATURE_DEFAULTS:
            feature = await self._ensure_feature(config, provider, feature_code)
            if feature_code in {"current_weather", "forecast", "rainfall"}:
                await self._ensure_policy(config, provider, feature)

    async def _ensure_feature(
        self,
        config: TenantIntegracao,
        provider: MarketplaceIntegracao,
        feature_code: str,
    ) -> IntegrationFeature:
        defaults = _FEATURE_DEFAULTS[feature_code]
        stmt = select(IntegrationFeature).where(
            IntegrationFeature.config_id == config.id,
            IntegrationFeature.codigo == feature_code,
        )
        feature = (await self.db.execute(stmt)).scalar_one_or_none()
        if feature is None:
            feature = IntegrationFeature(
                tenant_id=config.tenant_id,
                config_id=config.id,
                provider_id=provider.id,
                codigo=feature_code,
                nome=defaults["nome"],
                descricao=defaults["descricao"],
                habilitada=defaults["habilitada"],
                obrigatoria=False,
                settings_payload=defaults.get("settings_payload"),
            )
            self.db.add(feature)
            await self.db.flush()
            return feature

        feature.nome = defaults["nome"]
        feature.descricao = defaults["descricao"]
        feature.habilitada = defaults["habilitada"]
        feature.settings_payload = defaults.get("settings_payload")
        self.db.add(feature)
        await self.db.flush()
        return feature

    async def _ensure_policy(
        self,
        config: TenantIntegracao,
        provider: MarketplaceIntegracao,
        feature: IntegrationFeature,
    ) -> IntegrationSyncPolicy:
        defaults = _FEATURE_DEFAULTS[feature.codigo]
        stmt = select(IntegrationSyncPolicy).where(IntegrationSyncPolicy.feature_id == feature.id)
        policy = (await self.db.execute(stmt)).scalar_one_or_none()
        if policy is None:
            policy = IntegrationSyncPolicy(
                tenant_id=config.tenant_id,
                config_id=config.id,
                feature_id=feature.id,
                provider_id=provider.id,
                mode=defaults["mode"].value,
                prioridade=defaults["prioridade"].value,
                settings_payload=defaults.get("settings_payload"),
                ativa=defaults["habilitada"],
                trigger_expression=self._trigger_expression_for(feature.codigo),
            )
            self.db.add(policy)
            await self.db.flush()
            return policy

        policy.mode = defaults["mode"].value
        policy.prioridade = defaults["prioridade"].value
        policy.settings_payload = defaults.get("settings_payload")
        policy.ativa = defaults["habilitada"]
        policy.trigger_expression = self._trigger_expression_for(feature.codigo)
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def _ensure_initial_health(
        self,
        config: TenantIntegracao,
        provider: MarketplaceIntegracao,
    ) -> IntegrationHealth:
        health = await self._get_health_by_config_id(config.id)
        if health is not None:
            return health
        health = IntegrationHealth(
            tenant_id=config.tenant_id,
            config_id=config.id,
            provider_id=provider.id,
            status=IntegrationHealthStatus.DISCONNECTED.value,
            summary="Aguardando teste inicial da conexão OpenWeather.",
            details_payload={"reason": "pending_initial_validation"},
            checked_at=datetime.now(timezone.utc),  # noqa: UP017
            consecutive_failures=0,
        )
        self.db.add(health)
        await self.db.flush()
        return health

    async def _append_version(
        self,
        config: TenantIntegracao,
        credential: IntegrationCredential,
        payload: OpenWeatherConfigUpsert,
        reason: str,
    ) -> None:
        snapshot = self._snapshot_from_payload(payload)
        stmt = (
            select(IntegrationVersion)
            .where(IntegrationVersion.config_id == config.id)
            .order_by(IntegrationVersion.version_number.desc())
        )
        latest = (await self.db.execute(stmt)).scalars().first()
        if (
            latest is not None
            and latest.snapshot_mascarado == snapshot
            and latest.credential_ref_id == credential.id
        ):
            return

        version_number = 1 if latest is None else latest.version_number + 1
        version = IntegrationVersion(
            tenant_id=config.tenant_id,
            config_id=config.id,
            credential_ref_id=credential.id,
            version_number=version_number,
            snapshot_mascarado=snapshot,
            motivo=reason,
        )
        self.db.add(version)
        await self.db.flush()

    async def _start_job(
        self,
        *,
        config: TenantIntegracao,
        provider: MarketplaceIntegracao,
        feature: IntegrationFeature,
        policy: IntegrationSyncPolicy,
        trigger_type: IntegrationJobTrigger,
        request_payload: dict[str, Any] | None,
    ) -> IntegrationJob:
        causation_id = None
        job = IntegrationJob(
            tenant_id=config.tenant_id,
            config_id=config.id,
            feature_id=feature.id,
            sync_policy_id=policy.id,
            provider_id=provider.id,
            status=IntegrationJobStatus.RUNNING.value,
            trigger_type=trigger_type.value,
            started_at=datetime.now(timezone.utc),  # noqa: UP017
            request_payload=request_payload or {},
            causation_id=causation_id,
            correlation_id=uuid.uuid4(),
        )
        self.db.add(job)
        await self.db.flush()
        await self._publish_sync_started_event(config, job, feature.codigo)
        return job

    async def _finalize_job(
        self,
        *,
        job: IntegrationJob,
        success: bool,
        processados: int,
        erros: int,
        error_message: str | None,
        snapshot: OpenWeatherWeatherSnapshot | None,
    ) -> None:
        job.status = (
            IntegrationJobStatus.SUCCESS.value if success else IntegrationJobStatus.FAILED.value
        )
        job.finished_at = datetime.now(timezone.utc)  # noqa: UP017
        job.processados = processados
        job.sucessos = max(processados - erros, 0)
        job.erros = erros
        job.error_message = error_message
        job.result_payload = self._snapshot_to_dict(snapshot) if snapshot else None
        self.db.add(job)
        await self.db.flush()

    async def _upsert_health(
        self,
        *,
        config: TenantIntegracao,
        provider: MarketplaceIntegracao,
        status: str,
        summary: str,
        details_payload: dict[str, Any] | None,
        last_success: bool,
        last_job_id: uuid.UUID | None = None,
    ) -> IntegrationHealth:
        health = await self._get_health_by_config_id(config.id)
        now = datetime.now(timezone.utc)  # noqa: UP017
        if health is None:
            health = IntegrationHealth(
                tenant_id=config.tenant_id,
                config_id=config.id,
                provider_id=provider.id,
                status=status,
                summary=summary,
                details_payload=details_payload,
                checked_at=now,
                last_job_id=last_job_id,
                consecutive_failures=0,
            )
            if last_success:
                health.last_success_at = now
            else:
                health.last_failure_at = now
                health.consecutive_failures = 1
            self.db.add(health)
            await self.db.flush()
            return health

        health.status = status
        health.summary = summary
        health.details_payload = details_payload
        health.checked_at = now
        health.last_job_id = last_job_id
        if last_success:
            health.last_success_at = now
            health.consecutive_failures = 0
        else:
            health.last_failure_at = now
            health.consecutive_failures += 1
        self.db.add(health)
        await self.db.flush()
        return health

    async def _publish_configured_event(self, config: TenantIntegracao) -> None:
        await publish_domain_event_safe(
            IntegrationConfigured(
                tenant_id=self._tenant_uuid(config.tenant_id),
                entity_id=self._config_entity_uuid(config),
                provider_id=config.provider_id,
                config_id=config.id,
                metadata={"origin": _OPENWEATHER_SLUG, "scope_type": config.scope_type},
            ),
            session=self.db,
            commit=False,
        )

    async def _publish_credential_rotated_event(
        self,
        config: TenantIntegracao,
        credential: IntegrationCredential,
    ) -> None:
        await publish_domain_event_safe(
            IntegrationCredentialRotated(
                tenant_id=self._tenant_uuid(config.tenant_id),
                entity_id=self._config_entity_uuid(config),
                provider_id=config.provider_id,
                config_id=config.id,
                credential_id=credential.id,
                metadata={"origin": _OPENWEATHER_SLUG},
            ),
            session=self.db,
            commit=False,
        )

    async def _publish_sync_started_event(
        self,
        config: TenantIntegracao,
        job: IntegrationJob,
        feature_code: str,
    ) -> None:
        await publish_domain_event_safe(
            IntegrationSyncStarted(
                tenant_id=self._tenant_uuid(config.tenant_id),
                entity_id=job.id,
                provider_id=config.provider_id,
                config_id=config.id,
                job_id=job.id,
                feature_code=feature_code,
                correlation_id=job.correlation_id,
                causation_id=job.causation_id,
                metadata={"origin": _OPENWEATHER_SLUG},
            ),
            session=self.db,
            commit=False,
        )

    async def _publish_sync_completed_event(
        self,
        config: TenantIntegracao,
        job: IntegrationJob,
        feature_code: str,
    ) -> None:
        await publish_domain_event_safe(
            IntegrationSyncCompleted(
                tenant_id=self._tenant_uuid(config.tenant_id),
                entity_id=job.id,
                provider_id=config.provider_id,
                config_id=config.id,
                job_id=job.id,
                feature_code=feature_code,
                processed=job.processados,
                succeeded=job.sucessos,
                failed=job.erros,
                correlation_id=job.correlation_id,
                causation_id=job.causation_id,
                metadata={"origin": _OPENWEATHER_SLUG},
            ),
            session=self.db,
            commit=False,
        )

    async def _publish_sync_failed_event(
        self,
        config: TenantIntegracao,
        job: IntegrationJob,
        feature_code: str,
        error_message: str | None,
    ) -> None:
        await publish_domain_event_safe(
            IntegrationSyncFailed(
                tenant_id=self._tenant_uuid(config.tenant_id),
                entity_id=job.id,
                provider_id=config.provider_id,
                config_id=config.id,
                job_id=job.id,
                feature_code=feature_code,
                error_message=error_message,
                correlation_id=job.correlation_id,
                causation_id=job.causation_id,
                metadata={"origin": _OPENWEATHER_SLUG},
            ),
            session=self.db,
            commit=False,
        )

    async def _publish_health_changed_event(
        self,
        config: TenantIntegracao,
        previous_status: str | None,
        current_status: str,
    ) -> None:
        await publish_domain_event_safe(
            IntegrationHealthChanged(
                tenant_id=self._tenant_uuid(config.tenant_id),
                entity_id=self._config_entity_uuid(config),
                provider_id=config.provider_id,
                config_id=config.id,
                previous_status=previous_status,
                current_status=current_status,
                metadata={"origin": _OPENWEATHER_SLUG},
            ),
            session=self.db,
            commit=False,
        )

    async def _create_operational_alert(
        self,
        config: TenantIntegracao,
        job: IntegrationJob,
        feature_code: str,
        health_status: str,
        error_message: str | None,
    ) -> None:
        alert_service = AlertLifecycleService(self.db, self._tenant_uuid(config.tenant_id))
        severity, priority = self._alert_profile_for_status(health_status)
        payload = OperationalAlertCreate(
            tenant_id=self._tenant_uuid(config.tenant_id),
            domain=Domain.INTEGRATIONS,
            category=Category.CLIMATICO,
            title="Falha no OpenWeather",
            message=error_message or "Falha na consulta climática OpenWeather.",
            severity=severity,
            priority=priority,
            status="OPEN",
            confidence=None,
            trigger_type=TriggerType.MANUAL,
            source_type="integration.openweather",
            source_id=str(config.id),
            source_event_ids=[],
            source_indicator_ids=[],
            dedupe_key=f"openweather:{health_status}:{config.id}:{feature_code}",
            action_label="Verificar conexão",
            action_url="/dashboard/settings/integracoes/clima/openweather",
            context={
                "provider": _OPENWEATHER_SLUG,
                "job_id": str(job.id),
                "feature_code": feature_code,
                "health_status": health_status,
            },
        )
        await alert_service.create_or_update_alert(payload)

    async def _get_or_create_config(self, tenant_id: str) -> TenantIntegracao:
        config = await self.get_config(tenant_id)
        if config is None:
            raise ValueError("OpenWeather não configurado para o tenant informado.")
        return config

    async def _get_provider_by_id(self, provider_id: int) -> MarketplaceIntegracao | None:
        stmt = select(MarketplaceIntegracao).where(MarketplaceIntegracao.id == provider_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _get_health_by_config_id(self, config_id: int | None) -> IntegrationHealth | None:
        if config_id is None:
            return None
        stmt = select(IntegrationHealth).where(IntegrationHealth.config_id == config_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _get_canonical_health(self, config_id: int | None) -> IntegrationHealth | None:
        return await self._get_health_by_config_id(config_id)

    async def _get_credential_by_id(
        self, credential_id: int | None
    ) -> IntegrationCredential | None:
        if credential_id is None:
            return None
        stmt = select(IntegrationCredential).where(IntegrationCredential.id == credential_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _get_latest_job(self, config_id: int | None) -> IntegrationJob | None:
        if config_id is None:
            return None
        stmt = (
            select(IntegrationJob)
            .where(
                IntegrationJob.config_id == config_id,
            )
            .order_by(IntegrationJob.created_at.desc())
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def _list_canonical_features(self, config_id: int | None) -> list[IntegrationFeature]:
        if config_id is None:
            return []
        stmt = (
            select(IntegrationFeature)
            .where(
                IntegrationFeature.config_id == config_id,
                IntegrationFeature.deleted_at.is_(None),
            )
            .order_by(IntegrationFeature.codigo.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def _list_canonical_policies(
        self,
        config_id: int | None,
    ) -> list[tuple[IntegrationSyncPolicy, IntegrationFeature]]:
        if config_id is None:
            return []
        stmt = (
            select(IntegrationSyncPolicy, IntegrationFeature)
            .join(IntegrationFeature, IntegrationSyncPolicy.feature_id == IntegrationFeature.id)
            .where(
                IntegrationSyncPolicy.config_id == config_id,
                IntegrationSyncPolicy.deleted_at.is_(None),
                IntegrationFeature.deleted_at.is_(None),
            )
            .order_by(IntegrationFeature.codigo.asc())
        )
        return list((await self.db.execute(stmt)).all())

    def _connection_payload(self, payload: OpenWeatherConfigUpsert) -> dict[str, Any]:
        return {
            "api_base_url": payload.api_base_url or _DEFAULT_API_BASE_URL,
            "environment": payload.environment,
            "location_query": payload.location_query or _DEFAULT_LOCATION_QUERY,
            "units": payload.units,
            "language": payload.language or _DEFAULT_LANGUAGE,
            "timeout_seconds": payload.timeout_seconds or _DEFAULT_TIMEOUT,
            "cache_ttl_seconds": payload.cache_ttl_seconds or _DEFAULT_CACHE_TTL,
            "api_version": "2.5",
        }

    def _configuracoes_payload(self, payload: OpenWeatherConfigUpsert) -> dict[str, Any]:
        return {
            "units": payload.units,
            "language": payload.language or _DEFAULT_LANGUAGE,
            "location_query": payload.location_query or _DEFAULT_LOCATION_QUERY,
            "cache_ttl_seconds": payload.cache_ttl_seconds or _DEFAULT_CACHE_TTL,
        }

    @staticmethod
    def _sync_delta(config: TenantIntegracao) -> Any:
        cache_ttl = _DEFAULT_CACHE_TTL
        if config.connection_payload and config.connection_payload.get("cache_ttl_seconds"):
            cache_ttl = int(config.connection_payload["cache_ttl_seconds"])
        return timedelta(seconds=cache_ttl)

    @staticmethod
    def _canonical_secret(raw_or_encrypted: str) -> str:
        if raw_or_encrypted.startswith("enc::"):
            return raw_or_encrypted
        return encrypt_integration_secret(raw_or_encrypted)

    @staticmethod
    def _tenant_uuid(tenant_id: str | uuid.UUID) -> uuid.UUID:
        if isinstance(tenant_id, uuid.UUID):
            return tenant_id
        return uuid.UUID(str(tenant_id))

    @staticmethod
    def _config_entity_uuid(config: TenantIntegracao) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"openweather-config:{config.tenant_id}:{config.id}")

    @staticmethod
    def _health_from_status_code(status_code: int | None) -> str:
        if status_code in {401, 403}:
            return IntegrationHealthStatus.AUTH_ERROR.value
        if status_code == 429:
            return IntegrationHealthStatus.RATE_LIMITED.value
        if status_code and status_code >= 500:
            return IntegrationHealthStatus.DEGRADED.value
        return IntegrationHealthStatus.DISCONNECTED.value

    def _derive_health_status_from_sync(
        self,
        *,
        success: bool,
        erros: int,
        error_message: str | None,
    ) -> str:
        if success and erros == 0:
            return IntegrationHealthStatus.CONNECTED.value
        if success and erros > 0:
            return IntegrationHealthStatus.PARTIAL_FAILURE.value
        normalized = (error_message or "").lower()
        if any(
            token in normalized for token in ("auth", "api key", "apikey", "token", "401", "403")
        ):
            return IntegrationHealthStatus.AUTH_ERROR.value
        if any(token in normalized for token in ("rate", "limite", "quota", "429")):
            return IntegrationHealthStatus.RATE_LIMITED.value
        if any(token in normalized for token in ("timeout", "unavailable", "503", "502", "500")):
            return IntegrationHealthStatus.DEGRADED.value
        return IntegrationHealthStatus.DEGRADED.value

    def _build_health_summary(
        self,
        success: bool,
        error_message: str | None,
    ) -> str:
        if success:
            return "Consulta climática atualizada com sucesso."
        return error_message or "Falha ao consultar OpenWeather."

    def _build_operational_recommendation(
        self,
        *,
        health_atual: str,
        falhas_consecutivas: int,
        jobs_pendentes: int,
        feature_mais_problematica: str | None,
    ) -> str:
        if health_atual == IntegrationHealthStatus.CONNECTED.value and jobs_pendentes == 0:
            return "Integração climática estável. Manter atualização periódica."
        if health_atual == IntegrationHealthStatus.RATE_LIMITED.value:
            return "Reduzir frequência de consulta e revisar limite do provider."
        if health_atual == IntegrationHealthStatus.AUTH_ERROR.value:
            return "Validar API key e rotação da credencial."
        if falhas_consecutivas >= 3:
            return "Investigar falhas consecutivas e validar conectividade do provider."
        if feature_mais_problematica:
            return f"Revisar a feature {feature_mais_problematica}."
        return "Reexecutar a consulta climática e validar o retorno do provider."

    @staticmethod
    def _build_job_summary(job: dict[str, Any]) -> str:
        feature = job.get("feature_code") or "clima"
        status = job.get("job_status") or "UNKNOWN"
        return f"OpenWeather {feature} {status.lower()}."

    @staticmethod
    def _build_health_timeline_entry(health: dict[str, Any]) -> dict[str, Any]:
        occurred_at = health.get("checked_at") or datetime.now(timezone.utc)
        return {
            "id": "health:current",
            "tipo_registro": "health_snapshot",
            "origem_dado": health.get("origem", "canonical"),
            "feature_code": None,
            "status": health.get("status", "DISCONNECTED"),
            "event_type": "integrations.health_snapshot",
            "resumo": health.get("summary") or "Snapshot atual de health da integração.",
            "occurred_at": occurred_at,
            "started_at": health.get("checked_at"),
            "finished_at": health.get("checked_at"),
            "duracao_ms": None,
            "processados": 0,
            "sucessos": 0,
            "erros": 0,
            "correlation_id": None,
            "payload": health.get("details"),
        }

    @staticmethod
    def _filter_timeline_entries(
        timeline: list[dict[str, Any]],
        *,
        status: str | None,
        feature_code: str | None,
        origem: str | None,
    ) -> list[dict[str, Any]]:
        filtered = timeline
        if status:
            filtered = [
                item for item in filtered if str(item.get("status", "")).lower() == status.lower()
            ]
        if feature_code:
            normalized = feature_code.lower()
            filtered = [
                item for item in filtered if normalized in str(item.get("feature_code", "")).lower()
            ]
        if origem:
            filtered = [
                item
                for item in filtered
                if str(item.get("origem_dado", "")).lower() == origem.lower()
            ]
        return filtered

    @staticmethod
    def _resolve_latest_timestamp(values: list[datetime | None]) -> datetime | None:
        filtered = [value for value in values if value is not None]
        return max(filtered) if filtered else None

    @staticmethod
    def _resolve_problematic_feature(jobs: list[dict[str, Any]]) -> str | None:
        for job in jobs:
            if job["job_status"] == "FAILED" and job.get("feature_code"):
                return str(job["feature_code"])
        return None

    @staticmethod
    def _serialize_job(
        job: IntegrationJob,
        feature: IntegrationFeature | None,
    ) -> dict[str, Any]:
        error_payload = job.error_message
        if job.status == IntegrationJobStatus.FAILED.value and job.result_payload:
            error_payload = job.result_payload
        return {
            "id": str(job.id),
            "tenant_id": str(job.tenant_id),
            "config_id": job.config_id,
            "feature_code": feature.codigo if feature else None,
            "job_status": job.status,
            "trigger_type": job.trigger_type,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "processados": job.processados,
            "sucessos": job.sucessos,
            "erros": job.erros,
            "correlation_id": str(job.correlation_id) if job.correlation_id else None,
            "result_payload": mask_sensitive_payload(job.result_payload),
            "error_payload": mask_sensitive_payload(error_payload),
        }

    def _build_job_timeline_entries(
        self,
        jobs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for job in jobs:
            started_at = job.get("started_at")
            finished_at = job.get("finished_at")
            occurred_at = finished_at or started_at or datetime.now(timezone.utc)
            entries.append(
                {
                    "id": f"job:{job['id']}",
                    "tipo_registro": "canonical_job",
                    "origem_dado": "canonical",
                    "feature_code": job.get("feature_code"),
                    "status": job["job_status"],
                    "event_type": self._map_job_event_type(job["job_status"]),
                    "resumo": self._build_job_summary(job),
                    "occurred_at": occurred_at,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "duracao_ms": self._duration_ms(started_at, finished_at),
                    "processados": job.get("processados", 0),
                    "sucessos": job.get("sucessos", 0),
                    "erros": job.get("erros", 0),
                    "correlation_id": job.get("correlation_id"),
                    "payload": job.get("error_payload") or job.get("result_payload"),
                }
            )
        return entries

    @staticmethod
    def _map_job_event_type(status: str) -> str:
        if status == IntegrationJobStatus.SUCCESS.value:
            return "integrations.sync_completed"
        if status == IntegrationJobStatus.FAILED.value:
            return "integrations.sync_failed"
        return "integrations.sync_started"

    @staticmethod
    def _duration_ms(started_at: datetime | None, finished_at: datetime | None) -> float | None:
        if not started_at or not finished_at:
            return None
        delta = finished_at - started_at
        return max(delta.total_seconds() * 1000, 0)

    @staticmethod
    def _snapshot_to_dict(snapshot: OpenWeatherWeatherSnapshot | None) -> dict[str, Any] | None:
        if snapshot is None:
            return None
        return {
            "location": snapshot.location,
            "temperature": snapshot.temperature,
            "humidity": snapshot.humidity,
            "rainfall_mm": snapshot.rainfall_mm,
            "wind_speed": snapshot.wind_speed,
            "condition": snapshot.condition,
            "units": snapshot.units,
            "observed_at": snapshot.observed_at.isoformat() if snapshot.observed_at else None,
            "source": "openweather",
        }

    def _snapshot_from_job(self, job: IntegrationJob | None) -> OpenWeatherWeatherSnapshot | None:
        if job is None or not isinstance(job.result_payload, dict):
            return None
        payload = job.result_payload
        return OpenWeatherWeatherSnapshot(
            location=payload.get("location"),
            temperature=payload.get("temperature"),
            humidity=payload.get("humidity"),
            rainfall_mm=payload.get("rainfall_mm"),
            wind_speed=payload.get("wind_speed"),
            condition=payload.get("condition"),
            units=payload.get("units"),
            observed_at=self._parse_datetime(payload.get("observed_at")),
            job_id=job.id,
        )

    @staticmethod
    def _snapshot_from_payload(payload: OpenWeatherConfigUpsert) -> dict[str, Any]:
        return {
            "api_base_url": payload.api_base_url or _DEFAULT_API_BASE_URL,
            "environment": payload.environment,
            "location_query": payload.location_query or _DEFAULT_LOCATION_QUERY,
            "units": payload.units,
            "language": payload.language or _DEFAULT_LANGUAGE,
            "timeout_seconds": payload.timeout_seconds or _DEFAULT_TIMEOUT,
            "cache_ttl_seconds": payload.cache_ttl_seconds or _DEFAULT_CACHE_TTL,
        }

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _trigger_expression_for(feature_code: str) -> str | None:
        if feature_code in {"current_weather", "forecast", "rainfall"}:
            return "*/30 * * * *"
        return None

    @staticmethod
    def _alert_profile_for_status(health_status: str) -> tuple[Severity, Priority]:
        if health_status == IntegrationHealthStatus.AUTH_ERROR.value:
            return Severity.CRITICAL, Priority.HIGH
        if health_status == IntegrationHealthStatus.RATE_LIMITED.value:
            return Severity.WARNING, Priority.NORMAL
        return Severity.WARNING, Priority.HIGH

    def _build_openweather_snapshot(
        self,
        payload: dict[str, Any],
        *,
        units: str,
        job_id: uuid.UUID | None = None,
    ) -> OpenWeatherWeatherSnapshot:
        weather = payload.get("weather") or [{}]
        main = payload.get("main") or {}
        wind = payload.get("wind") or {}
        rain = payload.get("rain") or {}
        rainfall = rain.get("1h")
        if rainfall is None:
            rainfall = rain.get("3h")
        observed_at = payload.get("dt")
        observed_dt = (
            datetime.fromtimestamp(observed_at, tz=timezone.utc)
            if isinstance(observed_at, (int, float))
            else datetime.now(timezone.utc)
        )
        return OpenWeatherWeatherSnapshot(
            location=payload.get("name") or payload.get("location"),
            temperature=main.get("temp"),
            humidity=main.get("humidity"),
            rainfall_mm=rainfall,
            wind_speed=wind.get("speed"),
            condition=(weather[0].get("description") if weather else None),
            units=units,
            observed_at=observed_dt,
            job_id=job_id,
        )


class OpenWeatherService:
    """Serviço de domínio do provider OpenWeather."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.adapter = OpenWeatherCanonicalAdapter(db)

    async def salvar_config(
        self,
        tenant_id: str,
        payload: OpenWeatherConfigUpsert,
    ) -> OpenWeatherConfigResponse:
        """Cria ou atualiza a configuração OpenWeather do tenant."""

        await self._validate_sync_frequency(tenant_id, payload)

        config = await self.adapter.sync_provider_config(
            tenant_id,
            payload,
            reason="openweather_config_saved",
        )
        return await self._config_response(tenant_id, config)

    async def salvar_config_unidade(
        self, tenant_id: str, unidade_produtiva_id: str, payload: OpenWeatherConfigUpsert
    ) -> OpenWeatherConfigResponse:
        """Salva a configuração climática de uma unidade do tenant."""

        await self._assert_unit(tenant_id, unidade_produtiva_id)
        await self._validate_sync_frequency(tenant_id, payload)
        config = await self.adapter.sync_provider_config(
            tenant_id,
            payload,
            reason="openweather_unit_config_saved",
            unidade_produtiva_id=unidade_produtiva_id,
        )
        return await self._config_response(tenant_id, config, unidade_produtiva_id)

    async def _validate_sync_frequency(self, tenant_id: str, payload: OpenWeatherConfigUpsert) -> None:
        """Calcula a frequência mínima segura para evitar o estouro da cota e levanta exceção se o usuário pedir mais rápido."""
        daily_quota = getattr(payload, "daily_quota", 1000)
        sync_freq = getattr(payload, "sync_frequency_minutes", 60)

        # Obter número de Unidades Produtivas ativas
        import uuid
        stmt = select(func.count(UnidadeProdutiva.id)).where(
            UnidadeProdutiva.tenant_id == uuid.UUID(tenant_id),
            UnidadeProdutiva.ativo.is_(True)
        )
        result = await self.db.execute(stmt)
        ups_count = result.scalar() or 1
        ups_count = max(1, ups_count) # Evitar divisão por zero caso não tenha UP

        # Calcula o número máximo de chamadas que CADA fazenda pode fazer por dia
        calls_per_up = max(1, daily_quota // ups_count)

        # Calcula a frequência mínima segura em minutos
        # Limitado a 15 min, pois chamadas menores são inúteis para a API do OpenWeather
        min_safe_freq = max(15, 1440 // calls_per_up)

        if sync_freq < min_safe_freq:
            raise ValueError(
                f"Sua cota diária de {daily_quota} requisições dividida pelas {ups_count} unidades produtivas ativas "
                f"permite atualizações seguras no máximo a cada {min_safe_freq} minutos. "
                f"Você configurou {sync_freq} minutos, o que iria estourar a sua cota."
            )

    async def testar_conexao(self, tenant_id: str) -> OpenWeatherTestConnectionResponse:
        """Testa a credencial OpenWeather com consulta atual."""

        config = await self._get_config_or_raise(tenant_id)
        snapshot, success, message = await self._execute_current_weather(
            config,
            trigger_type=IntegrationJobTrigger.MANUAL,
            reason="connection_test",
        )
        return OpenWeatherTestConnectionResponse(
            sucesso=success,
            mensagem=message,
            weather=snapshot.to_response() if snapshot else None,
        )

    async def testar_conexao_unidade(
        self, tenant_id: str, unidade_produtiva_id: str
    ) -> OpenWeatherTestConnectionResponse:
        """Testa o provider usando somente a unidade indicada."""

        config = await self._get_unit_config(tenant_id, unidade_produtiva_id)
        snapshot, success, message = await self._execute_current_weather(
            config,
            trigger_type=IntegrationJobTrigger.MANUAL,
            reason="unit_connection_test",
            unidade_produtiva_id=unidade_produtiva_id,
        )
        return OpenWeatherTestConnectionResponse(
            sucesso=success,
            mensagem=message,
            weather=snapshot.to_response() if snapshot else None,
        )

    async def sincronizar_clima_atual(
        self,
        tenant_id: str,
    ) -> OpenWeatherWeatherSnapshotResponse:
        """Executa a consulta atual do provider OpenWeather."""

        config = await self._get_config_or_raise(tenant_id)
        snapshot, _, _ = await self._execute_current_weather(
            config,
            trigger_type=IntegrationJobTrigger.PULL,
            reason="current_weather_sync",
        )
        if snapshot is None:
            raise ValueError("Snapshot climático indisponível.")
        return snapshot.to_response()

    async def sincronizar_previsao_atual(
        self,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Executa a consulta de previsão do provider OpenWeather para todas unidades."""

        config = await self._get_config_or_raise(tenant_id)
        previsoes, _, _ = await self._execute_forecast_weather(
            config,
            trigger_type=IntegrationJobTrigger.PULL,
            reason="current_forecast_sync",
        )
        if not previsoes:
            raise ValueError("Previsão climática indisponível.")
        return previsoes

    async def sincronizar_clima_unidade(
        self, tenant_id: str, unidade_produtiva_id: str
    ) -> OpenWeatherWeatherSnapshotResponse:
        """Sincroniza o clima exclusivamente da unidade indicada."""

        config = await self._get_unit_config(tenant_id, unidade_produtiva_id)
        snapshot, _, _ = await self._execute_current_weather(
            config,
            trigger_type=IntegrationJobTrigger.PULL,
            reason="unit_weather_sync",
            unidade_produtiva_id=unidade_produtiva_id,
        )
        if snapshot is None:
            raise ValueError("Snapshot climático indisponível.")
        return snapshot.to_response()

    async def sincronizar_previsao_unidade(
        self, tenant_id: str, unidade_produtiva_id: str
    ) -> list[dict[str, Any]]:
        """Sincroniza a previsão do clima de 5 dias exclusivamente da unidade indicada."""

        config = await self._get_unit_config(tenant_id, unidade_produtiva_id)
        previsoes, _, _ = await self._execute_forecast_weather(
            config,
            trigger_type=IntegrationJobTrigger.PULL,
            reason="unit_forecast_sync",
            unidade_produtiva_id=unidade_produtiva_id,
        )
        if not previsoes:
            raise ValueError("Previsão climática indisponível.")
        return previsoes

    async def obter_config_response(
        self, tenant_id: str, unidade_produtiva_id: str | None = None
    ) -> OpenWeatherConfigResponse | None:
        """Retorna a configuração mascarada do provider."""

        config = await self.adapter.obter_config_response(tenant_id, unidade_produtiva_id)
        return config

    async def obter_status_detalhado(
        self, tenant_id: str, unidade_produtiva_id: str | None = None
    ) -> dict[str, Any]:
        """Retorna status canônico do provider."""

        return await self.adapter.obter_status_detalhado(tenant_id, unidade_produtiva_id)

    async def obter_health_detalhado(
        self, tenant_id: str, unidade_produtiva_id: str | None = None
    ) -> dict[str, Any]:
        """Retorna snapshot canônico de health do provider."""

        return await self.adapter.obter_health_detalhado(tenant_id, unidade_produtiva_id)

    async def listar_jobs(
        self,
        tenant_id: str,
        *,
        limit: int = 20,
        unidade_produtiva_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lista jobs canônicos do provider."""

        return await self.adapter.listar_jobs(
            tenant_id, limit=limit, unidade_produtiva_id=unidade_produtiva_id
        )

    async def listar_timeline_operacional(
        self,
        tenant_id: str,
        *,
        limit: int = 50,
        status: str | None = None,
        feature_code: str | None = None,
        origem: str | None = None,
        unidade_produtiva_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Consolida a linha do tempo operacional do provider."""

        return await self.adapter.listar_timeline_operacional(
            tenant_id,
            limit=limit,
            status=status,
            feature_code=feature_code,
            origem=origem,
            unidade_produtiva_id=unidade_produtiva_id,
        )

    async def obter_diagnostico_operacional(
        self, tenant_id: str, unidade_produtiva_id: str | None = None
    ) -> dict[str, Any]:
        """Retorna um resumo operacional para suporte e tenant."""

        return await self.adapter.obter_diagnostico_operacional(tenant_id, unidade_produtiva_id)

    async def _config_response(
        self,
        tenant_id: str,
        config: TenantIntegracao | None = None,
        unidade_produtiva_id: str | None = None,
    ) -> OpenWeatherConfigResponse:
        """Serializa a configuração mascarada após operações de escrita."""

        response = await self.adapter.obter_config_response(tenant_id, unidade_produtiva_id)
        if response is None and config is not None:
            response = await self.adapter.obter_config_response(
                config.tenant_id, config.scope_id
            )
        if response is None:
            scope_label = "a unidade produtiva" if unidade_produtiva_id else "o tenant"
            raise ValueError(f"OpenWeather não configurado para {scope_label} informado.")
        return response

    async def _get_config_or_raise(
        self, tenant_id: str, unidade_produtiva_id: str | None = None
    ) -> TenantIntegracao:
        config = await self.adapter.get_config(tenant_id, unidade_produtiva_id)
        if config is None:
            # If tenant config missing, attempt to fallback to any unidade produtiva config
            if unidade_produtiva_id is None:
                # Try to find a unit config for this tenant
                from sqlalchemy import select
                from integracoes.models import IntegrationScope, TenantIntegracao
                stmt = select(TenantIntegracao).where(
                    TenantIntegracao.tenant_id == tenant_id,
                    TenantIntegracao.scope_type == IntegrationScope.UNIDADE_PRODUTIVA.value,
                    TenantIntegracao.deleted_at.is_(None),
                ).limit(1)
                unit_config = (await self.adapter.db.execute(stmt)).scalar_one_or_none()
                if unit_config:
                    # Materialize as tenant config using the same credential and settings
                    # Reuse existing credential reference
                    cred_id = unit_config.credential_ref_id
                    # Create a new tenant-level config based on unit config
                    tenant_config = TenantIntegracao(
                        tenant_id=tenant_id,
                        integracao_id=unit_config.integracao_id,
                        status=unit_config.status,
                        configuracoes=unit_config.configuracoes,
                        scope_type=IntegrationScope.TENANT.value,
                        scope_id=None,
                        lifecycle_state=unit_config.lifecycle_state,
                        connection_payload=unit_config.connection_payload,
                        credential_ref_id=cred_id,
                    )
                    self.adapter.db.add(tenant_config)
                    await self.adapter.db.flush()
                    return tenant_config
            scope_label = "a unidade produtiva" if unidade_produtiva_id else "o tenant"
            raise ValueError(f"OpenWeather não configurado para {scope_label} informado.")
        return config

    async def _get_unit_config(self, tenant_id: str, unidade_produtiva_id: str) -> TenantIntegracao:
        await self._assert_unit(tenant_id, unidade_produtiva_id)
        config = await self.adapter.materializar_config_unidade(
            tenant_id, unidade_produtiva_id
        )
        if config is None:
            raise ValueError("OpenWeather não configurado para a unidade produtiva informada.")
        return config

    async def _assert_unit(self, tenant_id: str, unidade_produtiva_id: str) -> None:
        """Garante que a unidade solicitada pertença ao tenant atual."""

        import uuid
        stmt = select(UnidadeProdutiva.id).where(
            UnidadeProdutiva.id == uuid.UUID(unidade_produtiva_id),
            UnidadeProdutiva.tenant_id == uuid.UUID(tenant_id),
            UnidadeProdutiva.ativo.is_(True),
        )
        if (await self.adapter.db.execute(stmt)).scalar_one_or_none() is None:
            raise ValueError("Unidade produtiva não encontrada para o tenant informado.")

    async def _execute_current_weather(
        self,
        config: TenantIntegracao,
        *,
        trigger_type: IntegrationJobTrigger,
        reason: str,
        unidade_produtiva_id: str | None = None,
    ) -> tuple[OpenWeatherWeatherSnapshot | None, bool, str]:
        provider = await self.adapter.get_provider()
        payload = self._config_payload(config)
        credential = await self.adapter._get_credential_by_id(config.credential_ref_id)
        if credential is None:
            raise ValueError("Credencial OpenWeather não encontrada.")

        feature_code = "current_weather"
        _, _, feature, policy, job = await self.adapter.ensure_job_context(
            config.tenant_id,
            feature_code,
            trigger_type,
            request_payload={"reason": reason, **payload},
            config=config,
        )

        client = OpenWeatherClient(
            api_base_url=payload["api_base_url"],
            api_key=decrypt_integration_secret(credential.segredo_criptografado),
            timeout_seconds=payload["timeout_seconds"],
            units=payload["units"],
            language=payload["language"],
        )

        stmt = select(UnidadeProdutiva).where(
            UnidadeProdutiva.tenant_id == self.adapter._tenant_uuid(config.tenant_id),
            UnidadeProdutiva.ativo.is_(True),
        )
        if unidade_produtiva_id:
            import uuid
            stmt = stmt.where(UnidadeProdutiva.id == uuid.UUID(unidade_produtiva_id))
        unidades = list((await self.db.execute(stmt)).scalars().all())

        processados = 0
        sucessos = 0
        erros = 0
        message = ""
        first_snapshot = None

        if not unidades:
            # Fallback para location_query textual se nao houver unidades
            try:
                response = await client.fetch_current_weather(
                    location_query=payload["location_query"]
                )
                snapshot = self.adapter._build_openweather_snapshot(
                    response,
                    units=payload["units"],
                    job_id=job.id,
                )
                first_snapshot = snapshot
                processados = 1
                sucessos = 1
                message = "Consulta climática concluída com sucesso (fallback)."
            except Exception as exc:
                processados = 1
                erros = 1
                message = str(exc) or "Falha inesperada ao consultar OpenWeather."
        else:
            # Importar publish_domain_event_safe and event local para evitar cirular ref se necessario
            from events import publish_domain_event_safe
            from agricola.climatico.events import ClimaSyncRealizado

            for up in unidades:
                processados += 1
                lat = None
                lon = None
                if up.coordenadas_sede:
                    try:
                        parts = up.coordenadas_sede.split(",")
                        if len(parts) == 2:
                            lat = float(parts[0].strip())
                            lon = float(parts[1].strip())
                    except ValueError:
                        pass

                try:
                    if lat is not None and lon is not None:
                        response = await client.fetch_current_weather(lat=lat, lon=lon)
                    else:
                        # Ignorar unidade sem coordenadas (ou faz fallback, mas o requisito diz "Unidade sem coordenada é ignorada com registro de erro")
                        erros += 1
                        message = f"Unidade {up.id} ignorada: sem coordenadas válidas."
                        continue

                    snapshot = self.adapter._build_openweather_snapshot(
                        response,
                        units=payload["units"],
                        job_id=job.id,
                    )
                    sucessos += 1

                    if not first_snapshot:
                        first_snapshot = snapshot

                    # Disparar Domain Event para a Unidade
                    evento = ClimaSyncRealizado(
                        tenant_id=self.adapter._tenant_uuid(config.tenant_id),
                        unidade_produtiva_id=up.id,
                        domain=Domain.AGRICULTURE,
                        source_type="integration.openweather",
                        provider="OPENWEATHER",
                        occurred_at=snapshot.observed_at or datetime.now(timezone.utc),
                        latitude=lat,
                        longitude=lon,
                        temperatura=snapshot.temperature,
                        umidade=snapshot.humidity,
                        chuva_mm=snapshot.rainfall_mm,
                        vento_kmh=snapshot.wind_speed,
                        condicao=snapshot.condition,
                        raw_payload=response,
                        correlation_id=job.correlation_id,
                        integration_job_id=job.id,
                    )
                    publish_result = await publish_domain_event_safe(
                        evento,
                        session=self.db,
                        commit=False,
                        use_outbox=False,
                    )
                    if publish_result is None or publish_result.failed or publish_result.errors:
                        raise RuntimeError(
                            "Falha ao persistir o registro climático sincronizado."
                        )

                except Exception as exc:
                    erros += 1
                    message = str(exc) or f"Falha na unidade {up.id}"

            if sucessos > 0:
                message = f"Consulta climática concluída ({sucessos} sucessos, {erros} erros)."
            else:
                message = f"Falha na consulta climática para as unidades ({erros} erros)."

        success = sucessos > 0 or (processados == 0)
        await self.adapter.finish_job(
            config=config,
            provider=provider,
            feature=feature,
            job=job,
            success=success,
            processados=processados,
            erros=erros,
            error_message=message if not success else None,
            snapshot=first_snapshot,
            trigger_type=trigger_type,
        )
        await self._update_config_last_sync(config, job)
        return first_snapshot, success, message

    async def _execute_forecast_weather(
        self,
        config: TenantIntegracao,
        *,
        trigger_type: IntegrationJobTrigger,
        reason: str,
        unidade_produtiva_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], bool, str]:
        provider = await self.adapter.get_provider()
        payload = self._config_payload(config)
        credential = await self.adapter._get_credential_by_id(config.credential_ref_id)
        if credential is None:
            raise ValueError("Credencial OpenWeather não encontrada.")

        feature_code = "forecast"
        _, _, feature, policy, job = await self.adapter.ensure_job_context(
            config.tenant_id,
            feature_code,
            trigger_type,
            request_payload={"reason": reason, **payload},
            config=config,
        )

        client = OpenWeatherClient(
            api_base_url=payload["api_base_url"],
            api_key=decrypt_integration_secret(credential.segredo_criptografado),
            timeout_seconds=payload["timeout_seconds"],
            units=payload["units"],
            language=payload["language"],
        )

        stmt = select(UnidadeProdutiva).where(
            UnidadeProdutiva.tenant_id == self.adapter._tenant_uuid(config.tenant_id),
            UnidadeProdutiva.ativo.is_(True),
        )
        if unidade_produtiva_id:
            import uuid
            stmt = stmt.where(UnidadeProdutiva.id == uuid.UUID(unidade_produtiva_id))
        unidades = list((await self.db.execute(stmt)).scalars().all())

        processados = 0
        sucessos = 0
        erros = 0
        message = ""
        first_previsoes: list[dict[str, Any]] = []

        if not unidades:
            message = "Nenhuma unidade produtiva encontrada."
            erros = 1
        else:
            from events import publish_domain_event_safe
            from agricola.climatico.events import PrevisaoClimaSyncRealizado
            from collections import defaultdict

            for up in unidades:
                processados += 1
                lat = None
                lon = None
                if up.coordenadas_sede:
                    try:
                        parts = up.coordenadas_sede.split(",")
                        if len(parts) == 2:
                            lat = float(parts[0].strip())
                            lon = float(parts[1].strip())
                    except ValueError:
                        pass

                try:
                    if lat is not None and lon is not None:
                        response = await client.fetch_forecast_weather(lat=lat, lon=lon)
                    else:
                        erros += 1
                        message = f"Unidade {up.id} ignorada: sem coordenadas válidas."
                        continue

                    # Agregar de 3 em 3 horas para dados diários
                    agregado_diario: dict[str, dict[str, Any]] = defaultdict(lambda: {
                        "chuva_mm": 0.0,
                        "temps_max": [],
                        "temps_min": [],
                        "prob_chuva": [],
                        "periodos": [],
                    })

                    for item in response.get("list", []):
                        dt_txt = item.get("dt_txt", "")
                        if not dt_txt:
                            continue

                        dia = dt_txt.split(" ")[0]  # yyyy-mm-dd

                        chuva = item.get("rain", {}).get("3h", 0.0)
                        agregado_diario[dia]["chuva_mm"] += chuva

                        temp_max = item.get("main", {}).get("temp_max")
                        temp_min = item.get("main", {}).get("temp_min")
                        if temp_max is not None:
                            agregado_diario[dia]["temps_max"].append(temp_max)
                        if temp_min is not None:
                            agregado_diario[dia]["temps_min"].append(temp_min)

                        pop = item.get("pop", 0)
                        agregado_diario[dia]["prob_chuva"].append(pop)
                        weather = (item.get("weather") or [{}])[0]
                        wind_speed = item.get("wind", {}).get("speed")
                        agregado_diario[dia]["periodos"].append({
                            "horario": dt_txt,
                            "temperatura_c": item.get("main", {}).get("temp"),
                            "sensacao_c": item.get("main", {}).get("feels_like"),
                            "precipitacao_mm": chuva,
                            "probabilidade_chuva_pct": pop * 100,
                            "umidade_pct": item.get("main", {}).get("humidity"),
                            "vento_kmh": round(wind_speed * 3.6, 2) if wind_speed is not None else None,
                            "condicao": weather.get("description"),
                            "icone": weather.get("icon"),
                        })

                    previsoes_up = []
                    for dia, dados in agregado_diario.items():
                        tmax = max(dados["temps_max"]) if dados["temps_max"] else None
                        tmin = min(dados["temps_min"]) if dados["temps_min"] else None
                        pop_avg = (sum(dados["prob_chuva"]) / len(dados["prob_chuva"])) if dados["prob_chuva"] else 0

                        previsoes_up.append({
                            "data_previsao": dia,
                            "precipitacao_mm": dados["chuva_mm"],
                            "temp_max_c": tmax,
                            "temp_min_c": tmin,
                            "probabilidade_chuva_pct": pop_avg * 100,
                            "periodos": dados["periodos"],
                        })

                    sucessos += 1

                    if not first_previsoes:
                        first_previsoes = previsoes_up

                    evento = PrevisaoClimaSyncRealizado(
                        tenant_id=self.adapter._tenant_uuid(config.tenant_id),
                        unidade_produtiva_id=up.id,
                        domain=Domain.AGRICULTURE,
                        source_type="integration.openweather",
                        provider="OPENWEATHER",
                        occurred_at=datetime.now(timezone.utc),
                        previsoes=previsoes_up,
                        raw_payload=response,
                        integration_job_id=job.id,
                    )
                    publish_result = await publish_domain_event_safe(
                        evento,
                        session=self.db,
                        commit=False,
                        use_outbox=False,
                    )
                    if publish_result is None or publish_result.failed or publish_result.errors:
                        raise RuntimeError(
                            "Falha ao persistir a previsão climática sincronizada."
                        )

                except Exception as exc:
                    erros += 1
                    message = str(exc) or f"Falha na unidade {up.id}"

            if sucessos > 0:
                message = f"Consulta de previsão concluída ({sucessos} sucessos, {erros} erros)."
            else:
                message = f"Falha na consulta de previsão ({erros} erros)."

        success = sucessos > 0 or (processados == 0)
        await self.adapter.finish_job(
            config=config,
            provider=provider,
            feature=feature,
            job=job,
            success=success,
            processados=processados,
            erros=erros,
            error_message=message if not success else None,
            snapshot=None,  # Não temos snapshot singular
            trigger_type=trigger_type,
        )
        return first_previsoes, success, message

    @staticmethod
    def _utc_naive(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    async def _update_config_last_sync(self, config: TenantIntegracao, job: IntegrationJob) -> None:
        last_sync = job.finished_at or datetime.now(timezone.utc)
        config.ultima_sincronizacao = self._utc_naive(last_sync)
        self.db.add(config)
        await self.db.commit()
        await self.db.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(config.tenant_id)},
        )
        await self.db.refresh(config)

    @staticmethod
    def _humanize_http_error(status_code: int) -> str:
        if status_code in {401, 403}:
            return "API key inválida ou sem permissão para OpenWeather."
        if status_code == 429:
            return "Limite de requisições atingido no OpenWeather."
        if status_code >= 500:
            return "OpenWeather indisponível no momento."
        return f"OpenWeather retornou erro HTTP {status_code}."

    @staticmethod
    def _config_payload(config: TenantIntegracao) -> dict[str, Any]:
        connection = config.connection_payload or {}
        settings = config.configuracoes or {}
        return {
            "api_base_url": connection.get("api_base_url", _DEFAULT_API_BASE_URL),
            "location_query": connection.get("location_query", _DEFAULT_LOCATION_QUERY),
            "units": connection.get("units", _DEFAULT_UNITS),
            "language": connection.get("language", _DEFAULT_LANGUAGE),
            "timeout_seconds": int(connection.get("timeout_seconds", _DEFAULT_TIMEOUT)),
            "cache_ttl_seconds": int(connection.get("cache_ttl_seconds", _DEFAULT_CACHE_TTL)),
            "environment": connection.get("environment", "production"),
            "api_version": connection.get("api_version", "2.5"),
            "settings": settings,
        }

    @staticmethod
    def _alert_profile_for_status(health_status: str) -> tuple[Severity, Priority]:
        if health_status == IntegrationHealthStatus.AUTH_ERROR.value:
            return Severity.CRITICAL, Priority.HIGH
        if health_status == IntegrationHealthStatus.RATE_LIMITED.value:
            return Severity.WARNING, Priority.NORMAL
        return Severity.WARNING, Priority.HIGH

    @staticmethod
    def _trigger_expression_for(feature_code: str) -> str | None:
        if feature_code in {"current_weather", "forecast", "rainfall"}:
            return "*/30 * * * *"
        return None

    def _build_openweather_snapshot(
        self,
        payload: dict[str, Any],
        *,
        units: str,
        job_id: uuid.UUID | None = None,
    ) -> OpenWeatherWeatherSnapshot:
        weather = payload.get("weather") or [{}]
        main = payload.get("main") or {}
        wind = payload.get("wind") or {}
        rain = payload.get("rain") or {}
        rainfall = rain.get("1h")
        if rainfall is None:
            rainfall = rain.get("3h")
        observed_at = payload.get("dt")
        observed_dt = (
            datetime.fromtimestamp(observed_at, tz=timezone.utc)
            if isinstance(observed_at, (int, float))
            else datetime.now(timezone.utc)
        )
        return OpenWeatherWeatherSnapshot(
            location=payload.get("name") or payload.get("location"),
            temperature=main.get("temp"),
            humidity=main.get("humidity"),
            rainfall_mm=rainfall,
            wind_speed=wind.get("speed"),
            condition=(weather[0].get("description") if weather else None),
            units=units,
            observed_at=observed_dt,
            job_id=job_id,
        )
