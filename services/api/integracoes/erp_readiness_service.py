"""Serviço interno para avaliação consolidada da prontidão ERP."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationStatus,
    IntegrationFeature,
    IntegrationHealth,
    IntegrationHealthStatus,
    IntegrationScope,
    IntegrationStatus,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)

_ERP_REQUIRED_FEATURE_CODES = ("pessoas", "produtos", "financeiro", "nfe")
_ERP_CRITICAL_HEALTH = {
    IntegrationHealthStatus.AUTH_ERROR.value,
    IntegrationHealthStatus.CONFIG_ERROR.value,
    IntegrationHealthStatus.DISCONNECTED.value,
}
_ERP_ALLOWED_HEALTH_WARNING = {
    IntegrationHealthStatus.DEGRADED.value,
    IntegrationHealthStatus.PARTIAL_FAILURE.value,
    IntegrationHealthStatus.RATE_LIMITED.value,
}
_ERP_REQUIRED_DIAGNOSTICS = ("connection_test", "timeline", "manual_reconciliation")
_ERP_REQUIRED_OBSERVABILITY = ("health", "jobs", "logs", "reconciliation")
_ERP_READINESS_CTA = "/dashboard/settings/integracoes/erp"


@dataclass(frozen=True)
class ErpChecklistRuntime:
    """Snapshot canônico do runtime ERP já materializado."""

    declared: bool
    provider: MarketplaceIntegracao | None
    config: TenantIntegracao | None
    health: IntegrationHealth | None
    features: dict[str, IntegrationFeature]
    policies: dict[str, IntegrationSyncPolicy]
    pending_links: int = 0
    conflict_links: int = 0


@dataclass(frozen=True)
class ErpReadinessResult:
    """Resultado consolidado de prontidão ERP."""

    status: str
    provider_code: str | None
    provider_name: str | None
    provider_display_name: str | None
    health_status: str | None
    capabilities_evaluated: list[dict[str, Any]] = field(default_factory=list)
    policies_evaluated: list[dict[str, Any]] = field(default_factory=list)
    pending_links: int = 0
    conflict_links: int = 0
    pending_items: list[str] = field(default_factory=list)
    block_reasons: list[str] = field(default_factory=list)
    cta_url: str = _ERP_READINESS_CTA
    description: str = ""
    declared: bool = False


class ErpReadinessService:
    """Calcula prontidão ERP sem duplicar regra entre Wizard e Console."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def avaliar(self, implantacao: Any) -> ErpReadinessResult:
        """Avalia a prontidão ERP a partir da implantação corrente.

        Args:
            implantacao: Implantação operacional do tenant.

        Returns:
            Snapshot consolidado da prontidão ERP.
        """

        runtime = await self.carregar_runtime(implantacao)
        return self.avaliar_runtime(implantacao, runtime)

    async def carregar_runtime(self, implantacao: Any) -> ErpChecklistRuntime:
        """Carrega o runtime canônico do provider ERP.

        Args:
            implantacao: Implantação operacional do tenant.

        Returns:
            Snapshot do runtime ERP com provider, health, capabilities, policies e conflitos.
        """

        declared = self._erp_declared_for_implantacao(implantacao)
        tenant_id = str(implantacao.tenant_id)
        config_stmt = (
            select(TenantIntegracao, MarketplaceIntegracao)
            .join(MarketplaceIntegracao, TenantIntegracao.provider_id == MarketplaceIntegracao.id)
            .where(
                TenantIntegracao.tenant_id == tenant_id,
                TenantIntegracao.deleted_at.is_(None),
                TenantIntegracao.scope_type.in_(
                    [IntegrationScope.TENANT.value, IntegrationScope.ESTABELECIMENTO.value]
                ),
                TenantIntegracao.lifecycle_state.notin_(
                    [IntegrationStatus.REMOVED.value, IntegrationStatus.REVOKED.value]
                ),
                MarketplaceIntegracao.provider_type == "ERP",
                MarketplaceIntegracao.ativa.is_(True),
            )
            .order_by(TenantIntegracao.installed_at.desc())
            .limit(1)
        )
        runtime_row = (await self.session.execute(config_stmt)).first()
        if runtime_row is None:
            return ErpChecklistRuntime(
                declared=declared,
                provider=None,
                config=None,
                health=None,
                features={},
                policies={},
            )

        config, provider = runtime_row
        return ErpChecklistRuntime(
            declared=declared,
            provider=provider,
            config=config,
            health=await self._load_health(config.id),
            features=await self._load_features(config.id),
            policies=await self._load_policies(config.id),
            pending_links=await self._count_links(
                tenant_id,
                config.id,
                provider.id,
                ExternalRecordAssociationStatus.PENDING.value,
            ),
            conflict_links=await self._count_links(
                tenant_id,
                config.id,
                provider.id,
                ExternalRecordAssociationStatus.CONFLICT.value,
            ),
        )

    def avaliar_runtime(
        self,
        implantacao: Any,
        runtime: ErpChecklistRuntime,
    ) -> ErpReadinessResult:
        """Consolida o status de prontidão a partir do runtime carregado.

        Args:
            implantacao: Implantação operacional do tenant.
            runtime: Snapshot canônico já carregado.

        Returns:
            Resultado consolidado com status, pendências e motivos de bloqueio.
        """

        capabilities = self._build_capability_evaluation(runtime)
        policies = self._build_policy_evaluation(runtime)
        pending_items: list[str] = []
        block_reasons: list[str] = []
        provider_code = None
        provider_name = None
        provider_display_name = None
        if runtime.provider is not None:
            provider_code = getattr(runtime.provider, "slug", None) or getattr(
                runtime.provider, "provider_code", None
            )
            provider_name = getattr(runtime.provider, "nome", None) or getattr(
                runtime.provider, "provider_name", None
            )
            provider_definition = getattr(runtime.provider, "provider_definition", None)
            if isinstance(provider_definition, dict):
                provider_display_name = provider_definition.get("display_name") or provider_name
            else:
                provider_display_name = provider_name
        health_status = runtime.health.status if runtime.health is not None else None

        if not runtime.declared and runtime.config is None:
            return ErpReadinessResult(
                status="DISPENSADO",
                provider_code=provider_code,
                provider_name=provider_name,
                provider_display_name=provider_display_name,
                health_status=health_status,
                capabilities_evaluated=capabilities,
                policies_evaluated=policies,
                pending_links=runtime.pending_links,
                conflict_links=runtime.conflict_links,
                pending_items=["operação sem ERP informado"],
                description=(
                    "Este tenant pode operar sem ERP. O piloto inicial segue liberado enquanto não houver integração a configurar."
                ),
                declared=runtime.declared,
            )

        if runtime.config is None or runtime.provider is None:
            pending_items.append("ERP ainda não configurado")
            return self._build_result(
                status="PENDENTE",
                provider_code=provider_code,
                provider_name=provider_name,
                provider_display_name=provider_display_name,
                health_status=health_status,
                capabilities=capabilities,
                policies=policies,
                runtime=runtime,
                pending_items=pending_items,
                block_reasons=block_reasons,
                description=(
                    "O uso de ERP foi informado, mas a integração ainda não foi configurada no console ERP."
                ),
            )

        if runtime.health is None:
            pending_items.append("teste de comunicação ainda não executado")
            return self._build_result(
                status="PENDENTE",
                provider_code=provider_code,
                provider_name=provider_name,
                provider_display_name=provider_display_name,
                health_status=health_status,
                capabilities=capabilities,
                policies=policies,
                runtime=runtime,
                pending_items=pending_items,
                block_reasons=block_reasons,
                description=(
                    "O ERP já foi configurado, mas ainda falta validar a comunicação. Execute o teste de conexão no console ERP."
                ),
            )

        if runtime.health.status in _ERP_CRITICAL_HEALTH:
            block_reasons.append(
                f"a comunicação com o ERP apresentou falha crítica ({runtime.health.status})"
            )
            return self._build_result(
                status="FALHOU",
                provider_code=provider_code,
                provider_name=provider_name,
                provider_display_name=provider_display_name,
                health_status=health_status,
                capabilities=capabilities,
                policies=policies,
                runtime=runtime,
                pending_items=pending_items,
                block_reasons=block_reasons,
                description=(
                    "A comunicação com o ERP apresentou falha crítica e precisa ser corrigida "
                    f"antes do piloto ({runtime.health.status})."
                ),
            )

        missing_capabilities = self._missing_capabilities(capabilities)
        if missing_capabilities:
            block_reasons.append("faltam funções obrigatórias para o piloto inicial")
            pending_items.extend(
                f"função obrigatória indisponível: {code}" for code in missing_capabilities
            )
            return self._build_result(
                status="FALHOU",
                provider_code=provider_code,
                provider_name=provider_name,
                provider_display_name=provider_display_name,
                health_status=health_status,
                capabilities=capabilities,
                policies=policies,
                runtime=runtime,
                pending_items=pending_items,
                block_reasons=block_reasons,
                description=(
                    "Algumas funções obrigatórias para o piloto inicial ainda não estão disponíveis nesta integração: "
                    + ", ".join(missing_capabilities)
                    + "."
                ),
            )

        missing_policies = self._missing_policies(runtime)
        if missing_policies:
            pending_items.extend(
                f"regra de atualização pendente: {code}" for code in missing_policies
            )
            return self._build_result(
                status="PENDENTE",
                provider_code=provider_code,
                provider_name=provider_name,
                provider_display_name=provider_display_name,
                health_status=health_status,
                capabilities=capabilities,
                policies=policies,
                runtime=runtime,
                pending_items=pending_items,
                block_reasons=block_reasons,
                description=(
                    "Ainda faltam regras obrigatórias para atualização dos dados em: "
                    + ", ".join(missing_policies)
                    + "."
                ),
            )

        if runtime.conflict_links > 0:
            block_reasons.append("existem conflitos críticos de vínculo entre AgroSaaS e ERP")
            pending_items.append(
                f"conflitos críticos de vínculo pendentes: {runtime.conflict_links}"
            )
            return self._build_result(
                status="FALHOU",
                provider_code=provider_code,
                provider_name=provider_name,
                provider_display_name=provider_display_name,
                health_status=health_status,
                capabilities=capabilities,
                policies=policies,
                runtime=runtime,
                pending_items=pending_items,
                block_reasons=block_reasons,
                description=(
                    f"Existem {runtime.conflict_links} conflitos críticos de vínculo entre AgroSaaS e ERP aguardando tratamento."
                ),
            )

        if runtime.pending_links > 0:
            pending_items.append(
                f"confirmação manual pendente para {runtime.pending_links} vínculo(s) com o ERP"
            )
            return self._build_result(
                status="PENDENTE",
                provider_code=provider_code,
                provider_name=provider_name,
                provider_display_name=provider_display_name,
                health_status=health_status,
                capabilities=capabilities,
                policies=policies,
                runtime=runtime,
                pending_items=pending_items,
                block_reasons=block_reasons,
                description=(
                    f"Ainda existem {runtime.pending_links} vínculos com o ERP aguardando confirmação manual."
                ),
            )

        description = self._ready_message(runtime)
        return ErpReadinessResult(
            status="ATENDIDO",
            provider_code=provider_code,
            provider_name=provider_name,
            provider_display_name=provider_display_name,
            health_status=health_status,
            capabilities_evaluated=capabilities,
            policies_evaluated=policies,
            pending_links=runtime.pending_links,
            conflict_links=runtime.conflict_links,
            pending_items=pending_items,
            block_reasons=block_reasons,
            description=description,
            declared=runtime.declared,
        )

    def _build_result(
        self,
        *,
        status: str,
        provider_code: str | None,
        provider_name: str | None,
        provider_display_name: str | None,
        health_status: str | None,
        capabilities: list[dict[str, Any]],
        policies: list[dict[str, Any]],
        runtime: ErpChecklistRuntime,
        pending_items: list[str],
        block_reasons: list[str],
        description: str,
    ) -> ErpReadinessResult:
        return ErpReadinessResult(
            status=status,
            provider_code=provider_code,
            provider_name=provider_name,
            provider_display_name=provider_display_name,
            health_status=health_status,
            capabilities_evaluated=capabilities,
            policies_evaluated=policies,
            pending_links=runtime.pending_links,
            conflict_links=runtime.conflict_links,
            pending_items=pending_items,
            block_reasons=block_reasons,
            description=description,
            declared=runtime.declared,
        )

    def _build_capability_evaluation(self, runtime: ErpChecklistRuntime) -> list[dict[str, Any]]:
        capability_matrix = self._provider_capability_matrix(runtime.provider)
        evaluated: list[dict[str, Any]] = []
        for feature_code in _ERP_REQUIRED_FEATURE_CODES:
            feature = runtime.features.get(feature_code)
            capability = (
                capability_matrix.get(feature_code)
                or getattr(feature, "settings_payload", {})
                or {}
            )
            missing = self._missing_capability_requirements(feature_code, feature, capability)
            evaluated.append(
                {
                    "feature_code": feature_code,
                    "present": feature is not None
                    and getattr(feature, "habilitada", False) is True,
                    "status": capability.get("status"),
                    "maturity": capability.get("maturity"),
                    "observability_requirements": capability.get("observability_requirements")
                    or [],
                    "missing": missing,
                }
            )
        return evaluated

    def _build_policy_evaluation(self, runtime: ErpChecklistRuntime) -> list[dict[str, Any]]:
        evaluated: list[dict[str, Any]] = []
        for feature_code in _ERP_REQUIRED_FEATURE_CODES:
            policy = runtime.policies.get(feature_code)
            feature = runtime.features.get(feature_code)
            evaluated.append(
                {
                    "feature_code": feature_code,
                    "active": bool(policy and policy.ativa),
                    "mode": getattr(policy, "mode", None),
                    "retry_limite": getattr(policy, "retry_limite", None),
                    "batch_size": getattr(policy, "batch_size", None),
                    "timeout_seconds": getattr(policy, "timeout_seconds", None),
                    "supported_modes": ((feature.settings_payload or {}) if feature else {}).get(
                        "supported_modes", []
                    ),
                }
            )
        return evaluated

    def _missing_capabilities(self, capabilities: list[dict[str, Any]]) -> list[str]:
        return [item["feature_code"] for item in capabilities if item["missing"]]

    def _missing_capability_requirements(
        self,
        feature_code: str,
        feature: IntegrationFeature | None,
        capability: dict[str, Any],
    ) -> list[str]:
        if feature is None or feature.habilitada is not True:
            return [feature_code]
        if capability.get("status") not in {"SUPPORTED", "PARTIAL"}:
            return [feature_code]
        if capability.get("maturity") not in {"TESTED", "PILOT_READY", "PRODUCTION_READY"}:
            return [feature_code]
        observability = capability.get("observability_requirements")
        if not isinstance(observability, list):
            return [feature_code]
        return [
            f"{feature_code}:{requirement}"
            for requirement in _ERP_REQUIRED_OBSERVABILITY
            if requirement not in observability
        ]

    def _missing_policies(self, runtime: ErpChecklistRuntime) -> list[str]:
        missing: list[str] = []
        for feature_code in _ERP_REQUIRED_FEATURE_CODES:
            policy = runtime.policies.get(feature_code)
            feature = runtime.features.get(feature_code)
            supported = ((feature.settings_payload or {}) if feature else {}).get(
                "supported_modes", []
            )
            if policy is None or policy.ativa is not True:
                missing.append(feature_code)
                continue
            if supported and policy.mode not in supported:
                missing.append(feature_code)
        return sorted(set(missing))

    def _provider_capability_matrix(
        self,
        provider: MarketplaceIntegracao | None,
    ) -> dict[str, dict[str, Any]]:
        if provider is None:
            return {}
        schema = getattr(provider, "feature_schema", None) or {}
        matrix = schema.get("capability_matrix") if isinstance(schema, dict) else []
        if not isinstance(matrix, list):
            return {}
        return {
            item["feature_code"]: item
            for item in matrix
            if isinstance(item, dict) and isinstance(item.get("feature_code"), str)
        }

    def _ready_message(self, runtime: ErpChecklistRuntime) -> str:
        provider_name = "ERP"
        if runtime.provider is not None:
            provider_name = (
                getattr(runtime.provider, "nome", None)
                or getattr(runtime.provider, "provider_name", None)
                or provider_name
            )
        if runtime.health is not None and runtime.health.status in _ERP_ALLOWED_HEALTH_WARNING:
            return (
                f"A integração com o ERP {provider_name} está liberada para o piloto inicial, "
                f"mas a comunicação está em atenção ({runtime.health.status}) e deve ser acompanhada."
            )
        return f"A integração com o ERP {provider_name} está pronta para o piloto inicial."

    def _erp_declared_for_implantacao(self, implantacao: Any) -> bool:
        for payload in (
            implantacao.escopo_modulos or {},
            implantacao.diagnostico_inicial_snapshot or {},
        ):
            if not isinstance(payload, dict):
                continue
            if payload.get("integracao_erp") is True:
                return True
            if payload.get("estrategia_carga") == "ERP":
                return True
            if isinstance(payload.get("erp_nome"), str) and payload["erp_nome"].strip():
                return True
            if payload.get("carga_erp") or payload.get("escopo_carga_erp"):
                return True
        return False

    async def _load_health(self, config_id: int) -> IntegrationHealth | None:
        stmt = select(IntegrationHealth).where(IntegrationHealth.config_id == config_id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _load_features(self, config_id: int) -> dict[str, IntegrationFeature]:
        stmt = select(IntegrationFeature).where(IntegrationFeature.config_id == config_id)
        features = (await self.session.execute(stmt)).scalars().all()
        return {feature.codigo: feature for feature in features}

    async def _load_policies(self, config_id: int) -> dict[str, IntegrationSyncPolicy]:
        stmt = (
            select(IntegrationSyncPolicy, IntegrationFeature)
            .join(
                IntegrationFeature,
                IntegrationSyncPolicy.feature_id == IntegrationFeature.id,
            )
            .where(IntegrationSyncPolicy.config_id == config_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {feature.codigo: policy for policy, feature in rows}

    async def _count_links(
        self,
        tenant_id: str,
        config_id: int,
        provider_id: int,
        status: str,
    ) -> int:
        stmt = select(ExternalRecordAssociation.id).where(
            ExternalRecordAssociation.tenant_id == tenant_id,
            ExternalRecordAssociation.config_id == config_id,
            ExternalRecordAssociation.provider_id == provider_id,
            ExternalRecordAssociation.status == status,
        )
        return len((await self.session.execute(stmt)).scalars().all())


__all__ = [
    "ErpChecklistRuntime",
    "ErpReadinessResult",
    "ErpReadinessService",
]
