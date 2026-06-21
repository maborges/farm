from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_session, get_tenant_id
from core.models.auth import Usuario

from .models import TipoVinculoPropriedadeImovel
from .schemas import PropriedadeImovelCreate, PropriedadeImovelList, PropriedadeImovelRead, PropriedadeImovelUpdate
from .service import PropriedadeImovelService
from core.exceptions import BusinessRuleError, EntityNotFoundError


router = APIRouter(prefix="/propriedade-imovel", tags=["Territorial — Vínculo Propriedade-Imóvel"])


@router.get("", response_model=list[PropriedadeImovelList])
async def listar(
    propriedade_id: uuid.UUID | None = Query(None),
    imovel_rural_id: uuid.UUID | None = Query(None),
    tipo_vinculo: TipoVinculoPropriedadeImovel | None = Query(None),
    ativo: bool | None = Query(None),
    vinculo_principal: bool | None = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Lista vínculos do tenant atual com filtros úteis."""
    service = PropriedadeImovelService(session, tenant_id)
    return await service.listar(propriedade_id, imovel_rural_id, tipo_vinculo, ativo, vinculo_principal)


@router.get("/{vinculo_id}", response_model=PropriedadeImovelRead)
async def obter(
    vinculo_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Obtém um vínculo pelo ID."""
    service = PropriedadeImovelService(session, tenant_id)
    try:
        return await service.obter(vinculo_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("", response_model=PropriedadeImovelRead, status_code=status.HTTP_201_CREATED)
async def criar(
    data: PropriedadeImovelCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Cria um novo vínculo canônico."""
    service = PropriedadeImovelService(session, tenant_id)
    try:
        return await service.criar(data, usuario_id=user.id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BusinessRuleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{vinculo_id}", response_model=PropriedadeImovelRead)
async def atualizar(
    vinculo_id: uuid.UUID,
    data: PropriedadeImovelUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Atualiza um vínculo canônico existente."""
    service = PropriedadeImovelService(session, tenant_id)
    try:
        return await service.atualizar(vinculo_id, data, usuario_id=user.id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BusinessRuleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{vinculo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def inativar(
    vinculo_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Inativa um vínculo preservando histórico."""
    service = PropriedadeImovelService(session, tenant_id)
    try:
        await service.inativar(vinculo_id, usuario_id=user.id)
    except EntityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
