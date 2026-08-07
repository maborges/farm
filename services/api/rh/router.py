from fastapi import APIRouter, Depends, status, Query, Response, HTTPException
from typing import List, Optional
from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_tenant_id, get_session, require_module, require_tenant_permission
from rh.schemas import (
    EsocialEventoCreate, EsocialEventoUpdate, EsocialEventoResponse,
    DepartamentoCreate, DepartamentoUpdate, DepartamentoResponse,
    ColaboradorCreate, ColaboradorResponse,
    DiariaCreate, DiariaResponse, PagarDiariasRequest,
    EmpreitadaCreate, EmpreitadaResponse, ConcluirEmpreitadaRequest,
    DashboardRHResponse,
    ItemSegurancaCreate, ItemSegurancaResponse,
    EntregaSegurancaCreate, EntregaSegurancaResponse,
    DocumentoSSTCreate, DocumentoSSTResponse,
    ResumoSegurancaResponse,
)
from rh.service import (
    EsocialEventoService, DepartamentoService, ColaboradorService,
    DiariaService, EmpreitadaService, SegurancaTrabalhoService, get_dashboard_rh,
)

router = APIRouter(prefix="/rh", tags=["RH — Recursos Humanos"])

MODULE = "RH1_REMUNERACAO"
MODULE_SEGURANCA = "RH2_SEGURANCA"
MODULE_DEPENDENCY = require_module(MODULE_SEGURANCA)


# ── eSocial ───────────────────────────────────────────────────────────────────

@router.get("/esocial/eventos", response_model=List[EsocialEventoResponse])
async def listar_eventos_esocial(
    tipo_evento: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    periodo: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = EsocialEventoService(session, tenant_id)
    return await svc.listar_filtrado(tipo_evento, status, periodo)


@router.post("/esocial/eventos", response_model=EsocialEventoResponse, status_code=status.HTTP_201_CREATED)
async def registrar_evento_esocial(
    dados: EsocialEventoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = EsocialEventoService(session, tenant_id)
    ev = await svc.criar(dados)
    await session.commit()
    await session.refresh(ev)
    return ev


@router.patch("/esocial/eventos/{evento_id}", response_model=EsocialEventoResponse)
async def atualizar_evento_esocial(
    evento_id: UUID,
    dados: EsocialEventoUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = EsocialEventoService(session, tenant_id)
    ev = await svc.atualizar(evento_id, dados)
    await session.commit()
    await session.refresh(ev)
    return ev


# ── Departamentos ─────────────────────────────────────────────────────────────

@router.get("/departamentos", response_model=List[DepartamentoResponse])
async def listar_departamentos(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = DepartamentoService(session, tenant_id)
    return await svc.listar_com_contagem()


@router.post("/departamentos", response_model=DepartamentoResponse, status_code=status.HTTP_201_CREATED)
async def criar_departamento(
    dados: DepartamentoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = DepartamentoService(session, tenant_id)
    dep = await svc.criar(dados)
    await session.commit()
    await session.refresh(dep)
    return {**dep.__dict__, "total_colaboradores": 0}


@router.patch("/departamentos/{departamento_id}", response_model=DepartamentoResponse)
async def atualizar_departamento(
    departamento_id: UUID,
    dados: DepartamentoUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = DepartamentoService(session, tenant_id)
    dep = await svc.atualizar(departamento_id, dados)
    await session.commit()
    await session.refresh(dep)
    rows = await svc.listar_com_contagem()
    total = next((r["total_colaboradores"] for r in rows if str(r["id"]) == str(departamento_id)), 0)
    return {**dep.__dict__, "total_colaboradores": total}


@router.delete("/departamentos/{departamento_id}", status_code=200)
async def desativar_departamento(
    departamento_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = DepartamentoService(session, tenant_id)
    dep = await svc.get_or_fail(departamento_id)
    dep.ativo = False
    session.add(dep)
    await session.commit()
    return {"message": "Departamento desativado."}


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardRHResponse)
async def dashboard_rh(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    return await get_dashboard_rh(session, tenant_id)


# ── Colaboradores ─────────────────────────────────────────────────────────────

@router.get("/colaboradores", response_model=List[ColaboradorResponse])
async def listar_colaboradores(
    ativo: Optional[bool] = Query(True),
    tipo_contrato: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Busca por nome"),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = ColaboradorService(session, tenant_id)
    filters: dict = {}
    if ativo is not None:
        filters["ativo"] = ativo
    if tipo_contrato:
        filters["tipo_contrato"] = tipo_contrato
    return await svc.listar(q=q, **filters)


@router.post("/colaboradores", response_model=ColaboradorResponse, status_code=status.HTTP_201_CREATED)
async def criar_colaborador(
    dados: ColaboradorCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = ColaboradorService(session, tenant_id)
    col = await svc.criar(dados)
    await session.commit()
    await session.refresh(col)
    return col


@router.delete("/colaboradores/{colaborador_id}", status_code=200)
async def desativar_colaborador(
    colaborador_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = ColaboradorService(session, tenant_id)
    await svc.desativar(colaborador_id)
    return {"message": "Colaborador desativado."}


# ── Diárias ───────────────────────────────────────────────────────────────────

@router.get("/diarias", response_model=List[DiariaResponse])
async def listar_diarias(
    colaborador_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = DiariaService(session, tenant_id)
    return await svc.listar_filtrado(colaborador_id, status, data_inicio, data_fim)


@router.post("/diarias", response_model=DiariaResponse, status_code=status.HTTP_201_CREATED)
async def lancar_diaria(
    dados: DiariaCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = DiariaService(session, tenant_id)
    diaria = await svc.criar(dados)
    await session.commit()
    await session.refresh(diaria)
    return diaria


@router.post("/diarias/pagar-lote", status_code=200)
async def pagar_diarias(
    dados: PagarDiariasRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = DiariaService(session, tenant_id)
    count = await svc.pagar_lote(dados.ids, dados.data_pagamento)
    return {"message": f"{count} diária(s) marcada(s) como pagas."}


# ── Empreitadas ───────────────────────────────────────────────────────────────

@router.get("/empreitadas", response_model=List[EmpreitadaResponse])
async def listar_empreitadas(
    colaborador_id: Optional[UUID] = Query(None),
    status_filter: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = EmpreitadaService(session, tenant_id)
    return await svc.listar_filtrado(colaborador_id, status_filter)


@router.post("/empreitadas", response_model=EmpreitadaResponse, status_code=status.HTTP_201_CREATED)
async def criar_empreitada(
    dados: EmpreitadaCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = EmpreitadaService(session, tenant_id)
    emp = await svc.criar(dados)
    await session.commit()
    await session.refresh(emp)
    return emp


@router.patch("/empreitadas/{empreitada_id}/concluir", response_model=EmpreitadaResponse)
async def concluir_empreitada(
    empreitada_id: UUID,
    dados: ConcluirEmpreitadaRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = EmpreitadaService(session, tenant_id)
    return await svc.concluir(empreitada_id, dados.quantidade_final, dados.data_fim)


# ── Segurança do Trabalho ───────────────────────────────────────────────────

@router.get("/seguranca/resumo", response_model=ResumoSegurancaResponse)
async def resumo_seguranca(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(MODULE_DEPENDENCY),
):
    svc = SegurancaTrabalhoService(session, tenant_id)
    return await svc.get_resumo()


@router.get("/seguranca/itens", response_model=List[ItemSegurancaResponse])
async def listar_itens_seguranca(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(MODULE_DEPENDENCY),
):
    svc = SegurancaTrabalhoService(session, tenant_id)
    return await svc.listar_itens()


@router.post("/seguranca/itens", response_model=ItemSegurancaResponse, status_code=status.HTTP_201_CREATED)
async def criar_item_seguranca(
    dados: ItemSegurancaCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(MODULE_DEPENDENCY),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = SegurancaTrabalhoService(session, tenant_id)
    item = await svc.criar_item(dados)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/seguranca/entregas", response_model=List[EntregaSegurancaResponse])
async def listar_entregas_seguranca(
    colaborador_id: Optional[UUID] = Query(None),
    item_id: Optional[UUID] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(MODULE_DEPENDENCY),
):
    svc = SegurancaTrabalhoService(session, tenant_id)
    return await svc.listar_entregas(colaborador_id, item_id)


@router.post("/seguranca/entregas", response_model=EntregaSegurancaResponse, status_code=status.HTTP_201_CREATED)
async def registrar_entrega_seguranca(
    dados: EntregaSegurancaCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(MODULE_DEPENDENCY),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = SegurancaTrabalhoService(session, tenant_id)
    try:
        entrega = await svc.registrar_entrega(dados)
        await session.commit()
        await session.refresh(entrega)
        return entrega
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/seguranca/documentos", response_model=List[DocumentoSSTResponse])
async def listar_documentos_sst(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE_SEGURANCA)),
):
    svc = SegurancaTrabalhoService(session, tenant_id)
    return await svc.listar_documentos()


@router.post("/seguranca/documentos", response_model=DocumentoSSTResponse, status_code=status.HTTP_201_CREATED)
async def registrar_documento_sst(
    dados: DocumentoSSTCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE_SEGURANCA)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = SegurancaTrabalhoService(session, tenant_id)
    try:
        doc = await svc.registrar_documento(dados)
        await session.commit()
        await session.refresh(doc)
        return doc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/seguranca/export/nr31.pdf", dependencies=[Depends(MODULE_DEPENDENCY)])
async def exportar_relatorio_nr31(
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    svc = SegurancaTrabalhoService(session, tenant_id)
    pdf = await svc.gerar_pdf_nr31()
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="relatorio_nr31.pdf"'},
    )


@router.patch("/empreitadas/{empreitada_id}/pagar", response_model=EmpreitadaResponse)
async def pagar_empreitada(
    empreitada_id: UUID,
    data_pagamento: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    __: None = Depends(require_tenant_permission("rh:*")),
):
    svc = EmpreitadaService(session, tenant_id)
    return await svc.pagar(empreitada_id, data_pagamento)
