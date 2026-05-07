from __future__ import annotations

import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class IAGrowthTipoOferta(str, Enum):
    SEM_INCENTIVO = "SEM_INCENTIVO"
    INCENTIVO_LEVE = "INCENTIVO_LEVE"
    INCENTIVO_FORTE = "INCENTIVO_FORTE"
    EDUCATIVO = "EDUCATIVO"
    CONSULTIVO = "CONSULTIVO"

class IAAcaoAssistidaHistoricoResponse(BaseModel):
    id: uuid.UUID
    origem: str
    tipo_acao: str
    concluida: bool
    created_at: str

class IAPerformanceDashboardResponse(BaseModel):
    metrics: Dict
    funil: Dict
    resumo_performance: str

class IAUpgradeRecomendacaoResponse(BaseModel):
    deve_recomendar: bool
    tipo: str
    mensagem: str
    roi_estimado: float
    economia_gerada: float
    plano_atual: str
    plano_recomendado: str

class IAPredicaoRiscoResponse(BaseModel):
    risco: str
    descricao: str
    impacto_estimado: float
    tempo_estimated: str
    acao_recomendada: str
    confianca: float
    tendencia_custo: float
    tendencia_receita: float

class IAEstresseFinanceiroResponse(BaseModel):
    nivel_risco: str
    descricao: str
    pior_cenario: Optional[Dict[str, Any]] = None
    todos_cenarios: List[Dict[str, Any]] = []
    acao_recomendada: str
    probabilidade: str

class IAActionItem(BaseModel):
    id: str
    tipo: str
    descricao: str
    impacto_estimado: str
    impacto_valor: float
    prioridade: int
    acao_sugerida: str
    parametros_json: Dict[str, Any]

class IAAutopilotActionExecutada(BaseModel):
    descricao: str
    tipo: str
    impacto: str

class IAPlanoAcaoResponse(BaseModel):
    nivel_risco: str
    resumo: str
    acoes: List[IAActionItem]
    data_geracao: datetime
    acoes_executadas_automaticamente: List[IAAutopilotActionExecutada] = []

class IAAutopilotMetricsResponse(BaseModel):
    total_acoes_automaticas: int
    impacto_financeiro_simulado_total: float
    impacto_medio_por_acao: float
    taxa_aprovacao_implicita: float
    taxa_reversao: float
    tempo_medio_ate_interacao_ms: float

class AcaoAssistidaResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    action_id: str
    tipo_acao: str
    origem: str
    concluida: bool
    created_at: datetime

class MetricasAcaoAssistidaResponse(BaseModel):
    total_acoes: int
    taxa_conversao: float
    impacto_total: float

class IAProgressoItem(BaseModel):
    atual: str
    melhoria: float
    status: str

class IAProgressoPerfil(BaseModel):
    atual: str
    anterior: str
    evoluiu: bool

class IAProgressoROI(BaseModel):
    total: str
    melhoria: float
    status: str

class IAProgressoData(BaseModel):
    tempo_decisao: IAProgressoItem
    taxa_execucao: IAProgressoItem
    roi: IAProgressoROI
    perfil: IAProgressoPerfil

class IAProgressoResponse(BaseModel):
    progresso: IAProgressoData
    mensagem_destaque: str
    periodo: str


class IAGrowthCTAResponse(BaseModel):
    deve_exibir: bool
    tipo: str = ""
    mensagem: str = ""
    cta_label: str = ""
    cta_url: str = ""
    contexto: str = ""
    cooldown_ativo: bool = False
    roi_valor: float = 0.0
    tipo_oferta: IAGrowthTipoOferta = IAGrowthTipoOferta.CONSULTIVO
    mensagem_oferta: str = ""
    beneficio_destacado: str = ""
    experimento_id: Optional[uuid.UUID] = None
    variante_id: Optional[uuid.UUID] = None
    titulo_alternativo: Optional[str] = None # Growth-10
    tipo_abordagem: Optional[str] = None # Growth-10
    moment_score: float = 0.0 # IA-Growth-14
    timing_decision: str = "FULL" # IA-Growth-14 (FULL, SOFT, HIDDEN)
    churn_risk_score: float = 0.0 # IA-Growth-15
    churn_risk_level: str = "BAIXO" # IA-Growth-15
    incentivo: Optional["IAGrowthIncentivoItem"] = None


class IAGrowthMetricaContexto(BaseModel):
    contexto: str
    total_exibicoes: int
    total_cliques: int
    taxa_conversao: float
    classificacao: str  # "ALTA" | "MÉDIA" | "BAIXA"


class IAGrowthMetricasResponse(BaseModel):
    periodo_dias: int
    total_exibicoes: int
    total_cliques: int
    taxa_conversao_geral: float
    por_contexto: List[IAGrowthMetricaContexto]
    recomendacoes: List[str]


class IAGrowthConfigResponse(BaseModel):
    contexto: str
    ativo: bool
    cooldown_horas: int
    prioridade: int
    updated_at: Optional[datetime] = None


class IAGrowthConfigUpdate(BaseModel):
    ativo: Optional[bool] = None
    cooldown_horas: Optional[int] = None
    prioridade: Optional[int] = None


class IAGrowthConfigHistoricoItem(BaseModel):
    contexto: str
    campo_alterado: str
    valor_anterior: Optional[str]
    valor_novo: str
    alterado_por: Optional[uuid.UUID]
    criado_em: datetime


class IAGrowthSugestao(BaseModel):
    id: str
    contexto: str
    tipo: str  # DESATIVAR | REDUZIR_COOLDOWN | AUMENTAR_PRIORIDADE | ESTABILIZAR
    justificativa: str
    impacto: str  # BAIXO | MÉDIO | ALTO
    confianca: float  # 0–1
    aplicavel: bool
    acao_payload: Dict[str, Any]


class IAGrowthSugestoesResponse(BaseModel):
    periodo_dias: int
    total: int
    sugestoes: List[IAGrowthSugestao]


class IAGrowthSugestaoDesempenho(BaseModel):
    sugestao_id: str
    contexto: str
    tipo: str
    impacto: str
    applied_at: Optional[str]
    taxa_antes: float
    taxa_depois: float
    variacao: float  # percentual relativo
    ganho: bool  # True se taxa_depois > taxa_antes


class IAGrowthSugestoesDesempenhoResponse(BaseModel):
    periodo_dias: int
    total_geradas: int
    total_aplicadas: int
    total_ignoradas: int
    total_pendentes: int
    taxa_aplicacao: float
    conversao_media_antes: float
    conversao_media_depois: float
    variacao_media: float
    com_ganho: List[IAGrowthSugestaoDesempenho]
    sem_ganho: List[IAGrowthSugestaoDesempenho]


class IAGrowthCTADinamico(BaseModel):
    titulo: str
    descricao: str
    botao: str
    tipo_abordagem: str # URGENCIA, PROVA_SOCIAL, GANHO, PERDA, EDUCATIVO


class IAGrowthExperimentoVarianteSchema(BaseModel):
    id: uuid.UUID
    nome: str
    config_override: Dict[str, Any]
    cta: Optional[IAGrowthCTADinamico] = None
    peso: float
    ativo: bool
    origem_copy: str = "HEURISTICA" # Growth-11


class IAGrowthExperimentoVarianteCreate(BaseModel):
    nome: str
    peso: float
    config_override: Dict[str, Any]
    cta: Optional[IAGrowthCTADinamico] = None


class IAGrowthExperimentoSchema(BaseModel):
    id: uuid.UUID
    contexto: str
    nome: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    variantes: List[IAGrowthExperimentoVarianteSchema]


class IAGrowthExperimentoCreate(BaseModel):
    contexto: str
    nome: str
    variantes: List[IAGrowthExperimentoVarianteCreate]

class IAGrowthExperimentoAutoCreate(BaseModel):
    contexto: str
    nome: str

class IAGrowthExperimentoResultadoVariante(BaseModel):
    variante_id: uuid.UUID
    nome: str
    exibicoes: int
    cliques: int
    conversao: float

class IAGrowthExperimentoResultado(BaseModel):
    experimento_id: uuid.UUID
    nome: str
    status: str
    total_exibicoes: int
    total_cliques: int
    variantes: List[IAGrowthExperimentoResultadoVariante]
    vencedora: Optional[str] = None
    significancia_atingida: bool = False


class IAGrowthCopyPerformance(BaseModel):
    tipo_abordagem: str
    exibicoes: int
    cliques: int
    conversao: float

class IAGrowthCopyPerformanceResponse(BaseModel):
    contexto: str
    performance: List[IAGrowthCopyPerformance]
    melhor_abordagem: Optional[str] = None


class IAGrowthPersonaPerformance(BaseModel):
    persona: str
    usuarios: int
    exibicoes: int
    cliques: int
    conversao: float
    melhor_abordagem: Optional[str] = None
    melhor_origem: Optional[str] = None  # LLM ou HEURISTICA
    melhor_contexto: Optional[str] = None


class IAGrowthTimingPerformance(BaseModel):
    timing_decision: str # FULL, SOFT, HIDDEN
    exibicoes: int
    cliques: int
    skipped: int
    conversao: float

class IAGrowthPersonasPerformanceResponse(BaseModel):
    periodo_dias: int
    total_usuarios_classificados: int
    distribuicao_persona: Dict[str, int]
    performance_por_persona: List[IAGrowthPersonaPerformance]
    timing_performance: List[IAGrowthTimingPerformance] = [] # IA-Growth-14
    melhor_persona_conversao: Optional[str] = None
    melhor_abordagem_geral: Optional[str] = None
    melhor_origem_geral: Optional[str] = None


class IAGrowthChurnNivelItem(BaseModel):
    nivel: str
    usuarios: int
    percentual: float


class IAGrowthChurnConversaoItem(BaseModel):
    nivel: str
    exibicoes: int
    cliques: int
    conversao: float


class IAGrowthChurnRecuperacao(BaseModel):
    usuarios_alto_risco: int
    usuarios_recuperados: int
    taxa_recuperacao: float


class IAGrowthChurnImpactoPreventivo(BaseModel):
    exibicoes: int
    cliques: int
    dismisses: int
    conversao: float


class IAGrowthChurnDashboardResponse(BaseModel):
    periodo_dias: int
    total_usuarios_avaliados: int
    distribuicao_niveis: List[IAGrowthChurnNivelItem]
    conversao_por_nivel: List[IAGrowthChurnConversaoItem]
    recuperacao_alto_risco: IAGrowthChurnRecuperacao
    impacto_cta_preventivo: IAGrowthChurnImpactoPreventivo


# ─── IA-Growth-21: Incentivos controlados ──────────────────────────────────────

class IAGrowthTipoIncentivo(str, Enum):
    TRIAL_PROFISSIONAL = "TRIAL_PROFISSIONAL"
    TRIAL_ENTERPRISE = "TRIAL_ENTERPRISE"
    DEMO_ASSISTIDA = "DEMO_ASSISTIDA"
    CONSULTORIA_RAPIDA = "CONSULTORIA_RAPIDA"
    EXTENSAO_AVALIACAO = "EXTENSAO_AVALIACAO"


class IAGrowthOrigemIncentivo(str, Enum):
    MANUAL = "MANUAL"
    AUTOPILOT = "AUTOPILOT"
    ASSISTENTE = "ASSISTENTE"


class IAGrowthStatusIncentivo(str, Enum):
    OFERECIDO = "OFERECIDO"
    ACEITO = "ACEITO"
    RECUSADO = "RECUSADO"
    EXPIRADO = "EXPIRADO"
    CANCELADO = "CANCELADO"
    PENDENTE_APROVACAO = "PENDENTE_APROVACAO"
    APROVADO = "APROVADO"
    REPROVADO = "REPROVADO"


class IAGrowthIncentivoItem(BaseModel):
    id: uuid.UUID
    usuario_id: Optional[uuid.UUID] = None
    tipo_incentivo: IAGrowthTipoIncentivo
    tipo_incentivo_label: str
    plano_alvo: str
    plano_alvo_label: str
    origem: IAGrowthOrigemIncentivo
    origem_label: str
    status: IAGrowthStatusIncentivo
    status_label: str
    validade_inicio: datetime
    validade_fim: datetime
    motivo: str
    aprovado_por: Optional[uuid.UUID] = None
    aprovado_em: Optional[datetime] = None
    motivo_reprovacao: Optional[str] = None
    created_at: datetime
    accepted_at: Optional[datetime] = None
    ativo: bool = False
    dias_validade_restantes: int = 0


class IAGrowthIncentivosResponse(BaseModel):
    periodo_dias: int
    oferecidos: int
    aceitos: int
    recusados: int
    expirados: int
    cancelados: int
    taxa_aceite: float
    conversao_pos_incentivo: float
    incentivos: List[IAGrowthIncentivoItem]


class IAGrowthIncentivoActionResponse(BaseModel):
    status: str
    incentivo: IAGrowthIncentivoItem


class IAGrowthIncentivosAprovacaoResponse(BaseModel):
    periodo_dias: int
    pendentes: int
    aprovados: int
    reprovados: int
    incentivos: List[IAGrowthIncentivoItem]


# ─── IA-Growth-16: Recomendação consultiva de plano ────────────────────────────

class IAGrowthPlanoFitItem(BaseModel):
    """Score de fit de um plano específico (BASICO | PROFISSIONAL | ENTERPRISE)."""
    plano: str
    plano_label: str
    score_fit: float
    motivos: List[str] = []
    funcionalidades_relevantes: List[str] = []


class IAGrowthPlanoRecomendadoResponse(BaseModel):
    """Resposta de GET /ia/growth/plano-recomendado.

    Resultado consultivo que combina fit dos planos + copy + CTA, sem
    alterar billing real.
    """
    plano_atual: str
    plano_atual_label: str
    plano_recomendado: str
    plano_recomendado_label: str
    score_fit: float
    motivos: List[str]
    beneficios: List[str]
    funcionalidades_mais_relevantes: List[str]
    cta_label: str
    cta_url: str
    cta_secundaria_label: Optional[str] = None
    cta_secundaria_url: Optional[str] = None
    tipo_oferta: IAGrowthTipoOferta = IAGrowthTipoOferta.CONSULTIVO
    mensagem_oferta: str = ""
    beneficio_destacado: str = ""
    incentivo: Optional[IAGrowthIncentivoItem] = None
    nivel_urgencia: str   # ALTA | MEDIA | BAIXA
    churn_risk_level: str
    persona: Optional[str] = None
    fit_por_plano: List[IAGrowthPlanoFitItem] = []
    log_id: Optional[uuid.UUID] = None


class IAGrowthOportunidadeItem(BaseModel):
    usuario_id: uuid.UUID
    usuario_label: str
    persona: Optional[str] = None
    plano_atual: str
    plano_atual_label: str
    plano_recomendado: str
    plano_recomendado_label: str
    score_fit: float
    score_oportunidade: float
    nivel: str
    categoria: str
    contexto: str
    cta_label: str
    cta_url: str
    acao_sugerida: str
    impacto_estimado: float
    impacto_estimado_label: str
    churn_risk_level: str
    uso_premium_score: float
    frequencia_uso_score: float
    assistente_score: float
    cta_score: float
    cta_clicks: int
    cta_views: int
    assistente_interacoes: int
    tipo_oferta: IAGrowthTipoOferta = IAGrowthTipoOferta.CONSULTIVO
    mensagem_oferta: str = ""
    beneficio_destacado: str = ""


class IAGrowthOportunidadesResponse(BaseModel):
    periodo_dias: int
    total_oportunidades: int
    alto_potencial: int
    travados: int
    risco: int
    neutros: int
    impacto_total_estimado: float
    contextos_disponiveis: List[str]
    oportunidades: List[IAGrowthOportunidadeItem]


class IAGrowthAutopilotAcaoItem(BaseModel):
    id: uuid.UUID
    usuario_id: Optional[uuid.UUID] = None
    tipo_acao: str
    contexto: str
    motivo: str
    score_oportunidade: float
    churn_risk: float
    impacto_estimado: float
    executada_em: datetime
    resultado: Optional[Dict[str, Any]] = None
    tipo_oferta: IAGrowthTipoOferta = IAGrowthTipoOferta.CONSULTIVO
    mensagem_oferta: str = ""
    beneficio_destacado: str = ""


class IAGrowthAutopilotStatusResponse(BaseModel):
    ativo: bool
    autopilot_enabled: bool
    nivel_autonomia: str
    modo: str
    tipo_oferta: IAGrowthTipoOferta = IAGrowthTipoOferta.CONSULTIVO
    mensagem_oferta: str = ""
    beneficio_destacado: str = ""
    incentivo: Optional[IAGrowthIncentivoItem] = None
    acoes_executadas: int
    impacto_estimado: float
    recentes: List[IAGrowthAutopilotAcaoItem]


class IAGrowthOfertaPerformanceItem(BaseModel):
    tipo_oferta: IAGrowthTipoOferta
    total_recomendacoes: int
    total_clicks: int
    total_conversoes: int
    taxa_conversao: float
    participacao: float
    impacto_estimado: float
    impacto_estimado_label: str


class IAGrowthOfertasPerformanceResponse(BaseModel):
    periodo_dias: int
    total_recomendacoes: int
    total_conversoes: int
    impacto_total_estimado: float
    performance: List[IAGrowthOfertaPerformanceItem]


class IAGrowthAssistenteContextoResponse(BaseModel):
    visao_completa: bool = False
    resumo_perfil: str
    oportunidade_identificada: str
    plano_atual: str
    plano_atual_label: str
    plano_sugerido: str
    plano_sugerido_label: str
    motivo_principal: str
    proximos_passos_sugeridos: List[str]
    perguntas_sugeridas: List[str]
    score_fit: float
    persona: Optional[str] = None
    churn_risk_level: str = "BAIXO"
    safra_status: Optional[str] = None
    safra_ano: Optional[str] = None
    estagio_safra: Optional[str] = None
    modulos_usados: List[str] = []
    features_bloqueadas: List[str] = []
    cta_recente: Dict[str, int] = {}
    sinais: Dict[str, Any] = {}
    tipo_oferta: IAGrowthTipoOferta = IAGrowthTipoOferta.CONSULTIVO
    mensagem_oferta: str = ""
    beneficio_destacado: str = ""
    incentivo: Optional[IAGrowthIncentivoItem] = None


class IAGrowthAssistenteMensagemRequest(BaseModel):
    mensagem_usuario: str
    contexto_atual: Optional[IAGrowthAssistenteContextoResponse] = None


class IAGrowthAssistenteMensagemResponse(BaseModel):
    resposta_ia: str
    cta_sugerido: str
    cta_url: str
    plano_recomendado: str
    acao_sugerida: str
    fonte: str
    tipo_oferta: IAGrowthTipoOferta = IAGrowthTipoOferta.CONSULTIVO
    mensagem_oferta: str = ""
    beneficio_destacado: str = ""
    incentivo: Optional[IAGrowthIncentivoItem] = None
    log_id: Optional[uuid.UUID] = None
    contexto: Optional[IAGrowthAssistenteContextoResponse] = None


class IAGrowthOfertaPerformanceItem(BaseModel):
    tipo_oferta: IAGrowthTipoOferta
    total_recomendacoes: int
    total_clicks: int
    total_conversoes: int
    taxa_clique: float
    taxa_conversao: float
    impacto_total_estimado: float


class IAGrowthOfertaPerformanceResponse(BaseModel):
    periodo_dias: int
    total_recomendacoes: int
    distribuicao: List[IAGrowthOfertaPerformanceItem]
    impacto_total_estimado: float
    melhor_tipo_oferta: Optional[IAGrowthTipoOferta] = None


class IAGrowthPlanoMetricasItem(BaseModel):
    plano: str
    plano_label: str
    total_recomendacoes: int
    total_clicks: int
    taxa_clique: float        # 0.0 - 1.0
    total_conversoes: int
    taxa_conversao: float     # 0.0 - 1.0


class IAGrowthPlanoMetricasResponse(BaseModel):
    periodo_dias: int
    total_recomendacoes: int
    distribuicao: List[IAGrowthPlanoMetricasItem]
