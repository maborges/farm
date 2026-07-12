import re

# Update erp/router.py
with open("services/api/integracoes/erp/router.py", "r") as f:
    erp_content = f.read()

# Replace the sankhya router imports that we don't need anymore
erp_content = re.sub(r"from integracoes\.sankhya\.routers import \(\n    listar_associacoes_externas_pendentes as listar_associacoes_externas_pendentes_sankhya,\n    listar_associacoes_externas as listar_associacoes_externas_sankhya,\n    resumo_associacoes_externas as resumo_associacoes_externas_sankhya,\n\)", "", erp_content)
erp_content = re.sub(r"from integracoes\.sankhya\.routers import \(\n    reconciliar_associacao_externa as reconciliar_associacao_externa_sankhya,\n\)", "", erp_content)

# Add necessary imports
imports = """
from integracoes.models import (
    MarketplaceIntegracao,
    ExternalRecordAssociationStatus,
    ExternalRecordAssociation,
    IntegrationFeature,
)
from integracoes.services import ExternalRecordAssociationService, DuplicateAssociationError
from integracoes.schemas import (
    ExternalRecordAssociationGovernanceReconcileRequest,
    ExternalRecordAssociationHistoryItemResponse,
    ExternalRecordAssociationPendingItemResponse,
    ExternalRecordAssociationReconcile,
    ExternalRecordAssociationSummaryResponse,
    ProviderSchemaResponse,
    ProviderPublicIdentity,
)
"""
# Replace duplicate imports
erp_content = re.sub(r"from integracoes\.schemas import \([\s\S]*?ProviderPublicIdentity,\n\)", imports, erp_content)
erp_content = re.sub(r"from integracoes\.services import ExternalRecordAssociationService\nfrom integracoes\.models import MarketplaceIntegracao, ExternalRecordAssociationStatus", "", erp_content)

# Add helpers
helpers = """

def _sanitize_external_payload(association) -> dict[str, object]:
    return {
        "secondary_keys": association.secondary_keys or {},
        "metadata_json": association.metadata_json or {},
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

"""
erp_content = erp_content.replace("router = APIRouter(prefix=\"/erp\", tags=[\"Integração ERP\"])", "router = APIRouter(prefix=\"/erp\", tags=[\"Integração ERP\"])\n" + helpers)

# Replace endpoints
endpoints = """
@router.get(
    "/associacoes/pendentes",
    response_model=list[ExternalRecordAssociationPendingItemResponse],
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
) -> list[ExternalRecordAssociationPendingItemResponse]:
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

    return [
        await _serialize_pending_item(
            association,
            service=association_service,
            feature_code_by_id=feature_code_by_id,
        )
        for association in associations
    ]


@router.get(
    "/associacoes",
    response_model=list[ExternalRecordAssociationPendingItemResponse],
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
) -> list[ExternalRecordAssociationPendingItemResponse]:
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

    return [
        await _serialize_pending_item(
            association,
            service=association_service,
            feature_code_by_id=feature_code_by_id,
        )
        for association in associations
    ]


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
"""

erp_content = re.sub(r"@router\.get\(\n    \"/associacoes/pendentes\",[\s\S]*", endpoints, erp_content)
with open("services/api/integracoes/erp/router.py", "w") as f:
    f.write(erp_content)

# Update sankhya/routers/__init__.py
with open("services/api/integracoes/sankhya/routers/__init__.py", "r") as f:
    sankhya_content = f.read()

sankhya_content = re.sub(r"def _sanitize_external_payload[\s\S]*?async def listar_associacoes_externas_pendentes[\s\S]*?(?=@router\.get\(\n    \"/associacoes\",)", "", sankhya_content)
sankhya_content = re.sub(r"@router\.get\(\n    \"/associacoes\",[\s\S]*", "", sankhya_content)

# Also remove unneeded imports from sankhya
sankhya_content = re.sub(r"from integracoes\.schemas import \([\s\S]*?ExternalRecordAssociationSummaryResponse,\n\)\nfrom integracoes\.services import ExternalRecordAssociationService, DuplicateAssociationError", "", sankhya_content)
sankhya_content = re.sub(r"def get_external_association_service\([\s\S]*?    return ExternalRecordAssociationService\(db\)", "", sankhya_content)
sankhya_content = sankhya_content.replace("from integracoes.models import (\n    ExternalRecordAssociation,\n    ExternalRecordAssociationStatus,\n    IntegrationFeature,\n)", "")
with open("services/api/integracoes/sankhya/routers/__init__.py", "w") as f:
    f.write(sankhya_content)

