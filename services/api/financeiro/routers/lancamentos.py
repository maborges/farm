import uuid
from datetime import date
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from core.dependencies import get_session, get_tenant_id
from financeiro.schemas.lancamento_schema import (
    LancamentoCreate, 
    LancamentoUpdate, 
    LancamentoResponse, 
    LancamentoResumo, 
    InsightDashboard, 
    SerieTemporal, 
    AlertaSafra, 
    RecomendacaoSafra, 
    ResumoInteligente, 
    ItemPlanoAcao, 
    ResumoConsultivoResponse, 
    LancamentoOrigemItem,
    DREOperacional,
    SimulacaoDREPayload,
    SimulacaoDREResponse,
    PerformanceUsuarioResponse,
    AlertaInteligente
)
from financeiro.schemas.cenario_schema import CenarioSafraCreate, CenarioSafraResponse
from financeiro.services.lancamento_service import LancamentoService
from financeiro.services.cenario_service import CenarioFinanceiroService

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


@router.get("/", response_model=list[LancamentoResponse])
async def listar_lancamentos(
    safra_id: uuid.UUID | None = Query(None),
    tipo: str | None = Query(None, enum=["CUSTO", "RECEITA"]),
    categoria: str | None = Query(None),
    origem: str | None = Query(None),
    data_inicio: date | None = Query(None),
    data_fim: date | None = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    return await svc.listar(
        safra_id=safra_id,
        tipo=tipo,
        categoria=categoria,
        origem=origem,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@router.get("/resumo", response_model=LancamentoResumo)
async def resumo_lancamentos(
    safra_id: uuid.UUID | None = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    svc = LancamentoService(session, tenant_id)
    return await svc.resumo(safra_id=safra_id)


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


@router.get("/dre", response_model=DREOperacional)
async def gerar_dre(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Gera o DRE Operacional da safra (Step 183)."""
    svc = LancamentoService(session, tenant_id)
    return await svc.gerar_dre(safra_id)


@router.post("/dre/simular", response_model=SimulacaoDREResponse)
async def simular_dre(
    payload: SimulacaoDREPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Simula o resultado da safra com base em ajustes percentuais (Step 185)."""
    svc = LancamentoService(session, tenant_id)
    return await svc.simular_dre(
        safra_id=payload.safra_id,
        receita_pct=payload.ajustes.receita_percentual,
        custos_pct=payload.ajustes.custos_percentual
    )


@router.post("/dre/cenarios", response_model=CenarioSafraResponse)
async def salvar_cenario(
    payload: CenarioSafraCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Salva um cenário de simulação (Step 186)."""
    svc = CenarioFinanceiroService(session, tenant_id)
    return await svc.salvar(payload)


@router.get("/dre/cenarios", response_model=list[CenarioSafraResponse])
async def listar_cenarios(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Lista cenários salvos de uma safra (Step 186)."""
    svc = CenarioFinanceiroService(session, tenant_id)
    return await svc.listar(safra_id)


@router.delete("/dre/cenarios/{cenario_id}")
async def deletar_cenario(
    cenario_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Remove um cenário salvo (Step 186)."""
    svc = CenarioFinanceiroService(session, tenant_id)
    await svc.deletar(cenario_id)
    return {"status": "sucesso"}


@router.patch("/dre/cenarios/{cenario_id}/escolher", response_model=CenarioSafraResponse)
async def escolher_cenario(
    cenario_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Marca um cenário como o escolhido para a safra (Step 188)."""
    svc = CenarioFinanceiroService(session, tenant_id)
    return await svc.escolher(cenario_id)


@router.get("/dre/cenarios/analise", response_model=dict)
async def analisar_cenarios(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Analisa o desvio entre o cenário escolhido e o resultado real (Step 188)."""
    svc = CenarioFinanceiroService(session, tenant_id)
    return await svc.analisar_desvio(safra_id)


@router.get("/performance-usuario", response_model=PerformanceUsuarioResponse)
async def performance_usuario(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Retorna métricas de performance e gamificação do usuário (Step 191)."""
    from financeiro.services.performance_service import PerformanceService
    svc = PerformanceService(session, tenant_id)
    return await svc.obter_performance_usuario()


@router.get("/alertas-inteligentes", response_model=list[AlertaInteligente])
async def alertas_inteligentes(
    safra_id: uuid.UUID = Query(...),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Retorna alertas proativos de riscos e oportunidades financeiras (Step 192)."""
    from financeiro.services.alerta_inteligente_service import AlertaInteligenteService
    svc = AlertaInteligenteService(session, tenant_id)
    return await svc.verificar_alertas(safra_id)
