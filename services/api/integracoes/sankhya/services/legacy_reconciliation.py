"""Reconciliação controlada de `SankhyaConfig` legado com o runtime canônico."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from integracoes.models import (
    IntegrationCredential,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationScope,
    IntegrationStatus,
    IntegrationSyncPolicy,
    IntegrationVersion,
    MarketplaceIntegracao,
    TenantIntegracao,
)
from integracoes.sankhya.models import SankhyaConfig
from integracoes.sankhya.services.auth_service import SankhyaGatewayAuthService
from integracoes.sankhya.services.canonical_adapter import (
    _FEATURE_DEFAULTS,
    SankhyaCanonicalAdapter,
)
from integracoes.security import decrypt_integration_secret

_SANKHYA_SLUG = "sankhya"
_SANKHYA_PROVIDER_TYPE = "ERP"
_DEFAULT_SCOPE_TYPE = IntegrationScope.TENANT.value
_SOFT_DELETED_LIFECYCLE = {IntegrationStatus.REMOVED.value, IntegrationStatus.REVOKED.value}
_EXPECTED_FEATURE_CODES = ("pessoas", "produtos", "financeiro", "nfe", "pedidos", "estoque")


class LegacySankhyaReconciliationState(str, Enum):
    """Estados de reconciliação legada."""

    LEGACY_ONLY = "LEGACY_ONLY"
    CANONICAL_ONLY = "CANONICAL_ONLY"
    BOTH_CONSISTENT = "BOTH_CONSISTENT"
    BOTH_DIVERGENT = "BOTH_DIVERGENT"
    LEGACY_SOFT_DELETED = "LEGACY_SOFT_DELETED"
    CANONICAL_SOFT_DELETED = "CANONICAL_SOFT_DELETED"
    DUPLICATE_CANONICAL = "DUPLICATE_CANONICAL"
    NO_RECORDS = "NO_RECORDS"


@dataclass(frozen=True, slots=True)
class LegacySankhyaReconciliationResult:
    """Resumo sanitizado da reconciliação."""

    tenant_id: str
    dry_run: bool
    state_before: str
    state_after: str
    action: str
    provider_slug: str | None
    provider_active: bool | None
    scope_type: str | None
    scope_id: str | None
    legacy_config_id: int | None
    canonical_config_id: int | None
    provider_id: int | None
    changed: bool
    blocked: bool
    block_reasons: tuple[str, ...] = ()
    diff_summary: tuple[str, ...] = ()
    dependency_counts: dict[str, int] = field(default_factory=dict)
    feature_codes: tuple[str, ...] = ()
    policy_modes: tuple[str, ...] = ()
    health_status: str | None = None
    version_count: int = 0


@dataclass(frozen=True, slots=True)
class _TenantSnapshot:
    legacy_config: SankhyaConfig | None
    canonical_config: TenantIntegracao | None
    provider: MarketplaceIntegracao | None
    active_canonical_rows: tuple[TenantIntegracao, ...]
    deleted_canonical_rows: tuple[TenantIntegracao, ...]


@dataclass(frozen=True, slots=True)
class _MaterializedDetails:
    feature_codes: tuple[str, ...]
    policy_modes: tuple[str, ...]
    health_status: str | None
    version_count: int
    latest_version_snapshot: dict[str, Any] | None
    credential: IntegrationCredential | None


class SankhyaLegacyReconciliationService:
    """Reconcilia configs legadas Sankhya com o runtime canônico."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.adapter = SankhyaCanonicalAdapter(db)

    async def list_candidate_tenant_ids(self) -> list[str]:
        """Lista tenants com legado ou runtime canônico Sankhya."""

        legacy_rows = await self.db.execute(select(SankhyaConfig.tenant_id))
        canonical_rows = await self.db.execute(
            select(TenantIntegracao.tenant_id)
            .join(MarketplaceIntegracao, TenantIntegracao.integracao_id == MarketplaceIntegracao.id)
            .where(
                MarketplaceIntegracao.slug == _SANKHYA_SLUG,
                MarketplaceIntegracao.provider_type == _SANKHYA_PROVIDER_TYPE,
            )
        )
        tenant_ids = {str(row) for row in legacy_rows.scalars().all()}
        tenant_ids.update(str(row) for row in canonical_rows.scalars().all())
        return sorted(tenant_ids)

    async def reconcile_tenant(
        self,
        tenant_id: str,
        *,
        dry_run: bool = True,
    ) -> LegacySankhyaReconciliationResult:
        """Reconcilia um tenant isolado, sem expor segredos."""

        await self._restore_rls_context(tenant_id)
        snapshot = await self._load_snapshot(tenant_id)
        details = await self._load_materialized_details(snapshot.canonical_config)
        classification, diff_summary = self._classify(snapshot, details)
        dependency_counts = await self._dependency_counts(snapshot, details)
        block_reasons = self._block_reasons(
            snapshot,
            classification,
            dependency_counts,
            diff_summary,
        )

        if classification != LegacySankhyaReconciliationState.LEGACY_ONLY.value or block_reasons:
            return self._build_result(
                tenant_id=tenant_id,
                dry_run=dry_run,
                state_before=classification,
                state_after=classification,
                action=self._action_for_state(classification, blocked=bool(block_reasons)),
                snapshot=snapshot,
                details=details,
                dependency_counts=dependency_counts,
                changed=False,
                block_reasons=block_reasons,
                diff_summary=diff_summary,
            )

        if dry_run:
            return self._build_result(
                tenant_id=tenant_id,
                dry_run=True,
                state_before=classification,
                state_after=classification,
                action="MATERIALIZE_CANONICAL",
                snapshot=snapshot,
                details=details,
                dependency_counts=dependency_counts,
                changed=False,
                block_reasons=(),
                diff_summary=diff_summary,
            )

        assert snapshot.legacy_config is not None
        await self.adapter.sync_provider_config(
            snapshot.legacy_config,
            password_changed=False,
            reason="legacy_reconciliation",
        )
        refreshed_snapshot = await self._load_snapshot(tenant_id)
        refreshed_details = await self._load_materialized_details(
            refreshed_snapshot.canonical_config
        )
        refreshed_classification, refreshed_diff_summary = self._classify(
            refreshed_snapshot,
            refreshed_details,
        )
        refreshed_dependency_counts = await self._dependency_counts(
            refreshed_snapshot,
            refreshed_details,
        )
        return self._build_result(
            tenant_id=tenant_id,
            dry_run=False,
            state_before=classification,
            state_after=refreshed_classification,
            action="MATERIALIZED_CANONICAL",
            snapshot=refreshed_snapshot,
            details=refreshed_details,
            dependency_counts=refreshed_dependency_counts,
            changed=True,
            block_reasons=(),
            diff_summary=refreshed_diff_summary,
        )

    async def reconcile_many(
        self,
        tenant_ids: list[str],
        *,
        dry_run: bool = True,
        stop_on_error: bool = False,
    ) -> list[LegacySankhyaReconciliationResult]:
        """Reconcilia múltiplos tenants com controle de falha."""

        results: list[LegacySankhyaReconciliationResult] = []
        for tenant_id in tenant_ids:
            result = await self.reconcile_tenant(tenant_id, dry_run=dry_run)
            results.append(result)
            if stop_on_error and result.blocked:
                break
        return results

    async def _load_snapshot(self, tenant_id: str) -> _TenantSnapshot:
        legacy_config = (
            await self.db.execute(select(SankhyaConfig).where(SankhyaConfig.tenant_id == tenant_id))
        ).scalar_one_or_none()

        provider = (
            await self.db.execute(
                select(MarketplaceIntegracao).where(
                    MarketplaceIntegracao.slug == _SANKHYA_SLUG,
                    MarketplaceIntegracao.provider_type == _SANKHYA_PROVIDER_TYPE,
                )
            )
        ).scalar_one_or_none()

        canonical_rows = tuple(
            (
                await self.db.execute(
                    select(TenantIntegracao)
                    .options(selectinload(TenantIntegracao.credential))
                    .join(
                        MarketplaceIntegracao,
                        TenantIntegracao.integracao_id == MarketplaceIntegracao.id,
                    )
                    .where(
                        TenantIntegracao.tenant_id == tenant_id,
                        MarketplaceIntegracao.slug == _SANKHYA_SLUG,
                        MarketplaceIntegracao.provider_type == _SANKHYA_PROVIDER_TYPE,
                    )
                    .order_by(TenantIntegracao.installed_at.desc(), TenantIntegracao.id.desc())
                )
            )
            .scalars()
            .all()
        )
        active_rows = tuple(
            row
            for row in canonical_rows
            if row.deleted_at is None and row.lifecycle_state not in _SOFT_DELETED_LIFECYCLE
        )
        deleted_rows = tuple(
            row
            for row in canonical_rows
            if row.deleted_at is not None or row.lifecycle_state in _SOFT_DELETED_LIFECYCLE
        )
        canonical_config = active_rows[0] if len(active_rows) == 1 else None
        return _TenantSnapshot(
            legacy_config=legacy_config,
            canonical_config=canonical_config,
            provider=provider,
            active_canonical_rows=active_rows,
            deleted_canonical_rows=deleted_rows,
        )

    async def _load_materialized_details(
        self,
        canonical_config: TenantIntegracao | None,
    ) -> _MaterializedDetails:
        if canonical_config is None:
            return _MaterializedDetails((), (), None, 0, None, None)

        feature_rows = (
            await self.db.execute(
                select(IntegrationFeature.codigo)
                .where(
                    IntegrationFeature.config_id == canonical_config.id,
                    IntegrationFeature.deleted_at.is_(None),
                )
                .order_by(IntegrationFeature.codigo.asc())
            )
        ).scalars().all()
        policy_rows = (
            await self.db.execute(
                select(IntegrationSyncPolicy.mode)
                .join(IntegrationFeature, IntegrationSyncPolicy.feature_id == IntegrationFeature.id)
                .where(
                    IntegrationSyncPolicy.config_id == canonical_config.id,
                    IntegrationSyncPolicy.deleted_at.is_(None),
                    IntegrationFeature.deleted_at.is_(None),
                )
                .order_by(IntegrationFeature.codigo.asc())
            )
        ).scalars().all()
        health_status = (
            await self.db.scalar(
                select(IntegrationHealth.status).where(
                    IntegrationHealth.config_id == canonical_config.id
                )
            )
        )
        versions = (
            await self.db.execute(
                select(IntegrationVersion)
                .where(IntegrationVersion.config_id == canonical_config.id)
                .order_by(IntegrationVersion.version_number.desc())
            )
        ).scalars().all()
        credential = None
        if canonical_config.credential_ref_id is not None:
            credential = (
                await self.db.execute(
                    select(IntegrationCredential).where(
                        IntegrationCredential.id == canonical_config.credential_ref_id,
                        IntegrationCredential.deleted_at.is_(None),
                    )
                )
            ).scalar_one_or_none()
        latest_version_snapshot = versions[0].snapshot_mascarado if versions else None
        return _MaterializedDetails(
            feature_codes=tuple(feature_rows),
            policy_modes=tuple(policy_rows),
            health_status=health_status,
            version_count=len(versions),
            latest_version_snapshot=latest_version_snapshot,
            credential=credential,
        )

    def _classify(
        self,
        snapshot: _TenantSnapshot,
        details: _MaterializedDetails,
    ) -> tuple[str, tuple[str, ...]]:
        if len(snapshot.active_canonical_rows) > 1:
            return LegacySankhyaReconciliationState.DUPLICATE_CANONICAL.value, ()

        if snapshot.legacy_config is None and snapshot.canonical_config is None:
            if snapshot.deleted_canonical_rows:
                return LegacySankhyaReconciliationState.CANONICAL_SOFT_DELETED.value, ()
            return LegacySankhyaReconciliationState.NO_RECORDS.value, ()

        if snapshot.legacy_config is not None and not snapshot.legacy_config.ativo:
            if snapshot.canonical_config is None:
                return LegacySankhyaReconciliationState.LEGACY_SOFT_DELETED.value, ()
            return LegacySankhyaReconciliationState.CANONICAL_ONLY.value, ()

        if snapshot.canonical_config is None and snapshot.legacy_config is not None:
            if snapshot.deleted_canonical_rows:
                return LegacySankhyaReconciliationState.CANONICAL_SOFT_DELETED.value, ()
            return LegacySankhyaReconciliationState.LEGACY_ONLY.value, ()

        if snapshot.canonical_config is not None and snapshot.legacy_config is None:
            return LegacySankhyaReconciliationState.CANONICAL_ONLY.value, ()

        assert snapshot.legacy_config is not None
        assert snapshot.canonical_config is not None
        diffs = self._compare_legacy_and_canonical(snapshot, details)
        if diffs:
            return LegacySankhyaReconciliationState.BOTH_DIVERGENT.value, tuple(diffs)
        return LegacySankhyaReconciliationState.BOTH_CONSISTENT.value, ()

    def _compare_legacy_and_canonical(
        self,
        snapshot: _TenantSnapshot,
        details: _MaterializedDetails,
    ) -> list[str]:
        legacy = snapshot.legacy_config
        canonical = snapshot.canonical_config
        provider = snapshot.provider
        assert legacy is not None
        assert canonical is not None

        auth_service = SankhyaGatewayAuthService(legacy)
        expected_connection = SankhyaCanonicalAdapter._connection_payload(legacy)
        expected_credential_payload = (
            SankhyaCanonicalAdapter._credentials_payload(legacy, canonical.credential)
            if canonical.credential is not None
            else None
        )
        expected_credential_bundle = SankhyaCanonicalAdapter._credential_bundle(legacy)
        expected_credential_mask_metadata = SankhyaCanonicalAdapter._credential_mask_metadata(
            legacy,
            {
                "auth_model": auth_service.auth_model(),
                "client_secret_mask": "••••••••" if legacy.client_secret else None,
                "x_token_mask": "••••••••" if legacy.x_token else None,
                "token_mask": "••••••••" if legacy.token else None,
                "appkey_mask": "••••••••" if legacy.appkey else None,
                "password_mask": "••••••••" if legacy.password else None,
            },
        )
        expected_health = SankhyaCanonicalAdapter._health_from_provider_status(legacy)
        expected_version_snapshot = self._expected_version_snapshot(legacy)

        diffs: list[str] = []
        if provider is None:
            diffs.append("provider_missing")
        elif not provider.ativa:
            diffs.append("provider_inactive")
        elif canonical.provider_id != provider.id:
            diffs.append("provider_mismatch")

        if canonical.scope_type != _DEFAULT_SCOPE_TYPE:
            diffs.append("scope_type_mismatch")
        if canonical.scope_id is not None:
            diffs.append("scope_id_not_null")
        if canonical.status != ("ativa" if legacy.ativo else "inativa"):
            diffs.append("status_mismatch")
        if canonical.lifecycle_state != (
            IntegrationStatus.ACTIVE.value if legacy.ativo else IntegrationStatus.DISABLED.value
        ):
            diffs.append("lifecycle_state_mismatch")
        if canonical.connection_payload != expected_connection:
            diffs.append("connection_payload_mismatch")
        if canonical.configuracoes != {"sync_interval": legacy.sync_interval}:
            diffs.append("configuracoes_mismatch")
        if canonical.credenciais != expected_credential_payload:
            diffs.append("credentials_payload_mismatch")

        credential = canonical.credential
        if credential is None:
            diffs.append("credential_missing")
        else:
            if credential.scope_type != _DEFAULT_SCOPE_TYPE:
                diffs.append("credential_scope_type_mismatch")
            if credential.scope_id is not None:
                diffs.append("credential_scope_id_not_null")
            if credential.provider_id != canonical.provider_id:
                diffs.append("credential_provider_mismatch")
            try:
                actual_bundle = decrypt_integration_secret(credential.segredo_criptografado) or ""
            except Exception:
                actual_bundle = ""
                diffs.append("credential_bundle_unreadable")
            if actual_bundle != expected_credential_bundle:
                diffs.append("credential_bundle_mismatch")
            if credential.mask_metadata != expected_credential_mask_metadata:
                diffs.append("credential_mask_metadata_mismatch")

        expected_feature_codes = tuple(sorted(_EXPECTED_FEATURE_CODES))
        if details.feature_codes != expected_feature_codes:
            diffs.append("feature_codes_mismatch")
        expected_policy_modes = tuple(
            _FEATURE_DEFAULTS[feature_code]["mode"].value
            for feature_code in sorted(_EXPECTED_FEATURE_CODES)
        )
        if details.policy_modes != expected_policy_modes:
            diffs.append("policy_count_mismatch")
        if details.health_status != expected_health:
            diffs.append("health_status_mismatch")
        if details.version_count < 1:
            diffs.append("version_missing")
        elif details.latest_version_snapshot != expected_version_snapshot:
            diffs.append("version_snapshot_mismatch")
        return diffs

    def _expected_version_snapshot(self, legacy: SankhyaConfig) -> dict[str, Any]:
        auth_service = SankhyaGatewayAuthService(legacy)
        return {
            "provider_slug": _SANKHYA_SLUG,
            "auth_model": auth_service.auth_model(),
            "sankhya_environment": legacy.environment,
            "sankhya_api_base_url": legacy.api_base_url or legacy.ws_url,
            "sankhya_auth_url": legacy.auth_url,
            "sankhya_client_id": legacy.client_id,
            "ws_url": legacy.ws_url,
            "username": legacy.username,
            "sync_interval": legacy.sync_interval,
            "ativo": legacy.ativo,
            "client_secret_configured": bool(legacy.client_secret),
            "client_secret_mask": "••••••••" if legacy.client_secret else None,
            "x_token_configured": bool(legacy.x_token),
            "x_token_mask": "••••••••" if legacy.x_token else None,
            "password_configured": bool(legacy.password),
            "password_mask": "••••••••" if legacy.password else None,
        }

    async def _dependency_counts(
        self,
        snapshot: _TenantSnapshot,
        details: _MaterializedDetails,
    ) -> dict[str, int]:
        canonical = snapshot.canonical_config
        counts = {
            "legacy_config": 1 if snapshot.legacy_config is not None else 0,
            "active_canonical": len(snapshot.active_canonical_rows),
            "deleted_canonical": len(snapshot.deleted_canonical_rows),
            "features": len(details.feature_codes),
            "policies": len(details.policy_modes),
            "health": 1 if details.health_status is not None else 0,
            "versions": details.version_count,
            "credentials": 0,
        }
        if canonical is None:
            return counts
        counts["credentials"] = int(
            await self.db.scalar(
                select(func.count()).select_from(IntegrationCredential).where(
                    IntegrationCredential.tenant_id == canonical.tenant_id,
                    IntegrationCredential.provider_id == canonical.provider_id,
                    IntegrationCredential.scope_type == canonical.scope_type,
                    IntegrationCredential.ativo.is_(True),
                    IntegrationCredential.deleted_at.is_(None),
                )
            )
            or 0
        )
        return counts

    async def _restore_rls_context(self, tenant_id: str) -> None:
        bind = self.db.get_bind()
        dialect = getattr(bind, "dialect", None)
        if getattr(dialect, "name", "") != "postgresql":
            return
        self.db.info["tenant_id"] = tenant_id
        await self.db.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )

    def _block_reasons(
        self,
        snapshot: _TenantSnapshot,
        classification: str,
        dependency_counts: dict[str, int],
        diff_summary: tuple[str, ...],
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if snapshot.provider is None:
            reasons.append("provider sankhya ausente no marketplace")
        elif not snapshot.provider.ativa:
            reasons.append("provider sankhya inativo no marketplace")

        if classification in {
            LegacySankhyaReconciliationState.BOTH_DIVERGENT.value,
            LegacySankhyaReconciliationState.DUPLICATE_CANONICAL.value,
        }:
            reasons.append("estado legado/canônico divergente ou duplicado")

        if dependency_counts.get("credentials", 0) > 1:
            reasons.append("credenciais canônicas duplicadas")
        if dependency_counts.get("health", 0) > 1:
            reasons.append("health canônico duplicado")
        if (
            dependency_counts.get("versions", 0) > 1
            and classification == LegacySankhyaReconciliationState.LEGACY_ONLY.value
        ):
            reasons.append("versionamento canônico múltiplo detectado")

        if diff_summary and classification != LegacySankhyaReconciliationState.LEGACY_ONLY.value:
            reasons.extend(diff_summary)

        return tuple(dict.fromkeys(reasons))

    def _action_for_state(self, classification: str, *, blocked: bool) -> str:
        if blocked:
            return "BLOCKED"
        if classification == LegacySankhyaReconciliationState.LEGACY_ONLY.value:
            return "MATERIALIZE_CANONICAL"
        return "NOOP"

    def _build_result(
        self,
        *,
        tenant_id: str,
        dry_run: bool,
        state_before: str,
        state_after: str,
        action: str,
        snapshot: _TenantSnapshot,
        details: _MaterializedDetails,
        dependency_counts: dict[str, int],
        changed: bool,
        block_reasons: tuple[str, ...],
        diff_summary: tuple[str, ...],
    ) -> LegacySankhyaReconciliationResult:
        canonical = snapshot.canonical_config
        provider = snapshot.provider
        return LegacySankhyaReconciliationResult(
            tenant_id=tenant_id,
            dry_run=dry_run,
            state_before=state_before,
            state_after=state_after,
            action=action,
            provider_slug=provider.slug if provider else None,
            provider_active=provider.ativa if provider else None,
            scope_type=canonical.scope_type if canonical else None,
            scope_id=canonical.scope_id if canonical else None,
            legacy_config_id=snapshot.legacy_config.id if snapshot.legacy_config else None,
            canonical_config_id=canonical.id if canonical else None,
            provider_id=canonical.provider_id if canonical else None,
            changed=changed,
            blocked=bool(block_reasons),
            block_reasons=block_reasons,
            diff_summary=diff_summary,
            dependency_counts=dependency_counts,
            feature_codes=details.feature_codes,
            policy_modes=details.policy_modes,
            health_status=details.health_status,
            version_count=details.version_count,
        )
