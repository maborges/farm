import urllib.parse
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, Integer as sa_Integer
from pydantic import BaseModel, Field
from loguru import logger

from core.dependencies import (
    get_session, get_tenant_id, get_current_user_claims, 
    get_session_with_tenant, get_current_tenant
)
from core.models.billing import AssinaturaTenant, PlanoAssinatura
from core.models.solicitacoes_comerciais import SolicitacaoComercial
from ia.usage_service import (
    consultar_uso_mensal, consultar_creditos, solicitar_creditos,
    consultar_uso_hibrido, LIMITES_MENSAIS,
)
from ia.models import IAUso
from financeiro.schemas.lancamento_schema import SimulacaoDREPayload, ResumoDiarioResponse
from financeiro.services.resumo_diario_service import ResumoDiarioService
from ia.acoes_assistidas_service import AcaoAssistidaService
from ia.performance_service import IAPerformanceService
from ia.upgrade_recomendacao_service import IARecomendacaoUpgradeService
from ia.commercial_assistant_service import IACommercialAssistantService
from ia.schemas import (
    IAAcaoAssistidaHistoricoResponse,
    IAPerformanceDashboardResponse,
    IAUpgradeRecomendacaoResponse,
    IAPredicaoRiscoResponse,
    IAEstresseFinanceiroResponse,
    IAPlanoAcaoResponse,
    IAAutopilotMetricsResponse,
    AcaoAssistidaResponse,
    MetricasAcaoAssistidaResponse,
    IAProgressoResponse,
    IAGrowthCTAResponse,
    IAGrowthExperimentoSchema,
    IAGrowthExperimentoCreate,
    IAGrowthExperimentoResultado,
    IAGrowthExperimentoAutoCreate,
    IAGrowthCopyPerformanceResponse,
    IAGrowthPersonasPerformanceResponse,
    IAGrowthChurnDashboardResponse,
    IAGrowthPlanoRecomendadoResponse,
    IAGrowthPlanoMetricasResponse,
    IAGrowthOfertasPerformanceResponse,
    IAGrowthOportunidadesResponse,
    IAGrowthAutopilotStatusResponse,
    IAGrowthAssistenteContextoResponse,
    IAGrowthAssistenteMensagemRequest,
    IAGrowthAssistenteMensagemResponse,
)
from ia.predicao_risco_service import IAPredicaoRiscoService
from ia.estresse_financeiro_service import IAEstresseFinanceiroService
from ia.autopilot_service import IAAutopilotService

router = APIRouter(prefix="/ia", tags=["IA — Uso"])


class AutopilotConfigUpdate(BaseModel):
    ativo: Optional[bool] = None
    autopilot_enabled: Optional[bool] = None
    nivel_autonomia: Optional[str] = None
    tipos_permitidos: Optional[list[str]] = None
    limite_impacto_percentual: Optional[float] = None


class AutopilotConfigResponse(BaseModel):
    ativo: bool
    autopilot_enabled: bool
    nivel_autonomia: str
    tipos_permitidos: list[str]
    limite_impacto_percentual: float
    updated_at: datetime


class IAAutopilotMetricsResponse(BaseModel):
    total_acoes_automaticas: int
    impacto_financeiro_simulado_total: float
    impacto_medio_por_acao: float
    taxa_aprovacao_implicita: float
    taxa_reversao: float
    tempo_medio_ate_interacao_minutos: float
    insight: str
    indicador_confianca: int

class IAAutopilotTuningResponse(BaseModel):
    deve_ajustar: bool
    acao: str
    limite_atual: float
    novo_limite: float
    mensagem: str
    motivo: str

class IAEssentialResponse(BaseModel):
    prioridade: str
    tipo: str
    titulo: str
    resumo: str
    detalhe: str
    impacto_financeiro: str
    acao_label: str
    rota: str
    cor: str
    id_referencia: Optional[str] = None


class ResumoCreditosIA(BaseModel):
    limite_plano: Optional[int] = None
    usado_plano: int = 0
    creditos_extras: int = 0
    creditos_extras_disponiveis: int = 0
    creditos_extras_usados: int = 0
    total_disponivel: int = 0


class SolicitarCreditosPayload(BaseModel):
    quantidade: int = Field(..., ge=10, le=10000)


class SolicitarCreditosResponse(BaseModel):
    id: str
    protocolo: str
    quantidade: int
    status: str
    mensagem: str


class RegistrarAcaoAssistidaPayload(BaseModel):
    origem: str
    origem_id: Optional[uuid.UUID] = None
    tipo_acao: str
    parametros_json: Optional[dict] = None


# Schemas definidos em ia/schemas.py


# ── Precificação centralizada ────────────────────────────────────────────────
# Tabela de preços por faixa (R$/crédito) — mínimo → preço_unitário
_PRECO_POR_CREDITO: list[tuple[int, Decimal]] = [
    (1000, Decimal("0.07")),
    (500,  Decimal("0.08")),
    (200,  Decimal("0.09")),
    (0,    Decimal("0.10")),
]

# Custo médio estimado por crédito em R$ (baseado no custo LLM + infra)
CUSTO_ESTIMADO_CREDITO_IA = Decimal("0.035")

# Margem mínima aceitável (percentual). Checkout abaixo disso é bloqueado.
MARGEM_MINIMA_IA_PERCENTUAL = Decimal("30")

_WHATSAPP_NUMERO = "5511999999999"  # substituir pelo número comercial real


def _calcular_valor(quantidade: int) -> Decimal:
    for minimo, preco_unitario in _PRECO_POR_CREDITO:
        if quantidade >= minimo:
            return (preco_unitario * quantidade).quantize(Decimal("0.01"))
    return (Decimal("0.10") * quantidade).quantize(Decimal("0.01"))


def _calcular_margem(valor_total: Decimal, quantidade: int) -> dict:
    """Retorna custo_estimado, margem_estimada e margem_percentual."""
    custo = (CUSTO_ESTIMADO_CREDITO_IA * quantidade).quantize(Decimal("0.01"))
    margem = (valor_total - custo).quantize(Decimal("0.01"))
    pct = ((margem / valor_total) * 100).quantize(Decimal("0.01")) if valor_total else Decimal("0")
    return {
        "custo_estimado": custo,
        "margem_estimada": margem,
        "margem_percentual": pct,
    }


def _validar_margem(margem_percentual: Decimal) -> None:
    if margem_percentual < MARGEM_MINIMA_IA_PERCENTUAL:
        raise HTTPException(
            status_code=422,
            detail=f"Margem estimada ({margem_percentual}%) abaixo do mínimo permitido ({MARGEM_MINIMA_IA_PERCENTUAL}%).",
        )


def _gerar_link_pagamento(protocolo: str, quantidade: int, valor: Decimal) -> str:
    valor_fmt = f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    mensagem = (
        f"Olá! Gostaria de finalizar a compra de {quantidade} créditos de IA "
        f"(protocolo {protocolo}). Valor: {valor_fmt}."
    )
    return f"https://wa.me/{_WHATSAPP_NUMERO}?text={urllib.parse.quote(mensagem)}"


class CheckoutPayload(BaseModel):
    quantidade: int = Field(..., ge=10, le=10000)


class CheckoutResponse(BaseModel):
    link_pagamento: str
    valor_estimado: float
    protocolo: str
    custo_estimado: float
    margem_estimada: float
    margem_percentual: float


class ResumoUsoIA(BaseModel):
    # campos originais — backward compat
    plano: Optional[str] = None
    limite_mensal: Optional[int] = None
    usado_mes: int = 0
    restante: Optional[int] = None
    percentual_uso: float = 0.0
    custo_estimado_mes: float = 0.0
    ia_disponivel: bool = False
    # campos híbridos (step 121)
    uso_plano: int = 0
    uso_pacotes: int = 0
    creditos_extras_disponiveis: int = 0
    usando_creditos_extras: bool = False


class RegistroHistoricoIA(BaseModel):
    data: datetime
    origem: str
    status: str
    tokens_entrada: int
    tokens_saida: int
    custo_estimado: Optional[float] = None


def _assinatura_ativa_filter():
    return AssinaturaTenant.status.in_(["ATIVA", "TRIAL"])


async def _get_tier(tenant_id: uuid.UUID, session: AsyncSession, claims: dict) -> str | None:
    tier_str = claims.get("plan_tier")
    if not tier_str:
        stmt = (
            select(PlanoAssinatura.plan_tier)
            .join(AssinaturaTenant, AssinaturaTenant.plano_id == PlanoAssinatura.id)
            .where(
                AssinaturaTenant.tenant_id == tenant_id,
                _assinatura_ativa_filter(),
                AssinaturaTenant.tipo_assinatura == "TENANT",
            ).limit(1)
        )
        tier_str = (await session.execute(stmt)).scalar_one_or_none()
    return tier_str


@router.get("/uso/resumo", response_model=ResumoUsoIA)
async def resumo_uso_ia(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    tier = await _get_tier(tenant_id, session, claims)
    uso = await consultar_uso_mensal(tenant_id, session)
    hibrido = await consultar_uso_hibrido(tenant_id, tier, session)
    limite = LIMITES_MENSAIS.get(tier or "")
    usado = uso["total_chamadas"]
    ia_disponivel = limite is not None

    return ResumoUsoIA(
        plano=tier,
        limite_mensal=limite,
        usado_mes=usado,
        restante=max(0, limite - usado) if limite is not None else None,
        percentual_uso=round(usado / limite * 100, 1) if limite else 0.0,
        custo_estimado_mes=round(uso["custo_estimado_usd"], 4),
        ia_disponivel=ia_disponivel,
        uso_plano=hibrido["uso_plano"],
        uso_pacotes=hibrido["uso_pacotes"],
        creditos_extras_disponiveis=hibrido["creditos_extras_disponiveis"],
        usando_creditos_extras=hibrido["usando_creditos_extras"],
    )


@router.get("/uso/historico", response_model=list[RegistroHistoricoIA])
async def historico_uso_ia(
    limit: int = Query(20, ge=1, le=100),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(IAUso)
        .where(IAUso.tenant_id == tenant_id)
        .order_by(desc(IAUso.created_at))
        .limit(limit)
    )
    registros = list((await session.execute(stmt)).scalars().all())
    return [
        RegistroHistoricoIA(
            data=r.created_at,
            origem=r.origem,
            status=r.status,
            tokens_entrada=r.tokens_entrada,
            tokens_saida=r.tokens_saida,
            custo_estimado=float(r.custo_estimado) if r.custo_estimado is not None else None,
        )
        for r in registros
    ]


@router.get("/creditos", response_model=ResumoCreditosIA)
async def resumo_creditos(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    tier = await _get_tier(tenant_id, session, claims)
    dados = await consultar_creditos(tenant_id, tier, session)
    return ResumoCreditosIA(**dados)


@router.post("/creditos/solicitar", response_model=SolicitarCreditosResponse, status_code=201)
async def solicitar_creditos_ia(
    body: SolicitarCreditosPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None

    pacote = await solicitar_creditos(tenant_id, body.quantidade, session)

    solicitacao = SolicitacaoComercial(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        tipo="CREDITOS_IA",
        origem="ia_creditos_adicionais",
        detalhes={"quantidade": body.quantidade, "pacote_id": str(pacote.id)},
        status="ABERTA",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(solicitacao)
    await session.commit()

    protocolo = f"IA-{str(solicitacao.id)[:8].upper()}"
    logger.bind(
        event="upgrade_intention_created",
        tenant_id=str(tenant_id),
        tipo="CREDITOS_IA",
        origem="ia_creditos_adicionais",
        quantidade=body.quantidade,
        solicitacao_id=str(solicitacao.id),
    ).info("upgrade_intention_created")

    return SolicitarCreditosResponse(
        id=str(pacote.id),
        protocolo=protocolo,
        quantidade=pacote.quantidade_creditos,
        status=pacote.status,
        mensagem=f"Solicitação registrada com protocolo {protocolo}. Nossa equipe entrará em contato em breve.",
    )


@router.post("/creditos/checkout", response_model=CheckoutResponse, status_code=200)
async def checkout_creditos_ia(
    body: CheckoutPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Gera link de pagamento para créditos de IA e atualiza a solicitação comercial."""
    valor = _calcular_valor(body.quantidade)
    margem_info = _calcular_margem(valor, body.quantidade)
    _validar_margem(margem_info["margem_percentual"])

    # Busca solicitação ABERTA mais recente do tenant
    stmt = (
        select(SolicitacaoComercial)
        .where(
            SolicitacaoComercial.tenant_id == tenant_id,
            SolicitacaoComercial.tipo == "CREDITOS_IA",
            SolicitacaoComercial.status == "ABERTA",
        )
        .order_by(desc(SolicitacaoComercial.created_at))
        .limit(1)
    )
    solicitacao = (await session.execute(stmt)).scalar_one_or_none()

    detalhes_economicos = {
        "quantidade": body.quantidade,
        "valor_total": str(valor),
        "custo_estimado": str(margem_info["custo_estimado"]),
        "margem_estimada": str(margem_info["margem_estimada"]),
        "margem_percentual": str(margem_info["margem_percentual"]),
    }

    # Cria solicitação se não existir (checkout direto sem solicitar antes)
    if not solicitacao:
        usuario_id_str = claims.get("sub")
        usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
        solicitacao = SolicitacaoComercial(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            usuario_id=usuario_id,
            tipo="CREDITOS_IA",
            origem="ia_creditos_checkout",
            detalhes=detalhes_economicos,
            status="ABERTA",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(solicitacao)
        await session.flush()
    else:
        solicitacao.detalhes = {**(solicitacao.detalhes or {}), **detalhes_economicos}

    protocolo = f"IA-{str(solicitacao.id)[:8].upper()}"
    link = _gerar_link_pagamento(protocolo, body.quantidade, valor)

    solicitacao.valor_estimado = valor
    solicitacao.link_pagamento = link
    solicitacao.status_pagamento = "PENDENTE"
    solicitacao.updated_at = datetime.now(timezone.utc)

    await session.commit()

    logger.bind(
        event="checkout_initiated",
        tenant_id=str(tenant_id),
        protocolo=protocolo,
        quantidade=body.quantidade,
        valor=str(valor),
        margem_percentual=str(margem_info["margem_percentual"]),
    ).info("checkout_initiated")

    return CheckoutResponse(
        link_pagamento=link,
        valor_estimado=float(valor),
        protocolo=protocolo,
        custo_estimado=float(margem_info["custo_estimado"]),
        margem_estimada=float(margem_info["margem_estimada"]),
        margem_percentual=float(margem_info["margem_percentual"]),
    )


@router.get("/financeiro/predicao-risco", response_model=IAPredicaoRiscoResponse)
async def prever_risco_financeiro(
    safra_id: Optional[uuid.UUID] = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Analisa tendências históricas para antecipar riscos financeiros (Step 205).
    """
    from ia.essential_service import IAEssentialService
    safra_id = await IAEssentialService.resolve_safra_id(session, tenant_id, safra_id)
    if not safra_id:
        raise HTTPException(status_code=422, detail="Safra não informada e nenhuma safra ativa encontrada.")
        
    svc = IAPredicaoRiscoService(session, tenant_id)
    resultado = await svc.prever_risco_financeiro(safra_id)
    return IAPredicaoRiscoResponse(**resultado)


@router.get("/financeiro/simulacao-estresse", response_model=IAEstresseFinanceiroResponse)
async def get_simulacao_estresse(
    safra_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """Retorna a simulação de estresse financeiro (Step 206)."""
    from ia.essential_service import IAEssentialService
    safra_id = await IAEssentialService.resolve_safra_id(db, tenant_id, safra_id)
    if not safra_id:
        raise HTTPException(status_code=422, detail="Safra não informada e nenhuma safra ativa encontrada.")
        
    service = IAEstresseFinanceiroService(db, tenant_id)
    return await service.simular_estresse_financeiro(safra_id)

@router.get("/autopilot/metricas", response_model=IAAutopilotMetricsResponse)
async def get_autopilot_metricas(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Retorna métricas de performance e ROI do Autopilot (Step 211)."""
    from ia.autopilot_metrics_service import IAAutopilotMetricsService
    return await IAAutopilotMetricsService.obter_metricas(session, tenant_id)


@router.get("/autopilot/sugestao-tuning", response_model=IAAutopilotTuningResponse)
async def get_autopilot_sugestao_tuning(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Retorna sugestão de ajuste de autonomia baseada em performance (Step 212)."""
    from ia.adaptive_service import IAAutopilotAdaptiveService
    return await IAAutopilotAdaptiveService.avaliar_ajuste_autonomia(session, tenant_id)


@router.post("/autopilot/aplicar-tuning")
async def aplicar_autopilot_tuning(
    request: dict,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Aplica o novo limite sugerido de autonomia (Step 212)."""
    from ia.autopilot_service import IAAutopilotService
    novo_limite = request.get("novo_limite")
    
    if novo_limite is None:
        return {"success": False, "error": "novo_limite_obrigatorio"}
        
    await IAAutopilotService.update_config(session, tenant_id, {"limite_impacto_percentual": novo_limite})
    
    # Evento de Tracking (Log ou Tabela de Eventos se existir)
    # logger.info(f"autopilot_tuning_applied: tenant={tenant_id} novo_limite={novo_limite}")
    
    return {"success": True, "novo_limite": novo_limite}


@router.get("/essencial", response_model=IAEssentialResponse)
async def get_visao_essencial(
    safra_id: Optional[uuid.UUID] = Query(None),
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
):
    """Retorna a visão essencial e priorizada de IA (Step UX-02)."""
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None

    from ia.essential_service import IAEssentialService
    safra_id = await IAEssentialService.resolve_safra_id(session, tenant_id, safra_id)
    return await IAEssentialService.obter_essencial(session, tenant_id, safra_id, usuario_id=usuario_id)


@router.get("/progresso", response_model=IAProgressoResponse)
async def get_progresso_usuario_ia(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Retorna a evolução e progresso do usuário no uso da IA (Step UX-11)."""
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
    
    from ia.ux_telemetry_service import IAUXTelemetryService
    return await IAUXTelemetryService.calcular_progresso_usuario_ia(session, tenant_id, usuario_id=usuario_id)


@router.get("/growth/recomendacao-upgrade", response_model=IAGrowthCTAResponse)
async def get_growth_recomendacao(
    contexto: str = Query("progresso"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Avalia gatilhos de conversão e retorna CTA contextual (Growth-01)."""
    from ia.growth_service import IAGrowthService
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
    return await IAGrowthService.recomendacao_upgrade(session, tenant_id, usuario_id, contexto)


@router.get("/growth/plano-recomendado", response_model=IAGrowthPlanoRecomendadoResponse)
async def get_growth_plano_recomendado(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Recomendação consultiva de plano para o tenant/usuário (IA-Growth-16).

    Não altera billing — apenas sugere plano + copy + CTA com base em fit.
    """
    from ia.growth_service import IAGrowthService
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
    return await IAGrowthService.gerar_recomendacao_plano(session, tenant_id, usuario_id)


@router.get("/growth/plano-recomendado/metricas", response_model=IAGrowthPlanoMetricasResponse)
async def get_growth_plano_recomendado_metricas(
    periodo_dias: int = Query(30, ge=7, le=180),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Distribuição/CTR/conversão por plano recomendado (IA-Growth-16).

    Restrito a owner/admin do tenant. Usuário comum só consome o CTA do
    endpoint principal.
    """
    if not claims.get("is_owner"):
        raise HTTPException(
            status_code=403,
            detail="Apenas o proprietário do tenant pode acessar métricas de Growth.",
        )
    from ia.growth_service import IAGrowthService
    return await IAGrowthService.metricas_plano_recomendado(session, tenant_id, periodo_dias)


@router.get("/growth/ofertas/performance", response_model=IAGrowthOfertasPerformanceResponse)
async def get_growth_ofertas_performance(
    periodo_dias: int = Query(30, ge=7, le=180),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Consolida distribuição, conversão e impacto por tipo de oferta."""
    if not (claims.get("role") in {"owner", "admin"} or claims.get("is_owner") is True):
        raise HTTPException(
            status_code=403,
            detail="Apenas proprietários e administradores podem acessar performance de ofertas.",
        )
    from ia.growth_service import IAGrowthService
    resultado = await IAGrowthService.metricas_ofertas(session, tenant_id, periodo_dias)
    return IAGrowthOfertasPerformanceResponse(**resultado)


@router.post("/growth/plano-recomendado/{log_id}/clique")
async def post_growth_plano_recomendado_clique(
    log_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Marca clique no CTA da recomendação de plano (IA-Growth-16)."""
    from ia.growth_service import IAGrowthService
    ok = await IAGrowthService.marcar_plano_recomendado_evento(session, tenant_id, log_id, "clique")
    if not ok:
        raise HTTPException(status_code=404, detail="Recomendação não encontrada para este tenant.")
    return {"status": "ok"}


@router.post("/growth/plano-recomendado/{log_id}/conversao")
async def post_growth_plano_recomendado_conversao(
    log_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Marca conversão (upgrade efetivo) referente a uma recomendação (IA-Growth-16)."""
    from ia.growth_service import IAGrowthService
    ok = await IAGrowthService.marcar_plano_recomendado_evento(session, tenant_id, log_id, "conversao")
    if not ok:
        raise HTTPException(status_code=404, detail="Recomendação não encontrada para este tenant.")
    return {"status": "ok"}


@router.post("/growth/track")
async def track_growth_evento(
    payload: dict,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Registra evento de CTA de upgrade para cooldown e analytics (Growth-01)."""
    from ia.growth_service import IAGrowthService
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
    await IAGrowthService.registrar_evento(
        db=session,
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        evento=payload.get("evento", "upgrade_cta_viewed"),
        tipo_cta=payload.get("tipo_cta", ""),
        contexto=payload.get("contexto", ""),
        churn_risk_score=payload.get("churn_risk_score"),
        churn_risk_level=payload.get("churn_risk_level"),
        metadados=payload.get("metadados"),
    )
    return {"status": "ok"}


@router.get("/growth/metricas")
async def get_growth_metricas(
    periodo_dias: int = Query(30, ge=7, le=90),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Métricas de conversão de CTAs por contexto (Growth-02)."""
    from ia.growth_service import IAGrowthService
    return await IAGrowthService.calcular_metricas_cta(session, tenant_id, periodo_dias)


@router.get("/growth/config")
async def get_growth_config(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Lista configurações de CTA por contexto do tenant (Growth-03)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário do tenant pode acessar configurações de growth.")
    from ia.growth_service import IAGrowthService
    return await IAGrowthService.listar_configs(session, tenant_id)


@router.patch("/growth/config/{contexto}")
async def patch_growth_config(
    contexto: str,
    payload: dict,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Aplica ajuste manual em config de CTA (Growth-03). Requer is_owner."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário do tenant pode alterar configurações de growth.")
    from ia.growth_service import IAGrowthService
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
    return await IAGrowthService.atualizar_config(session, tenant_id, contexto, usuario_id, payload)


@router.post("/growth/config/{contexto}/reverter")
async def reverter_growth_config(
    contexto: str,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Reverte config do contexto para defaults de fábrica (Growth-03)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário do tenant pode reverter configurações de growth.")
    from ia.growth_service import IAGrowthService
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
    return await IAGrowthService.reverter_config(session, tenant_id, contexto, usuario_id)


@router.get("/growth/config/historico")
async def get_growth_config_historico(
    contexto: Optional[str] = Query(None),
    periodo_dias: int = Query(30, ge=1, le=90),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Histórico auditável de alterações em configurações de CTA (Growth-04)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário do tenant pode visualizar o histórico de growth.")
    from ia.growth_service import IAGrowthService
    return await IAGrowthService.listar_historico(session, tenant_id, contexto, periodo_dias)


@router.get("/growth/sugestoes")
async def get_growth_sugestoes(
    periodo_dias: int = Query(30, ge=7, le=90),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Sugestões persistidas de otimização de CTAs (Growth-05/06)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário do tenant pode visualizar sugestões de growth.")
    from ia.growth_service import IAGrowthService
    return await IAGrowthService.gerar_sugestoes_otimizacao(session, tenant_id, periodo_dias)


@router.post("/growth/sugestoes/{sugestao_id}/aplicar")
async def aplicar_growth_sugestao(
    sugestao_id: str,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Aplica sugestão de otimização e atualiza config (Growth-06)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário do tenant pode aplicar sugestões.")
    from ia.growth_service import IAGrowthService
    usuario_id = uuid.UUID(claims["sub"]) if claims.get("sub") else None
    try:
        return await IAGrowthService.aplicar_sugestao(session, tenant_id, sugestao_id, usuario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/growth/sugestoes/{sugestao_id}/ignorar")
async def ignorar_growth_sugestao(
    sugestao_id: str,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Marca sugestão como ignorada (Growth-06)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário do tenant pode ignorar sugestões.")
    from ia.growth_service import IAGrowthService
    usuario_id = uuid.UUID(claims["sub"]) if claims.get("sub") else None
    try:
        return await IAGrowthService.ignorar_sugestao(session, tenant_id, sugestao_id, usuario_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/growth/sugestoes/desempenho")
async def get_growth_sugestoes_desempenho(
    periodo_dias: int = Query(30, ge=7, le=90),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Avalia resultado das sugestões aplicadas vs. métricas reais (Growth-07)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário do tenant pode visualizar o desempenho das sugestões.")
    from ia.growth_service import IAGrowthService
    return await IAGrowthService.avaliar_resultado_sugestoes(session, tenant_id, periodo_dias)


@router.get("/growth/experimentos", response_model=list[IAGrowthExperimentoSchema])
async def listar_experimentos(
    contexto: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Lista experimentos de growth do tenant (Growth-08)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário pode gerir experimentos.")
    from ia.growth_service import IAGrowthService
    return await IAGrowthService.listar_experimentos(session, tenant_id, contexto, status)


@router.post("/growth/experimentos", response_model=IAGrowthExperimentoSchema, status_code=201)
async def criar_experimento(
    body: IAGrowthExperimentoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Cria um novo experimento A/B para um contexto (Growth-08)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário pode criar experimentos.")
    from ia.growth_service import IAGrowthService
    return await IAGrowthService.criar_experimento(
        session, tenant_id, body.contexto, body.nome, body.variantes
    )


@router.post("/growth/experimentos/auto-gerar", response_model=IAGrowthExperimentoSchema, status_code=201)
async def auto_gerar_experimento(
    body: IAGrowthExperimentoAutoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Gera automaticamente um experimento com variante LLM + Heurísticas (IA-Growth-11)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário pode criar experimentos.")
    
    from ia.growth_service import IAGrowthService
    
    # Simula dados de contexto básicos para a geração
    # Em um fluxo real, isso viria de métricas reais do tenant
    dados_contexto = {
        "roi_valor": 1250.0,
        "percentual_uso": 85.0
    }
    
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
    
    variantes = await IAGrowthService.gerar_variacoes_cta(
        session, tenant_id, body.contexto, dados_contexto, usuario_id
    )
    
    # Formata para o formato esperado pelo criar_experimento
    variantes_data = []
    for i, v in enumerate(variantes):
        variantes_data.append({
            "nome": f"Variante {chr(65+i)} ({v['origem']})",
            "peso": 1.0,
            "cta": v,
            "origem": v["origem"]
        })
        
    return await IAGrowthService.criar_experimento(
        session, tenant_id, body.contexto, body.nome, variantes_data
    )


@router.post("/growth/experimentos/{experimento_id}/finalizar")
async def finalizar_experimento(
    experimento_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Finaliza um experimento ativo (Growth-08)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário pode finalizar experimentos.")
    from ia.growth_service import IAGrowthService
    return await IAGrowthService.finalizar_experimento(session, experimento_id)


@router.get("/growth/experimentos/{experimento_id}/resultado", response_model=IAGrowthExperimentoResultado)
async def get_resultado_experimento(
    experimento_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Calcula e retorna os resultados de um experimento (Growth-08)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário pode ver resultados de experimentos.")
    from ia.growth_service import IAGrowthService
    return await IAGrowthService.calcular_resultado_experimento(session, experimento_id)


@router.get("/growth/copy/performance", response_model=IAGrowthCopyPerformanceResponse)
async def get_growth_copy_performance(
    contexto: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Retorna performance por tipo de abordagem de copy (Growth-10)."""
    if not claims.get("is_owner"):
        raise HTTPException(status_code=403, detail="Apenas o proprietário pode ver performance de copy.")
    from ia.growth_service import IAGrowthService
    perf = await IAGrowthService.calcular_performance_copy(session, tenant_id, contexto)
    
    melhor = None
    if perf:
        melhor = max(perf, key=lambda x: x["conversao"])["tipo_abordagem"]
        
    return {
        "contexto": contexto or "todos",
        "performance": perf,
        "melhor_abordagem": melhor
    }


@router.post("/growth/experimentos/track-click")
async def track_click_experimento(
    payload: dict,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Registra clique em um CTA de experimento (Growth-08)."""
    from ia.growth_service import IAGrowthService
    experimento_id = payload.get("experimento_id")
    variante_id = payload.get("variante_id")
    contexto = payload.get("contexto")
    usuario_id = uuid.UUID(claims["sub"]) if claims.get("sub") else None
    
    if not experimento_id or not variante_id:
        raise HTTPException(status_code=400, detail="experimento_id e variante_id são obrigatórios.")
        
    await IAGrowthService.registrar_click_experimento(
        session,
        tenant_id,
        usuario_id,
        uuid.UUID(experimento_id),
        uuid.UUID(variante_id),
        contexto,
        churn_risk_score=payload.get("churn_risk_score"),
        churn_risk_level=payload.get("churn_risk_level"),
    )
    return {"status": "ok"}


@router.get("/financeiro/plano-acao", response_model=IAPlanoAcaoResponse)
async def get_plano_acao(
    safra_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    tenant_id: uuid.UUID = Depends(get_current_tenant)
):
    """Retorna o plano de ação automático para recuperação financeira (Step 207)."""
    from ia.essential_service import IAEssentialService
    safra_id = await IAEssentialService.resolve_safra_id(db, tenant_id, safra_id)
    if not safra_id:
        raise HTTPException(status_code=422, detail="Safra não informada e nenhuma safra ativa encontrada.")
        
    from ia.plano_acao_service import IAPlanoAcaoService
    service = IAPlanoAcaoService(db, tenant_id)
    return await service.gerar_plano_recuperacao(safra_id)


# ── Estratégia de Compra por IA (Step 168) ───────────────────────────────────

class EstrategiaCompraPayload(BaseModel):
    item_id: uuid.UUID
    solicitacao_id: uuid.UUID


class EstrategiaCompraResponse(BaseModel):
    resumo: str
    estrategia: str
    justificativas: list[str]
    nivel_confianca: float
    fonte: str
    ia_disponivel: bool
    limite_atingido: bool


@router.post("/compras/estrategia", response_model=EstrategiaCompraResponse)
async def gerar_estrategia_compra(
    body: EstrategiaCompraPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Gera recomendação estratégica de compra com base no contexto completo do item (Step 168)."""
    from ia.compras_estrategia_service import ContextoCompra, gerar_estrategia_compra as _gerar
    from operacional.services.compras_service import ComprasService

    svc = ComprasService(session, tenant_id)

    # Monta contexto com dados dos steps anteriores
    ctx = ContextoCompra()

    # Nome do item
    try:
        from core.cadastros.produtos.models import Produto
        from sqlalchemy import select as sa_select
        p = (await session.execute(sa_select(Produto).where(Produto.id == body.item_id))).scalar_one_or_none()
        ctx.item_nome = p.nome if p else str(body.item_id)
    except Exception:
        ctx.item_nome = str(body.item_id)

    # Solicitação (quantidade e unidade)
    try:
        from operacional.models.compras import SolicitacaoCompra
        from sqlalchemy import select as sa_select
        sol = (await session.execute(
            sa_select(SolicitacaoCompra).where(
                SolicitacaoCompra.id == body.solicitacao_id,
                SolicitacaoCompra.tenant_id == tenant_id
            )
        )).scalar_one_or_none()
        if sol:
            ctx.solicitacao_id = str(body.solicitacao_id)
            ctx.quantidade = sol.quantidade_solicitada
            ctx.unidade = sol.unidade
    except Exception:
        pass

    # Preço ideal
    try:
        ideal = await svc.obter_preco_ideal(body.item_id)
        if ideal:
            ctx.preco_minimo = ideal.get("preco_minimo_referencia")
            ctx.preco_ideal = ideal.get("preco_ideal")
            ctx.preco_maximo = ideal.get("preco_maximo_recomendado")
    except Exception:
        pass

    # Melhor fornecedor
    try:
        rec = await svc.obter_melhor_fornecedor(body.item_id)
        if rec:
            ctx.melhor_fornecedor = rec.get("fornecedor_nome")
            ctx.score_melhor = rec.get("score")
            ctx.ultimo_preco = rec.get("ultimo_preco")
            ctx.preco_medio_historico = rec.get("preco_medio")
            ctx.qtd_compras_historicas = rec.get("qtd_compras", 0)
    except Exception:
        pass

    # Consistência do melhor fornecedor
    try:
        consistencia = await svc.obter_consistencia_fornecedores(body.item_id)
        if consistencia and ctx.melhor_fornecedor:
            match = next((c for c in consistencia if c.get("fornecedor_nome") == ctx.melhor_fornecedor), None)
            if match:
                ctx.consistencia_melhor_fornecedor = match.get("classificacao")
    except Exception:
        pass

    # Cotações atuais da solicitação
    try:
        cotacoes = await svc.listar_cotacoes(body.solicitacao_id)
        ctx.cotacoes = [
            {
                "fornecedor_nome": c.fornecedor_nome,
                "valor_unitario": float(c.valor_unitario),
                "prazo_entrega_dias": c.prazo_entrega_dias,
            }
            for c in (cotacoes or [])
        ]
    except Exception:
        pass

    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
    tier = await _get_tier(tenant_id, session, claims)

    resultado = await _gerar(
        ctx, tenant_id=tenant_id, session=session, tier=tier,
        usuario_id=usuario_id, item_id=body.item_id,
    )
    await session.commit()

    return EstrategiaCompraResponse(
        resumo=resultado.resumo,
        estrategia=resultado.estrategia,
        justificativas=resultado.justificativas,
        nivel_confianca=resultado.nivel_confianca,
        fonte=resultado.fonte,
        ia_disponivel=resultado.ia_disponivel,
        limite_atingido=resultado.limite_atingido,
    )


# ── Histórico de Recomendações IA (Step 169) ─────────────────────────────────

class RecomendacaoHistoricoItem(BaseModel):
    id: str
    estrategia: str
    resumo: str
    justificativas: list[str]
    nivel_confianca: float
    fonte: str
    limite_atingido: bool
    feedback_util: Optional[bool] = None
    feedback_comentario: Optional[str] = None
    created_at: datetime


# ── Métricas de Qualidade (Step 171) ─────────────────────────────────────────

class MetricasRecomendacoesResponse(BaseModel):
    total_recomendacoes: int
    avaliadas: int
    uteis: int
    nao_uteis: int
    taxa_utilidade: float


@router.get("/compras/recomendacoes/metricas", response_model=MetricasRecomendacoesResponse)
async def get_metricas_recomendacoes(
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    fonte: Optional[str] = None,
    estrategia: Optional[str] = None,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Retorna métricas de qualidade das recomendações de IA (Step 171)."""
    from ia.models import IAComprasRecomendacao
    from sqlalchemy import select as sa_select, func, and_

    conditions = [IAComprasRecomendacao.tenant_id == tenant_id]
    if data_inicio:
        conditions.append(IAComprasRecomendacao.created_at >= data_inicio)
    if data_fim:
        conditions.append(IAComprasRecomendacao.created_at <= data_fim)
    if fonte:
        conditions.append(IAComprasRecomendacao.fonte == fonte)
    if estrategia:
        conditions.append(IAComprasRecomendacao.estrategia == estrategia)

    stmt = sa_select(
        func.count(IAComprasRecomendacao.id).label("total"),
        func.count(IAComprasRecomendacao.feedback_util).label("avaliadas"),
        func.sum(
            func.cast(IAComprasRecomendacao.feedback_util == True, sa_Integer)
        ).label("uteis"),
        func.sum(
            func.cast(IAComprasRecomendacao.feedback_util == False, sa_Integer)
        ).label("nao_uteis"),
    ).where(and_(*conditions))

    row = (await session.execute(stmt)).one()
    total = int(row.total or 0)
    avaliadas = int(row.avaliadas or 0)
    uteis = int(row.uteis or 0)
    nao_uteis = int(row.nao_uteis or 0)
    taxa = round((uteis / avaliadas * 100), 1) if avaliadas > 0 else 0.0

    return MetricasRecomendacoesResponse(
        total_recomendacoes=total,
        avaliadas=avaliadas,
        uteis=uteis,
        nao_uteis=nao_uteis,
        taxa_utilidade=taxa,
    )


class FeedbackRecomendacaoPayload(BaseModel):
    feedback_util: bool
    feedback_comentario: Optional[str] = None


@router.patch("/compras/recomendacoes/{rec_id}/feedback", response_model=RecomendacaoHistoricoItem)
async def registrar_feedback_recomendacao(
    rec_id: uuid.UUID,
    body: FeedbackRecomendacaoPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session_with_tenant),
):
    """Registra avaliação do usuário sobre a recomendação de IA (Step 170)."""
    from ia.models import IAComprasRecomendacao
    from sqlalchemy import select as sa_select

    logger.bind(
        event="registrar_feedback_recomendacao_search",
        rec_id=str(rec_id),
        tenant_id=str(tenant_id),
    ).debug("Buscando recomendação para feedback")

    rec = (await session.execute(
        sa_select(IAComprasRecomendacao).where(
            IAComprasRecomendacao.id == rec_id,
            IAComprasRecomendacao.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()

    if not rec:
        logger.bind(
            event="registrar_feedback_recomendacao_not_found",
            rec_id=str(rec_id),
            tenant_id=str(tenant_id),
        ).warning("Recomendação não encontrada para feedback")
        raise HTTPException(status_code=404, detail="Recomendação não encontrada")

    rec.feedback_util = body.feedback_util
    rec.feedback_comentario = body.feedback_comentario
    rec.feedback_at = datetime.now(timezone.utc)

    # Estabilização: garante flush/commit/refresh para persistência imediata e visível
    await session.flush()
    await session.commit()
    await session.refresh(rec)

    return RecomendacaoHistoricoItem(
        id=str(rec.id),
        estrategia=rec.estrategia,
        resumo=rec.resumo,
        justificativas=rec.justificativas or [],
        nivel_confianca=rec.nivel_confianca,
        fonte=rec.fonte,
        limite_atingido=rec.limite_atingido,
        feedback_util=rec.feedback_util,
        feedback_comentario=rec.feedback_comentario,
        created_at=rec.created_at,
    )


# ── Feedbacks Negativos (Step 173) ───────────────────────────────────────────

class FeedbackNegativoItem(BaseModel):
    id: str
    created_at: datetime
    estrategia: str
    fonte: str
    resumo: str
    feedback_comentario: Optional[str] = None
    solicitacao_id: Optional[str] = None
    feedback_revisado: bool = False
    feedback_revisado_at: Optional[datetime] = None
    feedback_revisao_observacao: Optional[str] = None


@router.get("/compras/recomendacoes/feedbacks-negativos", response_model=list[FeedbackNegativoItem])
async def listar_feedbacks_negativos(
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    estrategia: Optional[str] = None,
    fonte: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Retorna recomendações avaliadas como não úteis para diagnóstico operacional (Step 173)."""
    from ia.models import IAComprasRecomendacao
    from sqlalchemy import select as sa_select, and_

    conditions = [
        IAComprasRecomendacao.tenant_id == tenant_id,
        IAComprasRecomendacao.feedback_util == False,  # noqa: E712
    ]
    if data_inicio:
        conditions.append(IAComprasRecomendacao.feedback_at >= data_inicio)
    if data_fim:
        conditions.append(IAComprasRecomendacao.feedback_at <= data_fim)
    if estrategia:
        conditions.append(IAComprasRecomendacao.estrategia == estrategia)
    if fonte:
        conditions.append(IAComprasRecomendacao.fonte == fonte)

    stmt = (
        sa_select(IAComprasRecomendacao)
        .where(and_(*conditions))
        .order_by(
            desc(IAComprasRecomendacao.feedback_at),
            desc(IAComprasRecomendacao.created_at),
        )
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        FeedbackNegativoItem(
            id=str(r.id),
            created_at=r.created_at,
            estrategia=r.estrategia,
            fonte=r.fonte,
            resumo=r.resumo,
            feedback_comentario=r.feedback_comentario,
            solicitacao_id=str(r.solicitacao_id) if r.solicitacao_id else None,
            feedback_revisado=r.feedback_revisado or False,
            feedback_revisado_at=r.feedback_revisado_at,
            feedback_revisao_observacao=r.feedback_revisao_observacao,
        )
        for r in rows
    ]


# ── Controle de Versão do Prompt (Step 177) ──────────────────────────────────

CONTEXTO_COMPRAS_ESTRATEGIA = "COMPRAS_ESTRATEGIA"

PROMPT_HARDCODED_DEFAULT = """Você é um especialista em compras agrícolas no mercado brasileiro.

Com base APENAS nos dados abaixo, gere uma estratégia de compra objetiva.

REGRAS OBRIGATÓRIAS:
- Não invente preços ou fornecedores fora dos dados
- Estratégia deve ser exatamente uma de: "Comprar agora", "Negociar", "Aguardar"
- Justificativas: máximo 4 itens diretos e acionáveis
- nivel_confianca: número entre 0 e 1 (ex: 0.85)
- Tom: direto, prático, voltado ao gestor de compras rural

{feedback_block}
DADOS:
{dados}

Responda em JSON com exatamente este formato:
{{
  "resumo": "frase única objetiva sobre a decisão",
  "estrategia": "Comprar agora" | "Negociar" | "Aguardar",
  "justificativas": ["motivo 1", "motivo 2", "motivo 3"],
  "nivel_confianca": 0.85
}}"""


class PromptVersaoResponse(BaseModel):
    id: str
    contexto: str
    versao: str
    conteudo: str
    ativo: bool
    observacao: Optional[str] = None
    created_at: datetime
    is_global: bool


class PromptVersaoCreate(BaseModel):
    contexto: str = CONTEXTO_COMPRAS_ESTRATEGIA
    versao: str
    conteudo: str
    observacao: Optional[str] = None


class PromptVersaoHistoricoResponse(BaseModel):
    id: str
    prompt_versao_id: str
    tenant_id: Optional[str] = None
    usuario_id: Optional[str] = None
    usuario_nome: Optional[str] = None
    tipo_evento: str
    valor_anterior: Optional[dict] = None
    valor_novo: Optional[dict] = None
    created_at: datetime


def _snapshot_prompt_versao(versao) -> dict:
    return {
        "versao": versao.versao,
        "contexto": versao.contexto,
        "ativo": bool(versao.ativo),
        "observacao": versao.observacao,
    }


async def _registrar_historico_prompt(
    session: AsyncSession,
    versao,
    tipo_evento: str,
    usuario_id: Optional[uuid.UUID] = None,
    valor_anterior: Optional[dict] = None,
    valor_novo: Optional[dict] = None,
) -> None:
    from ia.models import IAPromptVersaoHistorico

    session.add(
        IAPromptVersaoHistorico(
            id=uuid.uuid4(),
            tenant_id=versao.tenant_id,
            prompt_versao_id=versao.id,
            usuario_id=usuario_id,
            tipo_evento=tipo_evento,
            valor_anterior=valor_anterior,
            valor_novo=valor_novo,
        )
    )


@router.get("/prompts/versoes", response_model=list[PromptVersaoResponse])
async def listar_versoes_prompt(
    contexto: str = Query(CONTEXTO_COMPRAS_ESTRATEGIA),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Lista versões do prompt para o contexto (tenant + globais) ordenadas por data (Step 177)."""
    from ia.models import IAPromptVersao
    from sqlalchemy import select as sa_select, or_

    stmt = (
        sa_select(IAPromptVersao)
        .where(
            IAPromptVersao.contexto == contexto,
            or_(IAPromptVersao.tenant_id == tenant_id, IAPromptVersao.tenant_id.is_(None)),
        )
        .order_by(desc(IAPromptVersao.created_at))
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [
        PromptVersaoResponse(
            id=str(r.id),
            contexto=r.contexto,
            versao=r.versao,
            conteudo=r.conteudo,
            ativo=r.ativo,
            observacao=r.observacao,
            created_at=r.created_at,
            is_global=r.tenant_id is None,
        )
        for r in rows
    ]


@router.post("/prompts/versoes", response_model=PromptVersaoResponse, status_code=201)
async def criar_versao_prompt(
    body: PromptVersaoCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Cria nova versão do prompt (inativa por padrão) (Step 177)."""
    from ia.models import IAPromptVersao

    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None

    versao = IAPromptVersao(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        contexto=body.contexto,
        versao=body.versao,
        conteudo=body.conteudo,
        ativo=False,
        observacao=body.observacao,
        created_by=usuario_id,
    )
    session.add(versao)
    await _registrar_historico_prompt(
        session=session,
        versao=versao,
        tipo_evento="CRIADA",
        usuario_id=usuario_id,
        valor_anterior=None,
        valor_novo=_snapshot_prompt_versao(versao),
    )
    await session.commit()
    await session.refresh(versao)

    return PromptVersaoResponse(
        id=str(versao.id),
        contexto=versao.contexto,
        versao=versao.versao,
        conteudo=versao.conteudo,
        ativo=versao.ativo,
        observacao=versao.observacao,
        created_at=versao.created_at,
        is_global=False,
    )


@router.patch("/prompts/versoes/{versao_id}/ativar", response_model=PromptVersaoResponse)
async def ativar_versao_prompt(
    versao_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Ativa uma versão do prompt, desativando as demais do mesmo tenant/contexto (Step 177)."""
    from ia.models import IAPromptVersao
    from sqlalchemy import select as sa_select

    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None

    versao = (await session.execute(
        sa_select(IAPromptVersao).where(
            IAPromptVersao.id == versao_id,
            IAPromptVersao.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()

    if not versao:
        raise HTTPException(status_code=404, detail="Versão não encontrada")

    outras_ativas = list((await session.execute(
        sa_select(IAPromptVersao)
        .where(
            IAPromptVersao.tenant_id == tenant_id,
            IAPromptVersao.contexto == versao.contexto,
            IAPromptVersao.id != versao_id,
            IAPromptVersao.ativo == True,  # noqa: E712
        )
    )).scalars().all())

    for outra in outras_ativas:
        valor_anterior_outra = _snapshot_prompt_versao(outra)
        outra.ativo = False
        session.add(outra)
        await _registrar_historico_prompt(
            session=session,
            versao=outra,
            tipo_evento="DESATIVADA",
            usuario_id=usuario_id,
            valor_anterior=valor_anterior_outra,
            valor_novo=_snapshot_prompt_versao(outra),
        )

    valor_anterior = _snapshot_prompt_versao(versao)
    versao.ativo = True
    session.add(versao)
    await _registrar_historico_prompt(
        session=session,
        versao=versao,
        tipo_evento="ATIVADA",
        usuario_id=usuario_id,
        valor_anterior=valor_anterior,
        valor_novo=_snapshot_prompt_versao(versao),
    )
    await session.commit()
    await session.refresh(versao)

    return PromptVersaoResponse(
        id=str(versao.id),
        contexto=versao.contexto,
        versao=versao.versao,
        conteudo=versao.conteudo,
        ativo=versao.ativo,
        observacao=versao.observacao,
        created_at=versao.created_at,
        is_global=versao.tenant_id is None,
    )


@router.get("/prompts/versoes/{versao_id}/historico", response_model=list[PromptVersaoHistoricoResponse])
async def listar_historico_versao_prompt(
    versao_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Lista histórico de eventos da versão do prompt ordenado por data desc (Step 178)."""
    from core.models.auth import Usuario
    from ia.models import IAPromptVersao, IAPromptVersaoHistorico
    from sqlalchemy import select as sa_select, or_

    versao = (await session.execute(
        sa_select(IAPromptVersao).where(
            IAPromptVersao.id == versao_id,
            or_(IAPromptVersao.tenant_id == tenant_id, IAPromptVersao.tenant_id.is_(None)),
        )
    )).scalar_one_or_none()

    if not versao:
        raise HTTPException(status_code=404, detail="Versão não encontrada")

    stmt = (
        sa_select(IAPromptVersaoHistorico, Usuario)
        .outerjoin(Usuario, Usuario.id == IAPromptVersaoHistorico.usuario_id)
        .where(IAPromptVersaoHistorico.prompt_versao_id == versao_id)
        .order_by(desc(IAPromptVersaoHistorico.created_at))
    )
    rows = (await session.execute(stmt)).all()

    return [
        PromptVersaoHistoricoResponse(
            id=str(hist.id),
            prompt_versao_id=str(hist.prompt_versao_id),
            tenant_id=str(hist.tenant_id) if hist.tenant_id else None,
            usuario_id=str(hist.usuario_id) if hist.usuario_id else None,
            usuario_nome=(usuario.nome_completo or usuario.username or usuario.email) if usuario else None,
            tipo_evento=hist.tipo_evento,
            valor_anterior=hist.valor_anterior,
            valor_novo=hist.valor_novo,
            created_at=hist.created_at,
        )
        for hist, usuario in rows
    ]


# ── Sugestões de Melhoria do Prompt (Step 176) ───────────────────────────────

_PALAVRAS_GENERICAS = {"genérico", "generico", "óbvio", "obvio", "sem detalhe", "vago", "raso", "superficial"}

_MENSAGENS_ESTRATEGIA: dict[str, tuple[str, str]] = {
    "Negociar": (
        "ESTRATEGIA_NEGOCIAR_EXCESSIVA",
        "Muitas recomendações 'Negociar' foram marcadas como não úteis.",
        "Ajustar o prompt para justificar melhor quando negociar em vez de comprar agora, "
        "incluindo critérios objetivos como margem acima do ideal e prazo disponível.",
    ),
    "Aguardar": (
        "ESTRATEGIA_AGUARDAR_EXCESSIVA",
        "Muitas recomendações 'Aguardar' foram marcadas como não úteis.",
        "Refinar o prompt para indicar 'Aguardar' apenas quando há evidência concreta de "
        "tendência de queda de preço ou sazonalidade favorável.",
    ),
    "Comprar agora": (
        "ESTRATEGIA_COMPRAR_AGORA_EXCESSIVA",
        "Muitas recomendações 'Comprar agora' foram marcadas como não úteis.",
        "Revisar o prompt para garantir que 'Comprar agora' só seja sugerido quando o preço "
        "está claramente dentro da faixa ideal e o fornecedor tem histórico consistente.",
    ),
}

_TIPO_SEM_COMENTARIO = "FEEDBACK_SEM_COMENTARIO"
_TIPO_GENERICO = "COMENTARIO_GENERICO"


class SugestaoPromptItem(BaseModel):
    tipo: str
    mensagem: str
    sugestao: str
    total_ocorrencias: int


@router.get("/compras/recomendacoes/sugestoes-prompt", response_model=list[SugestaoPromptItem])
async def get_sugestoes_prompt(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Gera sugestões determinísticas de melhoria do prompt com base nos feedbacks negativos (Step 176)."""
    from ia.models import IAComprasRecomendacao
    from sqlalchemy import select as sa_select, func, and_

    # Busca todos os feedbacks negativos do tenant
    stmt = sa_select(
        IAComprasRecomendacao.estrategia,
        IAComprasRecomendacao.feedback_comentario,
    ).where(
        IAComprasRecomendacao.tenant_id == tenant_id,
        IAComprasRecomendacao.feedback_util == False,  # noqa: E712
    )
    rows = (await session.execute(stmt)).all()

    if not rows:
        return []

    sugestoes: list[SugestaoPromptItem] = []

    # Regra 1 — estratégia com >= 3 feedbacks negativos
    contagem_estrategia: dict[str, int] = {}
    for r in rows:
        contagem_estrategia[r.estrategia] = contagem_estrategia.get(r.estrategia, 0) + 1

    for estrategia, total in sorted(contagem_estrategia.items(), key=lambda x: -x[1]):
        if total >= 3 and estrategia in _MENSAGENS_ESTRATEGIA:
            tipo, mensagem, sugestao = _MENSAGENS_ESTRATEGIA[estrategia]
            sugestoes.append(SugestaoPromptItem(tipo=tipo, mensagem=mensagem, sugestao=sugestao, total_ocorrencias=total))

    # Regra 2 — muitos feedbacks sem comentário (>= 3 ou > 50% dos negativos)
    sem_comentario = sum(1 for r in rows if not (r.feedback_comentario or "").strip())
    if sem_comentario >= 3 or (len(rows) > 0 and sem_comentario / len(rows) >= 0.5):
        sugestoes.append(SugestaoPromptItem(
            tipo=_TIPO_SEM_COMENTARIO,
            mensagem="Muitos feedbacks negativos não possuem comentário explicativo.",
            sugestao="Melhorar a clareza das justificativas no prompt para incentivar feedback mais detalhado dos usuários.",
            total_ocorrencias=sem_comentario,
        ))

    # Regra 3 — comentários com palavras genéricas recorrentes
    comentarios = [r.feedback_comentario.lower() for r in rows if r.feedback_comentario]
    palavras_encontradas: dict[str, int] = {}
    for comentario in comentarios:
        for palavra in _PALAVRAS_GENERICAS:
            if palavra in comentario:
                palavras_encontradas[palavra] = palavras_encontradas.get(palavra, 0) + 1

    total_genericos = sum(
        1 for comentario in comentarios
        if any(p in comentario for p in _PALAVRAS_GENERICAS)
    )
    if total_genericos >= 2:
        sugestoes.append(SugestaoPromptItem(
            tipo=_TIPO_GENERICO,
            mensagem="Comentários de feedback frequentemente mencionam que as recomendações são genéricas ou óbvias.",
            sugestao="Aumentar a especificidade do prompt: solicitar exemplos práticos, valores concretos e comparações diretas com o histórico.",
            total_ocorrencias=total_genericos,
        ))

    return sugestoes


# ── Resumo Executivo de Qualidade (Step 175) ─────────────────────────────────

class EstrategiaFeedbackNegativo(BaseModel):
    estrategia: str
    total: int


class QualidadeResumoResponse(BaseModel):
    total_recomendacoes: int
    avaliadas: int
    taxa_utilidade: float
    feedbacks_negativos: int
    feedbacks_pendentes_revisao: int
    feedbacks_revisados: int
    taxa_revisao: float
    estrategias_com_mais_feedback_negativo: list[EstrategiaFeedbackNegativo]


@router.get("/compras/recomendacoes/qualidade-resumo", response_model=QualidadeResumoResponse)
async def get_qualidade_resumo(
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    fonte: Optional[str] = None,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Resumo executivo de qualidade das recomendações de IA (Step 175)."""
    from ia.models import IAComprasRecomendacao
    from sqlalchemy import select as sa_select, func, and_, case

    conditions = [IAComprasRecomendacao.tenant_id == tenant_id]
    if data_inicio:
        conditions.append(IAComprasRecomendacao.created_at >= data_inicio)
    if data_fim:
        conditions.append(IAComprasRecomendacao.created_at <= data_fim)
    if fonte:
        conditions.append(IAComprasRecomendacao.fonte == fonte)

    # Agregações principais em uma query
    stmt = sa_select(
        func.count(IAComprasRecomendacao.id).label("total"),
        func.count(IAComprasRecomendacao.feedback_util).label("avaliadas"),
        func.sum(func.cast(IAComprasRecomendacao.feedback_util == True, sa_Integer)).label("uteis"),  # noqa: E712
        func.sum(func.cast(IAComprasRecomendacao.feedback_util == False, sa_Integer)).label("negativos"),  # noqa: E712
        func.sum(
            func.cast(
                and_(IAComprasRecomendacao.feedback_util == False, IAComprasRecomendacao.feedback_revisado == True),  # noqa: E712
                sa_Integer,
            )
        ).label("revisados"),
        func.sum(
            func.cast(
                and_(IAComprasRecomendacao.feedback_util == False, IAComprasRecomendacao.feedback_revisado == False),  # noqa: E712
                sa_Integer,
            )
        ).label("pendentes"),
    ).where(and_(*conditions))

    row = (await session.execute(stmt)).one()
    total = int(row.total or 0)
    avaliadas = int(row.avaliadas or 0)
    uteis = int(row.uteis or 0)
    negativos = int(row.negativos or 0)
    revisados = int(row.revisados or 0)
    pendentes = int(row.pendentes or 0)

    taxa_utilidade = round(uteis / avaliadas * 100, 1) if avaliadas > 0 else 0.0
    taxa_revisao = round(revisados / negativos * 100, 1) if negativos > 0 else 0.0

    # Estratégias com mais feedback negativo
    neg_conditions = [*conditions, IAComprasRecomendacao.feedback_util == False]  # noqa: E712
    stmt_est = (
        sa_select(
            IAComprasRecomendacao.estrategia,
            func.count(IAComprasRecomendacao.id).label("total"),
        )
        .where(and_(*neg_conditions))
        .group_by(IAComprasRecomendacao.estrategia)
        .order_by(desc("total"))
        .limit(5)
    )
    est_rows = (await session.execute(stmt_est)).all()

    return QualidadeResumoResponse(
        total_recomendacoes=total,
        avaliadas=avaliadas,
        taxa_utilidade=taxa_utilidade,
        feedbacks_negativos=negativos,
        feedbacks_pendentes_revisao=pendentes,
        feedbacks_revisados=revisados,
        taxa_revisao=taxa_revisao,
        estrategias_com_mais_feedback_negativo=[
            EstrategiaFeedbackNegativo(estrategia=r.estrategia, total=r.total)
            for r in est_rows
        ],
    )


# ── Revisão Manual de Feedback (Step 174) ────────────────────────────────────

class RevisaoFeedbackPayload(BaseModel):
    feedback_revisado: bool
    feedback_revisao_observacao: Optional[str] = None


@router.patch("/compras/recomendacoes/{rec_id}/revisao-feedback", response_model=FeedbackNegativoItem)
async def revisar_feedback_recomendacao(
    rec_id: uuid.UUID,
    body: RevisaoFeedbackPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Marca ou desmarca um feedback negativo como revisado, com observação opcional (Step 174)."""
    from ia.models import IAComprasRecomendacao
    from sqlalchemy import select as sa_select

    rec = (await session.execute(
        sa_select(IAComprasRecomendacao).where(
            IAComprasRecomendacao.id == rec_id,
            IAComprasRecomendacao.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()

    if not rec:
        raise HTTPException(status_code=404, detail="Recomendação não encontrada")

    rec.feedback_revisado = body.feedback_revisado
    rec.feedback_revisado_at = datetime.now(timezone.utc) if body.feedback_revisado else None
    rec.feedback_revisao_observacao = body.feedback_revisao_observacao
    session.add(rec)
    await session.commit()
    await session.refresh(rec)

    return FeedbackNegativoItem(
        id=str(rec.id),
        created_at=rec.created_at,
        estrategia=rec.estrategia,
        fonte=rec.fonte,
        resumo=rec.resumo,
        feedback_comentario=rec.feedback_comentario,
        solicitacao_id=str(rec.solicitacao_id) if rec.solicitacao_id else None,
        feedback_revisado=rec.feedback_revisado or False,
        feedback_revisado_at=rec.feedback_revisado_at,
        feedback_revisao_observacao=rec.feedback_revisao_observacao,
    )


@router.get("/compras/recomendacoes", response_model=list[RecomendacaoHistoricoItem])
async def listar_recomendacoes_compra(
    solicitacao_id: Optional[uuid.UUID] = None,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Retorna histórico de recomendações de estratégia de compra (Step 169)."""
    from ia.models import IAComprasRecomendacao
    from sqlalchemy import select as sa_select, desc

    stmt = (
        sa_select(IAComprasRecomendacao)
        .where(IAComprasRecomendacao.tenant_id == tenant_id)
        .order_by(desc(IAComprasRecomendacao.created_at))
        .limit(50)
    )
    if solicitacao_id:
        stmt = stmt.where(IAComprasRecomendacao.solicitacao_id == solicitacao_id)

    rows = (await session.execute(stmt)).scalars().all()
    return [
        RecomendacaoHistoricoItem(
            id=str(r.id),
            estrategia=r.estrategia,
            resumo=r.resumo,
            justificativas=r.justificativas or [],
            nivel_confianca=r.nivel_confianca,
            fonte=r.fonte,
            limite_atingido=r.limite_atingido,
            feedback_util=r.feedback_util,
            feedback_comentario=r.feedback_comentario,
            created_at=r.created_at,
        )
        for r in rows
    ]


# ── DRE Intelligence (Step 184) ──────────────────────────────────────────────

class DREAnalysisPayload(BaseModel):
    safra_id: uuid.UUID

class DREAnalysisResponse(BaseModel):
    resumo: str
    pontos_positivos: list[str]
    pontos_atencao: list[str]
    recomendacoes: list[str]
    nivel_confianca: float
    fonte: str
    ia_disponivel: bool
    limite_atingido: bool

@router.post("/financeiro/analise-dre", response_model=DREAnalysisResponse)
async def analisar_dre_safra_endpoint(
    body: DREAnalysisPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Analisa o resultado da safra usando IA para traduzir números em decisões (Step 184)."""
    from financeiro.services.lancamento_service import LancamentoService
    from ia.dre_intelligence_service import ContextoDRE, analisar_dre_safra as _analisar
    
    # 1. Obtém dados da DRE
    fin_svc = LancamentoService(session, tenant_id)
    dre = await fin_svc.gerar_dre(body.safra_id)
    
    # 2. Monta contexto
    ctx = ContextoDRE(
        receita_bruta=dre.receita_bruta,
        custos_operacionais=dre.custos_operacionais,
        resultado_operacional=dre.resultado_operacional,
        margem_percentual=dre.margem_percentual,
        breakdown_custos=[{"categoria": c.nome, "valor": c.valor} for c in dre.breakdown_custos],
        breakdown_receitas=[{"categoria": c.nome, "valor": c.valor} for c in dre.breakdown_receitas]
    )
    
    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None
    
    # 3. Chama serviço de IA
    resultado = await _analisar(
        ctx,
        tenant_id=tenant_id,
        session=session,
        usuario_id=usuario_id
    )
    
    # Commit usage registration
    await session.commit()
    
    return DREAnalysisResponse(
        resumo=resultado.resumo,
        pontos_positivos=resultado.pontos_positivos,
        pontos_atencao=resultado.pontos_atencao,
        recomendacoes=resultado.recomendacoes,
        nivel_confianca=resultado.nivel_confianca,
        fonte=resultado.fonte,
        ia_disponivel=resultado.ia_disponivel,
        limite_atingido=resultado.limite_atingido
    )


class DRESimulationResponse(BaseModel):
    impacto: str
    riscos: list[str]
    recomendacoes: list[str]
    nivel_confianca: float
    fonte: str
    ia_disponivel: bool
    limite_atingido: bool
class RecomendacaoCenarioResponse(BaseModel):
    cenario_recomendado_id: Optional[str] = None
    resumo: str
    justificativas: list[str]
    pontos_risco: list[str]
    nivel_confianca: float
    fonte: str
    ia_disponivel: bool
    limite_atingido: bool


class SafraIDPayload(BaseModel):
    safra_id: uuid.UUID


@router.post("/financeiro/simulacao", response_model=DRESimulationResponse)
async def analisar_simulacao_endpoint(
    payload: SimulacaoDREPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    from financeiro.services.lancamento_service import LancamentoService
    from ia.dre_intelligence_service import ContextoSimulacao, analisar_simulacao_dre

    svc = LancamentoService(session, tenant_id)
    
    # 1. Obtém a simulação numérica (base de dados real)
    sim = await svc.simular_dre(
        safra_id=payload.safra_id,
        receita_pct=payload.ajustes.receita_percentual,
        custos_pct=payload.ajustes.custos_percentual
    )
    
    # 2. Prepara contexto para IA
    ctx = ContextoSimulacao(
        receita_real=sim.receita_real,
        custos_real=sim.custos_real,
        resultado_real=sim.resultado_real,
        margem_real=sim.margem_real,
        receita_simulada=sim.receita_simulada,
        custos_simulados=sim.custos_simulados,
        resultado_simulado=sim.resultado_simulado,
        margem_simulada=sim.margem_simulada,
        ajuste_receita_pct=payload.ajustes.receita_percentual,
        ajuste_custos_pct=payload.ajustes.custos_percentual
    )
    
    # 3. Executa análise inteligente
    claims = getattr(session, "_claims", {}) if hasattr(session, "_claims") else {}
    usuario_id = claims.get("sub")
    if usuario_id:
        usuario_id = uuid.UUID(usuario_id)

    resultado = await analisar_simulacao_dre(
        ctx, tenant_id=tenant_id, session=session, usuario_id=usuario_id
    )
    
    # Commit usage registration
    await session.commit()
    
    return DRESimulationResponse(
        impacto=resultado.impacto,
        riscos=resultado.riscos,
        recomendacoes=resultado.recomendacoes,
        nivel_confianca=resultado.nivel_confianca,
        fonte=resultado.fonte,
        ia_disponivel=resultado.ia_disponivel,
        limite_atingido=resultado.limite_atingido
    )

@router.post("/financeiro/recomendar-cenario", response_model=RecomendacaoCenarioResponse)
async def recomendar_cenario_endpoint(
    payload: SafraIDPayload,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
    claims: dict = Depends(get_current_user_claims),
):
    from financeiro.services.lancamento_service import LancamentoService
    from financeiro.services.cenario_service import CenarioFinanceiroService
    from ia.dre_intelligence_service import (
        ContextoDRE, ContextoCenarios, recomendar_cenario_safra
    )

    # 1. Obtém DRE Real
    fin_svc = LancamentoService(session, tenant_id)
    dre = await fin_svc.gerar_dre(payload.safra_id)
    
    ctx_dre = ContextoDRE(
        receita_bruta=dre.receita_bruta,
        custos_operacionais=dre.custos_operacionais,
        resultado_operacional=dre.resultado_operacional,
        margem_percentual=dre.margem_percentual,
        breakdown_custos=[{"categoria": c.nome, "valor": c.valor} for c in dre.breakdown_custos],
        breakdown_receitas=[{"categoria": c.nome, "valor": c.valor} for c in dre.breakdown_receitas]
    )

    # 2. Obtém cenários salvos
    cen_svc = CenarioFinanceiroService(session, tenant_id)
    cenarios_lista = await cen_svc.listar_cenarios(payload.safra_id)
    
    cenarios_contexto = [
        {
            "id": str(c.id),
            "nome": c.nome,
            "receita_simulada": c.resultado_simulado / (c.margem_simulada / 100) if c.margem_simulada > 0 else 0, # Aproximação se não tiver campo direto
            "custos_simulados": (c.resultado_simulado / (c.margem_simulada / 100)) - c.resultado_simulado if c.margem_simulada > 0 else 0,
            "resultado_simulado": c.resultado_simulado,
            "margem_simulada": c.margem_simulada
        }
        for c in cenarios_lista
    ]
    
    # Nota: Como o model de cenário pode não ter receita/custo bruto salvo (conforme Step 186),
    # recalculamos a partir do resultado e margem salvos, ou usamos os percentuais se disponíveis.
    # Vamos conferir o model do cenário.

    ctx = ContextoCenarios(
        dre_real=ctx_dre,
        cenarios=cenarios_contexto
    )

    usuario_id_str = claims.get("sub")
    usuario_id = uuid.UUID(usuario_id_str) if usuario_id_str else None

    # 3. Chama serviço de recomendação
    resultado = await recomendar_cenario_safra(
        ctx,
        tenant_id=tenant_id,
        session=session,
        usuario_id=usuario_id
    )
    
    # 3.1 Marca o cenário recomendado no banco de dados para rastreio de score (Step 190)
    if resultado.cenario_recomendado_id:
        from financeiro.models.cenario import FinanceiroSafraCenario
        from sqlalchemy import update
        
        # Desmarca recomendações anteriores da mesma safra
        await session.execute(
            update(FinanceiroSafraCenario)
            .where(FinanceiroSafraCenario.safra_id == payload.safra_id)
            .values(recomendado_pela_ia=False)
        )
        
        # Marca o novo recomendado
        try:
            target_id = uuid.UUID(resultado.cenario_recomendado_id)
            await session.execute(
                update(FinanceiroSafraCenario)
                .where(FinanceiroSafraCenario.id == target_id)
                .values(recomendado_pela_ia=True)
            )
        except (ValueError, TypeError):
            logger.warning(f"ID de cenário recomendado inválido: {resultado.cenario_recomendado_id}")

    await session.commit()

class ScoreIAResponse(BaseModel):
    total_decisoes: int
    acertos: int
    parciais: int
    erros: int
    taxa_acerto: float
    taxa_erro: float
    status: str

@router.get("/financeiro/score", response_model=ScoreIAResponse)
async def obter_score_ia_endpoint(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Retorna o score de confiabilidade da IA (Step 190)."""
    from ia.dre_intelligence_service import _calcular_score_ia
    res = await _calcular_score_ia(tenant_id, session)
    return res


# ── Histórico de Alertas e Auditoria (Step 194) ──────────────────────────────

class AlertaHistoricoResponse(BaseModel):
    id: uuid.UUID
    tipo_alerta: str
    titulo: str
    mensagem: str
    gravidade: str
    parametros_json: Optional[dict] = None
    visualizado_em: Optional[datetime] = None
    acao_executada: bool
    acao_executada_em: Optional[datetime] = None
    ignorado: bool
    ignorado_em: Optional[datetime] = None
    created_at: datetime


@router.get("/alertas/historico", response_model=list[AlertaHistoricoResponse])
async def listar_historico_alertas(
    safra_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Lista o histórico de alertas gerados pela IA e interações do usuário (Step 194)."""
    from ia.models import IAAlertaHistorico
    from sqlalchemy import select, desc, and_
    
    conditions = [IAAlertaHistorico.tenant_id == tenant_id]
    if safra_id:
        conditions.append(IAAlertaHistorico.safra_id == safra_id)
        
    stmt = (
        select(IAAlertaHistorico)
        .where(and_(*conditions))
        .order_by(desc(IAAlertaHistorico.created_at))
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    
    return [
        AlertaHistoricoResponse(
            id=r.id,
            tipo_alerta=r.tipo_alerta,
            titulo=r.titulo,
            mensagem=r.mensagem,
            gravidade=r.gravidade,
            parametros_json=r.parametros_json,
            visualizado_em=r.visualizado_em,
            acao_executada=r.acao_executada,
            acao_executada_em=r.acao_executada_em,
            ignorado=r.ignorado,
            ignorado_em=r.ignorado_em,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.patch("/alertas/{alerta_id}/visualizado", status_code=204)
async def marcar_alerta_visualizado(
    alerta_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Registra que o usuário visualizou o alerta (Step 194)."""
    from ia.models import IAAlertaHistorico
    from sqlalchemy import update
    
    stmt = (
        update(IAAlertaHistorico)
        .where(IAAlertaHistorico.id == alerta_id, IAAlertaHistorico.tenant_id == tenant_id)
        .values(visualizado_em=datetime.now(timezone.utc))
    )
    res = await session.execute(stmt)
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    await session.commit()
    return None


@router.patch("/alertas/{alerta_id}/executado", status_code=204)
async def marcar_alerta_executado(
    alerta_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Registra que o usuário executou a ação sugerida pelo alerta (Step 194)."""
    from ia.models import IAAlertaHistorico
    from sqlalchemy import update
    
    stmt = (
        update(IAAlertaHistorico)
        .where(IAAlertaHistorico.id == alerta_id, IAAlertaHistorico.tenant_id == tenant_id)
        .values(
            acao_executada=True,
            acao_executada_em=datetime.now(timezone.utc)
        )
    )
    res = await session.execute(stmt)
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    await session.commit()
    return None


@router.patch("/alertas/{alerta_id}/ignorado", status_code=204)
async def marcar_alerta_ignorado(
    alerta_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Registra que o usuário ignorou o alerta (Step 194)."""
    from ia.models import IAAlertaHistorico
    from sqlalchemy import update
    
    stmt = (
        update(IAAlertaHistorico)
        .where(IAAlertaHistorico.id == alerta_id, IAAlertaHistorico.tenant_id == tenant_id)
        .values(
            ignorado=True,
            ignorado_em=datetime.now(timezone.utc)
        )
    )
    res = await session.execute(stmt)
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    await session.commit()
    return None

# ── Resumo Diário Inteligente (Step 198) ───────────────────────────────────

@router.get("/financeiro/resumo-diario", response_model=ResumoDiarioResponse)
async def get_resumo_diario(
    safra_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session),
):
    """Retorna o resumo consolidado diário da safra com alertas e saúde financeira (Step 198)."""
    svc = ResumoDiarioService(session, tenant_id)
    return await svc.obter_resumo(safra_id)

# ── Ações Assistidas (Step 201) ──────────────────────────────────────────────

@router.post("/acoes-assistidas/registrar", response_model=AcaoAssistidaResponse)
async def registrar_acao_assistida(
    payload: RegistrarAcaoAssistidaPayload,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
):
    """Registra o início de uma ação assistida pela IA."""
    usuario_id = uuid.UUID(claims["sub"]) if "sub" in claims else None
    
    acao = await AcaoAssistidaService.registrar_acao(
        session=session,
        tenant_id=tenant_id,
        usuario_id=usuario_id,
        origem=payload.origem,
        origem_id=payload.origem_id,
        tipo_acao=payload.tipo_acao,
        parametros_json=payload.parametros_json
    )
    
    await session.commit()
    return {"id": acao.id, "status": "registrada"}


@router.patch("/acoes-assistidas/{id}/concluir")
async def concluir_acao_assistida(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Marca uma ação assistida como concluída pelo usuário."""
    sucesso = await AcaoAssistidaService.concluir_acao(
        session=session,
        acao_id=id,
        tenant_id=tenant_id
    )
    
    if not sucesso:
        raise HTTPException(status_code=404, detail="Ação assistida não encontrada.")
        
    await session.commit()
    return {"status": "concluida"}


@router.get("/acoes-assistidas/metricas", response_model=MetricasAcaoAssistidaResponse)
async def obter_metricas_acoes_assistidas(
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Retorna métricas de eficiência das ações assistidas do Copiloto."""
    return await AcaoAssistidaService.obter_metricas(session, tenant_id)

@router.get("/performance/dashboard", response_model=IAPerformanceDashboardResponse)
async def obter_dashboard_performance_ia(
    session: AsyncSession = Depends(get_session),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
):
    """Consolida métricas de performance e ROI da IA para o dashboard."""
    return await IAPerformanceService.get_dashboard_metrics(session, tenant_id)

@router.get("/autopilot/config", response_model=AutopilotConfigResponse)
async def get_autopilot_config(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    """Retorna as configurações de autopilot do tenant (Step 210)."""
    config = await IAAutopilotService.get_config(session, tenant_id)
    return AutopilotConfigResponse(
        ativo=config.ativo,
        autopilot_enabled=getattr(config, "autopilot_enabled", config.ativo),
        nivel_autonomia=config.nivel_autonomia,
        tipos_permitidos=config.tipos_permitidos,
        limite_impacto_percentual=config.limite_impacto_percentual,
        updated_at=config.updated_at
    )

@router.patch("/autopilot/config", response_model=AutopilotConfigResponse)
async def update_autopilot_config(
    body: AutopilotConfigUpdate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: AsyncSession = Depends(get_session)
):
    """Atualiza as configurações de autopilot do tenant (Step 210)."""
    updates = body.dict(exclude_unset=True)
    config = await IAAutopilotService.update_config(session, tenant_id, updates)
    return AutopilotConfigResponse(
        ativo=config.ativo,
        autopilot_enabled=getattr(config, "autopilot_enabled", config.ativo),
        nivel_autonomia=config.nivel_autonomia,
        tipos_permitidos=config.tipos_permitidos,
        limite_impacto_percentual=config.limite_impacto_percentual,
        updated_at=config.updated_at
    )

@router.get("/growth/autopilot/status", response_model=IAGrowthAutopilotStatusResponse)
async def get_growth_autopilot_status(
    periodo_dias: int = Query(30, ge=1, le=90),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Retorna status, auditoria recente e impacto estimado do Autopilot de Growth."""
    is_owner = claims.get("role") == "owner" or claims.get("is_owner") is True or claims.get("role") == "admin"
    if not is_owner:
        raise HTTPException(status_code=403, detail="Acesso restrito a proprietários e administradores do tenant.")

    from ia.growth_service import IAGrowthService
    resultado = await IAGrowthService.get_status_autopilot(session, tenant_id, periodo_dias)
    return IAGrowthAutopilotStatusResponse(**resultado)
@router.get("/growth/personas/performance", response_model=IAGrowthPersonasPerformanceResponse)
async def get_performance_personas(
    periodo_dias: int = Query(30, ge=1, le=90),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """
    Retorna a performance de conversão segmentada por persona (Growth-13).
    Apenas acessível por owners do tenant.
    """
    # Verifica se é owner (pode vir via role ou claims específicas do sistema)
    is_owner = claims.get("role") == "owner" or claims.get("is_owner") is True
    if not is_owner:
        raise HTTPException(status_code=403, detail="Acesso restrito a proprietários do tenant.")

    from ia.growth_service import IAGrowthService
    return await IAGrowthService.get_dashboard_personas(session, tenant_id, periodo_dias)


@router.get("/growth/churn/performance", response_model=IAGrowthChurnDashboardResponse)
async def get_performance_churn(
    periodo_dias: int = Query(30, ge=1, le=90),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Retorna consolidado de risco de churn e impacto de CTAs preventivos (IA-Growth-15)."""
    is_owner = claims.get("role") == "owner" or claims.get("is_owner") is True
    if not is_owner:
        raise HTTPException(status_code=403, detail="Acesso restrito a proprietários do tenant.")

    from ia.growth_service import IAGrowthService
    return await IAGrowthService.get_dashboard_churn(session, tenant_id, periodo_dias)


@router.get("/growth/oportunidades", response_model=IAGrowthOportunidadesResponse)
async def get_oportunidades_receita(
    periodo_dias: int = Query(30, ge=7, le=90),
    limite: int = Query(20, ge=1, le=100),
    persona: Optional[str] = Query(None),
    plano: Optional[str] = Query(None),
    contexto: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Retorna oportunidades priorizadas de revenue intelligence (IA-Growth-18)."""
    is_privileged = claims.get("role") in {"owner", "admin"} or claims.get("is_owner") is True
    if not is_privileged:
        raise HTTPException(status_code=403, detail="Acesso restrito a proprietários e administradores do tenant.")

    from ia.growth_service import IAGrowthService

    resultado = await IAGrowthService.get_dashboard_oportunidades(
        session,
        tenant_id,
        periodo_dias=periodo_dias,
        limite=limite,
        persona=persona,
        plano=plano,
        contexto=contexto,
        categoria=categoria,
    )
    return IAGrowthOportunidadesResponse(**resultado)


@router.get("/growth/assistente-comercial/contexto", response_model=IAGrowthAssistenteContextoResponse)
async def get_assistente_comercial_contexto(
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Retorna contexto comercial consultivo para o assistente de IA-Growth-17."""
    usuario_id = uuid.UUID(claims["sub"]) if claims.get("sub") else None
    visao_completa = IACommercialAssistantService._is_privilegiado(claims)
    contexto = await IACommercialAssistantService.gerar_contexto_usuario(
        session,
        tenant_id,
        usuario_id,
        visao_completa=visao_completa,
    )
    return IAGrowthAssistenteContextoResponse(**contexto)


@router.post("/growth/assistente-comercial/mensagem", response_model=IAGrowthAssistenteMensagemResponse)
async def post_assistente_comercial_mensagem(
    payload: IAGrowthAssistenteMensagemRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_session),
):
    """Gera uma resposta consultiva e registra a interação do assistente comercial."""
    usuario_id = uuid.UUID(claims["sub"]) if claims.get("sub") else None
    visao_completa = IACommercialAssistantService._is_privilegiado(claims)

    contexto = (
        payload.contexto_atual.model_dump()
        if payload.contexto_atual is not None
        else None
    )
    resultado = await IACommercialAssistantService.gerar_recomendacao_conversacional(
        session,
        tenant_id,
        usuario_id,
        payload.mensagem_usuario,
        contexto_atual=contexto,
        visao_completa=visao_completa,
    )

    await session.commit()

    contexto_final = contexto or await IACommercialAssistantService.gerar_contexto_usuario(
        session,
        tenant_id,
        usuario_id,
        visao_completa=visao_completa,
    )
    return IAGrowthAssistenteMensagemResponse(
        resposta_ia=resultado["resposta_ia"],
        cta_sugerido=resultado["cta_sugerido"],
        cta_url=resultado.get("cta_url", ""),
        plano_recomendado=resultado["plano_recomendado"],
        acao_sugerida=resultado["acao_sugerida"],
        fonte=resultado["fonte"],
        tipo_oferta=resultado.get("tipo_oferta", "CONSULTIVO"),
        mensagem_oferta=resultado.get("mensagem_oferta", ""),
        beneficio_destacado=resultado.get("beneficio_destacado", ""),
        log_id=resultado.get("log_id"),
        contexto=IAGrowthAssistenteContextoResponse(**contexto_final),
    )
