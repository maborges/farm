from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy import (
    Uuid as UUIDType,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

try:
    from datetime import UTC
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    UTC = timezone.utc  # noqa: UP017


class WizardStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    BLOCKED = "BLOCKED"
    READY_FOR_GO_LIVE = "READY_FOR_GO_LIVE"
    GO_LIVE = "GO_LIVE"
    STABILIZATION = "STABILIZATION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


ACTIVE_WIZARD_STATUSES = (
    WizardStatus.NOT_STARTED.value,
    WizardStatus.IN_PROGRESS.value,
    WizardStatus.PAUSED.value,
    WizardStatus.BLOCKED.value,
    WizardStatus.READY_FOR_GO_LIVE.value,
    WizardStatus.GO_LIVE.value,
    WizardStatus.STABILIZATION.value,
)

FINAL_WIZARD_STATUSES = (
    WizardStatus.COMPLETED.value,
    WizardStatus.CANCELLED.value,
)


class WizardStageCode(str, Enum):
    DIAGNOSTICO = "DIAGNOSTICO"
    UNIDADE_PRODUTIVA = "UNIDADE_PRODUTIVA"
    TERRITORIO = "TERRITORIO"
    ATIVIDADES = "ATIVIDADES"
    AGRICULTURA = "AGRICULTURA"
    PECUARIA = "PECUARIA"
    ESTOQUE = "ESTOQUE"
    FINANCEIRO = "FINANCEIRO"
    MAQUINAS = "MAQUINAS"
    EQUIPE = "EQUIPE"
    REVISAO = "REVISAO"
    GO_LIVE = "GO_LIVE"
    ESTABILIZACAO = "ESTABILIZACAO"


class ModoImplantacao(str, Enum):
    ASSISTIDA = "ASSISTIDA"
    MANUAL_ASSISTIDA = "MANUAL_ASSISTIDA"
    PILOTO_CONTROLADO = "PILOTO_CONTROLADO"
    PARCEIRO = "PARCEIRO"


class OrigemImplantacao(str, Enum):
    NOVO_ASSINANTE = "NOVO_ASSINANTE"
    UPGRADE_ASSINANTE = "UPGRADE_ASSINANTE"
    IMPLANTACAO_INTERNA = "IMPLANTACAO_INTERNA"
    PARCEIRO = "PARCEIRO"


class WizardEtapaStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"


class ChecklistItemStatus(str, Enum):
    PENDENTE = "PENDENTE"
    ATENDIDO = "ATENDIDO"
    DISPENSADO = "DISPENSADO"
    FALHOU = "FALHOU"


class ChecklistItemSeverity(str, Enum):
    INFO = "INFO"
    ATENCAO = "ATENCAO"
    CRITICO = "CRITICO"


class ChecklistEvidenceType(str, Enum):
    AUTOMATICA = "AUTOMATICA"
    MANUAL = "MANUAL"
    DOCUMENTAL = "DOCUMENTAL"
    REFERENCIAL = "REFERENCIAL"


class PendenciaTipo(str, Enum):
    PENDENCIA = "PENDENCIA"
    BLOQUEIO = "BLOQUEIO"
    RISCO = "RISCO"
    TAREFA_MANUAL = "TAREFA_MANUAL"


class PendenciaSeverity(str, Enum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class PendenciaStatus(str, Enum):
    ABERTA = "ABERTA"
    EM_TRATAMENTO = "EM_TRATAMENTO"
    RESOLVIDA = "RESOLVIDA"
    DESCARTADA = "DESCARTADA"


WIZARD_STATUS_CHECK = (
    "status IN ('NOT_STARTED', 'IN_PROGRESS', 'PAUSED', 'BLOCKED', "
    "'READY_FOR_GO_LIVE', 'GO_LIVE', 'STABILIZATION', 'COMPLETED', "
    "'CANCELLED')"
)
WIZARD_STAGE_CODE_CHECK = (
    "codigo_etapa IN ('DIAGNOSTICO', 'UNIDADE_PRODUTIVA', 'TERRITORIO', "
    "'ATIVIDADES', 'AGRICULTURA', 'PECUARIA', 'ESTOQUE', 'FINANCEIRO', "
    "'MAQUINAS', 'EQUIPE', 'REVISAO', 'GO_LIVE', 'ESTABILIZACAO')"
)
WIZARD_ETAPA_STATUS_CHECK = (
    "status IN ('NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'SKIPPED', "
    "'BLOCKED')"
)
CHECKLIST_STATUS_CHECK = "status IN ('PENDENTE', 'ATENDIDO', 'DISPENSADO', 'FALHOU')"
CHECKLIST_SEVERITY_CHECK = "severidade IN ('INFO', 'ATENCAO', 'CRITICO')"
CHECKLIST_EVIDENCE_CHECK = (
    "evidencia_tipo IN ('AUTOMATICA', 'MANUAL', 'DOCUMENTAL', 'REFERENCIAL')"
)
PENDENCIA_TIPO_CHECK = (
    "tipo IN ('PENDENCIA', 'BLOQUEIO', 'RISCO', 'TAREFA_MANUAL')"
)
PENDENCIA_SEVERITY_CHECK = "severidade IN ('BAIXA', 'MEDIA', 'ALTA', 'CRITICA')"
PENDENCIA_STATUS_CHECK = (
    "status IN ('ABERTA', 'EM_TRATAMENTO', 'RESOLVIDA', 'DESCARTADA')"
)


class ImplantacaoOperacional(Base):
    __tablename__ = "wizard_implantacoes_operacionais"
    __table_args__ = (
        CheckConstraint(WIZARD_STATUS_CHECK, name="ck_wizard_implantacao_status"),
        CheckConstraint(WIZARD_STAGE_CODE_CHECK, name="ck_wizard_implantacao_etapa_atual"),
        CheckConstraint(
            "modo_implantacao IN ('ASSISTIDA', 'MANUAL_ASSISTIDA', "
            "'PILOTO_CONTROLADO', 'PARCEIRO')",
            name="ck_wizard_implantacao_modo",
        ),
        CheckConstraint(
            "origem IN ('NOVO_ASSINANTE', 'UPGRADE_ASSINANTE', "
            "'IMPLANTACAO_INTERNA', 'PARCEIRO')",
            name="ck_wizard_implantacao_origem",
        ),
        CheckConstraint(
            "percentual_progresso >= 0 AND percentual_progresso <= 100",
            name="ck_wizard_implantacao_progresso_range",
        ),
        CheckConstraint(
            "checklist_minimo_percentual >= 0 AND checklist_minimo_percentual <= 100",
            name="ck_wizard_implantacao_checklist_percentual_range",
        ),
        CheckConstraint(
            "status <> 'BLOCKED' OR blocked_at IS NOT NULL",
            name="ck_wizard_implantacao_blocked_requires_blocked_at",
        ),
        CheckConstraint(
            "status NOT IN ('READY_FOR_GO_LIVE', 'GO_LIVE', 'STABILIZATION', "
            "'COMPLETED') OR unidade_produtiva_id IS NOT NULL",
            name="ck_wizard_implantacao_status_requires_unidade",
        ),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name="ck_wizard_implantacao_completed_after_started",
        ),
        CheckConstraint(
            "cancelled_at IS NULL OR started_at IS NULL OR cancelled_at >= started_at",
            name="ck_wizard_implantacao_cancelled_after_started",
        ),
        CheckConstraint(
            "go_live_at IS NULL OR started_at IS NULL OR go_live_at >= started_at",
            name="ck_wizard_implantacao_go_live_after_started",
        ),
        CheckConstraint(
            "ready_for_go_live_at IS NULL OR started_at IS NULL OR "
            "ready_for_go_live_at >= started_at",
            name="ck_wizard_implantacao_ready_after_started",
        ),
        CheckConstraint(
            "stabilization_started_at IS NULL OR go_live_at IS NULL OR "
            "stabilization_started_at >= go_live_at",
            name="ck_wizard_implantacao_stabilization_after_go_live",
        ),
        Index("ix_wizard_implantacao_tenant_status", "tenant_id", "status"),
        Index("ix_wizard_implantacao_owner", "owner_usuario_id"),
        Index("ix_wizard_implantacao_unidade", "unidade_produtiva_id"),
        Index(
            "uq_wizard_implantacao_ativa_por_tenant",
            "tenant_id",
            unique=True,
            postgresql_where=text(
                "status IN ('NOT_STARTED', 'IN_PROGRESS', 'PAUSED', 'BLOCKED', "
                "'READY_FOR_GO_LIVE', 'GO_LIVE', 'STABILIZATION')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("unidades_produtivas.id", ondelete="SET NULL"),
        nullable=True,
    )
    owner_usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=WizardStatus.NOT_STARTED.value,
        server_default=text("'NOT_STARTED'"),
    )
    etapa_atual: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=WizardStageCode.DIAGNOSTICO.value,
        server_default=text("'DIAGNOSTICO'"),
    )
    percentual_progresso: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    modo_implantacao: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ModoImplantacao.ASSISTIDA.value,
        server_default=text("'ASSISTIDA'"),
    )
    origem: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=OrigemImplantacao.NOVO_ASSINANTE.value,
        server_default=text("'NOVO_ASSINANTE'"),
    )
    diagnostico_inicial_snapshot: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    escopo_modulos: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    bloqueio_critico_aberto: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    checklist_minimo_percentual: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    go_live_aprovado_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_for_go_live_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    go_live_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stabilization_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    etapas: Mapped[list[ImplantacaoEtapa]] = relationship(
        "ImplantacaoEtapa",
        back_populates="implantacao",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    checklist_itens: Mapped[list[ImplantacaoChecklistItem]] = relationship(
        "ImplantacaoChecklistItem",
        back_populates="implantacao",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    pendencias: Mapped[list[ImplantacaoPendencia]] = relationship(
        "ImplantacaoPendencia",
        back_populates="implantacao",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    historico: Mapped[list[ImplantacaoHistorico]] = relationship(
        "ImplantacaoHistorico",
        back_populates="implantacao",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class ImplantacaoEtapa(Base):
    __tablename__ = "wizard_implantacoes_etapas"
    __table_args__ = (
        CheckConstraint(WIZARD_STAGE_CODE_CHECK, name="ck_wizard_etapa_codigo"),
        CheckConstraint(WIZARD_ETAPA_STATUS_CHECK, name="ck_wizard_etapa_status"),
        CheckConstraint(
            "percentual_peso >= 0 AND percentual_peso <= 100",
            name="ck_wizard_etapa_peso_range",
        ),
        CheckConstraint(
            "completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at",
            name="ck_wizard_etapa_completed_after_started",
        ),
        CheckConstraint(
            "skipped_at IS NULL OR started_at IS NULL OR skipped_at >= started_at",
            name="ck_wizard_etapa_skipped_after_started",
        ),
        CheckConstraint(
            "blocked_at IS NULL OR started_at IS NULL OR blocked_at >= started_at",
            name="ck_wizard_etapa_blocked_after_started",
        ),
        Index("ix_wizard_etapa_implantacao_status", "implantacao_id", "status"),
        Index(
            "uq_wizard_etapa_implantacao_codigo",
            "implantacao_id",
            "codigo_etapa",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    implantacao_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("wizard_implantacoes_operacionais.id", ondelete="CASCADE"),
        nullable=False,
    )
    codigo_etapa: Mapped[str] = mapped_column(String(30), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=WizardEtapaStatus.NOT_STARTED.value,
        server_default=text("'NOT_STARTED'"),
    )
    obrigatoria: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    percentual_peso: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    skipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dados_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    implantacao: Mapped[ImplantacaoOperacional] = relationship(
        "ImplantacaoOperacional", back_populates="etapas", lazy="noload"
    )
    checklist_itens: Mapped[list[ImplantacaoChecklistItem]] = relationship(
        "ImplantacaoChecklistItem",
        back_populates="etapa",
        lazy="noload",
    )
    pendencias: Mapped[list[ImplantacaoPendencia]] = relationship(
        "ImplantacaoPendencia",
        back_populates="etapa",
        lazy="noload",
    )


class ImplantacaoChecklistItem(Base):
    __tablename__ = "wizard_implantacoes_checklist_itens"
    __table_args__ = (
        CheckConstraint(CHECKLIST_STATUS_CHECK, name="ck_wizard_checklist_status"),
        CheckConstraint(
            CHECKLIST_SEVERITY_CHECK, name="ck_wizard_checklist_severidade"
        ),
        CheckConstraint(
            CHECKLIST_EVIDENCE_CHECK, name="ck_wizard_checklist_evidencia_tipo"
        ),
        CheckConstraint(
            "checked_at IS NULL OR checked_by_usuario_id IS NOT NULL",
            name="ck_wizard_checklist_checked_requires_user",
        ),
        Index(
            "uq_wizard_checklist_implantacao_codigo",
            "implantacao_id",
            "codigo_item",
            unique=True,
        ),
        Index("ix_wizard_checklist_implantacao_status", "implantacao_id", "status"),
        Index("ix_wizard_checklist_etapa", "etapa_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    implantacao_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("wizard_implantacoes_operacionais.id", ondelete="CASCADE"),
        nullable=False,
    )
    etapa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("wizard_implantacoes_etapas.id", ondelete="SET NULL"),
        nullable=True,
    )
    codigo_item: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    obrigatorio: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ChecklistItemStatus.PENDENTE.value,
        server_default=text("'PENDENTE'"),
    )
    severidade: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ChecklistItemSeverity.INFO.value,
        server_default=text("'INFO'"),
    )
    evidencia_tipo: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ChecklistEvidenceType.AUTOMATICA.value,
        server_default=text("'AUTOMATICA'"),
    )
    evidencia_ref_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    checked_by_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    implantacao: Mapped[ImplantacaoOperacional] = relationship(
        "ImplantacaoOperacional", back_populates="checklist_itens", lazy="noload"
    )
    etapa: Mapped[ImplantacaoEtapa | None] = relationship(
        "ImplantacaoEtapa", back_populates="checklist_itens", lazy="noload"
    )


class ImplantacaoPendencia(Base):
    __tablename__ = "wizard_implantacoes_pendencias"
    __table_args__ = (
        CheckConstraint(PENDENCIA_TIPO_CHECK, name="ck_wizard_pendencia_tipo"),
        CheckConstraint(
            PENDENCIA_SEVERITY_CHECK, name="ck_wizard_pendencia_severidade"
        ),
        CheckConstraint(PENDENCIA_STATUS_CHECK, name="ck_wizard_pendencia_status"),
        CheckConstraint(
            "resolved_at IS NULL OR status IN ('RESOLVIDA', 'DESCARTADA')",
            name="ck_wizard_pendencia_resolved_status",
        ),
        CheckConstraint(
            "due_date IS NULL OR resolved_at IS NULL OR resolved_at::date >= due_date",
            name="ck_wizard_pendencia_resolved_after_due",
        ),
        Index(
            "ix_wizard_pendencia_implantacao_status",
            "implantacao_id",
            "status",
        ),
        Index(
            "ix_wizard_pendencia_implantacao_severidade",
            "implantacao_id",
            "severidade",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    implantacao_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("wizard_implantacoes_operacionais.id", ondelete="CASCADE"),
        nullable=False,
    )
    etapa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("wizard_implantacoes_etapas.id", ondelete="SET NULL"),
        nullable=True,
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    severidade: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PendenciaStatus.ABERTA.value,
        server_default=text("'ABERTA'"),
    )
    titulo: Mapped[str] = mapped_column(String(180), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    responsavel_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    implantacao: Mapped[ImplantacaoOperacional] = relationship(
        "ImplantacaoOperacional", back_populates="pendencias", lazy="noload"
    )
    etapa: Mapped[ImplantacaoEtapa | None] = relationship(
        "ImplantacaoEtapa", back_populates="pendencias", lazy="noload"
    )


class ImplantacaoHistorico(Base):
    __tablename__ = "wizard_implantacoes_historico"
    __table_args__ = (
        Index(
            "ix_wizard_historico_implantacao_created",
            "implantacao_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    implantacao_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("wizard_implantacoes_operacionais.id", ondelete="CASCADE"),
        nullable=False,
    )
    evento: Mapped[str] = mapped_column(String(120), nullable=False)
    status_anterior: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status_novo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    etapa_anterior: Mapped[str | None] = mapped_column(String(30), nullable=True)
    etapa_nova: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ator_usuario_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(as_uuid=True),
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
    )
    payload_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

    implantacao: Mapped[ImplantacaoOperacional] = relationship(
        "ImplantacaoOperacional", back_populates="historico", lazy="noload"
    )
