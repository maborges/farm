"""Sub-rotas do Backoffice para governança de fontes, execuções, sentinela e quarentena."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from agro_collector.backoffice_schemas import (
    CollectorApplySentinelRequest,
    CollectorBulkReviewRequest,
    CollectorBulkReviewResponse,
    CollectorDryRunResponse,
    CollectorRunsListResponse,
    CollectorSourceCreateRequest,
    CollectorSourceItem,
    CollectorSourcesListResponse,
    CollectorSourceUpdateRequest,
    CollectorStagingItem,
    CollectorStagingListResponse,
    CollectorStagingReviewRequest,
)
from agro_collector.backoffice_service import collector_backoffice_service
from agro_collector.contracts import CollectorRunSummary
from core.dependencies import get_session, require_any_permission

router = APIRouter(tags=["Backoffice — Agente Coletor Agropecuário"])

PERM_VIEW = ["backoffice:agro:market:view", "backoffice:agro:config:view", "backoffice:agro:*"]
PERM_UPDATE = ["backoffice:agro:market:update", "backoffice:agro:config:edit", "backoffice:agro:*"]

DbSessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminUpdateDep = Annotated[dict[str, Any], Depends(require_any_permission(*PERM_UPDATE))]


@router.get(
    "/sources",
    response_model=CollectorSourcesListResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Lista fontes oficiais e parceiros autorizados configurados no coletor",
)
async def list_collector_sources(session: DbSessionDep) -> CollectorSourcesListResponse:
    """Retorna fontes configuradas e totais de quarentena pendente."""
    return await collector_backoffice_service.list_sources(session)


@router.post(
    "/sources",
    response_model=CollectorSourceItem,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra nova fonte pública ou parceiro autorizado",
)
async def create_collector_source(
    payload: CollectorSourceCreateRequest,
    request: Request,
    session: DbSessionDep,
    admin_claims: AdminUpdateDep,
) -> CollectorSourceItem:
    """Registra nova fonte validando whitelist HTTPS e termo de parceiro."""
    return await collector_backoffice_service.create_source(
        session,
        payload,
        admin_claims,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.put(
    "/sources/{source_id}",
    response_model=CollectorSourceItem,
    summary="Atualiza parâmetros operacionais e URLs de uma fonte homologada",
)
async def update_collector_source(
    source_id: uuid.UUID,
    payload: CollectorSourceUpdateRequest,
    request: Request,
    session: DbSessionDep,
    admin_claims: AdminUpdateDep,
) -> CollectorSourceItem:
    """Atualiza parâmetros da fonte mantendo whitelist e auditoria."""
    return await collector_backoffice_service.update_source(
        session,
        source_id,
        payload,
        admin_claims,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/sources/{source_id}/test-dry-run",
    response_model=CollectorDryRunResponse,
    dependencies=[Depends(require_any_permission(*PERM_UPDATE))],
    summary="Testa coleta e extração da fonte em modo Dry-Run sem publicar",
)
async def test_collector_dry_run(
    source_id: uuid.UUID,
    session: DbSessionDep,
) -> CollectorDryRunResponse:
    """Executa fetch + extração + guardrails retornando prévia auditável."""
    return await collector_backoffice_service.test_dry_run(session, source_id)


@router.post(
    "/sources/{source_id}/run",
    response_model=CollectorRunSummary,
    summary="Dispara coleta imediata auditada para uma fonte homologada",
)
async def trigger_collector_run(
    source_id: uuid.UUID,
    request: Request,
    session: DbSessionDep,
    admin_claims: AdminUpdateDep,
) -> CollectorRunSummary:
    """Executa pipeline completo de ingestão sob rate limit administrativo."""
    return await collector_backoffice_service.trigger_run(
        session,
        source_id,
        admin_claims,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/runs",
    response_model=CollectorRunsListResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Lista execuções históricas, custos IA e sugestões do Sentinela",
)
async def list_collector_runs(
    session: DbSessionDep,
    source_id: uuid.UUID | None = None,
    status_filtro: str | None = None,
    limit: int = 50,
) -> CollectorRunsListResponse:
    """Retorna execuções ordenadas da mais recente para a mais antiga."""
    return await collector_backoffice_service.list_runs(
        session, source_id=source_id, run_status=status_filtro, limit=limit
    )


@router.get(
    "/runs/{run_id}/artifact",
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Baixa artefato original comprimido de uma execução dentro de 12 meses",
)
async def download_collector_artifact(
    run_id: uuid.UUID,
    session: DbSessionDep,
) -> Response:
    """Recupera documento original validando integridade SHA-256."""
    raw_bytes, filename, content_type, sha256 = (
        await collector_backoffice_service.download_run_artifact(session, run_id)
    )
    return Response(
        content=raw_bytes,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Artifact-SHA256": sha256,
        },
    )


@router.post(
    "/runs/{run_id}/apply-sentinel",
    response_model=CollectorSourceItem,
    summary="Aplica nova URL sugerida pelo Agente Sentinela com validação e auditoria",
)
async def apply_sentinel_suggestion(
    run_id: uuid.UUID,
    payload: CollectorApplySentinelRequest,
    request: Request,
    session: DbSessionDep,
    admin_claims: AdminUpdateDep,
) -> CollectorSourceItem:
    """Atualiza a URL principal da fonte usando sugestão segura do Sentinela."""
    return await collector_backoffice_service.apply_sentinel_suggestion(
        session,
        run_id,
        payload.justificativa,
        admin_claims,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.get(
    "/staging",
    response_model=CollectorStagingListResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Lista observações em fila de revisão/quarentena com evidência literal",
)
async def list_collector_staging(
    session: DbSessionDep,
    status_revisao: str = "PENDENTE_REVISAO",
    source_id: uuid.UUID | None = None,
    limit: int = 100,
) -> CollectorStagingListResponse:
    """Lista itens pendentes de curadoria humana no Backoffice."""
    return await collector_backoffice_service.list_staging(
        session, status_revisao=status_revisao, source_id=source_id, limit=limit
    )


@router.post(
    "/staging/bulk-review",
    response_model=CollectorBulkReviewResponse,
    summary="Aprova ou rejeita em lote múltiplas observações auditadas",
)
async def bulk_review_collector_staging(
    payload: CollectorBulkReviewRequest,
    request: Request,
    session: DbSessionDep,
    admin_claims: AdminUpdateDep,
) -> CollectorBulkReviewResponse:
    """Executa revisão em lote registrando trilha individual no AdminAuditLog."""
    return await collector_backoffice_service.bulk_review_staging(
        session,
        payload,
        admin_claims,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/staging/{staging_id}/approve",
    response_model=CollectorStagingItem,
    summary="Aprova 1-clique observação da quarentena e publica na série histórica",
)
async def approve_collector_staging(
    staging_id: uuid.UUID,
    payload: CollectorStagingReviewRequest,
    request: Request,
    session: DbSessionDep,
    admin_claims: AdminUpdateDep,
) -> CollectorStagingItem:
    """Promove observação validada para ``agro_market_observations`` com auditoria."""
    return await collector_backoffice_service.review_staging_item(
        session,
        staging_id,
        aprovar=True,
        justificativa=payload.justificativa,
        admin_claims=admin_claims,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post(
    "/staging/{staging_id}/reject",
    response_model=CollectorStagingItem,
    summary="Rejeita observação da quarentena com justificativa obrigatória",
)
async def reject_collector_staging(
    staging_id: uuid.UUID,
    payload: CollectorStagingReviewRequest,
    request: Request,
    session: DbSessionDep,
    admin_claims: AdminUpdateDep,
) -> CollectorStagingItem:
    """Descarta observação suspeita preservando histórico forense."""
    return await collector_backoffice_service.review_staging_item(
        session,
        staging_id,
        aprovar=False,
        justificativa=payload.justificativa,
        admin_claims=admin_claims,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
