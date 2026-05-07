import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Numeric, Index, JSON, Boolean, Float, Text
try:
    from sqlalchemy import Uuid as UUIDTYPE
except ImportError:
    from sqlalchemy.dialects.postgresql import UUID as UUIDTYPE

try:
    from sqlalchemy.orm import Mapped, mapped_column, relationship
except ImportError:
    from sqlalchemy.orm import relationship
    Mapped = type("Mapped", (), {"__getitem__": lambda s, x: x})()
    mapped_column = Column

from core.database import Base


class IACreditosPacote(Base):
    __tablename__ = "ia_creditos_pacotes"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    quantidade_creditos: Mapped[int] = mapped_column(Integer, nullable=False)
    creditos_usados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    origem: Mapped[str] = mapped_column(String(60), nullable=False, default="SOLICITACAO")
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="ATIVO")
    adquirido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    expira_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ia_creditos_tenant_status", "tenant_id", "status"),
    )


class IAUso(Base):
    __tablename__ = "ia_uso"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    origem: Mapped[str] = mapped_column(String(60), nullable=False)
    modelo: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    tokens_entrada: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_saida: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    custo_estimado: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="SUCESSO")
    fonte_consumo: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # PLANO | PACOTE
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ia_uso_tenant_created", "tenant_id", "created_at"),
    )


class IAComprasRecomendacao(Base):
    """Auditoria de recomendações estratégicas de compra geradas pela IA (Step 169)."""
    __tablename__ = "ia_compras_recomendacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    item_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    solicitacao_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    estrategia: Mapped[str] = mapped_column(String(30), nullable=False)
    resumo: Mapped[str] = mapped_column(String(500), nullable=False)
    justificativas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    nivel_confianca: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    fonte: Mapped[str] = mapped_column(String(20), nullable=False, default="DETERMINISTICO")
    limite_atingido: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    feedback_util: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    feedback_comentario: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Step 174 — revisão manual
    feedback_revisado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    feedback_revisado_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    feedback_revisao_observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ia_compras_rec_tenant", "tenant_id", "created_at"),
        Index("ix_ia_compras_rec_solicitacao", "solicitacao_id"),
    )


class IAPromptVersao(Base):
    """Versões versionadas do prompt de IA por contexto (Step 177)."""
    __tablename__ = "ia_prompts_versoes"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    contexto: Mapped[str] = mapped_column(String(60), nullable=False)          # COMPRAS_ESTRATEGIA
    versao: Mapped[str] = mapped_column(String(20), nullable=False)            # ex: v1, v2
    conteudo: Mapped[str] = mapped_column(Text, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ia_prompts_tenant_contexto", "tenant_id", "contexto"),
        Index("ix_ia_prompts_contexto_ativo", "contexto", "ativo"),
    )


class IAPromptVersaoHistorico(Base):
    """Histórico de eventos das versões de prompt para auditoria (Step 178)."""
    __tablename__ = "ia_prompt_versoes_historico"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True
    )
    prompt_versao_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("ia_prompts_versoes.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    tipo_evento: Mapped[str] = mapped_column(String(20), nullable=False)
    valor_anterior: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    valor_novo: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class IAAlertaHistorico(Base):
    """Histórico de alertas inteligentes gerados e ações do usuário (Step 194)."""
    __tablename__ = "ia_alertas_historico"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    safra_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    tipo_alerta: Mapped[str] = mapped_column(String(60), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    gravidade: Mapped[str] = mapped_column(String(20), nullable=False)
    parametros_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    visualizado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    acao_executada: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acao_executada_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    ignorado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ignorado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ia_alertas_hist_tenant", "tenant_id", "created_at"),
        Index("ix_ia_alertas_hist_safra", "safra_id"),
    )


class IAAcaoAssistidaHistorico(Base):
    """Histórico de ações assistidas (Magic Actions) executadas pelo usuário ou sistema (Step 201/210)."""
    __tablename__ = "ia_acoes_assistidas_historico"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    origem: Mapped[str] = mapped_column(String(60), nullable=False) # ALERTA_INTELIGENTE, RESUMO_DIARIO, PLANO_ACAO
    origem_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    tipo_acao: Mapped[str] = mapped_column(String(60), nullable=False) # SIMULACAO, AJUSTE_CENARIO, BATCH
    parametros_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    metodo_execucao: Mapped[str] = mapped_column(String(20), nullable=False, default="ASSISTIDA") # ASSISTIDA, AUTOMATICA
    
    impacto_valor: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True) # Step 211
    revertida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False) # Step 211
    revertida_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True) # Step 211
    
    concluida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    concluida_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ia_acoes_assist_tenant", "tenant_id", "created_at"),
        Index("ix_ia_acoes_assist_origem", "origem", "origem_id"),
    )


class IAGrowthLearningWeight(Base):
    """Pesos aprendidos por tenant/dimensão/chave para calibração de Growth (IA-Growth-24)."""
    __tablename__ = "ia_growth_learning_weights"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    dimensao: Mapped[str] = mapped_column(String(20), nullable=False)
    chave: Mapped[str] = mapped_column(String(80), nullable=False)
    peso_atual: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    amostras: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversoes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ia_growth_learning_tenant_dim_key", "tenant_id", "dimensao", "chave", unique=True),
        Index("ix_ia_growth_learning_tenant_dim", "tenant_id", "dimensao"),
    )


class IAAutopilotConfig(Base):
    """Configurações do Modo Autopilot (Execução Automática Controlada) (Step 210)."""
    __tablename__ = "ia_autopilot_config"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    autopilot_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    growth_incentivos_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    nivel_autonomia: Mapped[str] = mapped_column(String(20), nullable=False, default="BAIXO") # BAIXO, MEDIO, ALTO
    tipos_permitidos: Mapped[list] = mapped_column(JSON, nullable=False, default=list) # SIMULACAO, AJUSTE_CENARIO, ANALISE
    limite_impacto_percentual: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ia_autopilot_tenant", "tenant_id"),
    )


class IAGrowthIncentivo(Base):
    """Auditoria de incentivos/trials controlados de Growth (IA-Growth-21)."""
    __tablename__ = "ia_growth_incentivos"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    tipo_incentivo: Mapped[str] = mapped_column(String(30), nullable=False)
    plano_alvo: Mapped[str] = mapped_column(String(20), nullable=False)
    origem: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OFERECIDO")
    validade_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    validade_fim: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    aprovado_por: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    aprovado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo_reprovacao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_ia_growth_incentivos_tenant_usuario", "tenant_id", "usuario_id"),
        Index("ix_ia_growth_incentivos_tenant_status", "tenant_id", "status"),
        Index("ix_ia_growth_incentivos_tenant_validade", "tenant_id", "validade_fim"),
    )


class IAGrowthAutopilotAcao(Base):
    """Auditoria de ações executadas pelo Autopilot de Growth (IA-Growth-19)."""
    __tablename__ = "ia_growth_autopilot_acoes"

    id: Mapped[uuid.UUID] = mapped_column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUIDTYPE(as_uuid=True), nullable=True)
    tipo_acao: Mapped[str] = mapped_column(String(50), nullable=False)
    contexto: Mapped[str] = mapped_column(String(40), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    score_oportunidade: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    churn_risk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    impacto_estimado: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    resultado: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    executada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ia_growth_autopilot_tenant_exec", "tenant_id", "executada_em"),
        Index("ix_ia_growth_autopilot_tenant_usuario", "tenant_id", "usuario_id"),
        Index("ix_ia_growth_autopilot_tenant_tipo", "tenant_id", "tipo_acao"),
    )


class IAUXTelemetria(Base):
    """Métricas de eficiência de UX (Step UX-03)."""
    __tablename__ = "ia_ux_telemetria"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(UUIDTYPE(as_uuid=True), nullable=True)
    evento = Column(String(50), nullable=False) # essential_view_loaded, cta_clicked, etc.
    modo = Column(String(20), nullable=False)   # ESSENCIAL, AVANCADO
    sessao_id = Column(String(100), nullable=True)
    metadados = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ia_ux_telemetria_tenant_evento", "tenant_id", "evento", "created_at"),
        Index("ix_ia_ux_telemetria_evento", "evento"),
    )


class IAGrowthEvento(Base):
    """Rastreia eventos de CTA de upgrade para controle de cooldown (Growth-01)."""
    __tablename__ = "ia_growth_eventos"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(UUIDTYPE(as_uuid=True), nullable=True)
    evento = Column(String(60), nullable=False)
    tipo_cta = Column(String(40), nullable=True)
    contexto = Column(String(40), nullable=True)
    churn_risk_score = Column(Float, nullable=True)
    churn_risk_level = Column(String(10), nullable=True)
    metadados = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ia_growth_tenant_evento", "tenant_id", "evento", "created_at"),
        Index("ix_ia_growth_usuario", "usuario_id", "created_at"),
        Index("ix_ia_growth_churn_level", "tenant_id", "churn_risk_level", "created_at"),
    )


class IAGrowthSugestaoRegistro(Base):
    """Registro persistente de sugestões de otimização geradas (Growth-06)."""
    __tablename__ = "ia_growth_sugestoes"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    sugestao_id = Column(String(32), nullable=False)
    contexto = Column(String(40), nullable=False)
    tipo = Column(String(40), nullable=False)
    impacto = Column(String(10), nullable=False)
    confianca = Column(Float, nullable=False)
    justificativa = Column(Text, nullable=False)
    acao_sugerida = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default="PENDENTE")  # PENDENTE | APLICADA | IGNORADA
    applied_at = Column(DateTime(timezone=True), nullable=True)
    ignored_at = Column(DateTime(timezone=True), nullable=True)
    responsavel_id = Column(UUIDTYPE(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ia_growth_sugestoes_tenant_sid", "tenant_id", "sugestao_id", unique=True),
        Index("ix_ia_growth_sugestoes_tenant_status", "tenant_id", "status"),
    )


class IAGrowthConfig(Base):
    """Configuração manual de CTAs por contexto por tenant (Growth-03)."""
    __tablename__ = "ia_growth_config"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    contexto = Column(String(40), nullable=False)
    ativo = Column(Boolean, nullable=False, default=True)
    cooldown_horas = Column(Integer, nullable=False, default=24)
    prioridade = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ia_growth_config_tenant_contexto", "tenant_id", "contexto", unique=True),
    )


class IAGrowthConfigHistorico(Base):
    """Histórico de alterações manuais de config de CTAs (Growth-03)."""
    __tablename__ = "ia_growth_config_historico"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    contexto = Column(String(40), nullable=False)
    campo_alterado = Column(String(40), nullable=False)
    valor_anterior = Column(String(100), nullable=True)
    valor_novo = Column(String(100), nullable=False)
    alterado_por = Column(UUIDTYPE(as_uuid=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ia_growth_config_hist_tenant", "tenant_id", "criado_em"),
    )


class IAUXThreshold(Base):
    """Armazena thresholds dinâmicos para calibração de UX (Step UX-06)."""
    __tablename__ = "ia_ux_thresholds"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chave = Column(String(100), nullable=False, unique=True) # ex: confiante_tempo_p25
    valor = Column(Float, nullable=False)
    valor_padrao = Column(Float, nullable=False)
    descricao = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ia_ux_thresholds_chave", "chave"),
    )


class IAGrowthExperimento(Base):
    """Estrutura de Experimentos A/B para CTAs de Growth (Growth-08)."""
    __tablename__ = "ia_growth_experimentos"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    contexto = Column(String(40), nullable=False)
    nome = Column(String(120), nullable=False)
    status = Column(String(20), nullable=False, default="ATIVO") # ATIVO | FINALIZADO
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    variantes = relationship("IAGrowthExperimentoVariante", back_populates="experimento", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ia_growth_exp_tenant_ctx_status", "tenant_id", "contexto", "status"),
    )


class IAGrowthExperimentoVariante(Base):
    """Variantes (A, B, C...) de um experimento de Growth (Growth-08)."""
    __tablename__ = "ia_growth_experimento_variantes"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experimento_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("ia_growth_experimentos.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(20), nullable=False)
    config_override = Column(JSON, nullable=False, default=dict) # ex: {"cooldown_horas": 6}
    cta = Column(JSON, nullable=True) # Growth-10: titulo, descricao, botao, tipo_abordagem
    peso = Column(Float, nullable=False, default=1.0)
    ativo = Column(Boolean, nullable=False, default=True)
    origem_copy = Column(String(20), nullable=False, default="HEURISTICA") # HEURISTICA | LLM (Growth-11)

    experimento = relationship("IAGrowthExperimento", back_populates="variantes")

    __table_args__ = (
        Index("ix_ia_growth_variantes_exp", "experimento_id"),
    )


class IAGrowthExperimentoEvento(Base):
    """Rastreia visualizações e cliques específicos de experimentos A/B (Growth-08)."""
    __tablename__ = "ia_growth_experimento_eventos"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(UUIDTYPE(as_uuid=True), nullable=True)
    experimento_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("ia_growth_experimentos.id", ondelete="CASCADE"), nullable=False)
    variante_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("ia_growth_experimento_variantes.id", ondelete="CASCADE"), nullable=False)
    evento = Column(String(20), nullable=False) # SHOWN | CLICKED
    contexto = Column(String(40), nullable=False)
    origem_copy = Column(String(20), nullable=True) # Growth-11
    churn_risk_score = Column(Float, nullable=True)
    churn_risk_level = Column(String(10), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ia_growth_exp_eventos_exp", "experimento_id", "evento"),
        Index("ix_ia_growth_exp_eventos_tenant", "tenant_id", "created_at"),
        Index("ix_ia_growth_exp_eventos_user", "usuario_id"),
        Index("ix_ia_growth_exp_eventos_churn", "tenant_id", "churn_risk_level", "created_at"),
    )

class IAGrowthCopyCache(Base):
    """Cache de copy gerado por LLM para evitar chamadas excessivas (Growth-11)."""
    __tablename__ = "ia_growth_copy_cache"

    tenant_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    contexto = Column(String(40), primary_key=True)
    perfil_hash = Column(String(64), primary_key=True)
    cta = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class IAGrowthUserProfile(Base):
    """Perfil de comportamento de growth do usuário (Persona) (Growth-12)."""
    __tablename__ = "ia_growth_user_profiles"

    user_id = Column(UUIDTYPE(as_uuid=True), primary_key=True)
    perfil = Column(String(40), nullable=False) # CONSERVADOR, EXPLORADOR, ORIENTADO_A_RESULTADO, INICIANTE, AVANCADO
    score = Column(JSON, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_ia_growth_user_perfil", "perfil"),
    )


class IAGrowthPlanoRecomendadoLog(Base):
    """Snapshot de cada recomendação de plano emitida (IA-Growth-16).

    Persistido para permitir o cálculo de distribuição/CTR/conversão por
    plano recomendado no dashboard de Performance.
    """
    __tablename__ = "ia_growth_plano_recomendado_log"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(UUIDTYPE(as_uuid=True), nullable=True)

    plano_atual = Column(String(20), nullable=False)        # BASICO | PROFISSIONAL | ENTERPRISE
    plano_recomendado = Column(String(20), nullable=False)  # idem
    score_fit = Column(Float, nullable=False, default=0.0)  # 0.0 - 1.0
    nivel_urgencia = Column(String(10), nullable=False, default="BAIXA") # ALTA | MEDIA | BAIXA
    persona = Column(String(40), nullable=True)
    churn_risk_level = Column(String(10), nullable=True)
    tipo_oferta = Column(String(30), nullable=True)
    mensagem_oferta = Column(Text, nullable=True)
    beneficio_destacado = Column(String(200), nullable=True)

    motivos = Column(JSON, nullable=True)                # list[str]
    funcionalidades_relevantes = Column(JSON, nullable=True)  # list[str]
    sinais = Column(JSON, nullable=True)                 # dict bruto usado para auditoria

    exibida_em = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    clicada_em = Column(DateTime(timezone=True), nullable=True)
    convertida_em = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_iagrowth_plano_rec_tenant_data", "tenant_id", "exibida_em"),
        Index("ix_iagrowth_plano_rec_plano", "plano_recomendado"),
        Index("ix_iagrowth_plano_rec_usuario", "usuario_id"),
        Index("ix_iagrowth_plano_rec_oferta", "tenant_id", "tipo_oferta", "exibida_em"),
    )


class IAGrowthAssistenteInteracao(Base):
    """Interações registradas do assistente comercial/cs (IA-Growth-17)."""
    __tablename__ = "ia_growth_assistente_interacoes"

    id = Column(UUIDTYPE(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUIDTYPE(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    usuario_id = Column(UUIDTYPE(as_uuid=True), nullable=True)
    plano_atual = Column(String(20), nullable=False)
    plano_recomendado = Column(String(20), nullable=False)
    persona = Column(String(40), nullable=True)
    churn_risk_level = Column(String(10), nullable=True)
    mensagem_usuario = Column(Text, nullable=False)
    resposta_ia = Column(Text, nullable=False)
    cta_sugerido = Column(String(120), nullable=False)
    acao_sugerida = Column(String(60), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_iagrowth_assistente_tenant_data", "tenant_id", "created_at"),
        Index("ix_iagrowth_assistente_usuario", "usuario_id", "created_at"),
    )
