from core.dependencies import require_tenant_permission
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_tenant_id, require_role
from core.exceptions import BusinessRuleError, EntityNotFoundError
from agricola.custos import lote_allocation_service
from .service import ProdutoColhidoService
from .schemas import (
    ProdutoColhidoCreate,
    ProdutoColhidoUpdate,
    ProdutoColhidoResponse,
    ProdutoColhidoCustoResumoResponse,
    ProdutoColhidoCustoAlocacaoResponse,
    ProdutoColhidoCustoOverrideRequest,
    ResumoEstoqueResponse,
)

router = APIRouter(prefix="/agricola/produtos-colhidos", tags=["Agrícola — Produtos Colhidos"])


@router.get("/resumo", response_model=ResumoEstoqueResponse)
async def resumo_estoque(
    status: Optional[str] = Query(None),
    commodity_id: Optional[uuid.UUID] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    service = ProdutoColhidoService(session, tenant_id)
    return await service.resumo_estoque(status=status, commodity_id=commodity_id)


@router.get("/", response_model=list[ProdutoColhidoResponse])
async def listar(
    safra_id: Optional[uuid.UUID] = Query(None),
    commodity_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    service = ProdutoColhidoService(session, tenant_id)
    return await service.listar(safra_id=safra_id, commodity_id=commodity_id, status=status)


@router.post("/", response_model=ProdutoColhidoResponse, status_code=201)
async def criar(
    data: ProdutoColhidoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    service = ProdutoColhidoService(session, tenant_id)
    obj = await service.criar(data)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.get("/{produto_id}", response_model=ProdutoColhidoResponse)
async def obter(
    produto_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    service = ProdutoColhidoService(session, tenant_id)
    try:
        return await service.obter(produto_id)
    except EntityNotFoundError:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto colhido não encontrado")


@router.patch("/{produto_id}", response_model=ProdutoColhidoResponse)
async def atualizar(
    produto_id: uuid.UUID,
    data: ProdutoColhidoUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    service = ProdutoColhidoService(session, tenant_id)
    try:
        obj = await service.atualizar(produto_id, data)
        await session.commit()
        await session.refresh(obj)
        return obj
    except EntityNotFoundError:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto colhido não encontrado")


@router.post("/{produto_id}/reconciliar-custos", response_model=ProdutoColhidoCustoResumoResponse)
async def reconciliar_custos(
    produto_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    try:
        itens = await lote_allocation_service.reconciliar_alocacoes_lote(session, tenant_id, produto_id)
        await session.commit()
    except EntityNotFoundError:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto colhido não encontrado")
    except BusinessRuleError as exc:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    total = sum(float(item.valor_atribuido or 0) for item in itens)
    return ProdutoColhidoCustoResumoResponse(itens=itens, total=round(total, 2))


@router.get("/{produto_id}/custos", response_model=ProdutoColhidoCustoResumoResponse)
async def obter_custos(
    produto_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    try:
        resumo = await lote_allocation_service.obter_custo_alocado(session, tenant_id, produto_id)
    except EntityNotFoundError:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto colhido não encontrado")
    return ProdutoColhidoCustoResumoResponse(itens=resumo["itens"], total=resumo["total"])


@router.post("/{produto_id}/custos/override", response_model=ProdutoColhidoCustoAlocacaoResponse)
async def override_custo(
    produto_id: uuid.UUID,
    dados: ProdutoColhidoCustoOverrideRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    user: dict = Depends(require_role(["agronomo", "admin"])),
):
    usuario_id = uuid.UUID(user["sub"]) if user.get("sub") else None
    try:
        item = await lote_allocation_service.aplicar_override_manual(
            session,
            tenant_id,
            produto_id,
            dados.cost_allocation_id,
            dados.valor_atribuido,
            dados.justificativa,
            usuario_id,
        )
        await session.commit()
    except EntityNotFoundError:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto colhido ou CostAllocation não encontrado")
    except BusinessRuleError as exc:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return item


@router.delete("/{produto_id}", status_code=204)
async def remover(
    produto_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    service = ProdutoColhidoService(session, tenant_id)
    try:
        await service.remover(produto_id)
        await session.commit()
    except EntityNotFoundError:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto colhido não encontrado")
