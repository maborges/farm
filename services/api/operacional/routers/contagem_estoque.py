import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_session, get_current_tenant, get_current_user, require_module, require_tenant_permission
from core.models.tenant import Tenant
from core.models.auth import Usuario
from operacional.schemas.contagem_estoque import (
    ContagemAbrirRequest,
    ContagemItemRegistrarRequest,
    ContagemEstoqueResponse,
    ContagemEstoqueItemResponse,
)
from operacional.services.contagem_estoque_service import ContagemEstoqueService

router = APIRouter(
    prefix="/estoque/contagens",
    tags=["Operacional — Contagem de Estoque"],
    dependencies=[Depends(require_module("O2_ESTOQUE"))],
)


def _svc(session: AsyncSession, tenant: Tenant) -> ContagemEstoqueService:
    return ContagemEstoqueService(session, tenant.id)


@router.post("/", response_model=ContagemEstoqueResponse, status_code=201,
    dependencies=[Depends(require_tenant_permission("operacional:*"))])
async def abrir_contagem(
    data: ContagemAbrirRequest,
    tenant: Tenant = Depends(get_current_tenant),
    usuario: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    contagem = await svc.abrir_contagem(data, usuario_id=usuario.id)
    return await svc.detalhar_contagem(contagem.id)


@router.get("/", response_model=List[ContagemEstoqueResponse])
async def listar_contagens(
    deposito_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    contagens = await svc.listar_contagens(deposito_id=deposito_id, status=status)
    return [await svc.detalhar_contagem(c.id) for c in contagens]


@router.get("/{contagem_id}", response_model=ContagemEstoqueResponse)
async def detalhar_contagem(
    contagem_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    return await _svc(session, tenant).detalhar_contagem(contagem_id)


@router.patch("/{contagem_id}/itens/{produto_id}", response_model=ContagemEstoqueItemResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))])
async def registrar_item(
    contagem_id: uuid.UUID,
    produto_id: uuid.UUID,
    data: ContagemItemRegistrarRequest,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    item = await svc.registrar_contagem_item(contagem_id, produto_id, data.quantidade_contada)
    return ContagemEstoqueItemResponse(
        id=item.id, contagem_id=item.contagem_id, produto_id=item.produto_id,
        quantidade_sistema=item.quantidade_sistema, quantidade_contada=item.quantidade_contada,
        divergencia=float(item.quantidade_contada) - float(item.quantidade_sistema),
        contado_em=item.contado_em, movimento_ajuste_id=item.movimento_ajuste_id,
    )


@router.post("/{contagem_id}/concluir", response_model=ContagemEstoqueResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))])
async def concluir_contagem(
    contagem_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    usuario: Usuario = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    await svc.concluir_contagem(contagem_id, usuario_id=usuario.id)
    return await svc.detalhar_contagem(contagem_id)


@router.post("/{contagem_id}/cancelar", response_model=ContagemEstoqueResponse,
    dependencies=[Depends(require_tenant_permission("operacional:*"))])
async def cancelar_contagem(
    contagem_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_session),
):
    svc = _svc(session, tenant)
    await svc.cancelar_contagem(contagem_id)
    return await svc.detalhar_contagem(contagem_id)
