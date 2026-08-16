import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_current_tenant, get_current_user, require_tenant_permission
from core.models.tenant import Tenant
from core.models.auth import Usuario
from imoveis.schemas.manutencao_benfeitoria import (
    OrdemServicoBenfeitoriaConcluirRequest,
    OrdemServicoBenfeitoriaCreate,
    OrdemServicoBenfeitoriaResponse,
    PlanoManutencaoBenfeitoriaCreate,
    PlanoManutencaoBenfeitoriaResponse,
)
from imoveis.services.manutencao_benfeitoria_service import ManutencaoBenfeitoriaService

router = APIRouter(prefix="/imoveis/benfeitorias/manutencao", tags=["Imóveis — Manutenção de Benfeitorias"])


def _svc(session: AsyncSession, tenant: Tenant) -> ManutencaoBenfeitoriaService:
    return ManutencaoBenfeitoriaService(session, tenant.id)


@router.post("/planos", response_model=PlanoManutencaoBenfeitoriaResponse, status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))])
async def criar_plano(
    data: PlanoManutencaoBenfeitoriaCreate,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).criar_plano(data)


@router.get("/planos", response_model=List[PlanoManutencaoBenfeitoriaResponse])
async def listar_planos(
    benfeitoria_id: Optional[uuid.UUID] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_planos(benfeitoria_id)


@router.post("/ordens-servico", response_model=OrdemServicoBenfeitoriaResponse, status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))])
async def abrir_os(
    data: OrdemServicoBenfeitoriaCreate,
    tenant: Tenant = Depends(get_current_tenant),
    usuario: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).abrir_os(data, usuario_id=usuario.id)


@router.get("/ordens-servico", response_model=List[OrdemServicoBenfeitoriaResponse])
async def listar_os(
    benfeitoria_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).listar_os(benfeitoria_id=benfeitoria_id, status=status)


@router.get("/ordens-servico/{os_id}", response_model=OrdemServicoBenfeitoriaResponse)
async def detalhar_os(
    os_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant)._get_or_fail(os_id)


@router.post("/ordens-servico/{os_id}/concluir", response_model=OrdemServicoBenfeitoriaResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))])
async def concluir_os(
    os_id: uuid.UUID,
    data: OrdemServicoBenfeitoriaConcluirRequest,
    tenant: Tenant = Depends(get_current_tenant),
    usuario: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).concluir_os(os_id, custo_total=data.custo_total, usuario_id=usuario.id)


@router.post("/ordens-servico/{os_id}/cancelar", response_model=OrdemServicoBenfeitoriaResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))])
async def cancelar_os(
    os_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).cancelar_os(os_id)
