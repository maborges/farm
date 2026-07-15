"""Router canonico da superficie HTTP ERP."""

# ruff: noqa: B008

from __future__ import annotations

import uuid
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Garante que os providers estejam registrados ao carregar o router.
import integracoes.erp.provider_bootstrap  # noqa: F401
from core.dependencies import get_session, get_tenant_id, require_tenant_permission
from integracoes.erp.legacy_provider_resolution import resolve_legacy_sankhya_provider
from integracoes.erp.provider_contract import ErpProviderRuntime
from integracoes.erp.provider_registry import (
    ErpProviderNotRegisteredError,
    erp_provider_registry,
)
from integracoes.erp_readiness_service import ErpReadinessService
from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationStatus,
    IntegrationFeature,
    MarketplaceIntegracao,
)
from integracoes.schemas import (
    ExternalRecordAssociationGovernanceReconcileRequest,
    ExternalRecordAssociationHistoryItemResponse,
    ExternalRecordAssociationPendingItemResponse,
    ExternalRecordAssociationReconcile,
    ExternalRecordAssociationSummaryResponse,
    PaginatedExternalRecordAssociationResponse,
    ProviderPublicIdentity,
    ProviderSchemaResponse,
)
from integracoes.services import DuplicateAssociationError, ExternalRecordAssociationService

router = APIRouter(prefix="/erp", tags=["Integração ERP"])

_UNCONFIGURED_PROVIDER_SOURCE = "UNCONFIGURED"
_LEGACY_SANKHYA_SOURCE = "LEGACY_SANKHYA_CONFIG"
_NOT_CONFIGURED_STATUS = "NOT_CONFIGURED"
_NOT_CONFIGURED_SUMMARY = "Nenhum ERP configurado para este tenant."
_NOT_CONFIGURED_RECOMMENDATION = (
    "Selecione um provider no Console ERP e salve a configuração inicial para liberar "
    "a operação."
)


@dataclass(frozen=True)
class ErpRuntimeResolution:
    """Resultado semântico da resolução do runtime ERP corrente."""

    configured: bool
    provider_slug: str | None
    runtime: Any
    source: str
    provider_runtime: ErpProviderRuntime | None = None


def _sanitize_external_payload(association) -> dict[str, object]:
    metadata = association.metadata_json or {}
    return {
        "secondary_keys": association.secondary_keys or {},
        "metadata_keys": list(metadata.keys()),
    }


def _build_external_key(association) -> str:
    return "|".join(
        [
            str(association.provider_id),
            str(association.config_id),
            association.environment,
            association.external_entity,
            association.external_company_id or "-",
            association.external_branch_id or "-",
            association.external_record_id,
        ]
    )


def _serialize_history_item(history) -> ExternalRecordAssociationHistoryItemResponse:
    return ExternalRecordAssociationHistoryItemResponse.model_validate(history)


async def _serialize_pending_item(
    association,
    *,
    service: ExternalRecordAssociationService,
    feature_code_by_id: dict[int, str] | None = None,
) -> ExternalRecordAssociationPendingItemResponse:
    history = await service.list_history(tenant_id=association.tenant_id, link_id=association.id)
    payload = {
        "id": association.id,
        "tenant_id": association.tenant_id,
        "provider_id": association.provider_id,
        "config_id": association.config_id,
        "feature_id": association.feature_id,
        "feature_code": feature_code_by_id.get(association.feature_id)
        if feature_code_by_id
        else None,
        "environment": association.environment,
        "scope_type": association.scope_type,
        "scope_id": association.scope_id,
        "external_company_id": association.external_company_id,
        "external_branch_id": association.external_branch_id,
        "local_entity_type": association.local_entity,
        "local_entity_id": association.local_record_id,
        "external_entity_type": association.external_entity,
        "external_id": association.external_record_id,
        "external_key": _build_external_key(association),
        "external_payload": _sanitize_external_payload(association),
        "status": association.status,
        "confidence": association.confidence,
        "motivo": association.notes,
        "last_sync_at": association.last_sync_at,
        "last_job_id": association.last_job_id,
        "created_at": association.created_at,
        "updated_at": association.updated_at,
        "history": [_serialize_history_item(item) for item in history],
    }
    return ExternalRecordAssociationPendingItemResponse.model_validate(payload)


@router.get(
    "/providers/{provider_slug}/schema",
    response_model=ProviderSchemaResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_schema_do_provider(
    provider_slug: str,
    db: AsyncSession = Depends(get_session),
) -> ProviderSchemaResponse:
    """Devolve os esquemas declarativos de conexão e credenciais do provider ERP."""
    stmt = select(MarketplaceIntegracao).where(MarketplaceIntegracao.slug == provider_slug)
    result = await db.execute(stmt)
    provider = result.scalar_one_or_none()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider não encontrado.")

    if provider.provider_type != "ERP":
        raise HTTPException(status_code=400, detail="O provider selecionado não é do tipo ERP.")

    if not provider.ativa:
        raise HTTPException(status_code=400, detail="O provider selecionado está inativo.")

    return ProviderSchemaResponse(
        provider=ProviderPublicIdentity(
            id=provider.id,
            slug=provider.slug,
            nome=provider.nome,
            descricao_curta=provider.descricao_curta,
            logo_url=provider.logo_url,
            provider_type=provider.provider_type,
            ativa=provider.ativa,
            oficial=provider.oficial,
            versao=provider.versao,
        ),
        schema_version=1,
        connection_schema=provider.connection_schema or {"required": [], "optional": []},
        credential_schema=provider.credential_schema or {"required": [], "optional": []},
    )


def get_erp_readiness_service(
    db: AsyncSession = Depends(get_session),
) -> ErpReadinessService:
    """Fornece o serviço oficial de readiness ERP."""

    return ErpReadinessService(db)


def get_external_association_service(
    db: AsyncSession = Depends(get_session),
) -> ExternalRecordAssociationService:
    """Fornece o serviço oficial de governança de associações externas."""

    return ExternalRecordAssociationService(db)


def _runtime_probe(tenant_id: uuid.UUID) -> SimpleNamespace:
    """Monta o contexto mínimo para reutilizar o runtime oficial."""

    return SimpleNamespace(
        tenant_id=tenant_id,
        escopo_modulos={},
        diagnostico_inicial_snapshot={},
    )


def _extract_runtime_provider_slug(runtime: Any) -> str | None:
    """Extrai o slug do provider a partir do runtime carregado."""

    provider_slug = getattr(getattr(runtime, "provider", None), "slug", None)
    if isinstance(provider_slug, str) and provider_slug.strip():
        return provider_slug.strip().lower()
    return None


def _raise_inconsistent_runtime(runtime: Any) -> None:
    """Falha de forma explícita quando o runtime canônico vier inconsistente."""

    has_provider = getattr(runtime, "provider", None) is not None
    has_config = getattr(runtime, "config", None) is not None
    if has_provider == has_config:
        return
    raise HTTPException(
        status_code=500,
        detail="Runtime ERP inconsistente: provider e configuração não estão alinhados.",
    )


def _build_unconfigured_readiness() -> dict[str, Any]:
    """Monta o estado vazio oficial para o readiness do console ERP."""

    return {
        "status": _NOT_CONFIGURED_STATUS,
        "label": "Não configurado",
        "variant": "secondary",
        "summary": _NOT_CONFIGURED_SUMMARY,
        "pending": ["selecionar um ERP e salvar a configuração inicial"],
        "block_reasons": [],
        "cta_url": "/dashboard/settings/integracoes/erp",
        "provider_code": None,
        "provider_display_name": None,
        "health_status": _NOT_CONFIGURED_STATUS,
        "capabilities_evaluated": [],
        "policies_evaluated": [],
        "pending_links": 0,
        "conflict_links": 0,
    }


def _build_unconfigured_status_response() -> dict[str, Any]:
    """Retorna o estado vazio do status ERP sem assumir provider."""

    return {
        "configurado": False,
        "ativo": False,
        "ultimo_sync": None,
        "proximo_sync": None,
        "status_conexao": _NOT_CONFIGURED_STATUS,
        "status_legado": None,
        "status_canonico": None,
        "status_origem": _UNCONFIGURED_PROVIDER_SOURCE,
        "health_origem": _UNCONFIGURED_PROVIDER_SOURCE,
        "config_id_canonico": None,
        "lifecycle_state": None,
        "health_status": _NOT_CONFIGURED_STATUS,
        "health_summary": _NOT_CONFIGURED_SUMMARY,
        "last_success_at": None,
        "last_failure_at": None,
        "consecutive_failures": 0,
        "features_habilitadas": [],
        "policies_resumidas": [],
        "provider_definition": None,
        "feature_schema": None,
        "sync_schema": None,
        "health_schema": None,
        "readiness": _build_unconfigured_readiness(),
    }


def _build_unconfigured_health_response() -> dict[str, Any]:
    """Retorna o health vazio do runtime ERP."""

    return {
        "configurado": False,
        "origem": _UNCONFIGURED_PROVIDER_SOURCE,
        "status": _NOT_CONFIGURED_STATUS,
        "summary": "Integração ainda não configurada.",
        "checked_at": None,
        "last_success_at": None,
        "last_failure_at": None,
        "consecutive_failures": 0,
        "details": None,
    }


def _build_unconfigured_diagnosis_response() -> dict[str, Any]:
    """Retorna o diagnóstico vazio do runtime ERP."""

    return {
        "origem": _UNCONFIGURED_PROVIDER_SOURCE,
        "health_atual": _NOT_CONFIGURED_STATUS,
        "status_degradacao": "NONE",
        "ultimo_sucesso_at": None,
        "ultima_falha_at": None,
        "falhas_consecutivas": 0,
        "feature_mais_problematica": None,
        "jobs_pendentes": 0,
        "jobs_falhos": 0,
        "recomendacao_operacional": _NOT_CONFIGURED_RECOMMENDATION,
    }


def _apply_legacy_provider_hint(
    payload: dict[str, Any],
    *,
    provider_slug: str | None,
) -> dict[str, Any]:
    """Mantém o fallback legado identificável pelo frontend sem materializar nada."""

    if not provider_slug:
        return payload
    readiness_payload = payload.get("readiness")
    if not isinstance(readiness_payload, dict):
        payload["readiness"] = {
            **_build_unconfigured_readiness(),
            "provider_code": provider_slug,
        }
        return payload
    if readiness_payload.get("provider_code") in {None, ""}:
        readiness_payload["provider_code"] = provider_slug
    return payload


async def _resolve_active_erp_context(
    *,
    tenant_id: uuid.UUID,
    readiness_service: ErpReadinessService,
    db: AsyncSession,
) -> ErpRuntimeResolution:
    """Resolve o runtime ERP sem tratar bootstrap tardio como erro de recurso."""

    runtime = await readiness_service.carregar_runtime(_runtime_probe(tenant_id))
    _raise_inconsistent_runtime(runtime)
    provider_slug = _extract_runtime_provider_slug(runtime)
    if runtime.provider is not None and runtime.config is not None:
        if provider_slug is None:
            raise HTTPException(
                status_code=500,
                detail="Runtime ERP inconsistente: provider ativo sem slug resolvível.",
            )

        # Resolver pelo registry — sem branch por provider_slug.
        try:
            provider_runtime = erp_provider_registry.resolve(provider_slug, db)
        except ErpProviderNotRegisteredError as exc:
            raise HTTPException(
                status_code=501,
                detail=(
                    "Provider ERP configurado mas sem runtime registrado: "
                    f"{provider_slug}"
                ),
            ) from exc

        return ErpRuntimeResolution(
            configured=True,
            provider_slug=provider_slug,
            runtime=runtime,
            source="CANONICAL_RUNTIME",
            provider_runtime=provider_runtime,
        )

    # Fallback legado isolado.
    has_legacy = await resolve_legacy_sankhya_provider(str(tenant_id), db)
    if has_legacy:
        try:
            provider_runtime = erp_provider_registry.resolve("sankhya", db)
        except ErpProviderNotRegisteredError:
            provider_runtime = None

        return ErpRuntimeResolution(
            configured=True,
            provider_slug="sankhya",
            runtime=runtime,
            source=_LEGACY_SANKHYA_SOURCE,
            provider_runtime=provider_runtime,
        )

    return ErpRuntimeResolution(
        configured=False,
        provider_slug=None,
        runtime=runtime,
        source=_UNCONFIGURED_PROVIDER_SOURCE,
    )


async def _assert_configured_provider(
    *,
    tenant_id: uuid.UUID,
    readiness_service: ErpReadinessService,
    db: AsyncSession,
) -> ErpRuntimeResolution:
    """Garante delegação apenas para providers ERP com runtime registrado."""

    return await _resolve_active_erp_context(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=db,
    )


@router.get(
    "/status",
    response_model=dict[str, Any],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_status_erp(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Delega a leitura de status ERP para o provider ativo."""

    resolution = await _assert_configured_provider(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=db,
    )
    if not resolution.configured or resolution.provider_runtime is None:
        return _build_unconfigured_status_response()
    payload = await resolution.provider_runtime.get_status(str(tenant_id))
    return _apply_legacy_provider_hint(
        payload,
        provider_slug=(
            resolution.provider_slug
            if resolution.source == _LEGACY_SANKHYA_SOURCE
            else None
        ),
    )


@router.get(
    "/health",
    response_model=dict[str, Any],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_health_erp(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Delega a leitura de health ERP para o provider ativo."""

    resolution = await _assert_configured_provider(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=db,
    )
    if not resolution.configured or resolution.provider_runtime is None:
        return _build_unconfigured_health_response()
    return await resolution.provider_runtime.get_health(str(tenant_id))


@router.get(
    "/jobs",
    response_model=list[dict[str, Any]],
    dependencies=[Depends(require_tenant_permission("integrations:logs:view"))],
)
async def listar_jobs_erp(
    limit: int = 20,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Delega a listagem de jobs ERP para o provider ativo."""

    resolution = await _assert_configured_provider(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=db,
    )
    if not resolution.configured or resolution.provider_runtime is None:
        return []
    return await resolution.provider_runtime.get_jobs(str(tenant_id), limit=limit)


@router.get(
    "/timeline",
    response_model=list[dict[str, Any]],
    dependencies=[Depends(require_tenant_permission("integrations:logs:view"))],
)
async def listar_timeline_erp(
    status: str | None = None,
    feature_code: str | None = None,
    origem: str | None = None,
    limit: int = 50,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Delega a timeline ERP ao provider ativo sem duplicar composicao."""

    resolution = await _assert_configured_provider(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=db,
    )
    if not resolution.configured or resolution.provider_runtime is None:
        return []
    return await resolution.provider_runtime.get_timeline(
        str(tenant_id),
        status=status,
        feature_code=feature_code,
        origem=origem,
        limit=limit,
    )


@router.get(
    "/diagnostico",
    response_model=dict[str, Any],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_diagnostico_erp(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Delega o diagnostico ERP ao provider ativo sem regra paralela."""

    resolution = await _assert_configured_provider(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        db=db,
    )
    if not resolution.configured or resolution.provider_runtime is None:
        return _build_unconfigured_diagnosis_response()
    return await resolution.provider_runtime.get_diagnosis(str(tenant_id))


@router.get(
    "/associacoes/pendentes",
    response_model=PaginatedExternalRecordAssociationResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def listar_associacoes_erp_pendentes(
    provider_id: int | None = None,
    feature_id: int | None = None,
    feature_code: str | None = None,
    entity_type: str | None = None,
    external_entity_type: str | None = None,
    environment: str | None = None,
    tenant_filter: uuid.UUID | None = Query(default=None, alias="tenant_id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    db: AsyncSession = Depends(get_session),
    association_service: ExternalRecordAssociationService = Depends(
        get_external_association_service
    ),
) -> PaginatedExternalRecordAssociationResponse:
    await _assert_configured_provider(
        tenant_id=current_tenant_id,
        readiness_service=readiness_service,
        db=db,
    )
    if tenant_filter is not None and tenant_filter != current_tenant_id:
        raise HTTPException(status_code=403, detail="Filtro de tenant fora do escopo atual")

    associations = await association_service.list_pending_associations(
        tenant_id=str(current_tenant_id),
        provider_id=provider_id,
        feature_id=feature_id,
        feature_code=feature_code,
        environment=environment,
        local_entity=entity_type,
        external_entity=external_entity_type,
        limit=limit,
        offset=offset,
    )

    feature_code_by_id: dict[int, str] = {}
    feature_ids = {item.feature_id for item in associations if item.feature_id is not None}
    if feature_ids:
        rows = await association_service.db.execute(
            select(IntegrationFeature.id, IntegrationFeature.codigo).where(
                IntegrationFeature.id.in_(feature_ids),
            ),
        )
        feature_code_by_id = {row.id: row.codigo for row in rows}

    items = [
        await _serialize_pending_item(
            association,
            service=association_service,
            feature_code_by_id=feature_code_by_id,
        )
        for association in associations
    ]

    total_filtered = await association_service.count_pending_associations(
        tenant_id=str(current_tenant_id),
        provider_id=provider_id,
        feature_id=feature_id,
        feature_code=feature_code,
        environment=environment,
        local_entity=entity_type,
        external_entity=external_entity_type,
    )

    total_global = await association_service.count_pending_associations(
        tenant_id=str(current_tenant_id),
    )

    return PaginatedExternalRecordAssociationResponse(
        items=items,
        total=total_global,
        total_filtered=total_filtered,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/associacoes",
    response_model=PaginatedExternalRecordAssociationResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def listar_associacoes_erp(
    provider_id: int | None = None,
    feature_id: int | None = None,
    feature_code: str | None = None,
    entity_type: str | None = None,
    external_entity_type: str | None = None,
    environment: str | None = None,
    status: ExternalRecordAssociationStatus | None = None,
    search: str | None = None,
    tenant_filter: uuid.UUID | None = Query(default=None, alias="tenant_id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    db: AsyncSession = Depends(get_session),
    association_service: ExternalRecordAssociationService = Depends(
        get_external_association_service
    ),
) -> PaginatedExternalRecordAssociationResponse:
    await _assert_configured_provider(
        tenant_id=current_tenant_id,
        readiness_service=readiness_service,
        db=db,
    )
    if tenant_filter is not None and tenant_filter != current_tenant_id:
        raise HTTPException(status_code=403, detail="Filtro de tenant fora do escopo atual")

    associations = await association_service.list_associations(
        tenant_id=str(current_tenant_id),
        provider_id=provider_id,
        feature_id=feature_id,
        feature_code=feature_code,
        environment=environment,
        local_entity=entity_type,
        external_entity=external_entity_type,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )

    feature_code_by_id: dict[int, str] = {}
    feature_ids = {item.feature_id for item in associations if item.feature_id is not None}
    if feature_ids:
        rows = await association_service.db.execute(
            select(IntegrationFeature.id, IntegrationFeature.codigo).where(
                IntegrationFeature.id.in_(feature_ids),
            ),
        )
        feature_code_by_id = {row.id: row.codigo for row in rows}

    items = [
        await _serialize_pending_item(
            association,
            service=association_service,
            feature_code_by_id=feature_code_by_id,
        )
        for association in associations
    ]

    total_filtered = await association_service.count_associations(
        tenant_id=str(current_tenant_id),
        provider_id=provider_id,
        feature_id=feature_id,
        feature_code=feature_code,
        environment=environment,
        local_entity=entity_type,
        external_entity=external_entity_type,
        status=status,
        search=search,
    )

    total_global = await association_service.count_associations(
        tenant_id=str(current_tenant_id),
    )

    return PaginatedExternalRecordAssociationResponse(
        items=items,
        total=total_global,
        total_filtered=total_filtered,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/associacoes/resumo",
    response_model=ExternalRecordAssociationSummaryResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def resumo_associacoes_erp(
    provider_id: int | None = None,
    environment: str | None = None,
    tenant_filter: uuid.UUID | None = Query(default=None, alias="tenant_id"),
    current_tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    db: AsyncSession = Depends(get_session),
    association_service: ExternalRecordAssociationService = Depends(
        get_external_association_service
    ),
) -> ExternalRecordAssociationSummaryResponse:
    await _assert_configured_provider(
        tenant_id=current_tenant_id,
        readiness_service=readiness_service,
        db=db,
    )
    if tenant_filter is not None and tenant_filter != current_tenant_id:
        raise HTTPException(status_code=403, detail="Filtro de tenant fora do escopo atual")

    summary = await association_service.get_association_summary(
        tenant_id=str(current_tenant_id),
        provider_id=provider_id,
        environment=environment,
    )
    return ExternalRecordAssociationSummaryResponse(**summary)


@router.post(
    "/associacoes/{association_id}/reconciliar",
    response_model=ExternalRecordAssociationPendingItemResponse,
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def reconciliar_associacao_erp(
    association_id: uuid.UUID,
    payload: ExternalRecordAssociationGovernanceReconcileRequest,
    current_tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    db: AsyncSession = Depends(get_session),
    association_service: ExternalRecordAssociationService = Depends(
        get_external_association_service
    ),
) -> ExternalRecordAssociationPendingItemResponse:
    await _assert_configured_provider(
        tenant_id=current_tenant_id,
        readiness_service=readiness_service,
        db=db,
    )

    association = await association_service.db.get(ExternalRecordAssociation, association_id)
    if (
        association is None
        or association.tenant_id != str(current_tenant_id)
        or association.deleted_at is not None
    ):
        raise HTTPException(status_code=404, detail="Associacao externa nao encontrada")
    if association.status != ExternalRecordAssociationStatus.PENDING.value:
        raise HTTPException(
            status_code=409, detail="Somente associacoes pendentes podem ser reconciliadas"
        )

    try:
        await association_service.detect_duplicate(
            tenant_id=association.tenant_id,
            provider_id=association.provider_id,
            config_id=association.config_id,
            environment=association.environment,
            local_entity=payload.local_entity_type,
            local_record_id=payload.local_entity_id,
            external_entity=association.external_entity,
            external_record_id=association.external_record_id,
            external_company_id=association.external_company_id,
            external_branch_id=association.external_branch_id,
            ignore_link_id=association.id,
        )
    except DuplicateAssociationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    reconciled = await association_service.reconcile_pending(
        association,
        ExternalRecordAssociationReconcile(
            actor_usuario_id=payload.actor_usuario_id,
            reason=payload.reason,
            local_entity=payload.local_entity_type,
            local_record_id=payload.local_entity_id,
            confidence=payload.confidence,
            last_job_id=payload.last_job_id,
            notes=payload.notes,
        ),
    )

    feature_code_by_id: dict[int, str] = {}
    if reconciled.feature_id is not None:
        rows = await association_service.db.execute(
            select(IntegrationFeature.id, IntegrationFeature.codigo).where(
                IntegrationFeature.id == reconciled.feature_id,
            ),
        )
        feature_code_by_id = {row.id: row.codigo for row in rows}

    return await _serialize_pending_item(
        reconciled,
        service=association_service,
        feature_code_by_id=feature_code_by_id,
    )
