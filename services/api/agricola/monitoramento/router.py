from core.dependencies import require_tenant_permission
from fastapi import APIRouter, Depends, status, UploadFile, File
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.dependencies import get_tenant_id, require_module, require_role
from core.dependencies import get_session_with_tenant
from core.cadastros.propriedades.models import AreaRural
from agricola.monitoramento.schemas import (
    MonitoramentoPragasCreate,
    MonitoramentoPragasUpdate,
    MonitoramentoPragasResponse,
    MonitoramentoCatalogoCreate,
    MonitoramentoCatalogoResponse,
)
from agricola.monitoramento.service import MonitoramentoService, MonitoramentoCatalogoService

router = APIRouter(prefix="/monitoramentos", tags=["Monitoramento Fitossanitário"])


async def _enriquecer_talhao_nome(
    session: AsyncSession,
    registros: list[MonitoramentoPragasResponse] | list,
):
    talhao_ids = {r.talhao_id for r in registros if getattr(r, "talhao_id", None)}
    if not talhao_ids:
        return [MonitoramentoPragasResponse.model_validate(r) for r in registros]

    stmt = select(AreaRural.id, AreaRural.nome).where(AreaRural.id.in_(talhao_ids))
    result = await session.execute(stmt)
    talhoes = {talhao_id: nome for talhao_id, nome in result.all()}

    return [
        MonitoramentoPragasResponse.model_validate(r).model_copy(
            update={"talhao_nome": talhoes.get(r.talhao_id)}
        )
        for r in registros
    ]

# ─── Catálogo ─────────────────────────────────────────────────────────────────

@router.get("/catalogo", response_model=List[MonitoramentoCatalogoResponse])
async def listar_catalogo(
    tipo: str | None = None,
    cultura: str | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
):
    svc = MonitoramentoCatalogoService(session, tenant_id)
    items = await svc.listar(tipo=tipo, cultura=cultura)
    return [MonitoramentoCatalogoResponse.model_validate(i) for i in items]


@router.post("/catalogo", response_model=MonitoramentoCatalogoResponse, status_code=status.HTTP_201_CREATED)
async def criar_catalogo(
    dados: MonitoramentoCatalogoCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
    user: dict = Depends(require_role(["agronomo", "admin"])),
):
    svc = MonitoramentoCatalogoService(session, tenant_id)
    item = await svc.criar(dados.model_dump())
    await session.commit()
    await session.refresh(item)
    return MonitoramentoCatalogoResponse.model_validate(item)


# ─── Monitoramento ────────────────────────────────────────────────────────────

@router.post("/", response_model=MonitoramentoPragasResponse, status_code=status.HTTP_201_CREATED)
async def criar_monitoramento(
    dados: MonitoramentoPragasCreate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
    user: dict = Depends(require_role(["agronomo", "admin", "operador"])),
):
    svc = MonitoramentoService(session, tenant_id)
    tecnico_id = UUID(user["sub"]) if user.get("sub") else None
    registro = await svc.criar(dados, tecnico_id=tecnico_id)
    await session.commit()
    await session.refresh(registro)
    return (
        await _enriquecer_talhao_nome(session, [registro])
    )[0]


@router.get("/safra/{safra_id}", response_model=List[MonitoramentoPragasResponse])
async def listar_por_safra(
    safra_id: UUID,
    tipo: str | None = None,
    talhao_id: UUID | None = None,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
):
    svc = MonitoramentoService(session, tenant_id)
    registros = await svc.listar_por_safra(safra_id, tipo=tipo, talhao_id=talhao_id)
    return await _enriquecer_talhao_nome(session, registros)


@router.get("/{id}", response_model=MonitoramentoPragasResponse)
async def detalhar_monitoramento(
    id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
):
    svc = MonitoramentoService(session, tenant_id)
    registro = await svc.get_or_fail(id)
    return (await _enriquecer_talhao_nome(session, [registro]))[0]


@router.patch("/{id}", response_model=MonitoramentoPragasResponse)
async def atualizar_monitoramento(
    id: UUID,
    dados: MonitoramentoPragasUpdate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
    user: dict = Depends(require_role(["agronomo", "admin"])),
):
    svc = MonitoramentoService(session, tenant_id)
    registro = await svc.update(id, dados.model_dump(exclude_none=True))
    await session.commit()
    await session.refresh(registro)
    return (await _enriquecer_talhao_nome(session, [registro]))[0]


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_monitoramento(
    id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
    user: dict = Depends(require_role(["agronomo", "admin"])),
):
    svc = MonitoramentoService(session, tenant_id)
    await svc.hard_delete(id)
    await session.commit()


@router.post("/diagnosticar-avulso")
async def diagnosticar_avulso(
    foto: UploadFile = File(...),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module("A2_CAMPO")),
    user: dict = Depends(require_role(["agronomo", "admin", "operador"])),
):
    """Diagnóstico IA rápido antes de salvar o registro."""
    svc = MonitoramentoService(session, tenant_id)
    return await svc.diagnosticar_imagem(await foto.read())
