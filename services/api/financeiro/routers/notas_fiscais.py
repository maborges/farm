from core.dependencies import require_tenant_permission
from fastapi import APIRouter, Depends, status, Query, HTTPException, UploadFile, File, Form, Response
from typing import Literal, Optional
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.dependencies import get_tenant_id, get_session, require_module
from core.schemas.pagination import PaginatedResponse
from financeiro.models.nota_fiscal import NotaFiscal, TipoNF, StatusSEFAZ
from financeiro.services import documentos_fiscais as documentos
from financeiro.services.documento_xml import MAX_XML, validar_chave
from financeiro.services.documento_sefaz import consultar

router = APIRouter(prefix="/notas-fiscais", tags=["Financeiro — NF-e / NFP-e"])

MODULE = "F3_FISCAL"


# ── Schemas ───────────────────────────────────────────────────────────────────

class NotaFiscalCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid', allow_inf_nan=False)
    direcao: Literal['entrada', 'saida'] = 'entrada'
    observacoes: str = Field('', max_length=2000)
    tipo: Literal['NFP-e', 'NF-e', 'NFC-e'] = 'NF-e'
    numero: Optional[int] = Field(None, ge=1, le=999999999)
    serie: str = Field('1', min_length=1, max_length=3, pattern=r'^[0-9]+$')
    emitente_nome: str = Field(min_length=1, max_length=200)
    emitente_cpf_cnpj: Optional[str] = Field(None, max_length=18)
    destinatario_nome: str = Field(min_length=1, max_length=200)
    destinatario_documento: Optional[str] = Field(None, max_length=18)
    destinatario_uf: Optional[str] = Field(None, pattern=r'^[A-Z]{2}$')
    valor_produtos: float = Field(0, ge=0, le=9999999999999)
    valor_frete: float = Field(0, ge=0, le=9999999999999)
    valor_icms: float = Field(0, ge=0, le=9999999999999)
    valor_total: float = Field(ge=0, le=9999999999999)
    descricao_produto: Optional[str] = Field(None, max_length=300)
    ncm: Optional[str] = Field(None, pattern=r'^[0-9]{8}$')
    quantidade: Optional[float] = Field(None, ge=0)
    unidade: Optional[str] = Field(None, max_length=6)
    chave_acesso: Optional[str] = None
    unidade_produtiva_id: Optional[UUID] = None
    data_emissao: Optional[datetime] = None
    itens: list[dict] = Field(default_factory=list, max_length=990)

    @field_validator('chave_acesso')
    @classmethod
    def conferir_chave(cls, value):
        return validar_chave(value) if value else None


class NotaFiscalUpdate(BaseModel):
    status_sefaz: Optional[str] = None
    chave_acesso: Optional[str] = None
    numero_protocolo: Optional[str] = None
    numero_recibo: Optional[str] = None
    motivo_cancelamento: Optional[str] = None
    data_autorizacao: Optional[datetime] = None
    data_cancelamento: Optional[datetime] = None


class NotaFiscalResponse(BaseModel):
    gestao: Optional[dict] = None
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


@router.get("", response_model=PaginatedResponse[NotaFiscalResponse], response_model_exclude={
    'items': {'__all__': {'gestao': {'dados_xml': True, 'itens': True, 'historico': True, 'consulta': {'xml_retorno'}}}}})
async def listar_notas(
    q: Optional[str] = Query(None, max_length=100),
    direcao: Optional[Literal['entrada', 'saida']] = Query(None),
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
    if direcao:
        stmt = stmt.where(NotaFiscal.gestao['direcao'].as_string() == direcao)
    if q:
        from sqlalchemy import or_, cast, String
        stmt = stmt.where(or_(NotaFiscal.emitente_nome.ilike(f'%{q}%'), NotaFiscal.destinatario_nome.ilike(f'%{q}%'),
                             NotaFiscal.chave_acesso == q, cast(NotaFiscal.numero, String) == q))

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    # Paginate
    stmt = stmt.order_by(NotaFiscal.data_emissao.desc(), NotaFiscal.id)
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
    return await documentos.salvar_manual(session, tenant_id, dados)


@router.post('/importar-xml', response_model=NotaFiscalResponse)
async def importar_xml(
    arquivo: UploadFile = File(...), direcao: Literal['entrada', 'saida'] = Form(...),
    unidade_id: Optional[UUID] = Form(None), nota_id: Optional[UUID] = Form(None),
    session: AsyncSession = Depends(get_session), tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)), __: None = Depends(require_tenant_permission('financeiro:*')),
):
    try:
        raw = await arquivo.read(MAX_XML + 1)
    finally:
        await arquivo.close()
    return await documentos.importar(session, tenant_id, dict(raw=raw, direcao=direcao, unidade_id=unidade_id, nota_id=nota_id))


@router.post('/importar-lote-xml')
async def importar_lote_xml(
    arquivos: list[UploadFile] = File(...), direcao: Literal['entrada', 'saida'] = Form(...),
    unidade_id: Optional[UUID] = Form(None), session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id), _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission('financeiro:*')),
):
    """Importa XMLs independentes, preservando o resultado de cada arquivo."""
    if not arquivos or len(arquivos) > 200:
        raise HTTPException(422, 'Envie entre 1 e 200 arquivos XML por lote.')
    resultados = []
    for arquivo in arquivos:
        try:
            raw = await arquivo.read(MAX_XML + 1)
            nota = await documentos.importar(session, tenant_id, {
                'raw': raw, 'direcao': direcao, 'unidade_id': unidade_id,
            })
            resultados.append({'arquivo': arquivo.filename, 'ok': True, 'id': str(nota.id),
                               'chave_acesso': nota.chave_acesso})
        except HTTPException as exc:
            resultados.append({'arquivo': arquivo.filename, 'ok': False, 'erro': exc.detail})
        finally:
            await arquivo.close()
    return {'total': len(resultados), 'importados': sum(r['ok'] for r in resultados),
            'falhas': sum(not r['ok'] for r in resultados), 'resultados': resultados}


@router.get('/processos')
async def processos(
    tipo: str, q: str = Query('', max_length=100),
    session: AsyncSession = Depends(get_session), tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)), __: None = Depends(require_tenant_permission('financeiro:*')),
):
    return await documentos.listar_processos(session, tenant_id, {'tipo': tipo, 'q': q})


@router.get('/{nota_id}', response_model=NotaFiscalResponse)
async def detalhe(
    nota_id: UUID, session: AsyncSession = Depends(get_session), tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    return await documentos.buscar_nota(session, tenant_id, nota_id)


@router.get('/{nota_id}/xml')
async def baixar_xml(
    nota_id: UUID, session: AsyncSession = Depends(get_session), tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    await documentos.buscar_nota(session, tenant_id, nota_id)
    raw = await session.scalar(select(NotaFiscal.xml_original).where(NotaFiscal.id == nota_id, NotaFiscal.tenant_id == tenant_id))
    if not raw:
        raise HTTPException(404, 'Este registro ainda não possui XML.')
    return Response(raw, media_type='application/xml', headers={
        'Content-Disposition': f'attachment; filename="nota-{nota_id}.xml"', 'Cache-Control': 'no-store'})


class VinculoInput(BaseModel):
    tipo: Literal['compra', 'despesa', 'receita', 'safra', 'comercializacao']
    id: UUID


@router.post('/{nota_id}/vinculos', response_model=NotaFiscalResponse)
async def associar(
    nota_id: UUID, dados: VinculoInput, session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id), _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission('financeiro:*')),
):
    return await documentos.vincular(session, tenant_id, {'nota_id': nota_id, **dados.model_dump()})


@router.post('/{nota_id}/consultar-sefaz', response_model=NotaFiscalResponse)
async def consultar_sefaz(
    nota_id: UUID, session: AsyncSession = Depends(get_session), tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)), __: None = Depends(require_tenant_permission('financeiro:*')),
):
    return await consultar(session, tenant_id, nota_id)


@router.patch("/{nota_id}", response_model=NotaFiscalResponse)
async def atualizar_nota(
    nota_id: UUID,
    dados: NotaFiscalUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("financeiro:*")),
):
    await documentos.buscar_nota(session, tenant_id, nota_id)
    raise HTTPException(409, 'Situação fiscal e protocolos devem vir do documento ou da consulta SEFAZ, não de edição manual.')
