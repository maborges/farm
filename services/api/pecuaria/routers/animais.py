from fastapi import APIRouter, Depends, status, Query, HTTPException
from typing import Optional
import math
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_module
from core.exceptions import EntityNotFoundError

from pecuaria.schemas.animal_schema import (
    AnimalCreate,
    AnimalUpdate,
    AnimalResponse,
    AnimalListResponse,
    AnimalFilter
)
from pecuaria.services.animal_service import AnimalService
from pecuaria.schemas.pesagem_schema import PesagemCreate, PesagemResponse
from pecuaria.services.pesagem_service import PesagemService
from typing import List

router = APIRouter(
    prefix="/pecuaria/animais",
    tags=["Pecuária - Rebanho Individual (P1)"],
    dependencies=[Depends(require_module("P1_REBANHO"))]
)


@router.get("", response_model=AnimalListResponse)
async def list_animais(
    unidade_produtiva_id: uuid.UUID,
    q: Optional[str] = Query(None, description="Busca por brinco, sisbov ou nome"),
    lote_id: Optional[uuid.UUID] = Query(None),
    categoria: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sexo: Optional[str] = Query(None),
    especie: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Lista animais de forma paginada com suporte a múltiplos filtros cruzados."""
    svc = AnimalService(db, tenant_id)
    
    # Montar objeto de filtro
    filter_params = AnimalFilter(
        q=q,
        lote_id=lote_id,
        categoria=categoria,
        status=status,
        sexo=sexo,
        especie=especie
    )
    
    skip = (page - 1) * page_size
    items, total = await svc.list_paginated(skip, page_size, unidade_produtiva_id, filter_params)
    
    pages = math.ceil(total / page_size) if total > 0 else 0
    
    return AnimalListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{animal_id}", response_model=AnimalResponse)
async def get_animal(
    animal_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Retorna os dados completos de um animal específico."""
    svc = AnimalService(db, tenant_id)
    try:
        return await svc.get_or_fail(animal_id)
    except EntityNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("", response_model=AnimalResponse, status_code=status.HTTP_201_CREATED)
async def create_animal(
    payload: AnimalCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Cria um novo animal individual no rebanho."""
    svc = AnimalService(db, tenant_id)
    try:
        animal = await svc.create(payload)
        await db.commit()
        return animal
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{animal_id}", response_model=AnimalResponse)
async def update_animal(
    animal_id: uuid.UUID,
    payload: AnimalUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Atualiza dados do cadastro de um animal existente."""
    svc = AnimalService(db, tenant_id)
    try:
        animal = await svc.update(animal_id, payload)
        await db.commit()
        return animal
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{animal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_animal(
    animal_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Realiza a exclusão (hard_delete) de um animal."""
    svc = AnimalService(db, tenant_id)
    try:
        await svc.hard_delete(animal_id)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{animal_id}/pesagens", response_model=PesagemResponse, status_code=status.HTTP_201_CREATED)
async def registrar_pesagem(
    animal_id: uuid.UUID,
    payload: PesagemCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Registra uma nova pesagem para o animal indicado e atualiza o peso atual."""
    svc = PesagemService(db, tenant_id)
    try:
        return await svc.registrar_pesagem(animal_id, payload)
    except HTTPException as he:
        await db.rollback()
        raise he
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{animal_id}/pesagens", response_model=List[PesagemResponse])
async def listar_pesagens(
    animal_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Lista o histórico de pesagens do animal com cálculo dinâmico de GMD."""
    svc = PesagemService(db, tenant_id)
    try:
        return await svc.listar_pesagens(animal_id)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
