"""Adapter canônico do provider Sankhya para o domínio de Integrações."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from events import publish_domain_event_safe
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
from integracoes.sankhya.models import SankhyaConfig
from integracoes.sankhya.services.auth_service import SankhyaGatewayAuthService
from integracoes.security import (
    decrypt_integration_secret,
    encrypt_integration_secret,
    mask_integration_secret,
)

_SANKHYA_SLUG = "sankhya"
_SANKHYA_NAME = "Sankhya"
_LOG_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "agrosaas:sankhya:sync-log")
_PROVIDER_SCOPES = [
    IntegrationScope.TENANT.value,
    IntegrationScope.ESTABELECIMENTO.value,
]
_CANONICAL_SYNC_MODES = {
    IntegrationSyncMode.MANUAL: "MANUAL",
    IntegrationSyncMode.AGENDADO: "SCHEDULED",
    IntegrationSyncMode.EVENTO: "EVENT_DRIVEN",
    IntegrationSyncMode.WEBHOOK: "WEBHOOK",
    IntegrationSyncMode.PULL: "POLLING",
    IntegrationSyncMode.PUSH: "ON_DEMAND",
}

_FEATURE_DEFAULTS: dict[str, dict[str, Any]] = {
    "pessoas": {
        "nome": "Pessoas",
        "descricao": "Sincronização cadastral de pessoas.",
        "habilitada": True,
        "mode": IntegrationSyncMode.MANUAL,
        "prioridade": IntegrationPolicyPriority.NORMAL,
        "settings_payload": {
            "supported_modes": ["MANUAL", "AGENDADO"],
            "capability_code": "erp.cadastros.pessoas.importar",
            "status": "SUPPORTED",
            "maturity": "TESTED",
            "direction": "ERP_TO_AGROSAAS",
            "supported_scopes": _PROVIDER_SCOPES,
            "supported_sync_modes": ["MANUAL", "ON_DEMAND", "SCHEDULED"],
            "runtime_sync_modes": ["MANUAL", "AGENDADO"],
            "dependencies": [],
            "restrictions": [
                "requer credenciais válidas no gateway Sankhya",
                "depende de reconciliação via ExternalRecordAssociation quando necessário",
            ],
            "observability_requirements": ["health", "jobs", "logs", "reconciliation"],
            "pilot_tier": "P0",
        },
    },
    "produtos": {
        "nome": "Produtos",
        "descricao": "Sincronização cadastral de produtos.",
        "habilitada": True,
        "mode": IntegrationSyncMode.MANUAL,
        "prioridade": IntegrationPolicyPriority.NORMAL,
        "settings_payload": {
            "supported_modes": ["MANUAL", "AGENDADO"],
            "capability_code": "erp.cadastros.produtos.importar",
            "status": "SUPPORTED",
            "maturity": "TESTED",
            "direction": "ERP_TO_AGROSAAS",
            "supported_scopes": _PROVIDER_SCOPES,
            "supported_sync_modes": ["MANUAL", "ON_DEMAND", "SCHEDULED"],
            "runtime_sync_modes": ["MANUAL", "AGENDADO"],
            "dependencies": ["pessoas"],
            "restrictions": [
                "não redefine ownership do estoque operacional",
                "depende de reconciliação manual quando o produto externo já existir",
            ],
            "observability_requirements": ["health", "jobs", "logs", "reconciliation"],
            "pilot_tier": "P0",
        },
    },
    "financeiro": {
        "nome": "Financeiro",
        "descricao": "Sincronização financeira com o ERP.",
        "habilitada": True,
        "mode": IntegrationSyncMode.PULL,
        "prioridade": IntegrationPolicyPriority.HIGH,
        "settings_payload": {
            "supported_modes": ["MANUAL", "AGENDADO", "PULL"],
            "capability_code": "erp.financeiro.basico.sincronizar",
            "status": "PARTIAL",
            "maturity": "TESTED",
            "direction": "ERP_TO_AGROSAAS",
            "supported_scopes": _PROVIDER_SCOPES,
            "supported_sync_modes": ["MANUAL", "ON_DEMAND", "SCHEDULED", "POLLING"],
            "runtime_sync_modes": ["MANUAL", "AGENDADO", "PULL"],
            "dependencies": ["pessoas", "produtos"],
            "restrictions": [
                "cobertura focada no financeiro administrativo do ERP",
                "não substitui DRE operacional nem custos operacionais do AgroSaaS",
            ],
            "observability_requirements": ["health", "jobs", "logs", "reconciliation"],
            "pilot_tier": "P0",
        },
    },
    "nfe": {
        "nome": "NFe",
        "descricao": "Integração fiscal de notas fiscais eletrônicas.",
        "habilitada": True,
        "mode": IntegrationSyncMode.PULL,
        "prioridade": IntegrationPolicyPriority.HIGH,
        "settings_payload": {
            "supported_modes": ["MANUAL", "AGENDADO", "PULL"],
            "capability_code": "erp.fiscal.nfe.evidencia",
            "status": "PARTIAL",
            "maturity": "TESTED",
            "direction": "EVIDENCE_RETURN",
            "supported_scopes": _PROVIDER_SCOPES,
            "supported_sync_modes": ["MANUAL", "ON_DEMAND", "SCHEDULED", "POLLING"],
            "runtime_sync_modes": ["MANUAL", "AGENDADO", "PULL"],
            "dependencies": ["pessoas", "produtos"],
            "restrictions": [
                "retorno fiscal é tratado como evidência oficial do ERP",
                "não habilita CT-e, MDF-e ou exportação fiscal completa no P0",
            ],
            "observability_requirements": ["health", "jobs", "logs", "reconciliation"],
            "pilot_tier": "P0",
        },
    },
    "pedidos": {
        "nome": "Pedidos",
        "descricao": "Feature futura de pedidos com transporte por evento/outbox.",
        "habilitada": False,
        "mode": IntegrationSyncMode.EVENTO,
        "prioridade": IntegrationPolicyPriority.NORMAL,
        "settings_payload": {
            "supported_modes": ["EVENTO"],
            "transport": "OUTBOX",
            "future": True,
            "capability_code": "erp.comercial.pedidos.sincronizar",
            "status": "PARTIAL",
            "maturity": "DECLARED",
            "direction": "BIDIRECTIONAL_CONTROLLED",
            "supported_scopes": _PROVIDER_SCOPES,
            "supported_sync_modes": ["EVENT_DRIVEN"],
            "runtime_sync_modes": ["EVENTO"],
            "dependencies": ["pessoas", "produtos", "nfe"],
            "restrictions": [
                "capability declarada, sem materialização operacional no piloto restrito",
                "depende de política explícita de conflito e reconciliação",
            ],
            "observability_requirements": ["jobs", "logs", "reconciliation"],
            "pilot_tier": "P2",
        },
    },
    "estoque": {
        "nome": "Estoque",
        "descricao": "Feature futura de estoque com transporte por evento/outbox.",
        "habilitada": False,
        "mode": IntegrationSyncMode.EVENTO,
        "prioridade": IntegrationPolicyPriority.NORMAL,
        "settings_payload": {
            "supported_modes": ["EVENTO"],
            "transport": "OUTBOX",
            "future": True,
            "capability_code": "erp.estoque.administrativo.sincronizar",
            "status": "PARTIAL",
            "maturity": "DECLARED",
            "direction": "BIDIRECTIONAL_CONTROLLED",
            "supported_scopes": _PROVIDER_SCOPES,
            "supported_sync_modes": ["EVENT_DRIVEN"],
            "runtime_sync_modes": ["EVENTO"],
            "dependencies": ["produtos"],
            "restrictions": [
                "não cobre estoque operacional agrícola do AgroSaaS",
                "permanece fora do piloto restrito e exige evolução específica do adapter",
            ],
            "observability_requirements": ["jobs", "logs", "reconciliation"],
            "pilot_tier": "P2",
        },
    },
}


def _canonical_sync_mode_from_runtime_label(mode: str) -> str:
    runtime_mode = IntegrationSyncMode(mode)
    return _CANONICAL_SYNC_MODES[runtime_mode]


def _provider_definition_payload() -> dict[str, Any]:
    return {
        "provider": _SANKHYA_SLUG,
        "version": 1,
        "provider_code": _SANKHYA_SLUG,
        "provider_name": _SANKHYA_NAME,
        "display_name": "Sankhya ERP",
        "vendor": "Sankhya",
        "supported_versions": ["v1"],
        "authentication_models": ["GATEWAY", "LEGACY_CREDENTIAL_BUNDLE"],
        "supported_scopes": list(_PROVIDER_SCOPES),
        "supported_capabilities": [
            defaults["settings_payload"]["capability_code"]
            for defaults in _FEATURE_DEFAULTS.values()
        ],
        "supported_sync_modes": sorted(
            {
                _canonical_sync_mode_from_runtime_label(runtime_mode)
                for defaults in _FEATURE_DEFAULTS.values()
                for runtime_mode in defaults["settings_payload"]["supported_modes"]
            }
        ),
        "health_model": "INTEGRATION_HEALTH",
        "documentation_url": "/docs/architecture/ERP-PROVIDER-CONTRACT-02-CONTRATO-CANONICO-PROVIDER-ERP.md",
        "support_level": "REFERENCE_PROVIDER",
        "maturity": "PILOT_READY",
        "provider_notes": [
            "provider de referência para o contrato ERP canônico",
            "reutiliza ExternalRecordAssociation, IntegrationJob, IntegrationHealth e IntegrationSyncPolicy",
        ],
    }


def _feature_schema_payload() -> dict[str, Any]:
    return {
        "supported_features": list(_FEATURE_DEFAULTS.keys()),
        "capability_matrix": [
            {
                "feature_code": feature_code,
                "display_name": defaults["nome"],
                "description": defaults["descricao"],
                **defaults["settings_payload"],
            }
            for feature_code, defaults in _FEATURE_DEFAULTS.items()
        ],
    }


def _sync_schema_payload() -> dict[str, Any]:
    return {
        "default_trigger": "MANUAL",
        "supported_runtime_modes": [mode.value for mode in IntegrationSyncMode],
        "supported_canonical_modes": sorted(set(_CANONICAL_SYNC_MODES.values())),
        "triggers": {
            "manual": True,
            "scheduled": True,
            "event_driven": True,
            "webhook": False,
            "polling": True,
        },
        "retry": {
            "supported": True,
            "strategy": "provider_policy_runtime",
            "max_attempts_source": "IntegrationSyncPolicy.max_retries",
        },
        "timeout": {
            "supported": True,
            "source": "IntegrationSyncPolicy.timeout_seconds",
        },
        "backoff": {
            "supported": True,
            "source": "IntegrationSyncPolicy.backoff_seconds",
        },
        "batch": {
            "supported": True,
            "source": "IntegrationSyncPolicy.batch_size",
        },
        "polling": {
            "supported": True,
            "default_features": ["financeiro", "nfe"],
        },
        "webhook": {
            "supported": False,
            "reason": "provider atual usa gateway e sync desacoplado sem webhook oficial materializado",
        },
        "schedule": {
            "supported": True,
            "source": "IntegrationSyncPolicy.trigger_expression",
        },
        "event_driven": {
            "supported": True,
            "default_transport": "OUTBOX",
            "default_features": ["pedidos", "estoque"],
        },
    }


def _health_schema_payload() -> dict[str, Any]:
    return {
        "states": [status.value for status in IntegrationHealthStatus],
        "severity_by_state": {
            IntegrationHealthStatus.CONNECTED.value: "INFO",
            IntegrationHealthStatus.DISCONNECTED.value: "HIGH",
            IntegrationHealthStatus.DEGRADED.value: "MEDIUM",
            IntegrationHealthStatus.AUTH_ERROR.value: "HIGH",
            IntegrationHealthStatus.CONFIG_ERROR.value: "HIGH",
            IntegrationHealthStatus.PARTIAL_FAILURE.value: "MEDIUM",
            IntegrationHealthStatus.RATE_LIMITED.value: "MEDIUM",
        },
        "availability_source": "IntegrationHealth.status",
        "latency_source": "IntegrationHealth.latency_ms",
        "last_success_source": "IntegrationHealth.last_success_at",
        "last_failure_source": "IntegrationHealth.last_failure_at",
        "dependencies": ["gateway_auth", "provider_api", "sync_runtime"],
        "capability_degradation": True,
        "diagnostics": {
            "connection_test": True,
            "timeline": True,
            "job_correlation": True,
            "manual_reconciliation": True,
        },
    }


def _policy_settings_payload(feature_code: str) -> dict[str, Any]:
    defaults = _FEATURE_DEFAULTS[feature_code]
    feature_payload = defaults["settings_payload"]
    return {
        "supported_modes": feature_payload["supported_modes"],
        "supported_sync_modes": feature_payload["supported_sync_modes"],
        "runtime_sync_modes": feature_payload["runtime_sync_modes"],
        "default_runtime_mode": defaults["mode"].value,
        "default_canonical_mode": _CANONICAL_SYNC_MODES[defaults["mode"]],
        "transport": feature_payload.get("transport"),
        "future": feature_payload.get("future", False),
        "retry_managed_by": "IntegrationSyncPolicy",
        "observability_requirements": feature_payload["observability_requirements"],
    }


class SankhyaCanonicalAdapter:
    """Conecta SankhyaConfig/SankhyaSyncLog ao domínio canônico de Integrações."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def sync_provider_config(
        self,
        provider_config: SankhyaConfig,
        *,
        password_changed: bool = False,
        reason: str = "sync_provider_config",
    ) -> TenantIntegracao:
        provider = await self._ensure_provider()
        credential = await self._ensure_credential(
            provider_config,
            provider,
            rotate=password_changed,
        )
        config, config_changed = await self._ensure_config(provider_config, provider, credential)
        await self._ensure_default_features_and_policies(config, provider)
        await self._sync_health_snapshot_from_config(provider_config, config, provider)
        await self._append_version(
            config=config,
            credential=credential,
            provider_config=provider_config,
            reason=reason,
        )

        if config_changed:
            await self._publish_configured_event(config)
        if password_changed:
            await self._publish_credential_rotated_event(config, credential)

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def sync_connection_test(
        self,
        provider_config: SankhyaConfig,
        *,
        success: bool,
        message: str,
    ) -> IntegrationHealth:
        config = await self.sync_provider_config(
            provider_config,
            password_changed=False,
            reason="connection_test",
        )
        health = await self._get_health_by_config_id(config.id)
        previous_status = health.status if health else None
        provider = await self._get_provider_by_id(config.provider_id)
        assert provider is not None

        status = (
            IntegrationHealthStatus.CONNECTED.value
            if success
            else self._infer_error_health_status(message)
        )
        updated = await self._upsert_health(
            config=config,
            provider=provider,
            status=status,
            summary=message,
            details_payload={"source": "connection_test", "message": message},
            last_success=success,
        )

        if previous_status != updated.status:
            await self._publish_health_changed_event(config, previous_status, updated.status)

        await self.db.commit()
        await self.db.refresh(updated)
        return updated

    async def start_sync_job(
        self,
        *,
        tenant_id: str,
        feature_code: str,
        trigger_type: IntegrationJobTrigger,
        legacy_log_id: int | None = None,
        request_payload: dict[str, Any] | None = None,
    ) -> IntegrationJob:
        config = await self._get_or_create_config_by_tenant(tenant_id)
        provider = await self._get_provider_by_id(config.provider_id)
        assert provider is not None
        feature = await self._ensure_feature(config, provider, feature_code)
        policy = await self._ensure_policy(config, provider, feature)

        causation_id = self._legacy_log_causation_id(legacy_log_id) if legacy_log_id else None
        existing = await self._find_running_job(config.id, feature.id, causation_id)
        if existing is not None:
            return existing

        job = IntegrationJob(
            tenant_id=tenant_id,
            config_id=config.id,
            feature_id=feature.id,
            sync_policy_id=policy.id,
            provider_id=provider.id,
            status=IntegrationJobStatus.RUNNING.value,
            trigger_type=trigger_type.value,
            started_at=datetime.now(timezone.utc),  # noqa: UP017
            request_payload={
                "feature_code": feature_code,
                "legacy_log_id": legacy_log_id,
                **(request_payload or {}),
            },
            causation_id=causation_id,
            correlation_id=uuid.uuid4(),
        )
        self.db.add(job)
        await self.db.flush()

        await self._publish_sync_started_event(config, job, feature_code)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def finish_sync_job(
        self,
        *,
        tenant_id: str,
        feature_code: str,
        success: bool,
        processados: int,
        erros: int = 0,
        error_message: str | None = None,
        tempo_ms: float | None = None,
        trigger_type: IntegrationJobTrigger = IntegrationJobTrigger.MANUAL,
        legacy_log_id: int | None = None,
        request_payload: dict[str, Any] | None = None,
    ) -> IntegrationJob:
        config = await self._get_or_create_config_by_tenant(tenant_id)
        provider = await self._get_provider_by_id(config.provider_id)
        assert provider is not None
        feature = await self._ensure_feature(config, provider, feature_code)

        job = await self._find_running_job(
            config.id,
            feature.id,
            self._legacy_log_causation_id(legacy_log_id) if legacy_log_id else None,
        )
        if job is None:
            job = await self.start_sync_job(
                tenant_id=tenant_id,
                feature_code=feature_code,
                trigger_type=trigger_type,
                legacy_log_id=legacy_log_id,
                request_payload=request_payload,
            )

        previous_health = await self._get_health_by_config_id(config.id)
        previous_status = previous_health.status if previous_health else None

        success_count = max(processados - erros, 0)
        job.status = (
            IntegrationJobStatus.SUCCESS.value
            if success
            else IntegrationJobStatus.FAILED.value
        )
        job.finished_at = datetime.now(timezone.utc)  # noqa: UP017
        job.processados = processados
        job.sucessos = success_count
        job.erros = erros
        job.error_message = error_message
        job.result_payload = {
            "feature_code": feature_code,
            "legacy_log_id": legacy_log_id,
            "tempo_execucao_ms": tempo_ms,
            **(request_payload or {}),
        }
        self.db.add(job)
        await self.db.flush()

        next_health_status = self._derive_health_status_from_sync(
            success=success,
            erros=erros,
            error_message=error_message,
        )
        health = await self._upsert_health(
            config=config,
            provider=provider,
            status=next_health_status,
            summary=self._build_health_summary(success, feature_code, error_message),
            details_payload={
                "feature_code": feature_code,
                "legacy_log_id": legacy_log_id,
                "tempo_execucao_ms": tempo_ms,
                "processados": processados,
                "sucessos": success_count,
                "erros": erros,
            },
            last_success=success,
            last_job_id=job.id,
        )

        if success:
            await self._publish_sync_completed_event(config, job, feature_code)
        else:
            await self._publish_sync_failed_event(config, job, feature_code, error_message)

        if previous_status != health.status:
            await self._publish_health_changed_event(config, previous_status, health.status)

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def _ensure_provider(self) -> MarketplaceIntegracao:
        stmt = select(MarketplaceIntegracao).where(MarketplaceIntegracao.slug == _SANKHYA_SLUG)
        provider = (await self.db.execute(stmt)).scalar_one_or_none()
        if provider is None:
            provider = MarketplaceIntegracao(
                nome=_SANKHYA_NAME,
                slug=_SANKHYA_SLUG,
                descricao="Provider ERP Sankhya compatível com o domínio canônico.",
                categoria="ERP",
                fornecedor="Sankhya",
                ativa=True,
                oficial=True,
                provider_type="ERP",
                provider_definition=_provider_definition_payload(),
                connection_schema={
                    "required": [
                        "sankhya_environment",
                        "sankhya_api_base_url",
                        "sankhya_auth_url",
                        "sync_interval",
                    ],
                    "optional": [
                        "sankhya_client_id",
                        "ws_url",
                        "username",
                        "ultimo_teste",
                        "teste_status",
                        "ultimo_sync",
                        "auth_model",
                    ],
                },
                credential_schema={
                    "required": ["sankhya_client_id", "sankhya_client_secret", "sankhya_x_token"],
                    "optional": ["password", "legacy_auth_model"],
                },
                feature_schema=_feature_schema_payload(),
                sync_schema=_sync_schema_payload(),
                health_schema=_health_schema_payload(),
            )
            self.db.add(provider)
            await self.db.flush()
            return provider

        provider.provider_type = "ERP"
        provider.categoria = provider.categoria or "ERP"
        provider.ativa = True
        provider.provider_definition = _provider_definition_payload()
        provider.feature_schema = _feature_schema_payload()
        provider.sync_schema = _sync_schema_payload()
        provider.health_schema = _health_schema_payload()
        return provider

    async def _ensure_credential(
        self,
        provider_config: SankhyaConfig,
        provider: MarketplaceIntegracao,
        *,
        rotate: bool,
    ) -> IntegrationCredential:
        auth_service = SankhyaGatewayAuthService(provider_config)
        credential_bundle = self._credential_bundle(provider_config)
        credential_mask = auth_service.describe()
        stmt = (
            select(IntegrationCredential)
            .where(
                IntegrationCredential.tenant_id == provider_config.tenant_id,
                IntegrationCredential.provider_id == provider.id,
                IntegrationCredential.scope_type == IntegrationScope.TENANT.value,
                IntegrationCredential.ativo.is_(True),
            )
            .order_by(IntegrationCredential.version_number.desc())
        )
        current = (await self.db.execute(stmt)).scalars().first()

        if current is None:
            credential = IntegrationCredential(
                tenant_id=provider_config.tenant_id,
                provider_id=provider.id,
                scope_type=IntegrationScope.TENANT.value,
                segredo_criptografado=self._canonical_secret(credential_bundle),
                mask_metadata=self._credential_mask_metadata(provider_config, credential_mask),
                version_number=1,
                ativo=True,
                rotated_at=datetime.utcnow(),
            )
            self.db.add(credential)
            await self.db.flush()
            return credential

        if not rotate:
            return current

        current.ativo = False
        self.db.add(current)
        await self.db.flush()

        credential = IntegrationCredential(
            tenant_id=provider_config.tenant_id,
            provider_id=provider.id,
            scope_type=IntegrationScope.TENANT.value,
            segredo_criptografado=self._canonical_secret(credential_bundle),
            mask_metadata=self._credential_mask_metadata(provider_config, credential_mask),
            version_number=current.version_number + 1,
            ativo=True,
            rotated_at=datetime.utcnow(),
        )
        self.db.add(credential)
        await self.db.flush()
        return credential

    async def _ensure_config(
        self,
        provider_config: SankhyaConfig,
        provider: MarketplaceIntegracao,
        credential: IntegrationCredential,
    ) -> tuple[TenantIntegracao, bool]:
        stmt = select(TenantIntegracao).where(
            TenantIntegracao.tenant_id == provider_config.tenant_id,
            TenantIntegracao.integracao_id == provider.id,
            TenantIntegracao.scope_type == IntegrationScope.TENANT.value,
            TenantIntegracao.deleted_at.is_(None),
        )
        config = (await self.db.execute(stmt)).scalar_one_or_none()
        payload = self._connection_payload(provider_config)
        credentials_payload = self._credentials_payload(provider_config, credential)
        changed = False

        if config is None:
            config = TenantIntegracao(
                tenant_id=provider_config.tenant_id,
                integracao_id=provider.id,
                status="ativa" if provider_config.ativo else "inativa",
                configuracoes={"sync_interval": provider_config.sync_interval},
                credenciais=credentials_payload,
                scope_type=IntegrationScope.TENANT.value,
                lifecycle_state=(
                    IntegrationStatus.ACTIVE.value
                    if provider_config.ativo
                    else IntegrationStatus.DISABLED.value
                ),
                connection_payload=payload,
                credential_ref_id=credential.id,
            )
            self.db.add(config)
            await self.db.flush()
            return config, True

        if config.connection_payload != payload:
            config.connection_payload = payload
            changed = True
        if config.configuracoes != {"sync_interval": provider_config.sync_interval}:
            config.configuracoes = {"sync_interval": provider_config.sync_interval}
            changed = True
        if config.credenciais != credentials_payload:
            config.credenciais = credentials_payload
            changed = True

        status = "ativa" if provider_config.ativo else "inativa"
        lifecycle = (
            IntegrationStatus.ACTIVE.value
            if provider_config.ativo
            else IntegrationStatus.DISABLED.value
        )
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
        stmt = select(IntegrationSyncPolicy).where(
            IntegrationSyncPolicy.feature_id == feature.id
        )
        policy = (await self.db.execute(stmt)).scalar_one_or_none()
        if policy is None:
            policy = IntegrationSyncPolicy(
                tenant_id=config.tenant_id,
                config_id=config.id,
                feature_id=feature.id,
                provider_id=provider.id,
                mode=defaults["mode"].value,
                prioridade=defaults["prioridade"].value,
                settings_payload=_policy_settings_payload(feature.codigo),
                ativa=True,
            )
            self.db.add(policy)
            await self.db.flush()
            return policy

        policy.mode = defaults["mode"].value
        policy.prioridade = defaults["prioridade"].value
        policy.settings_payload = _policy_settings_payload(feature.codigo)
        policy.ativa = True
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def _append_version(
        self,
        *,
        config: TenantIntegracao,
        credential: IntegrationCredential,
        provider_config: SankhyaConfig,
        reason: str,
    ) -> None:
        auth_service = SankhyaGatewayAuthService(provider_config)
        snapshot = {
            "provider_slug": _SANKHYA_SLUG,
            "auth_model": auth_service.auth_model(),
            "sankhya_environment": provider_config.environment,
            "sankhya_api_base_url": provider_config.api_base_url or provider_config.ws_url,
            "sankhya_auth_url": provider_config.auth_url,
            "sankhya_client_id": provider_config.client_id,
            "ws_url": provider_config.ws_url,
            "username": provider_config.username,
            "sync_interval": provider_config.sync_interval,
            "ativo": provider_config.ativo,
            "client_secret_configured": bool(provider_config.client_secret),
            "client_secret_mask": mask_integration_secret(provider_config.client_secret),
            "x_token_configured": bool(provider_config.x_token),
            "x_token_mask": mask_integration_secret(provider_config.x_token),
            "password_configured": bool(provider_config.password),
            "password_mask": mask_integration_secret(provider_config.password),
        }
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

    async def _sync_health_snapshot_from_config(
        self,
        provider_config: SankhyaConfig,
        config: TenantIntegracao,
        provider: MarketplaceIntegracao,
    ) -> IntegrationHealth:
        status = self._health_from_provider_status(provider_config)
        return await self._upsert_health(
            config=config,
            provider=provider,
            status=status,
            summary="Configuração sincronizada a partir do provider Sankhya.",
            details_payload={
                "teste_status": provider_config.teste_status,
                "ultimo_teste": provider_config.ultimo_teste.isoformat()
                if provider_config.ultimo_teste
                else None,
                "ultimo_sync": provider_config.ultimo_sync.isoformat()
                if provider_config.ultimo_sync
                else None,
            },
            last_success=provider_config.teste_status == "sucesso",
        )

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
                metadata={"origin": "sankhya", "scope_type": config.scope_type},
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
                metadata={"origin": "sankhya"},
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
                metadata={"origin": "sankhya"},
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
                metadata={"origin": "sankhya"},
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
                metadata={"origin": "sankhya"},
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
                metadata={"origin": "sankhya"},
            ),
            session=self.db,
            commit=False,
        )

    async def _get_or_create_config_by_tenant(self, tenant_id: str) -> TenantIntegracao:
        stmt = select(SankhyaConfig).where(SankhyaConfig.tenant_id == tenant_id)
        provider_config = (await self.db.execute(stmt)).scalar_one_or_none()
        if provider_config is None:
            raise ValueError("Sankhya não configurado para o tenant informado")
        return await self.sync_provider_config(provider_config, password_changed=False)

    async def _get_provider_by_id(self, provider_id: int) -> MarketplaceIntegracao | None:
        stmt = select(MarketplaceIntegracao).where(MarketplaceIntegracao.id == provider_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _get_health_by_config_id(self, config_id: int) -> IntegrationHealth | None:
        stmt = select(IntegrationHealth).where(IntegrationHealth.config_id == config_id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def _find_running_job(
        self,
        config_id: int,
        feature_id: int,
        causation_id: uuid.UUID | None,
    ) -> IntegrationJob | None:
        stmt = select(IntegrationJob).where(
            IntegrationJob.config_id == config_id,
            IntegrationJob.feature_id == feature_id,
            IntegrationJob.status == IntegrationJobStatus.RUNNING.value,
        )
        if causation_id is not None:
            stmt = stmt.where(IntegrationJob.causation_id == causation_id)
        stmt = stmt.order_by(IntegrationJob.created_at.desc())
        return (await self.db.execute(stmt)).scalars().first()

    @staticmethod
    def _legacy_log_causation_id(legacy_log_id: int) -> uuid.UUID:
        return uuid.uuid5(_LOG_NAMESPACE, str(legacy_log_id))

    @staticmethod
    def _credential_bundle(provider_config: SankhyaConfig) -> str:
        auth_service = SankhyaGatewayAuthService(provider_config)
        if auth_service.auth_model() == "GATEWAY":
            return json.dumps(
                {
                    "sankhya_client_secret": decrypt_integration_secret(provider_config.client_secret),
                    "sankhya_x_token": decrypt_integration_secret(provider_config.x_token),
                    "legacy_password": None,
                },
                sort_keys=True,
            )
        return provider_config.password or ""

    @staticmethod
    def _credential_mask_metadata(
        provider_config: SankhyaConfig,
        auth_description: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "auth_model": auth_description["auth_model"],
            "sankhya_environment": provider_config.environment,
            "sankhya_api_base_url": provider_config.api_base_url or provider_config.ws_url,
            "sankhya_auth_url": provider_config.auth_url,
            "sankhya_client_id": provider_config.client_id,
            "sankhya_client_secret_mask": auth_description["client_secret_mask"],
            "sankhya_x_token_mask": auth_description["x_token_mask"],
            "password_mask": auth_description["password_mask"],
        }

    @staticmethod
    def _credentials_payload(
        provider_config: SankhyaConfig,
        credential: IntegrationCredential,
    ) -> dict[str, Any]:
        auth_service = SankhyaGatewayAuthService(provider_config)
        return {
            "auth_model": auth_service.auth_model(),
            "sankhya_environment": provider_config.environment,
            "sankhya_api_base_url": provider_config.api_base_url or provider_config.ws_url,
            "sankhya_auth_url": provider_config.auth_url,
            "sankhya_client_id": provider_config.client_id,
            "client_secret_mask": mask_integration_secret(provider_config.client_secret),
            "x_token_mask": mask_integration_secret(provider_config.x_token),
            "legacy_password_mask": mask_integration_secret(provider_config.password),
            "credential_ref_id": credential.id,
        }

    @staticmethod
    def _canonical_secret(raw_or_encrypted: str) -> str:
        if raw_or_encrypted.startswith("enc::"):
            return raw_or_encrypted
        return encrypt_integration_secret(raw_or_encrypted)

    @staticmethod
    def _tenant_uuid(tenant_id: str) -> uuid.UUID:
        try:
            return uuid.UUID(tenant_id)
        except ValueError:
            return uuid.uuid5(uuid.NAMESPACE_URL, f"sankhya-tenant:{tenant_id}")

    @staticmethod
    def _config_entity_uuid(config: TenantIntegracao) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"sankhya-config:{config.tenant_id}:{config.id}")

    @staticmethod
    def _connection_payload(provider_config: SankhyaConfig) -> dict[str, Any]:
        auth_service = SankhyaGatewayAuthService(provider_config)
        return {
            "auth_model": auth_service.auth_model(),
            "sankhya_environment": provider_config.environment,
            "sankhya_api_base_url": provider_config.api_base_url or provider_config.ws_url,
            "sankhya_auth_url": provider_config.auth_url,
            "sankhya_client_id": provider_config.client_id,
            "ws_url": provider_config.ws_url,
            "username": provider_config.username,
            "sync_interval": provider_config.sync_interval,
            "ativo": provider_config.ativo,
        }

    @staticmethod
    def _health_from_provider_status(provider_config: SankhyaConfig) -> str:
        if provider_config.teste_status == "sucesso":
            return IntegrationHealthStatus.CONNECTED.value
        if provider_config.teste_status == "erro":
            return IntegrationHealthStatus.DISCONNECTED.value
        return (
            IntegrationHealthStatus.CONNECTED.value
            if provider_config.ativo
            else IntegrationHealthStatus.DISCONNECTED.value
        )

    @staticmethod
    def _infer_error_health_status(message: str | None) -> str:
        normalized = (message or "").lower()
        if any(token in normalized for token in ("auth", "credencial", "senha", "401", "403")):
            return IntegrationHealthStatus.AUTH_ERROR.value
        if any(token in normalized for token in ("config", "url", "dns", "timeout", "host")):
            return IntegrationHealthStatus.CONFIG_ERROR.value
        if "rate" in normalized or "429" in normalized:
            return IntegrationHealthStatus.RATE_LIMITED.value
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
        if error_message:
            specific_status = self._infer_error_health_status(error_message)
            if specific_status != IntegrationHealthStatus.DISCONNECTED.value:
                return specific_status
        return IntegrationHealthStatus.DEGRADED.value

    @staticmethod
    def _build_health_summary(
        success: bool,
        feature_code: str,
        error_message: str | None,
    ) -> str:
        if success:
            return f"Sync Sankhya concluído com sucesso para {feature_code}."
        return error_message or f"Falha no sync Sankhya para {feature_code}."
