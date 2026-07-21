"""Serviço canônico de configuração das políticas de sincronização ERP."""

from __future__ import annotations

import uuid
from urllib.parse import urlencode, urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from integracoes.erp.schemas import ErpSyncPolicyResponse, ErpSyncPolicyUpdate
from integracoes.models import (
    IntegrationFeature,
    IntegrationStatus,
    IntegrationSyncPolicy,
    MarketplaceIntegracao,
    TenantIntegracao,
)

ALLOWED_SCHEDULES = {
    "*/5 * * * *",
    "*/15 * * * *",
    "*/30 * * * *",
    "0 * * * *",
    "0 */6 * * *",
    "0 */12 * * *",
    "0 0 * * *",
}


class ErpSyncPolicyNotFoundError(LookupError):
    """Política inexistente no runtime ERP do tenant."""


class ErpSyncPolicyValidationError(ValueError):
    """Configuração incompatível com o fluxo do provider."""


class ErpSyncPolicyService:
    """Consulta e altera políticas existentes sem duplicar o runtime legado."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def listar(self, tenant_id: uuid.UUID) -> list[ErpSyncPolicyResponse]:
        """Listar políticas do ERP ativo pertencentes ao tenant."""
        rows = (await self.session.execute(self._base_query(tenant_id))).all()
        return [self._serialize(policy, feature, config) for policy, feature, config in rows]

    async def atualizar(
        self,
        tenant_id: uuid.UUID,
        feature_code: str,
        payload: ErpSyncPolicyUpdate,
    ) -> ErpSyncPolicyResponse:
        """Atualizar uma política tenant-safe e preservar o restante do runtime."""
        policy, feature, config = await self._obter(tenant_id, feature_code)
        self._validar(feature, payload)
        self._aplicar(policy, payload)
        await self.session.commit()
        await self.session.refresh(policy)
        return self._serialize(policy, feature, config)

    async def garantir_execucao_manual(
        self,
        tenant_id: uuid.UUID,
        feature_code: str,
    ) -> None:
        """Bloquear execução direta quando a política do fluxo estiver desativada."""
        policy, feature, _ = await self._obter(tenant_id, feature_code)
        if not feature.habilitada:
            raise ErpSyncPolicyValidationError("Este recurso da integração está desativado.")
        if not policy.ativa:
            raise ErpSyncPolicyValidationError("A sincronização deste recurso está desativada.")
        if feature_code == "pessoas" and policy.mode == "MANUAL":
            raise ErpSyncPolicyValidationError(
                "No modo manual, consulte a pessoa pelo ID do ERP na página de Pessoas."
            )
        if policy.mode != "MANUAL":
            raise ErpSyncPolicyValidationError(
                "Este recurso está configurado para sincronização agendada."
            )

    def _base_query(self, tenant_id: uuid.UUID):
        return (
            select(IntegrationSyncPolicy, IntegrationFeature, TenantIntegracao)
            .join(IntegrationFeature, IntegrationSyncPolicy.feature_id == IntegrationFeature.id)
            .join(TenantIntegracao, IntegrationSyncPolicy.config_id == TenantIntegracao.id)
            .join(MarketplaceIntegracao, TenantIntegracao.integracao_id == MarketplaceIntegracao.id)
            .where(
                IntegrationSyncPolicy.tenant_id == tenant_id,
                IntegrationFeature.tenant_id == tenant_id,
                TenantIntegracao.tenant_id == tenant_id,
                IntegrationSyncPolicy.deleted_at.is_(None),
                IntegrationFeature.deleted_at.is_(None),
                TenantIntegracao.deleted_at.is_(None),
                TenantIntegracao.lifecycle_state.notin_(
                    [
                        IntegrationStatus.DISABLED.value,
                        IntegrationStatus.REVOKED.value,
                        IntegrationStatus.REMOVED.value,
                    ]
                ),
                MarketplaceIntegracao.provider_type == "ERP",
                MarketplaceIntegracao.ativa.is_(True),
            )
            .order_by(IntegrationFeature.nome.asc())
        )

    async def _obter(self, tenant_id: uuid.UUID, feature_code: str):
        stmt = self._base_query(tenant_id).where(IntegrationFeature.codigo == feature_code)
        row = (await self.session.execute(stmt)).first()
        if row is None:
            raise ErpSyncPolicyNotFoundError(feature_code)
        return row

    @staticmethod
    def _validar(feature: IntegrationFeature, payload: ErpSyncPolicyUpdate) -> None:
        settings = feature.settings_payload if isinstance(feature.settings_payload, dict) else {}
        supported = settings.get("runtime_sync_modes") or settings.get("supported_modes") or []
        if payload.mode not in supported:
            raise ErpSyncPolicyValidationError("Modo não suportado para este fluxo.")
        if payload.mode == "AGENDADO" and payload.trigger_expression not in ALLOWED_SCHEDULES:
            raise ErpSyncPolicyValidationError("Frequência de agendamento não suportada.")
        if payload.mode != "AGENDADO" and payload.record_scope == "ALL_EXTERNAL":
            raise ErpSyncPolicyValidationError(
                "A importação total exige o modo automático agendado."
            )

    @staticmethod
    def _aplicar(policy: IntegrationSyncPolicy, payload: ErpSyncPolicyUpdate) -> None:
        values = payload.model_dump(exclude={"record_scope"})
        for field, value in values.items():
            setattr(policy, field, value)
        settings = dict(policy.settings_payload or {})
        settings["record_scope"] = payload.record_scope
        policy.settings_payload = settings

    @staticmethod
    def _serialize(
        policy: IntegrationSyncPolicy,
        feature: IntegrationFeature,
        config: TenantIntegracao,
    ) -> ErpSyncPolicyResponse:
        settings = feature.settings_payload if isinstance(feature.settings_payload, dict) else {}
        endpoint = settings.get("runtime_endpoint") or {}
        connection = (
            config.connection_payload if isinstance(config.connection_payload, dict) else {}
        )
        base_url = connection.get("sankhya_api_base_url") or connection.get("ws_url")
        return ErpSyncPolicyResponse(
            feature_code=feature.codigo,
            feature_name=feature.nome,
            feature_description=feature.descricao,
            feature_enabled=feature.habilitada,
            mode=policy.mode,
            record_scope=(policy.settings_payload or {}).get("record_scope", "LINKED_ONLY"),
            ativa=policy.ativa,
            prioridade=policy.prioridade,
            retry_ativo=policy.retry_ativo,
            retry_limite=policy.retry_limite,
            batch_size=policy.batch_size,
            backoff_seconds=policy.backoff_seconds,
            timeout_seconds=policy.timeout_seconds,
            trigger_expression=policy.trigger_expression,
            supported_modes=list(settings.get("runtime_sync_modes") or []),
            endpoint_url=(
                ErpSyncPolicyService._resolve_endpoint_url(str(base_url), endpoint)
                if base_url and endpoint
                else None
            ),
            endpoint_service=endpoint.get("service_name"),
            endpoint_entity=endpoint.get("entity"),
        )

    @staticmethod
    def _resolve_endpoint_url(base_url: str, metadata: dict[str, object]) -> str | None:
        path = metadata.get("path")
        query = metadata.get("query")
        if not isinstance(path, str) or not isinstance(query, dict):
            return None
        parsed = urlsplit(base_url)
        prefix = parsed.path.split("/gateway/v1", maxsplit=1)[0].rstrip("/")
        safe_query = {str(key): str(value) for key, value in query.items()}
        return urlunsplit(
            (parsed.scheme, parsed.netloc, f"{prefix}{path}", urlencode(safe_query), "")
        )
