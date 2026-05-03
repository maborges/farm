import uuid
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.dependencies import get_session, get_tenant_id
from financeiro.schemas.lancamento_schema import LancamentoCreate, LancamentoUpdate, LancamentoResponse, LancamentoResumo, InsightDashboard, SerieTemporal, AlertaSafra, RecomendacaoSafra, ResumoInteligente, ItemPlanoAcao, ResumoConsultivoResponse, LancamentoOrigemItem
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


@router.patch("/{lancamento_id}", response_model=LancamentoResponse)
async def editar_lancamento(
    lancamento_id: uuid.UUID,
    dados: LancamentoUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    lancamento = await svc.atualizar(lancamento_id, dados)
    await session.commit()
    return lancamento


@router.get("/origens", response_model=list[LancamentoOrigemItem])
async def listar_origens(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    return await svc.listar_origens(safra_id)


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


@router.get("/resumo-inteligente", response_model=ResumoInteligente)
async def resumo_inteligente(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    return await svc.gerar_resumo_inteligente(safra_id)


@router.get("/resumo-consultivo", response_model=ResumoConsultivoResponse)
async def resumo_consultivo(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    from ia.insights_service import ContextoSafra, gerar_resumo_consultivo

    svc = LancamentoService(session, tenant_id)

    # Coleta dados reais — nunca delegados à IA para cálculo
    resumo_det = await svc.gerar_resumo_inteligente(safra_id)
    alertas = await svc.gerar_alertas(safra_id)
    serie = await svc.serie_temporal(safra_id)
    recomendacoes = await svc.gerar_recomendacoes(safra_id)
    insight = await svc.insight_dashboard()

    variacao: float | None = None
    if len(serie) >= 2 and serie[-2].total > 0:
        variacao = (serie[-1].total - serie[-2].total) / serie[-2].total * 100

    ctx = ContextoSafra(
        total_custos=insight.total_custos,
        categoria_dominante=next((c.nome for c in sorted(insight.categorias, key=lambda x: x.valor, reverse=True)), None) if insight.categorias else None,
        margem=insight.cenario_margem,
        variacao_mensal_pct=variacao,
        alertas=[a.mensagem for a in alertas],
        recomendacoes=[r.mensagem for r in recomendacoes],
        plano_acoes=resumo_det.proximas_acoes,
    )

    claims = getattr(session, "_claims", {}) if hasattr(session, "_claims") else {}
    tier = claims.get("plan_tier")

    resultado = await gerar_resumo_consultivo(
        ctx, tenant_id=tenant_id, session=session, tier=tier,
    )

    return ResumoConsultivoResponse(
        titulo="Resumo financeiro da safra",
        resumo=resultado.resumo,
        recomendacoes=resultado.recomendacoes,
        pontos_atencao=resumo_det.pontos_atencao,
        nivel_confianca=resultado.nivel_confianca,
        fonte=resultado.fonte,
        ia_disponivel=resultado.ia_disponivel,
        limite_atingido=resultado.limite_atingido,
    )


@router.get("/plano-acao", response_model=list[ItemPlanoAcao])
async def plano_acao(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    return await svc.gerar_plano_acao(safra_id)
