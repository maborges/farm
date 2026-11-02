from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from core.dependencies import get_session, get_tenant_id, get_current_user, require_tenant_permission
from operacional.schemas.qualidade import (
    QualidadeProtocoloCreate,
    QualidadeProtocoloResponse,
    QualidadeCriterioResponse,
    QualidadeLaudoCreate,
    QualidadeLaudoResponse,
    QualidadeLaudoStatusUpdate,
    QualidadeAjusteResponse,
    QualidadeRomaneioIntegrationResponse
)
from operacional.services.qualidade import QualidadeService

router = APIRouter(prefix="/qualidade", tags=["Operacional - Qualidade"])

@router.post("/protocolos", response_model=QualidadeProtocoloResponse, status_code=201)
async def create_protocolo(
    data: QualidadeProtocoloCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:protocolos:criar"))
):
    return await QualidadeService.create_protocolo(db, tenant_id, user.id, data)

@router.get("/protocolos", response_model=List[QualidadeProtocoloResponse])
async def list_protocolos(
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:protocolos:listar"))
):
    return await QualidadeService.list_protocolos(db, tenant_id)

@router.get("/protocolos/{protocolo_id}", response_model=QualidadeProtocoloResponse)
async def get_protocolo(
    protocolo_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:protocolos:listar"))
):
    return await QualidadeService.get_protocolo(db, tenant_id, protocolo_id)

@router.get("/protocolos/{protocolo_id}/criterios", response_model=List[QualidadeCriterioResponse])
async def list_criterios_by_protocolo(
    protocolo_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:protocolos:listar"))
):
    return await QualidadeService.list_criterios_by_protocolo(db, tenant_id, protocolo_id)

@router.post("/laudos", response_model=QualidadeLaudoResponse, status_code=201)
async def create_laudo(
    data: QualidadeLaudoCreate,
    tenant_id: UUID = Depends(get_tenant_id),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:laudos:criar"))
):
    return await QualidadeService.create_laudo(db, tenant_id, user.id, data)

@router.get("/laudos/{laudo_id}", response_model=QualidadeLaudoResponse)
async def get_laudo(
    laudo_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:laudos:listar"))
):
    return await QualidadeService.get_laudo(db, tenant_id, laudo_id)

@router.patch("/laudos/{laudo_id}/status", response_model=QualidadeLaudoResponse)
async def update_laudo_status(
    laudo_id: UUID,
    data: QualidadeLaudoStatusUpdate,
    tenant_id: UUID = Depends(get_tenant_id),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:laudos:aprovar"))
):
    return await QualidadeService.update_laudo_status(db, tenant_id, user.id, laudo_id, data)

@router.get("/romaneios/{romaneio_id}/laudos", response_model=List[QualidadeLaudoResponse])
async def list_laudos_by_romaneio(
    romaneio_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:laudos:listar"))
):
    return await QualidadeService.list_laudos_by_romaneio(db, tenant_id, romaneio_id)

@router.post("/laudos/{laudo_id}/calcular-ajustes", response_model=List[QualidadeAjusteResponse], status_code=201)
async def calcular_ajustes_laudo(
    laudo_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:laudos:aprovar"))
):
    return await QualidadeService.calcular_ajustes_laudo(db, tenant_id, user.id, laudo_id)

@router.get("/laudos/{laudo_id}/ajustes", response_model=List[QualidadeAjusteResponse])
async def get_ajustes_laudo(
    laudo_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:laudos:listar"))
):
    laudo = await QualidadeService.get_laudo(db, tenant_id, laudo_id)
    return laudo.ajustes

@router.post("/laudos/{laudo_id}/aplicar-romaneio", response_model=QualidadeRomaneioIntegrationResponse, status_code=200)
async def aplicar_laudo_romaneio(
    laudo_id: UUID,
    tenant_id: UUID = Depends(get_tenant_id),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    _=Depends(require_tenant_permission("operacional:qualidade:laudos:aprovar"))
):
    """Aplica o resultado final do laudo no romaneio vinculado e calcula o peso líquido comercial final."""
    return await QualidadeService.aplicar_laudo_romaneio(db, tenant_id, user.id, laudo_id)
