from fastapi import APIRouter, Depends, status, BackgroundTasks, Response, Query, HTTPException
from typing import List
from uuid import UUID
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
import traceback
from pathlib import Path

from core.dependencies import get_current_admin, get_current_user_claims, get_tenant_id, require_module, require_role
from core.dependencies import get_session, get_session_with_tenant
from core.utils.pdf_generator import generate_caderno_campo_pdf
from agricola.operacoes.schemas import (
    OperacaoAgricolaCreate, OperacaoAgricolaResponse, OperacaoAgricolaUpdate,
    OperacaoTipoFaseCreate,
    OperacaoTipoFaseResponse,
    OperacaoTipoFaseUpdate,
    SafraOperacoesPorFaseResponse,
)
from agricola.operacoes.service import OperacaoService, OperacaoTipoFaseService

router = APIRouter(prefix="/operacoes", tags=["Operações Agrícolas — A2"])
ERROR_DEBUG_LOG = Path(__file__).resolve().parents[2] / "error_debug.log"

MODULE = "A2_CAMPO"


def verificar_alertas_pos_operacao(operacao_id: UUID, tenant_id: UUID):
    # TODO: implementar worker de alertas (carência, clima)
    pass


@router.get(
    "/export/pdf",
    summary="Exporta caderno de campo em PDF",
)
async def exportar_caderno_pdf(
    safra_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = OperacaoService(session, tenant_id)
    filters = {}
    if safra_id:
        filters["safra_id"] = safra_id
    operacoes = await svc.list_all(**filters)

    data_list = [
        {
            "data_realizada": op.data_realizada.strftime("%d/%m/%Y"),
            "tipo": op.tipo,
            "talhao_id": str(op.talhao_id),
            "area_aplicada_ha": float(op.area_aplicada_ha or 0),
            "custo_total": float(op.custo_total or 0),
            "status": op.status,
        }
        for op in operacoes
    ]

    pdf_content = generate_caderno_campo_pdf(data_list)
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Caderno_Campo.pdf"},
    )


@router.post(
    "/",
    response_model=OperacaoAgricolaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registra operação agrícola no caderno de campo",
)
async def criar_operacao(
    dados: OperacaoAgricolaCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "operador"])),
):
    svc = OperacaoService(session, tenant_id)
    try:
        operacao = await svc.criar(dados)
        await session.commit()
    except Exception as exc:
        logger.exception("Erro ao criar operação agrícola")
        with ERROR_DEBUG_LOG.open("a") as f:
            f.write(
                "\n--- OPERACOES CREATE ---\n"
                f"payload={dados.model_dump()}\n"
                f"error={type(exc).__name__}: {exc}\n"
                f"{traceback.format_exc()}\n"
            )
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
    background_tasks.add_task(
        verificar_alertas_pos_operacao,
        operacao_id=operacao.id,
        tenant_id=tenant_id,
    )
    return OperacaoAgricolaResponse.model_validate(operacao)


@router.get(
    "/",
    response_model=List[OperacaoAgricolaResponse],
    summary="Lista operações agrícolas",
)
async def listar_operacoes(
    safra_id: UUID | None = Query(None),
    talhao_id: UUID | None = Query(None),
    tipo: str | None = Query(None),
    data_inicio: date | None = Query(None, description="YYYY-MM-DD"),
    data_fim: date | None = Query(None, description="YYYY-MM-DD"),
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = OperacaoService(session, tenant_id)
    filters: dict = {}
    if safra_id:
        filters["safra_id"] = safra_id
    if talhao_id:
        filters["talhao_id"] = talhao_id
    if tipo:
        filters["tipo"] = tipo

    operacoes = await svc.list_all(**filters)

    # Apply date range filter in-memory (simple, avoids raw SQL for now)
    if data_inicio:
        operacoes = [o for o in operacoes if o.data_realizada >= data_inicio]
    if data_fim:
        operacoes = [o for o in operacoes if o.data_realizada <= data_fim]

    return [OperacaoAgricolaResponse.model_validate(o) for o in operacoes]


@router.get(
    "/tipos",
    response_model=List[OperacaoTipoFaseResponse],
    summary="Lista tipos de operação cadastrados",
)
async def listar_tipos_operacao(
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims),
):
    _ = claims
    svc = OperacaoTipoFaseService(session)
    items = await svc.listar()
    await session.commit()
    return [OperacaoTipoFaseResponse.model_validate(i) for i in items]


@router.post(
    "/tipos",
    response_model=OperacaoTipoFaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria tipo de operação",
)
async def criar_tipo_operacao(
    dados: OperacaoTipoFaseCreate,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(get_current_admin),
):
    _ = admin
    svc = OperacaoTipoFaseService(session)
    item = await svc.criar(dados)
    await session.commit()
    await session.refresh(item)
    return OperacaoTipoFaseResponse.model_validate(item)


@router.patch(
    "/tipos/{tipo_id}",
    response_model=OperacaoTipoFaseResponse,
    summary="Atualiza tipo de operação",
)
async def atualizar_tipo_operacao(
    tipo_id: UUID,
    dados: OperacaoTipoFaseUpdate,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(get_current_admin),
):
    _ = admin
    svc = OperacaoTipoFaseService(session)
    item = await svc.atualizar(tipo_id, dados)
    await session.commit()
    await session.refresh(item)
    return OperacaoTipoFaseResponse.model_validate(item)


@router.delete(
    "/tipos/{tipo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Exclui tipo de operação",
)
async def excluir_tipo_operacao(
    tipo_id: UUID,
    session: AsyncSession = Depends(get_session),
    admin: dict = Depends(get_current_admin),
):
    _ = admin
    svc = OperacaoTipoFaseService(session)
    await svc.excluir(tipo_id)
    await session.commit()


@router.get(
    "/safra/{safra_id}/por-fase",
    response_model=SafraOperacoesPorFaseResponse,
    summary="KPIs e custo de operações agrupados por fase da safra",
)
async def operacoes_por_fase(
    safra_id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = OperacaoService(session, tenant_id)
    return await svc.resumo_por_fase(safra_id)


@router.get(
    "/safra/{safra_id}/fase/{fase}",
    response_model=List[OperacaoAgricolaResponse],
    summary="Lista operações de uma fase específica da safra",
)
async def operacoes_de_fase(
    safra_id: UUID,
    fase: str,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = OperacaoService(session, tenant_id)
    ops = await svc.listar_por_safra_e_fase(safra_id, fase.upper())
    return [OperacaoAgricolaResponse.model_validate(o) for o in ops]


@router.get(
    "/{id}",
    response_model=OperacaoAgricolaResponse,
    summary="Detalhes da operação",
)
async def detalhar_operacao(
    id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
):
    svc = OperacaoService(session, tenant_id)
    operacao = await svc.get_or_fail(id)
    return OperacaoAgricolaResponse.model_validate(operacao)


@router.patch(
    "/{id}",
    response_model=OperacaoAgricolaResponse,
    summary="Atualiza dados da operação",
)
async def atualizar_operacao(
    id: UUID,
    dados: OperacaoAgricolaUpdate,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin", "operador"])),
):
    svc = OperacaoService(session, tenant_id)
    operacao = await svc.atualizar(id, dados)
    await session.commit()
    await session.refresh(operacao)
    return OperacaoAgricolaResponse.model_validate(operacao)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove operação do caderno de campo",
)
async def deletar_operacao(
    id: UUID,
    session: AsyncSession = Depends(get_session_with_tenant),
    tenant_id: UUID = Depends(get_tenant_id),
    _: None = Depends(require_module(MODULE)),
    user: dict = Depends(require_role(["agronomo", "admin"])),
):
    svc = OperacaoService(session, tenant_id)
    await svc.hard_delete(id)
