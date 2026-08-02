from decimal import Decimal
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id
from core.exceptions import BusinessRuleError
from core.measurements.schemas import ConversaoRequest, ConversaoResponse, UnidadeMedidaResponse
from core.measurements.service import UnidadeMedidaService

router = APIRouter(prefix="/unidades-medida", tags=["Unidades de Medida"])


@router.post("/converter", response_model=ConversaoResponse)
async def converter_unidade(
    dados: ConversaoRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    svc = UnidadeMedidaService(session, tenant_id)
    try:
        valor_convertido = await svc.converter(
            valor=dados.valor,
            unidade_origem_id=dados.unidade_origem_id,
            unidade_destino_id=dados.unidade_destino_id,
            cultura=dados.cultura,
        )
    except BusinessRuleError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    return ConversaoResponse(
        valor_original=dados.valor,
        unidade_origem_id=dados.unidade_origem_id,
        valor_convertido=valor_convertido,
        unidade_destino_id=dados.unidade_destino_id,
    )


@router.get("/{id}", response_model=UnidadeMedidaResponse)
async def obter_unidade_medida(
    id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    svc = UnidadeMedidaService(session, tenant_id)
    unidade = await svc.obter(id)
    if unidade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unidade de medida não encontrada")
    return UnidadeMedidaResponse.model_validate(unidade)


@router.get("/", response_model=List[UnidadeMedidaResponse])
async def listar_unidades_medida(
    dimensao: str | None = None,
    q: str | None = Query(default=None, description="Busca por nome ou código"),
    skip: int = 0,
    limit: int = Query(default=100, le=1000),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    svc = UnidadeMedidaService(session, tenant_id)
    unidades = await svc.listar(dimensao=dimensao, q=q, skip=skip, limit=limit)
    return [UnidadeMedidaResponse.model_validate(u) for u in unidades]
