"""Router canonico da superficie HTTP ERP."""

# ruff: noqa: B008

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_tenant_permission
from integracoes.erp_readiness_service import ErpReadinessService
from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationStatus,
    IntegrationFeature,
    MarketplaceIntegracao,
)
from integracoes.sankhya.routers import (
    listar_timeline_sankhya as listar_timeline_sankhya_provider,
)
from integracoes.sankhya.routers import (
    obter_diagnostico_sankhya as obter_diagnostico_sankhya_provider,
)
from integracoes.sankhya.schemas import (
    SankhyaOperationalDiagnosisResponse,
    SankhyaTimelineItemResponse,
)
from integracoes.sankhya.services import SankhyaSyncService
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
        "feature_code": feature_code_by_id.get(association.feature_id) if feature_code_by_id else None,
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
    stmt = (
        select(MarketplaceIntegracao)
        .where(MarketplaceIntegracao.slug == provider_slug)
    )
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


def get_sankhya_sync_service(
    db: AsyncSession = Depends(get_session),
) -> SankhyaSyncService:
    """Fornece o serviço oficial do provider Sankhya."""

    return SankhyaSyncService(db)


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


async def _resolve_active_erp_provider_slug(
    *,
    tenant_id: uuid.UUID,
    readiness_service: ErpReadinessService,
    sankhya_sync_service: SankhyaSyncService,
) -> str:
    """Resolve o provider ERP ativo sem duplicar runtime ou queries no router."""

    runtime = await readiness_service.carregar_runtime(_runtime_probe(tenant_id))
    if runtime.provider is not None and runtime.config is not None:
        provider_slug = getattr(runtime.provider, "slug", None)
        if isinstance(provider_slug, str) and provider_slug:
            return provider_slug

    legacy_sankhya_config = await sankhya_sync_service.get_config(str(tenant_id))
    if legacy_sankhya_config is not None:
        return "sankhya"

    raise HTTPException(status_code=404, detail="ERP não configurado")


def _unsupported_provider_error(provider_slug: str) -> HTTPException:
    """Erro padronizado para providers ainda fora da superficie ERP."""

    return HTTPException(
        status_code=501,
        detail=(
            "Provider ERP ainda não suportado pela superfície HTTP ERP: "
            f"{provider_slug}"
        ),
    )


async def _assert_sankhya_provider(
    *,
    tenant_id: uuid.UUID,
    readiness_service: ErpReadinessService,
    sankhya_sync_service: SankhyaSyncService,
) -> None:
    """Garante delegação apenas para o provider ERP suportado nesta fase."""

    provider_slug = await _resolve_active_erp_provider_slug(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )
    if provider_slug != "sankhya":
        raise _unsupported_provider_error(provider_slug)


@router.get(
    "/status",
    response_model=dict[str, Any],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_status_erp(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    sankhya_sync_service: SankhyaSyncService = Depends(get_sankhya_sync_service),
) -> dict[str, Any]:
    """Delega a leitura de status ERP para o provider ativo."""

    await _assert_sankhya_provider(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )
    return await sankhya_sync_service.obter_status_detalhado(str(tenant_id))


@router.get(
    "/health",
    response_model=dict[str, Any],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_health_erp(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    sankhya_sync_service: SankhyaSyncService = Depends(get_sankhya_sync_service),
) -> dict[str, Any]:
    """Delega a leitura de health ERP para o provider ativo."""

    await _assert_sankhya_provider(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )
    return await sankhya_sync_service.obter_health_detalhado(str(tenant_id))


@router.get(
    "/jobs",
    response_model=list[dict[str, Any]],
    dependencies=[Depends(require_tenant_permission("integrations:logs:view"))],
)
async def listar_jobs_erp(
    limit: int = 20,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    sankhya_sync_service: SankhyaSyncService = Depends(get_sankhya_sync_service),
) -> list[dict[str, Any]]:
    """Delega a listagem de jobs ERP para o provider ativo."""

    await _assert_sankhya_provider(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )
    return await sankhya_sync_service.listar_jobs(str(tenant_id), limit=limit)


@router.get(
    "/timeline",
    response_model=list[SankhyaTimelineItemResponse],
    dependencies=[Depends(require_tenant_permission("integrations:logs:view"))],
)
async def listar_timeline_erp(
    status: str | None = None,
    feature_code: str | None = None,
    origem: str | None = None,
    limit: int = 50,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    sankhya_sync_service: SankhyaSyncService = Depends(get_sankhya_sync_service),
) -> list[SankhyaTimelineItemResponse]:
    """Delega a timeline ERP ao provider ativo sem duplicar composicao."""

    await _assert_sankhya_provider(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )
    return cast(
        list[SankhyaTimelineItemResponse],
        await listar_timeline_sankhya_provider(
        status=status,
        feature_code=feature_code,
        origem=origem,
        limit=limit,
        tenant_id=tenant_id,
        sync_service=sankhya_sync_service,
        ),
    )


@router.get(
    "/diagnostico",
    response_model=SankhyaOperationalDiagnosisResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_diagnostico_erp(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    readiness_service: ErpReadinessService = Depends(get_erp_readiness_service),
    sankhya_sync_service: SankhyaSyncService = Depends(get_sankhya_sync_service),
) -> SankhyaOperationalDiagnosisResponse:
    """Delega o diagnostico ERP ao provider ativo sem regra paralela."""

    await _assert_sankhya_provider(
        tenant_id=tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )
    return cast(
        SankhyaOperationalDiagnosisResponse,
        await obter_diagnostico_sankhya_provider(
            tenant_id=tenant_id,
            sync_service=sankhya_sync_service,
        ),
    )



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
    sankhya_sync_service: SankhyaSyncService = Depends(get_sankhya_sync_service),
    association_service: ExternalRecordAssociationService = Depends(get_external_association_service),
) -> PaginatedExternalRecordAssociationResponse:
    await _assert_sankhya_provider(
        tenant_id=current_tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
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
    sankhya_sync_service: SankhyaSyncService = Depends(get_sankhya_sync_service),
    association_service: ExternalRecordAssociationService = Depends(get_external_association_service),
) -> PaginatedExternalRecordAssociationResponse:
    await _assert_sankhya_provider(
        tenant_id=current_tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
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
    sankhya_sync_service: SankhyaSyncService = Depends(get_sankhya_sync_service),
    association_service: ExternalRecordAssociationService = Depends(get_external_association_service),
) -> ExternalRecordAssociationSummaryResponse:
    await _assert_sankhya_provider(
        tenant_id=current_tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
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
    sankhya_sync_service: SankhyaSyncService = Depends(get_sankhya_sync_service),
    association_service: ExternalRecordAssociationService = Depends(get_external_association_service),
) -> ExternalRecordAssociationPendingItemResponse:
    await _assert_sankhya_provider(
        tenant_id=current_tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )

    association = await association_service.db.get(ExternalRecordAssociation, association_id)
    if association is None or association.tenant_id != str(current_tenant_id) or association.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Associacao externa nao encontrada")
    if association.status != ExternalRecordAssociationStatus.PENDING.value:
        raise HTTPException(status_code=409, detail="Somente associacoes pendentes podem ser reconciliadas")

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
