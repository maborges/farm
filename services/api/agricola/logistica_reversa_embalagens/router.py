from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.constants import Modulos
from core.dependencies import get_session, get_tenant_id, require_module, require_tenant_permission
from agricola.logistica_reversa_embalagens.schemas import DevolucaoEmbalagemRead
from agricola.logistica_reversa_embalagens.service import DevolucaoEmbalagemService

router = APIRouter(
    prefix="/agricola/logistica-reversa-embalagens",
    tags=["Agrícola - Logística Reversa de Embalagens"],
    dependencies=[Depends(require_module(Modulos.AGRICOLA_DEFENSIVOS))],
)


@router.get(
    "/",
    response_model=List[DevolucaoEmbalagemRead],
    summary="Lista pendências de devolução de embalagens do tenant",
)
async def listar_devolucoes(
    status_filtro: str | None = Query(None, alias="status"),
    produto_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:logistica_reversa:ler")),
):
    svc = DevolucaoEmbalagemService(session, tenant_id)
    filtros = {}
    if status_filtro:
        filtros["status"] = status_filtro
    if produto_id:
        filtros["produto_id"] = produto_id
    return await svc.list_all(limit=500, **filtros)


@router.get(
    "/pendentes",
    response_model=List[DevolucaoEmbalagemRead],
    summary="Lista pendências PENDENTE, opcionalmente filtrando por proximidade do prazo legal (1 ano)",
)
async def listar_pendentes(
    vencendo_em_dias: int | None = Query(None, ge=0),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:logistica_reversa:ler")),
):
    svc = DevolucaoEmbalagemService(session, tenant_id)
    return await svc.listar_pendentes(vencendo_em_dias)


@router.get(
    "/{devolucao_id}",
    response_model=DevolucaoEmbalagemRead,
    summary="Detalha uma pendência de devolução de embalagens",
)
async def obter_devolucao(
    devolucao_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:logistica_reversa:ler")),
):
    svc = DevolucaoEmbalagemService(session, tenant_id)
    return await svc.get_or_fail(devolucao_id)


@router.post(
    "/{devolucao_id}/devolucao",
    response_model=DevolucaoEmbalagemRead,
    summary="Registra devolução (total ou parcial) de embalagens ao posto de recebimento",
)
async def registrar_devolucao(
    devolucao_id: UUID,
    quantidade_embalagens: int = Query(..., gt=0),
    destino_pessoa_id: UUID | None = Query(None),
    observacoes: str | None = Query(None),
    comprovante: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_tenant_permission("agricola:logistica_reversa:registrar")),
):
    svc = DevolucaoEmbalagemService(session, tenant_id)
    content = await comprovante.read() if comprovante is not None else None
    devolucao = await svc.registrar_devolucao(
        devolucao_id, quantidade_embalagens,
        destino_pessoa_id=destino_pessoa_id, observacoes=observacoes,
        comprovante_content=content,
        comprovante_filename=comprovante.filename if comprovante is not None else None,
    )
    await session.commit()
    return devolucao
