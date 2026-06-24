from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user, get_session, get_tenant_id, require_module
from core.models.auth import Usuario
from core.exceptions import BusinessRuleError, EntityNotFoundError
from pecuaria.schemas.manejo_schema import ManejoLoteCreate, ManejoLoteResponse
from pecuaria.services.manejo_service import ManejoLoteService
from pecuaria.schemas.manejo_planejamento_schema import (
    ManejoPlanejamentoCreate,
    ManejoPlanejamentoFiltro,
    ManejoPlanejamentoListResponse,
    ManejoPlanejamentoResponse,
)
from pecuaria.services.manejo_planejamento_service import ManejoPlanejamentoService

router = APIRouter(
    prefix="/pecuaria/manejos",
    tags=["Pecuária - Manejo (P1)"],
    dependencies=[Depends(require_module("P1_REBANHO"))],
)


@router.get("/", response_model=List[ManejoLoteResponse])
async def listar_manejos(
    lote_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Lista eventos de manejo. Filtra por lote quando `lote_id` for fornecido."""
    svc = ManejoLoteService(tenant_id)
    svc.session = db
    if lote_id:
        return await svc.listar_por_lote(db, lote_id=lote_id)
    return await svc.listar_todos(db)


@router.post("/", response_model=ManejoLoteResponse, status_code=status.HTTP_201_CREATED)
async def registrar_evento(
    payload: ManejoLoteCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Registra um evento de manejo: nascimento, morte, pesagem, vacinação ou transferência."""
    svc = ManejoLoteService(tenant_id)
    svc.session = db
    evento = await svc.registrar_evento(db, obj_in=payload)
    await db.commit()
    return evento


@router.post("/planejar", response_model=ManejoPlanejamentoResponse, status_code=status.HTTP_201_CREATED)
async def planejar_manejo(
    payload: ManejoPlanejamentoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Planeja um manejo pecuário programado para execução posterior no Campo."""
    svc = ManejoPlanejamentoService(db, tenant_id)
    try:
        planejamento = await svc.planejar(payload, current_user.id)
        await db.commit()
        return planejamento
    except EntityNotFoundError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except BusinessRuleError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/planejados", response_model=ManejoPlanejamentoListResponse)
async def listar_planejados(
    tipo: str | None = Query(None),
    lote_id: uuid.UUID | None = Query(None),
    operador_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None),
    data_inicio: date | None = Query(None),
    data_fim: date | None = Query(None),
    unidade_produtiva_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_session),
):
    """Lista tarefas de manejo programadas no Backoffice da Pecuária."""
    svc = ManejoPlanejamentoService(db, tenant_id)
    filtro = ManejoPlanejamentoFiltro(
        tipo=tipo,
        lote_id=lote_id,
        operador_id=operador_id,
        status=status,
        data_inicio=data_inicio,
        data_fim=data_fim,
        unidade_produtiva_id=unidade_produtiva_id,
        page=page,
        page_size=page_size,
    )
    return await svc.listar_planejados(filtro)
