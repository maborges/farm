from core.dependencies import require_tenant_permission
import uuid
from typing import Optional
from datetime import date, datetime, time, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_module
from operacional.services.frota_apontamento_service import FrotaApontamentoService
from operacional.services.apontamento_mao_obra_service import ApontamentoMaoObraService
from operacional.schemas.apontamento import (
    ApontamentoUsoCreate, ApontamentoUsoUpdate, ApontamentoUsoResponse,
    ApontamentoMaoObraCreate, ApontamentoMaoObraResponse,
)

router = APIRouter(
    prefix="/frota/apontamentos",
    tags=["Frota — Apontamentos de Uso"],
    dependencies=[Depends(require_module("O1_FROTA"))],
)

router_mao_obra = APIRouter(
    prefix="/mao-obra/apontamentos",
    tags=["Mão de Obra — Apontamentos de Execução"],
)


@router.get("/", response_model=list[ApontamentoUsoResponse])
@router.get("", response_model=list[ApontamentoUsoResponse])
async def listar(
    equipamento_id: Optional[uuid.UUID] = Query(None),
    jornada_id: Optional[uuid.UUID] = Query(None),
    operador_id: Optional[uuid.UUID] = Query(None),
    safra_id: Optional[uuid.UUID] = Query(None),
    production_unit_id: Optional[uuid.UUID] = Query(None),
    talhao_id: Optional[uuid.UUID] = Query(None),
    operacao_id: Optional[uuid.UUID] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = FrotaApontamentoService(session, tenant_id)
    return await svc.listar(
        equipamento_id=equipamento_id,
        jornada_id=jornada_id,
        operador_id=operador_id,
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        talhao_id=talhao_id,
        operacao_id=operacao_id,
        data_inicio=datetime.combine(data_inicio, time.min, tzinfo=timezone.utc) if data_inicio else None,
        data_fim=datetime.combine(data_fim, time.max, tzinfo=timezone.utc) if data_fim else None,
    )


@router.post("/", response_model=ApontamentoUsoResponse, status_code=201)
@router.post("", response_model=ApontamentoUsoResponse, status_code=201)
async def criar(
    data: ApontamentoUsoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = FrotaApontamentoService(session, tenant_id)
    apontamento = await svc.criar(data)
    await session.commit()
    await session.refresh(apontamento)
    return apontamento


@router.get("/{ap_id}", response_model=ApontamentoUsoResponse)
async def obter(
    ap_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = FrotaApontamentoService(session, tenant_id)
    return await svc._obter(ap_id)


@router.patch("/{ap_id}", response_model=ApontamentoUsoResponse)
async def atualizar(
    ap_id: uuid.UUID,
    data: ApontamentoUsoUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = FrotaApontamentoService(session, tenant_id)
    obj = await svc.atualizar(ap_id, data)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/{ap_id}", status_code=204)
async def remover(
    ap_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = FrotaApontamentoService(session, tenant_id)
    await svc.remover(ap_id)
    await session.commit()


# ---------------------------------------------------------------------------
# OPERATIONS-GAP-01 §21.14: apontamento de mão de obra manual (sem equipamento)
# ---------------------------------------------------------------------------

@router_mao_obra.get("/", response_model=list[ApontamentoMaoObraResponse])
@router_mao_obra.get("", response_model=list[ApontamentoMaoObraResponse])
async def listar_mao_obra(
    pessoa_id: Optional[uuid.UUID] = Query(None),
    safra_id: Optional[uuid.UUID] = Query(None),
    production_unit_id: Optional[uuid.UUID] = Query(None),
    talhao_id: Optional[uuid.UUID] = Query(None),
    operacao_id: Optional[uuid.UUID] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ApontamentoMaoObraService(session, tenant_id)
    return await svc.listar(
        pessoa_id=pessoa_id,
        safra_id=safra_id,
        production_unit_id=production_unit_id,
        talhao_id=talhao_id,
        operacao_id=operacao_id,
        data_inicio=datetime.combine(data_inicio, time.min, tzinfo=timezone.utc) if data_inicio else None,
        data_fim=datetime.combine(data_fim, time.max, tzinfo=timezone.utc) if data_fim else None,
    )


@router_mao_obra.post("/", response_model=ApontamentoMaoObraResponse, status_code=201)
@router_mao_obra.post("", response_model=ApontamentoMaoObraResponse, status_code=201)
async def criar_mao_obra(
    data: ApontamentoMaoObraCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ApontamentoMaoObraService(session, tenant_id)
    apontamento = await svc.criar(data)
    await session.commit()
    await session.refresh(apontamento)
    return apontamento


@router_mao_obra.get("/{ap_id}", response_model=ApontamentoMaoObraResponse)
async def obter_mao_obra(
    ap_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ApontamentoMaoObraService(session, tenant_id)
    return await svc._obter(ap_id)


@router_mao_obra.delete("/{ap_id}", status_code=204)
async def remover_mao_obra(
    ap_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    svc = ApontamentoMaoObraService(session, tenant_id)
    await svc.remover(ap_id)
    await session.commit()
