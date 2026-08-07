from core.dependencies import require_tenant_permission
from fastapi import APIRouter, Depends, status, Query, HTTPException
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel, ConfigDict

from core.dependencies import get_tenant_id, get_session, require_module
from core.schemas.pagination import PaginatedResponse
from financeiro.models.nota_fiscal import NotaFiscal, TipoNF, StatusSEFAZ

router = APIRouter(prefix="/notas-fiscais", tags=["Financeiro — NF-e / NFP-e"])

MODULE = "F3_FISCAL"


# ── Schemas ───────────────────────────────────────────────────────────────────

class NotaFiscalCreate(BaseModel):
    tipo: str = "NFP-e"
    numero: Optional[int] = None
    serie: str = "1"
    emitente_nome: str
    emitente_cpf_cnpj: Optional[str] = None
    destinatario_nome: str
    destinatario_documento: Optional[str] = None
    destinatario_uf: Optional[str] = None
    valor_produtos: float = 0.0
    valor_frete: float = 0.0
    valor_icms: float = 0.0
    valor_total: float
    descricao_produto: Optional[str] = None
    ncm: Optional[str] = None
    quantidade: Optional[float] = None
    unidade: Optional[str] = None
    chave_acesso: Optional[str] = None
    unidade_produtiva_id: Optional[UUID] = None
    data_emissao: Optional[datetime] = None


class NotaFiscalUpdate(BaseModel):
    status_sefaz: Optional[str] = None
    chave_acesso: Optional[str] = None
    numero_protocolo: Optional[str] = None
    numero_recibo: Optional[str] = None
    motivo_cancelamento: Optional[str] = None
    data_autorizacao: Optional[datetime] = None
    data_cancelamento: Optional[datetime] = None


class NotaFiscalResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    unidade_produtiva_id: Optional[UUID]
    tipo: str
    numero: Optional[int]
    serie: str
    emitente_nome: str
    emitente_cpf_cnpj: Optional[str]
    destinatario_nome: str
    destinatario_documento: Optional[str]
    destinatario_uf: Optional[str]
    valor_produtos: float
    valor_frete: float
    valor_icms: float
    valor_total: float
    status_sefaz: str
    chave_acesso: Optional[str]
    numero_protocolo: Optional[str]
    numero_recibo: Optional[str]
    descricao_produto: Optional[str]
    ncm: Optional[str]
    quantidade: Optional[float]
    unidade: Optional[str]
    data_emissao: datetime
    data_autorizacao: Optional[datetime]
    data_cancelamento: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardNFeResponse(BaseModel):
    total: int
    autorizadas: int
    canceladas: int
    em_digitacao: int
    valor_total_autorizado: float


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardNFeResponse)
async def dashboard_nfe(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    stmt = select(NotaFiscal).where(NotaFiscal.tenant_id == tenant_id)
    notas = list((await session.execute(stmt)).scalars().all())
    return {
        "total": len(notas),
        "autorizadas": sum(1 for n in notas if n.status_sefaz == StatusSEFAZ.AUTORIZADA),
        "canceladas": sum(1 for n in notas if n.status_sefaz == StatusSEFAZ.CANCELADA),
        "em_digitacao": sum(1 for n in notas if n.status_sefaz == StatusSEFAZ.EM_DIGITACAO),
        "valor_total_autorizado": sum(n.valor_total for n in notas if n.status_sefaz == StatusSEFAZ.AUTORIZADA),
    }


@router.get("", response_model=PaginatedResponse[NotaFiscalResponse])
async def listar_notas(
    tipo: Optional[str] = Query(None),
    status_sefaz: Optional[str] = Query(None),
    unidade_produtiva_id: Optional[UUID] = Query(None),
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    from sqlalchemy import func
    stmt = (
        select(NotaFiscal)
        .where(NotaFiscal.tenant_id == tenant_id)
    )
    if tipo:
        stmt = stmt.where(NotaFiscal.tipo == tipo)
    if status_sefaz:
        stmt = stmt.where(NotaFiscal.status_sefaz == status_sefaz)
    if unidade_produtiva_id:
        stmt = stmt.where(NotaFiscal.unidade_produtiva_id == unidade_produtiva_id)

    # Count total
    count_stmt = select(func.count(NotaFiscal.id)).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    # Paginate
    stmt = stmt.order_by(NotaFiscal.data_emissao.desc())
    stmt = stmt.limit(limit).offset(offset)
    
    items = list((await session.execute(stmt)).scalars().all())
    
    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("", response_model=NotaFiscalResponse, status_code=status.HTTP_201_CREATED)
async def criar_nota(
    dados: NotaFiscalCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("financeiro:*")),
):
    nota = NotaFiscal(tenant_id=tenant_id, **dados.model_dump(exclude_none=True))
    session.add(nota)
    await session.commit()
    await session.refresh(nota)
    return nota


@router.patch("/{nota_id}", response_model=NotaFiscalResponse)
async def atualizar_nota(
    nota_id: UUID,
    dados: NotaFiscalUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("financeiro:*")),
):
    nota = (await session.execute(
        select(NotaFiscal).where(NotaFiscal.id == nota_id, NotaFiscal.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not nota:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Nota fiscal não encontrada.")
    for k, v in dados.model_dump(exclude_none=True).items():
        setattr(nota, k, v)
    session.add(nota)
    await session.commit()
    await session.refresh(nota)
    return nota
