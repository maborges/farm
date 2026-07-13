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
from integracoes.services import DuplicateAssociationError, ExternalRecordAssociationService

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
                auth_model=config.auth_model,
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
            auth_model=config.auth_model,
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
