import uuid
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.dependencies import get_session, get_tenant_id
from financeiro.schemas.lancamento_schema import LancamentoCreate, LancamentoResponse, LancamentoResumo, InsightDashboard, SerieTemporal, AlertaSafra, RecomendacaoSafra
from financeiro.services.lancamento_service import LancamentoService

router = APIRouter(prefix="/lancamentos", tags=["Financeiro — Lançamentos"])


@router.post("/", response_model=LancamentoResponse, status_code=status.HTTP_201_CREATED)
async def criar_lancamento(
    dados: LancamentoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    lancamento = await svc.criar(dados)

    if lancamento.safra_id:
        try:
            from agricola.cenarios.service import CenariosService
            cenario_svc = CenariosService(session, tenant_id)
            await cenario_svc.recalcular_base(lancamento.safra_id)
            await session.commit()
            logger.info(f"Cenários recalculados para safra {lancamento.safra_id}")
        except Exception as e:
            logger.warning(f"Não foi possível recalcular cenários após lançamento: {e}")

    return lancamento


@router.get("/resumo", response_model=LancamentoResumo)
async def resumo_lancamentos(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    return await svc.resumo()


@router.get("/insight", response_model=InsightDashboard)
async def insight_dashboard(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    return await svc.insight_dashboard()


@router.get("/serie-temporal", response_model=list[SerieTemporal])
async def serie_temporal(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    return await svc.serie_temporal(safra_id)


@router.get("/alertas", response_model=list[AlertaSafra])
async def alertas_safra(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    return await svc.gerar_alertas(safra_id)


@router.get("/recomendacoes", response_model=list[RecomendacaoSafra])
async def recomendacoes_safra(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    return await svc.gerar_recomendacoes(safra_id)
