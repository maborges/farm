"""Rotas administrativas do Backoffice para Governança de Fontes de Mercado e Snapshots DERAL.

Implementa a administração de:
1. PTAX (Banco Central)
2. Séries SGS (Banco Central)
3. SIDRA (IBGE)
4. Preços Públicos e Snapshots DERAL (SEAB-PR)

Requisitos estritos de segurança:
- RBAC efetivo com isolamento total de usuários comerciais/gratuitos.
- Impossibilidade de adulterar cotações e indicadores oficiais individualmente.
- Publicação e rollback atômicos de snapshots versionados.
- Auditoria compulsória em AdminAuditLog.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, require_any_permission
from core.models.admin_audit_log import AdminAuditLog
from core.routers.backoffice_agro_collector import router as collector_router
from core.schemas.agro_config_schemas import (
    KEY_MERCADO,
    AgroMercadoConfig,
    DeralSnapshotActivationRequest,
    DeralSnapshotApprovalRequest,
    DeralSnapshotDetailResponse,
    DeralSnapshotIntegrityResponse,
    DeralSnapshotRollbackRequest,
    DeralSnapshotsListResponse,
    DeralSnapshotUploadResponse,
    DeralSyncTriggerResponse,
    MarketConfigUpdateRequest,
    MarketSourcesStatusResponse,
)
from core.services.admin_audit_service import resolve_admin_identity
from core.services.agro_config_service import agro_config_service
from core.services.deral_auto_sync_service import deral_auto_sync_service
from core.services.deral_snapshot_service import deral_snapshot_service
from core.services.market_sources_service import market_sources_service

router = APIRouter(
    prefix="/backoffice/agro/mercado",
    tags=["Backoffice — DeepFarms Agro Mercado e Fontes Oficiais"],
)
router.include_router(collector_router, prefix="/collector")

# Permissões canônicas
PERM_VIEW = ["backoffice:agro:market:view", "backoffice:agro:config:view", "backoffice:agro:*"]
PERM_UPDATE = ["backoffice:agro:market:update", "backoffice:agro:config:edit", "backoffice:agro:*"]


@router.get(
    "/status",
    response_model=MarketSourcesStatusResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Obtém a situação operacional consolidada das fontes oficiais de mercado",
)
async def get_market_sources_status(
    session: AsyncSession = Depends(get_session),
) -> MarketSourcesStatusResponse:
    """Retorna saúde, defasagem e TTLs de cache das 4 fontes oficiais (PTAX, SGS, SIDRA e DERAL)."""
    return await market_sources_service.get_sources_status(session=session)


@router.put(
    "/config",
    response_model=MarketSourcesStatusResponse,
    summary="Atualiza parâmetros operacionais e políticas de cache do subsistema de mercado",
)
async def update_market_config(
    payload: MarketConfigUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_UPDATE)),
) -> MarketSourcesStatusResponse:
    """Atualiza parâmetros de TTL e limites de defasagem com controle otimista de concorrência."""
    # 1. Carrega configuração atual
    current_val, current_meta, _ = await agro_config_service.get_config(
        session, KEY_MERCADO, use_cache=False
    )
    novo_dict = dict(current_val)

    # 2. Aplica apenas campos fornecidos no payload operacional
    if payload.ptax_cache_ttl_seconds is not None:
        novo_dict["ptax_cache_ttl_seconds"] = payload.ptax_cache_ttl_seconds
    if payload.macro_cache_ttl_seconds is not None:
        novo_dict["macro_cache_ttl_seconds"] = payload.macro_cache_ttl_seconds
    if payload.sidra_cache_ttl_seconds is not None:
        novo_dict["sidra_cache_ttl_seconds"] = payload.sidra_cache_ttl_seconds
    if payload.precos_cache_ttl_seconds is not None:
        novo_dict["precos_cache_ttl_seconds"] = payload.precos_cache_ttl_seconds
    if payload.max_defasagem_dias is not None:
        novo_dict["max_defasagem_dias"] = payload.max_defasagem_dias
    if payload.deral_source_url is not None:
        novo_dict["deral_source_url"] = payload.deral_source_url
    if payload.ptax_enabled is not None:
        novo_dict["ptax_enabled"] = payload.ptax_enabled
    if payload.sgs_enabled is not None:
        novo_dict["sgs_enabled"] = payload.sgs_enabled
    if payload.sidra_enabled is not None:
        novo_dict["sidra_enabled"] = payload.sidra_enabled
    if payload.deral_enabled is not None:
        novo_dict["deral_enabled"] = payload.deral_enabled

    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # 3. Atualiza via AgroConfigService com controle de concorrência e auditoria
    await agro_config_service.update_config(
        session=session,
        chave=KEY_MERCADO,
        novo_valor=novo_dict,
        admin_claims=admin_claims,
        expected_revision=payload.expected_revision,
        descricao="Ajuste administrativo de parâmetros de cache e tolerância de defasagem de mercado",
        ip_address=ip_address,
        user_agent=user_agent,
    )

    from public_mercado.router import apply_dynamic_market_config
    apply_dynamic_market_config(novo_dict)

    return await market_sources_service.get_sources_status(session=session)


@router.get(
    "/deral/snapshots",
    response_model=DeralSnapshotsListResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Lista todos os snapshots DERAL catalogados na plataforma",
)
async def list_deral_snapshots(
    session: AsyncSession = Depends(get_session),
) -> DeralSnapshotsListResponse:
    """Retorna histórico de snapshots com metadados de integridade SHA-256 e versão ativa."""
    return await deral_snapshot_service.list_snapshots(session=session)


@router.get(
    "/deral/snapshots/{snapshot_id}",
    response_model=DeralSnapshotDetailResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Obtém detalhes e itens de cotação de um snapshot DERAL específico",
)
async def get_deral_snapshot_details(
    snapshot_id: str,
    session: AsyncSession = Depends(get_session),
) -> DeralSnapshotDetailResponse:
    """Retorna itens e proveniência para pré-visualização antes da ativação ou rollback."""
    return await deral_snapshot_service.get_snapshot_details(session=session, snapshot_id=snapshot_id)


@router.post(
    "/deral/upload",
    response_model=DeralSnapshotUploadResponse,
    summary="Ingestão e validação estrita de novo arquivo de snapshot DERAL",
)
async def upload_deral_snapshot(
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_UPDATE)),
) -> DeralSnapshotUploadResponse:
    """Recebe arquivo (.json, .csv ou .xls), calcula SHA-256, valida 21 commodities e salva como VALIDADO."""
    content = await file.read()
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await deral_snapshot_service.upload_snapshot(
        session=session,
        raw_bytes=content,
        filename=file.filename or "deral_snapshot.json",
        admin_claims=admin_claims,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.get(
    "/deral/template.csv",
    summary="Baixa modelo CSV com as 21 commodities DERAL para preenchimento manual",
)
async def download_deral_template_csv(
    session: AsyncSession = Depends(get_session),
    _admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_VIEW)),
) -> Response:
    """Exporta planilha CSV UTF-8 BOM pré-preenchida com a última referência ativa."""
    csv_bytes, filename = await deral_snapshot_service.gerar_template_csv(session)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/deral/sync",
    response_model=DeralSyncTriggerResponse,
    summary="Dispara sincronização sob demanda com a planilha oficial DERAL/SEAB-PR",
)
async def trigger_deral_sync(
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_UPDATE)),
) -> DeralSyncTriggerResponse:
    """Consulta a fonte oficial HTTPS DERAL e ativa automaticamente semana mais recente."""
    return await deral_auto_sync_service.sincronizar_com_detalhes(session, admin_claims)


@router.post(
    "/deral/snapshots/{snapshot_id}/activate",
    response_model=DeralSnapshotDetailResponse,
    summary="Ativa atomicamente um snapshot DERAL validado",
)
async def activate_deral_snapshot(
    snapshot_id: str,
    payload: DeralSnapshotActivationRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_UPDATE)),
) -> DeralSnapshotDetailResponse:
    """Atualiza transacionalmente o ponteiro ativo, invalida o cache L1 e registra auditoria."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await deral_snapshot_service.activate_snapshot(
        session=session,
        snapshot_id=snapshot_id,
        admin_claims=admin_claims,
        expected_revision=payload.expected_revision,
        justificativa=payload.justificativa,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post(
    "/deral/snapshots/{snapshot_id}/rollback",
    response_model=DeralSnapshotDetailResponse,
    summary="Executa rollback atômico para um snapshot previamente homologado",
)
async def rollback_deral_snapshot(
    snapshot_id: str,
    payload: DeralSnapshotRollbackRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_UPDATE)),
) -> DeralSnapshotDetailResponse:
    """Reverte o ponteiro de snapshot ativo para a versão de destino especificada."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Garante que o ID da rota coincide com o payload ou usa o da rota
    target_id = payload.target_snapshot_id or snapshot_id

    return await deral_snapshot_service.rollback_snapshot(
        session=session,
        target_snapshot_id=target_id,
        admin_claims=admin_claims,
        expected_revision=payload.expected_revision,
        justificativa=payload.justificativa,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post(
    "/deral/snapshots/{snapshot_id}/approve",
    response_model=DeralSnapshotDetailResponse,
    summary="Aprova ou rejeita formalmente a proveniência e integridade de um snapshot",
)
async def approve_deral_snapshot(
    snapshot_id: str,
    payload: DeralSnapshotApprovalRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    admin_claims: dict[str, Any] = Depends(require_any_permission(*PERM_UPDATE)),
) -> DeralSnapshotDetailResponse:
    """Registra aprovação ou rejeição formal com rastreabilidade do operador e justificativa."""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    return await deral_snapshot_service.approve_snapshot(
        session=session,
        snapshot_id=snapshot_id,
        aprovado=payload.aprovado,
        justificativa=payload.justificativa,
        admin_claims=admin_claims,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.get(
    "/deral/snapshots/{snapshot_id}/verify-integrity",
    response_model=DeralSnapshotIntegrityResponse,
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Recalcula e audita a integridade criptográfica SHA-256 dos bytes persistidos",
)
async def verify_snapshot_integrity(
    snapshot_id: str,
    session: AsyncSession = Depends(get_session),
) -> DeralSnapshotIntegrityResponse:
    """Verifica e recalcula o hash SHA-256 e o tamanho a partir dos bytes originais imutáveis."""
    return await deral_snapshot_service.verify_snapshot_integrity(session=session, snapshot_id=snapshot_id)


@router.get(
    "/deral/snapshots/{snapshot_id}/download-raw",
    dependencies=[Depends(require_any_permission(*PERM_VIEW))],
    summary="Recupera o arquivo original imutável idêntico ao submetido no upload",
)
async def download_snapshot_raw_file(
    snapshot_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Retorna os bytes originais do documento para auditoria forense ou download."""
    raw_bytes, filename, content_type = await deral_snapshot_service.get_snapshot_raw_bytes(
        session=session, snapshot_id=snapshot_id
    )
    return Response(
        content=raw_bytes,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

