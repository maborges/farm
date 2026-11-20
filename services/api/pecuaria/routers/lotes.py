import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_module
from core.exceptions import BusinessRuleError, EntityNotFoundError

from pecuaria.schemas.lote_schema import (
    LoteBovinoCreate,
    LoteBovinoResponse,
    LoteBovinoUpdate,
)
from pecuaria.services.lote_service import LoteBovinoService
from pecuaria.schemas.lote_resumo_sanitario_schema import LoteResumoSanitarioResponse
from pecuaria.services.lote_resumo_sanitario_service import LoteResumoSanitarioService
from pecuaria.schemas.lote_indicadores_schema import LoteIndicadoresResponse
from pecuaria.services.lote_indicadores_service import LoteIndicadoresService

# A Trava impeditiva "P1" - Licença do Módulo Pecuária
router = APIRouter(
    prefix="/pecuaria/lotes",
    tags=["Pecuária - Rebanho (P1)"],
    dependencies=[Depends(require_module("P1_REBANHO"))]
)

@router.get("", response_model=List[LoteBovinoResponse])
async def listar_lotes(
    unidade_produtiva_id: uuid.UUID | None = None,
    categoria: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Lista Lotes de Animais na propriedade, filtrado por fazenda e/ou categoria."""
    svc = LoteBovinoService(tenant_id)
    filters: dict = {}
    if unidade_produtiva_id:
        filters["unidade_produtiva_id"] = unidade_produtiva_id
    if categoria:
        filters["categoria"] = categoria
    svc.session = db
    return await svc.list_all(skip=skip, limit=limit, **filters)


@router.post("", response_model=LoteBovinoResponse, status_code=status.HTTP_201_CREATED)
async def criar_lote(
    payload: LoteBovinoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Registra a fundação de um novo Lote na fazenda (Compra ou Nascimento)."""
    svc = LoteBovinoService(tenant_id)
    lote = await svc.create_lote(db, obj_in=payload)
    await db.commit()
    return lote


@router.patch("/{lote_id}", response_model=LoteBovinoResponse)
async def atualizar_lote(
    lote_id: uuid.UUID,
    payload: LoteBovinoUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Atualiza parâmetros híbridos, econômicos e piquete de um lote."""
    svc = LoteBovinoService(tenant_id)
    try:
        lote = await svc.update_lote(db, lote_id, payload)
        await db.commit()
        return lote
    except EntityNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BusinessRuleError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{lote_id}/resumo-sanitario", response_model=LoteResumoSanitarioResponse)
async def resumir_sanitario(
    lote_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Resumo sanitário e econômico do lote com foco em vacinação."""
    svc = LoteResumoSanitarioService(db, tenant_id)
    return await svc.resumir(lote_id)


@router.get("/{lote_id}/indicadores", response_model=LoteIndicadoresResponse)
async def indicadores(
    lote_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Indicadores zootécnicos e econômicos consolidados do lote."""
    svc = LoteIndicadoresService(db, tenant_id)
    return await svc.resumir(lote_id)
