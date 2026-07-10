"""Router canonico da superficie HTTP ERP."""

# ruff: noqa: B008

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_tenant_permission
from integracoes.erp_readiness_service import ErpReadinessService
from integracoes.sankhya.routers import (
    listar_associacoes_externas_pendentes as listar_associacoes_externas_pendentes_sankhya,
)
from integracoes.sankhya.routers import (
    listar_timeline_sankhya as listar_timeline_sankhya_provider,
)
from integracoes.sankhya.routers import (
    obter_diagnostico_sankhya as obter_diagnostico_sankhya_provider,
)
from integracoes.sankhya.routers import (
    reconciliar_associacao_externa as reconciliar_associacao_externa_sankhya,
)
from integracoes.sankhya.schemas import (
    SankhyaOperationalDiagnosisResponse,
    SankhyaTimelineItemResponse,
)
from integracoes.sankhya.services import SankhyaSyncService
from integracoes.schemas import (
    ExternalRecordAssociationGovernanceReconcileRequest,
    ExternalRecordAssociationPendingItemResponse,
)
from integracoes.services import ExternalRecordAssociationService

router = APIRouter(prefix="/erp", tags=["Integração ERP"])


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
    association_service: ExternalRecordAssociationService = Depends(
        get_external_association_service
    ),
) -> list[ExternalRecordAssociationPendingItemResponse]:
    """Delega governanca de associacoes pendentes ao provider ativo."""

    await _assert_sankhya_provider(
        tenant_id=current_tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )
    return cast(
        list[ExternalRecordAssociationPendingItemResponse],
        await listar_associacoes_externas_pendentes_sankhya(
            provider_id=provider_id,
            feature_id=feature_id,
            feature_code=feature_code,
            entity_type=entity_type,
            external_entity_type=external_entity_type,
            environment=environment,
            tenant_filter=tenant_filter,
            limit=limit,
            offset=offset,
            current_tenant_id=current_tenant_id,
            service=association_service,
        ),
    )


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
    association_service: ExternalRecordAssociationService = Depends(
        get_external_association_service
    ),
) -> ExternalRecordAssociationPendingItemResponse:
    """Delega conciliacao manual de associacoes ao provider ativo."""

    await _assert_sankhya_provider(
        tenant_id=current_tenant_id,
        readiness_service=readiness_service,
        sankhya_sync_service=sankhya_sync_service,
    )
    return cast(
        ExternalRecordAssociationPendingItemResponse,
        await reconciliar_associacao_externa_sankhya(
            association_id=association_id,
            payload=payload,
            current_tenant_id=current_tenant_id,
            service=association_service,
        ),
    )
