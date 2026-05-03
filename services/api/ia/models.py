import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Numeric, Index, JSON, Boolean, Float, Text
from sqlalchemy import Uuid as UUIDTYPE
from sqlalchemy.orm import Mapped, mapped_column

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

    __table_args__ = (
        Index("ix_ia_prompt_vers_hist_prompt", "prompt_versao_id", "created_at"),
        Index("ix_ia_prompt_vers_hist_tenant", "tenant_id", "created_at"),
    )
