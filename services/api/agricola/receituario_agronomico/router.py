from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import Modulos
from core.dependencies import get_session, get_tenant_id, get_current_user_claims, require_module, require_tenant_permission
from agricola.receituario_agronomico.schemas import (
    ReceituarioAgronomicoCreate,
    ReceituarioAgronomicoUpdate,
    ReceituarioAgronomicoRead,
    ReceituarioCancelarRequest,
    ReceituarioUploadPdfResponse,
)
from agricola.receituario_agronomico.service import ReceituarioAgronomicoService

router = APIRouter(
    prefix="/agricola/receituarios",
    tags=["Agrícola - Receituário Agronômico"],
    dependencies=[Depends(require_module(Modulos.AGRICOLA_DEFENSIVOS))],
)


def _user_id(user: dict) -> UUID | None:
    sub = user.get("sub")
    return UUID(sub) if sub else None


@router.post(
    "/",
    response_model=ReceituarioAgronomicoRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um Receituário Agronômico (RASCUNHO)",
)
async def criar_receituario(
    dados: ReceituarioAgronomicoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(get_current_user_claims),
    _: None = Depends(require_tenant_permission("agricola:receituario:criar")),
):
    svc = ReceituarioAgronomicoService(session, tenant_id, _user_id(user))
    receituario = await svc.emitir(dados)
    await session.commit()
    return await svc.obter_com_itens(receituario.id)


@router.get(
    "/",
    response_model=List[ReceituarioAgronomicoRead],
    summary="Lista Receituários Agronômicos do tenant",
)
async def listar_receituarios(
    status_filtro: str | None = Query(None, alias="status"),
    safra_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:receituario:ler")),
):
    svc = ReceituarioAgronomicoService(session, tenant_id)
    filtros = {}
    if status_filtro:
        filtros["status"] = status_filtro
    if safra_id:
        filtros["safra_id"] = safra_id
    return await svc.list_all(limit=500, **filtros)


@router.get(
    "/vigentes",
    response_model=List[ReceituarioAgronomicoRead],
    summary="Lista receituários EMITIDOS e não vencidos para um produto (pré-checagem de bloqueio de saída)",
)
async def listar_vigentes(
    produto_id: UUID = Query(...),
    safra_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:receituario:ler")),
):
    svc = ReceituarioAgronomicoService(session, tenant_id)
    return await svc.listar_vigentes_por_produto(produto_id, safra_id)


@router.get(
    "/{receituario_id}",
    response_model=ReceituarioAgronomicoRead,
    summary="Detalha um Receituário Agronômico",
)
async def obter_receituario(
    receituario_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:receituario:ler")),
):
    svc = ReceituarioAgronomicoService(session, tenant_id)
    return await svc.obter_com_itens(receituario_id)


@router.patch(
    "/{receituario_id}",
    response_model=ReceituarioAgronomicoRead,
    summary="Atualiza um Receituário Agronômico (somente RASCUNHO)",
)
async def atualizar_receituario(
    receituario_id: UUID,
    dados: ReceituarioAgronomicoUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:receituario:editar")),
):
    svc = ReceituarioAgronomicoService(session, tenant_id)
    receituario = await svc.atualizar(receituario_id, dados)
    await session.commit()
    return await svc.obter_com_itens(receituario.id)


@router.post(
    "/{receituario_id}/anexo-pdf",
    response_model=ReceituarioUploadPdfResponse,
    summary="Anexa o PDF assinado do Receituário e emite (RASCUNHO -> EMITIDO)",
)
async def anexar_pdf(
    receituario_id: UUID,
    arquivo: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:receituario:emitir")),
):
    svc = ReceituarioAgronomicoService(session, tenant_id)
    content = await arquivo.read()
    receituario = await svc.anexar_pdf(receituario_id, content, arquivo.filename or "receituario.pdf")
    await session.commit()
    return ReceituarioUploadPdfResponse(arquivo_pdf_url=receituario.arquivo_pdf_url, status=receituario.status)


@router.post(
    "/{receituario_id}/cancelar",
    response_model=ReceituarioAgronomicoRead,
    summary="Cancela um Receituário Agronômico",
)
async def cancelar_receituario(
    receituario_id: UUID,
    dados: ReceituarioCancelarRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:receituario:cancelar")),
):
    svc = ReceituarioAgronomicoService(session, tenant_id)
    receituario = await svc.cancelar(receituario_id, dados.motivo)
    await session.commit()
    return await svc.obter_com_itens(receituario.id)
