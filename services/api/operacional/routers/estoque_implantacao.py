from __future__ import annotations

import io
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_tenant, get_session, get_user_id, require_module, require_tenant_permission
from core.models.tenant import Tenant
from operacional.schemas.estoque_implantacao import (
    EstoqueImplantacaoAptidaoConfirmacaoResponse,
    EstoqueImplantacaoConfirmacaoRequest,
    EstoqueImplantacaoItemCorrecaoRequest,
    EstoqueImplantacaoItemListResponse,
    EstoqueImplantacaoPreviewResponse,
    EstoqueImplantacaoSessaoListResponse,
    EstoqueImplantacaoSessaoResponse,
)
from operacional.services.estoque_implantacao_service import EstoqueImplantacaoService


router = APIRouter(
    prefix="/estoque/implantacao-assistida",
    tags=["Operacional — Estoque Implantacao Assistida"],
    dependencies=[Depends(require_module("O2_ESTOQUE"))],
)


def _svc(session: AsyncSession, tenant: Tenant, user_id: uuid.UUID | None = None) -> EstoqueImplantacaoService:
    return EstoqueImplantacaoService(session, tenant.id, user_id=user_id)


def _parse_mapping(mapeamento: str | None) -> dict[str, str] | None:
    if not mapeamento:
        return None
    try:
        parsed = json.loads(mapeamento)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Campo mapeamento deve ser um JSON valido.") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=422, detail="Campo mapeamento deve ser um objeto JSON.")
    return {str(key): str(value) for key, value in parsed.items()}


@router.get("/template")
async def baixar_template_csv(
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:create")),
):
    content = await _svc(session, tenant).gerar_template_csv()
    filename = "estoque_implantacao_template.csv"
    return StreamingResponse(
        io.StringIO(content),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/preview", response_model=EstoqueImplantacaoPreviewResponse)
async def gerar_preview_csv(
    file: UploadFile = File(...),
    mapeamento: str | None = Form(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:create")),
):
    content = await file.read()
    mapping_dict = _parse_mapping(mapeamento)
    return await _svc(session, tenant).gerar_preview_csv(
        filename=file.filename or "upload.csv",
        content=content,
        mapping=mapping_dict,
    )


@router.post("/sessoes", response_model=EstoqueImplantacaoSessaoResponse, status_code=201)
async def criar_sessao_implantacao(
    file: UploadFile = File(...),
    mapeamento: str | None = Form(None),
    unidade_produtiva_id: uuid.UUID | None = Form(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_user_id),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:create")),
):
    content = await file.read()
    svc = _svc(session, tenant, user_id)
    result = await svc.criar_sessao_from_csv(
        filename=file.filename or "upload.csv",
        content=content,
        mapping=_parse_mapping(mapeamento),
        criado_por=user_id,
        unidade_produtiva_id=unidade_produtiva_id,
    )
    await session.commit()
    return result


@router.get("/sessoes", response_model=EstoqueImplantacaoSessaoListResponse)
async def listar_sessoes_implantacao(
    status: str | None = Query(None),
    arquivo_nome: str | None = Query(None),
    criado_em_inicio: datetime | None = Query(None),
    criado_em_fim: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_user_id),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:list")),
):
    return await _svc(session, tenant, user_id).listar_sessoes(
        status=status,
        arquivo_nome=arquivo_nome,
        criado_em_inicio=criado_em_inicio,
        criado_em_fim=criado_em_fim,
        limit=limit,
        offset=offset,
    )


@router.get("/sessoes/{sessao_id}", response_model=EstoqueImplantacaoSessaoResponse)
async def obter_sessao_implantacao(
    sessao_id: uuid.UUID,
    status: str | None = Query(None),
    somente_erros: bool = Query(False),
    somente_avisos: bool = Query(False),
    ignorado: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_user_id),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:view")),
):
    return await _svc(session, tenant, user_id).obter_sessao(
        sessao_id,
        status=status,
        somente_erros=somente_erros,
        somente_avisos=somente_avisos,
        ignorado=ignorado,
        limit=limit,
        offset=offset,
    )


@router.get("/sessoes/{sessao_id}/itens", response_model=EstoqueImplantacaoItemListResponse)
async def listar_itens_sessao_implantacao(
    sessao_id: uuid.UUID,
    status: str | None = Query(None),
    somente_erros: bool = Query(False),
    somente_avisos: bool = Query(False),
    ignorado: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_user_id),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:view")),
):
    return await _svc(session, tenant, user_id).listar_itens_sessao(
        sessao_id,
        status=status,
        somente_erros=somente_erros,
        somente_avisos=somente_avisos,
        ignorado=ignorado,
        limit=limit,
        offset=offset,
    )


@router.patch("/sessoes/{sessao_id}/itens/{item_id}", response_model=EstoqueImplantacaoSessaoResponse)
async def corrigir_item_implantacao(
    sessao_id: uuid.UUID,
    item_id: uuid.UUID,
    data: EstoqueImplantacaoItemCorrecaoRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_user_id),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:edit")),
):
    svc = _svc(session, tenant, user_id)
    result = await svc.corrigir_item(sessao_id, item_id, data)
    await session.commit()
    return result


@router.post("/sessoes/{sessao_id}/cancelar", response_model=EstoqueImplantacaoSessaoResponse)
async def cancelar_sessao_implantacao(
    sessao_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_user_id),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:delete")),
):
    svc = _svc(session, tenant, user_id)
    result = await svc.cancelar_sessao(sessao_id)
    await session.commit()
    return result


@router.post("/sessoes/{sessao_id}/revalidar", response_model=EstoqueImplantacaoSessaoResponse)
async def revalidar_sessao_implantacao(
    sessao_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_user_id),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:edit")),
):
    svc = _svc(session, tenant, user_id)
    result = await svc.revalidar_sessao(sessao_id)
    await session.commit()
    return result


@router.get("/sessoes/{sessao_id}/aptidao-confirmacao", response_model=EstoqueImplantacaoAptidaoConfirmacaoResponse)
async def obter_aptidao_confirmacao_implantacao(
    sessao_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_user_id),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:view")),
):
    return await _svc(session, tenant, user_id).validar_sessao_apta_para_confirmacao(sessao_id, tenant.id)


@router.post("/sessoes/{sessao_id}/confirmar", response_model=EstoqueImplantacaoSessaoResponse)
async def confirmar_sessao_implantacao(
    sessao_id: uuid.UUID,
    data: EstoqueImplantacaoConfirmacaoRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID | None = Depends(get_user_id),
    _: None = Depends(require_tenant_permission("estoque:implantacao_assistida:approve")),
):
    svc = _svc(session, tenant, user_id)
    result = await svc.confirmar_sessao(sessao_id, data)
    await session.commit()
    return result
