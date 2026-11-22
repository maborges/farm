"""Modelos globais ORM para o agente coletor multi-fonte de dados agropecuários."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class AgroCollectorBase(DeclarativeBase):
    """Base ORM isolada das tabelas globais do coletor (não altera a baseline v1)."""


def _utcnow() -> datetime:
    """Retorna timestamp UTC atual com fuso explícito."""
    return datetime.now(timezone.utc)  # noqa: UP017


class AgroDataSource(AgroCollectorBase):
    """Fonte pública ou parceira autorizada homologada para ingestão."""

    __tablename__ = "agro_data_sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain: Mapped[str] = mapped_column(String(30), nullable=False, default="MERCADO")
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    sigla: Mapped[str] = mapped_column(String(40), nullable=False)

    tipo_licenca: Mapped[str] = mapped_column(String(30), nullable=False)
    termo_autorizacao_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    atribuicao_obrigatoria: Mapped[str | None] = mapped_column(String(255), nullable=True)

    uf_padrao: Mapped[str] = mapped_column(String(2), nullable=False, default="BR")
    praca_padrao: Mapped[str | None] = mapped_column(String(120), nullable=True)
    dominios_whitelist: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    url_principal: Mapped[str] = mapped_column(Text, nullable=False)
    url_indice: Mapped[str | None] = mapped_column(Text, nullable=True)

    estrategia_coleta: Mapped[str] = mapped_column(String(40), nullable=False)
    config_extrator: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    cron_ou_intervalo_seg: Mapped[int] = mapped_column(Integer, nullable=False, default=3600)
    auto_publish_policy: Mapped[str] = mapped_column(
        String(40), nullable=False, default="AUTO_SE_GUARDRAILS_OK"
    )
    max_variacao_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("12.00")
    )
    max_defasagem_dias: Mapped[int] = mapped_column(Integer, nullable=False, default=14)
    prioridade_exibicao: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    falhas_consecutivas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ultima_execucao_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultimo_sucesso_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    proximo_ciclo_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class AgroIngestionRun(AgroCollectorBase):
    """Registro de auditoria de cada execução agendada ou manual de coleta."""

    __tablename__ = "agro_ingestion_runs"
    __table_args__ = (
        Index("ix_agro_ingestion_runs_source_iniciado", "source_id", "iniciado_em"),
        Index("ix_agro_ingestion_runs_source_sha256", "source_id", "sha256_bruto"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agro_data_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    trigger_tipo: Mapped[str] = mapped_column(String(30), nullable=False, default="AGENDADO")
    executado_por: Mapped[str | None] = mapped_column(String(120), nullable=True)

    url_efetiva: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sha256_bruto: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tamanho_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    skipped_unchanged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    modelo_ia: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tokens_entrada: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_saida: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    custo_estimado_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=Decimal("0")
    )
    total_extraidos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_publicados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_quarentena: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_rejeitados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    erro_resumo: Mapped[str | None] = mapped_column(Text, nullable=True)
    sugestao_sentinela: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    iniciado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    finalizado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AgroIngestionArtifact(AgroCollectorBase):
    """Armazenamento forense comprimido do documento bruto coletado."""

    __tablename__ = "agro_ingestion_artifacts"
    __table_args__ = (
        Index("ix_agro_ingestion_artifacts_retencao", "retencao_ate", "expurgado_em"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agro_ingestion_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agro_data_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    compressao: Mapped[str] = mapped_column(String(16), nullable=False, default="gzip")
    conteudo_comprimido: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    tamanho_original_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tamanho_comprimido_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    retencao_ate: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expurgado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class AgroStagingObservation(AgroCollectorBase):
    """Área de quarentena e trilha de validação pré-publicação."""

    __tablename__ = "agro_staging_observations"
    __table_args__ = (
        Index(
            "ix_agro_staging_pendentes",
            "status_revisao",
            "created_at",
            postgresql_where=sa.text("status_revisao = 'PENDENTE_REVISAO'"),
            sqlite_where=sa.text("status_revisao = 'PENDENTE_REVISAO'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agro_ingestion_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agro_data_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commodity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    praca: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo_preco: Mapped[str] = mapped_column(String(50), nullable=False)
    periodicidade: Mapped[str] = mapped_column(String(20), nullable=False)
    data_referencia: Mapped[date] = mapped_column(Date, nullable=False)

    valor_normalizado: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    moeda: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    unidade_normalizada: Mapped[str] = mapped_column(String(60), nullable=False)
    valor_original: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unidade_original: Mapped[str] = mapped_column(String(60), nullable=False)
    fator_conversao: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), nullable=False, default=Decimal("1.000000")
    )
    transformacao_aplicada: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trecho_evidencia: Mapped[str] = mapped_column(Text, nullable=False)
    registro_origem: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confianca_extracao: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=Decimal("1.000")
    )

    flags_anomalia: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status_revisao: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDENTE_REVISAO"
    )
    revisado_por: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    revisado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    justificativa_revisao: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class AgroMarketObservation(AgroCollectorBase):
    """Série histórica numérica permanente publicada para consumidores públicos e ERP."""

    __tablename__ = "agro_market_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_id",
            "commodity_id",
            "uf",
            "praca",
            "data_referencia",
            name="uq_agro_mkt_obs_serie",
        ),
        Index(
            "ix_agro_mkt_obs_uf_comm_data",
            "uf",
            "commodity_id",
            "data_referencia",
            postgresql_where=sa.text("ativo = true"),
            sqlite_where=sa.text("ativo = 1"),
        ),
        Index(
            "ix_agro_mkt_obs_comm_data",
            "commodity_id",
            "data_referencia",
            postgresql_where=sa.text("ativo = true"),
            sqlite_where=sa.text("ativo = 1"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agro_data_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agro_ingestion_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    staging_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agro_staging_observations.id", ondelete="SET NULL"),
        nullable=True,
    )

    commodity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False)
    praca: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo_preco: Mapped[str] = mapped_column(String(50), nullable=False)
    periodicidade: Mapped[str] = mapped_column(String(20), nullable=False)
    data_referencia: Mapped[date] = mapped_column(Date, nullable=False)

    valor: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    moeda: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    unidade: Mapped[str] = mapped_column(String(60), nullable=False)
    valor_original: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unidade_original: Mapped[str] = mapped_column(String(60), nullable=False)
    transformacao_aplicada: Mapped[str | None] = mapped_column(String(255), nullable=True)
    variacao_anterior_abs: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    variacao_anterior_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    documento_oficial: Mapped[str | None] = mapped_column(Text, nullable=True)
    documento_hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    registro_origem: Mapped[str | None] = mapped_column(String(120), nullable=True)
    publicado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
