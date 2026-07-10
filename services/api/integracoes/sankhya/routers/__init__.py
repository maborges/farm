"""Routers para integração com ERP Sankhya."""
# ruff: noqa: B008

from __future__ import annotations

import time
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_tenant_permission
from integracoes.models import (
    ExternalRecordAssociation,
    ExternalRecordAssociationStatus,
    IntegrationFeature,
)
from integracoes.sankhya.schemas import (
    SankhyaConfigCreate,
    SankhyaConfigResponse,
    SankhyaHealthResponse,
    SankhyaIntegrationJobResponse,
    SankhyaLancamentoFinanceiroResponse,
    SankhyaNFEResponse,
    SankhyaOperationalDiagnosisResponse,
    SankhyaPessoaResponse,
    SankhyaProdutoResponse,
    SankhyaSyncLogResponse,
    SankhyaSyncStatusResponse,
    SankhyaTestConnectionResponse,
    SankhyaTimelineItemResponse,
)
from integracoes.sankhya.services import (
    SankhyaFinanceiroService,
    SankhyaNFeService,
    SankhyaPessoaService,
    SankhyaProdutoService,
    SankhyaSyncService,
)
from integracoes.schemas import (
    ExternalRecordAssociationGovernanceReconcileRequest,
    ExternalRecordAssociationHistoryItemResponse,
    ExternalRecordAssociationPendingItemResponse,
    ExternalRecordAssociationReconcile,
)
from integracoes.services import ExternalRecordAssociationService, DuplicateAssociationError

router = APIRouter(prefix="/sankhya", tags=["Integração Sankhya"])


def get_sync_service(db: AsyncSession = Depends(get_session)) -> SankhyaSyncService:
    return SankhyaSyncService(db)


def get_pessoa_service(db: AsyncSession = Depends(get_session)) -> SankhyaPessoaService:
    return SankhyaPessoaService(db)


def get_produto_service(db: AsyncSession = Depends(get_session)) -> SankhyaProdutoService:
    return SankhyaProdutoService(db)


def get_nfe_service(db: AsyncSession = Depends(get_session)) -> SankhyaNFeService:
    return SankhyaNFeService(db)


def get_financeiro_service(db: AsyncSession = Depends(get_session)) -> SankhyaFinanceiroService:
    return SankhyaFinanceiroService(db)


def get_external_association_service(
    db: AsyncSession = Depends(get_session),
) -> ExternalRecordAssociationService:
    return ExternalRecordAssociationService(db)


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


@router.post(
    "/config",
    response_model=SankhyaConfigResponse,
    status_code=201,
    dependencies=[Depends(require_tenant_permission("integrations:configure"))],
)
async def configurar_sankhya(
    config: SankhyaConfigCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
):
    """Configura integração com Sankhya no escopo do tenant."""
    tenant_scope = str(tenant_id)
    existing = await sync_service.get_config(tenant_scope)

    if existing:
        try:
            updated = await sync_service.atualizar_config(
                existing,
                sankhya_environment=config.sankhya_environment,
                sankhya_api_base_url=config.sankhya_api_base_url,
                sankhya_auth_url=config.sankhya_auth_url,
                sankhya_client_id=config.sankhya_client_id,
                sankhya_client_secret=config.sankhya_client_secret,
                sankhya_x_token=config.sankhya_x_token,
                sankhya_token=config.sankhya_token,
                sankhya_appkey=config.sankhya_appkey,
                ws_url=config.ws_url,
                username=config.username,
                password=config.password,
                sync_interval=config.sync_interval,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return await sync_service.obter_config_console(tenant_scope)

    try:
        created = await sync_service.criar_config(
            tenant_id=tenant_scope,
            sankhya_environment=config.sankhya_environment,
            sankhya_api_base_url=config.sankhya_api_base_url,
            sankhya_auth_url=config.sankhya_auth_url,
            sankhya_client_id=config.sankhya_client_id,
            sankhya_client_secret=config.sankhya_client_secret,
            sankhya_x_token=config.sankhya_x_token,
            sankhya_token=config.sankhya_token,
            sankhya_appkey=config.sankhya_appkey,
            ws_url=config.ws_url,
            username=config.username,
            password=config.password,
            sync_interval=config.sync_interval,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return await sync_service.obter_config_console(tenant_scope)


@router.get(
    "/config",
    response_model=SankhyaConfigResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_config_sankhya(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
):
    config = await sync_service.get_config(str(tenant_id))
    if not config:
        raise HTTPException(status_code=404, detail="Sankhya não configurado")
    return await sync_service.obter_config_console(str(tenant_id))


@router.post(
    "/config/testar-conexao",
    response_model=SankhyaTestConnectionResponse,
    dependencies=[Depends(require_tenant_permission("integrations:test"))],
)
async def testar_conexao_sankhya(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
):
    return await sync_service.testar_conexao(str(tenant_id))


@router.get(
    "/status",
    response_model=SankhyaSyncStatusResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_status_sankhya(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
):
    # Compatibilidade: mantém os campos legados `status_conexao` e `ultimo_sync`.
    return await sync_service.obter_status_detalhado(str(tenant_id))


@router.get(
    "/health",
    response_model=SankhyaHealthResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_health_sankhya(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
):
    return await sync_service.obter_health_detalhado(str(tenant_id))


@router.post(
    "/sync/pessoas",
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def sincronizar_pessoas(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
    pessoa_service: SankhyaPessoaService = Depends(get_pessoa_service),
):
    tenant_scope = str(tenant_id)
    log = await sync_service.iniciar_sync_log(tenant_scope, "pessoas", "import")

    try:
        start_time = time.time()
        importados = await pessoa_service.importar_pessoas(tenant_scope, log.id)
        tempo_ms = (time.time() - start_time) * 1000
        await sync_service.finalizar_sync_log(log.id, True, importados, 0, None, tempo_ms)
        return {
            "sucesso": True,
            "mensagem": f"{importados} pessoas sincronizadas",
            "tempo_ms": tempo_ms,
        }
    except Exception as exc:
        await sync_service.finalizar_sync_log(log.id, False, 0, 0, str(exc), 0)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/sync/produtos",
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def sincronizar_produtos(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
    produto_service: SankhyaProdutoService = Depends(get_produto_service),
):
    tenant_scope = str(tenant_id)
    log = await sync_service.iniciar_sync_log(tenant_scope, "produtos", "import")

    try:
        start_time = time.time()
        importados = await produto_service.importar_produtos(tenant_scope, log.id)
        tempo_ms = (time.time() - start_time) * 1000
        await sync_service.finalizar_sync_log(log.id, True, importados, 0, None, tempo_ms)
        return {
            "sucesso": True,
            "mensagem": f"{importados} produtos sincronizados",
            "tempo_ms": tempo_ms,
        }
    except Exception as exc:
        await sync_service.finalizar_sync_log(log.id, False, 0, 0, str(exc), 0)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/sync/completo",
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def sincronizar_completo(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
    pessoa_service: SankhyaPessoaService = Depends(get_pessoa_service),
    produto_service: SankhyaProdutoService = Depends(get_produto_service),
):
    tenant_scope = str(tenant_id)

    log_pessoas = await sync_service.iniciar_sync_log(tenant_scope, "pessoas", "import")
    pessoas_importadas = await pessoa_service.importar_pessoas(tenant_scope, log_pessoas.id)

    log_produtos = await sync_service.iniciar_sync_log(tenant_scope, "produtos", "import")
    produtos_importados = await produto_service.importar_produtos(tenant_scope, log_produtos.id)

    return {
        "sucesso": True,
        "pessoas_importadas": pessoas_importadas,
        "produtos_importados": produtos_importados,
        "mensagem": "Sincronização completa iniciada com sucesso.",
    }


@router.get(
    "/logs",
    response_model=list[SankhyaSyncLogResponse],
    dependencies=[Depends(require_tenant_permission("integrations:logs:view"))],
)
async def listar_logs_sankhya(
    tipo: str | None = None,
    status: str | None = None,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
):
    return await sync_service.listar_logs_enriquecidos(
        str(tenant_id),
        tipo=tipo,
        status=status,
        limit=limit,
    )


@router.get(
    "/jobs",
    response_model=list[SankhyaIntegrationJobResponse],
    dependencies=[Depends(require_tenant_permission("integrations:logs:view"))],
)
async def listar_jobs_sankhya(
    limit: int = 20,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
):
    return await sync_service.listar_jobs(str(tenant_id), limit=limit)


@router.get(
    "/timeline",
    response_model=list[SankhyaTimelineItemResponse],
    dependencies=[Depends(require_tenant_permission("integrations:logs:view"))],
)
async def listar_timeline_sankhya(
    status: str | None = None,
    feature_code: str | None = None,
    origem: str | None = None,
    limit: int = 50,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
):
    return await sync_service.listar_timeline_operacional(
        str(tenant_id),
        status=status,
        feature_code=feature_code,
        origem=origem,
        limit=limit,
    )


@router.get(
    "/diagnostico",
    response_model=SankhyaOperationalDiagnosisResponse,
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def obter_diagnostico_sankhya(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    sync_service: SankhyaSyncService = Depends(get_sync_service),
):
    return await sync_service.obter_diagnostico_operacional(str(tenant_id))


@router.get(
    "/pessoas",
    response_model=list[SankhyaPessoaResponse],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def listar_pessoas_sankhya(
    tipo: str | None = None,
    ativo: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    pessoa_service: SankhyaPessoaService = Depends(get_pessoa_service),
):
    return await pessoa_service.listar_pessoas(
        str(tenant_id),
        tipo=tipo,
        ativo=ativo,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/produtos",
    response_model=list[SankhyaProdutoResponse],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def listar_produtos_sankhya(
    ativo: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    produto_service: SankhyaProdutoService = Depends(get_produto_service),
):
    return await produto_service.listar_produtos(
        str(tenant_id), ativo=ativo, skip=skip, limit=limit
    )


@router.post(
    "/nfe/exportar",
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def exportar_nfe(
    nfe_data: dict,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: SankhyaNFeService = Depends(get_nfe_service),
):
    try:
        resultado = await service.exportar_nfe(str(tenant_id), nfe_data)
        return {"sucesso": True, "dados": resultado}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/nfe/importar-entrada",
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def importar_nfe_entrada(
    periodo_inicio: date,
    periodo_fim: date,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: SankhyaNFeService = Depends(get_nfe_service),
):
    try:
        importadas = await service.importar_nfe_entrada(str(tenant_id), periodo_inicio, periodo_fim)
        return {"sucesso": True, "mensagem": f"{importadas} NFes de entrada importadas"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/nfe",
    response_model=list[SankhyaNFEResponse],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def listar_nfe_sankhya(
    tipo_operacao: str | None = None,
    exportado: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: SankhyaNFeService = Depends(get_nfe_service),
):
    return await service.listar_nfe(
        str(tenant_id),
        tipo_operacao=tipo_operacao,
        exportado=exportado,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/financeiro/exportar-contas-pagar",
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def exportar_contas_pagar(
    lancamentos: list[dict],
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: SankhyaFinanceiroService = Depends(get_financeiro_service),
):
    try:
        resultado = await service.exportar_contas_pagar(str(tenant_id), lancamentos)
        return {"sucesso": True, "dados": resultado}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/financeiro/exportar-contas-receber",
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def exportar_contas_receber(
    lancamentos: list[dict],
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: SankhyaFinanceiroService = Depends(get_financeiro_service),
):
    try:
        resultado = await service.exportar_contas_receber(str(tenant_id), lancamentos)
        return {"sucesso": True, "dados": resultado}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/financeiro/importar",
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def importar_financeiro(
    periodo_inicio: date,
    periodo_fim: date,
    tipo: str = "AMBOS",
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: SankhyaFinanceiroService = Depends(get_financeiro_service),
):
    try:
        importados = await service.importar_lancamentos(
            str(tenant_id),
            periodo_inicio,
            periodo_fim,
            tipo,
        )
        return {"sucesso": True, "mensagem": f"{importados} lançamentos importados"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/financeiro",
    response_model=list[SankhyaLancamentoFinanceiroResponse],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def listar_financeiro_sankhya(
    tipo: str | None = None,
    exportado: bool | None = None,
    skip: int = 0,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: SankhyaFinanceiroService = Depends(get_financeiro_service),
):
    return await service.listar_lancamentos(
        str(tenant_id),
        tipo=tipo,
        exportado=exportado,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/associacoes/pendentes",
    response_model=list[ExternalRecordAssociationPendingItemResponse],
    dependencies=[Depends(require_tenant_permission("integrations:view"))],
)
async def listar_associacoes_externas_pendentes(
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
    service: ExternalRecordAssociationService = Depends(get_external_association_service),
):
    if tenant_filter is not None and tenant_filter != current_tenant_id:
        raise HTTPException(status_code=403, detail="Filtro de tenant fora do escopo atual")

    associations = await service.list_pending_associations(
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
        rows = await service.db.execute(
            select(IntegrationFeature.id, IntegrationFeature.codigo).where(
                IntegrationFeature.id.in_(feature_ids),
            ),
        )
        feature_code_by_id = {row.id: row.codigo for row in rows}

    return [
        await _serialize_pending_item(
            association,
            service=service,
            feature_code_by_id=feature_code_by_id,
        )
        for association in associations
    ]


@router.post(
    "/associacoes/{association_id}/reconciliar",
    response_model=ExternalRecordAssociationPendingItemResponse,
    dependencies=[Depends(require_tenant_permission("integrations:sync"))],
)
async def reconciliar_associacao_externa(
    association_id: uuid.UUID,
    payload: ExternalRecordAssociationGovernanceReconcileRequest,
    current_tenant_id: uuid.UUID = Depends(get_tenant_id),
    service: ExternalRecordAssociationService = Depends(get_external_association_service),
):
    association = await service.db.get(ExternalRecordAssociation, association_id)
    if association is None or association.tenant_id != str(current_tenant_id) or association.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Associacao externa nao encontrada")
    if association.status != ExternalRecordAssociationStatus.PENDING.value:
        raise HTTPException(status_code=409, detail="Somente associacoes pendentes podem ser reconciliadas")

    try:
        await service.detect_duplicate(
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

    reconciled = await service.reconcile_pending(
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
        rows = await service.db.execute(
            select(IntegrationFeature.id, IntegrationFeature.codigo).where(
                IntegrationFeature.id == reconciled.feature_id,
            ),
        )
        feature_code_by_id = {row.id: row.codigo for row in rows}

    return await _serialize_pending_item(
        reconciled,
        service=service,
        feature_code_by_id=feature_code_by_id,
    )
