from core.dependencies import require_tenant_permission
from fastapi import APIRouter, Depends, status
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_tenant_id, require_module, require_role
from core.dependencies import get_session
from agricola.beneficiamento.schemas import (
    BeneficiamentoKPIs,
    BeneficiamentoRelatorioRendimento,
    CafeQualidadeMargemResponse,
    LoteBeneficiamentoCreate,
    LoteBeneficiamentoResponse,
    LoteBeneficiamentoUpdate,
    LoteFromRomaneiosRequest,
)
from agricola.beneficiamento.service import BeneficiamentoService

router = APIRouter(
    prefix="/beneficiamento",
    tags=["Beneficiamento Pós-Colheita"],
    dependencies=[
        Depends(require_module("A5_COLHEITA")),
    ],
)


@router.post("/", response_model=LoteBeneficiamentoResponse, status_code=status.HTTP_201_CREATED)
async def criar_lote(
    dados: LoteBeneficiamentoCreate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(require_role(["agronomo", "admin", "operador"])),
):
    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.criar(dados)
    await session.commit()
    lote = await svc.obter_com_detalhe(lote.id)
    return LoteBeneficiamentoResponse.model_validate(lote)


@router.get("/kpis", response_model=BeneficiamentoKPIs)
async def kpis_beneficiamento(
    safra_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    svc = BeneficiamentoService(session, tenant_id)
    return await svc.kpis_safra(safra_id)


@router.get("/relatorio-rendimento", response_model=BeneficiamentoRelatorioRendimento)
async def relatorio_rendimento(
    safra_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Gera relatório de rendimento por método de beneficiamento."""
    svc = BeneficiamentoService(session, tenant_id)
    return await svc.relatorio_rendimento(safra_id)


@router.get("/qualidade-margem", response_model=CafeQualidadeMargemResponse)
async def qualidade_margem_cafe(
    safra_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    """Correlaciona classificação de qualidade (SCA/ABIC), custo/saca e preço/margem."""
    svc = BeneficiamentoService(session, tenant_id)
    return await svc.analise_qualidade_margem(safra_id)


@router.get("/", response_model=List[LoteBeneficiamentoResponse])
async def listar_lotes(
    safra_id: UUID | None = None,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    svc = BeneficiamentoService(session, tenant_id)
    filters = {}
    if safra_id:
        filters["safra_id"] = safra_id
    if status:
        filters["status"] = status
    lotes = await svc.listar_com_detalhe(**filters)
    return [LoteBeneficiamentoResponse.model_validate(l) for l in lotes]


@router.post("/from-romaneio/{romaneio_id}", response_model=LoteBeneficiamentoResponse, status_code=status.HTTP_201_CREATED)
async def criar_lote_from_romaneio(
    romaneio_id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(require_role(["agronomo", "admin", "operador"])),
):
    """Cria um LoteBeneficiamento pré-populado a partir de um Romaneio."""
    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.criar_from_romaneio(romaneio_id)
    await session.commit()
    lote = await svc.obter_com_detalhe(lote.id)
    return LoteBeneficiamentoResponse.model_validate(lote)


@router.post("/from-romaneios", response_model=LoteBeneficiamentoResponse, status_code=status.HTTP_201_CREATED)
async def criar_lote_from_romaneios(
    req: LoteFromRomaneiosRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(require_role(["agronomo", "admin", "operador"])),
):
    """Cria um LoteBeneficiamento agrupando múltiplos romaneios (blend/agrupamento)."""
    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.criar_from_romaneios(req)
    return LoteBeneficiamentoResponse.model_validate(lote)


@router.post("/{id}/gerar-venda", response_model=dict)
async def gerar_venda_from_lote(
    id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(require_role(["agronomo", "admin"])),
):
    """Gera uma Comercializacao (venda em rascunho) a partir de um lote ARMAZENADO."""
    svc = BeneficiamentoService(session, tenant_id)
    resultado = await svc.gerar_venda(id)
    return resultado


@router.post("/{id}/armazenar", response_model=dict)
async def armazenar_lote(
    id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(require_role(["agronomo", "admin"])),
):
    """Armazena lote beneficiado em estoque (cria LoteEstoque)."""
    svc = BeneficiamentoService(session, tenant_id)
    resultado = await svc.armazenar_no_estoque(id)
    return resultado


@router.get("/{id}", response_model=LoteBeneficiamentoResponse)
async def detalhar_lote(
    id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
):
    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.obter_com_detalhe(id)
    return LoteBeneficiamentoResponse.model_validate(lote)


@router.patch("/{id}", response_model=LoteBeneficiamentoResponse)
async def atualizar_lote(
    id: UUID,
    dados: LoteBeneficiamentoUpdate,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(require_role(["agronomo", "admin"])),
):
    svc = BeneficiamentoService(session, tenant_id)
    lote = await svc.atualizar(id, dados)
    return LoteBeneficiamentoResponse.model_validate(lote)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_lote(
    id: UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: UUID = Depends(get_tenant_id),
    user: dict = Depends(require_role(["admin"])),
):
    svc = BeneficiamentoService(session, tenant_id)
    await svc.hard_delete(id)
