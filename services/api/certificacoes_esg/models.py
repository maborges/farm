from __future__ import annotations

import enum
import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class StatusProgramaCertificacao(str, enum.Enum):
    ATIVO = "ATIVO"
    INATIVO = "INATIVO"
    SUSPENSO = "SUSPENSO"


class TipoCertificacao(str, enum.Enum):
    ORGANICO = "ORGANICO"
    GLOBALGAP = "GLOBALGAP"
    REGENAGRI = "REGENAGRI"
    ESG_INTERNO = "ESG_INTERNO"
    OUTRO = "OUTRO"


class StatusChecklistCertificacao(str, enum.Enum):
    RASCUNHO = "RASCUNHO"
    PUBLICADO = "PUBLICADO"
    ARQUIVADO = "ARQUIVADO"


class ResultadoAvaliacao(str, enum.Enum):
    APROVADO = "APROVADO"
    APROVADO_COM_RESSALVA = "APROVADO_COM_RESSALVA"
    REPROVADO = "REPROVADO"
    PENDENTE = "PENDENTE"


class TipoEvidencia(str, enum.Enum):
    DOCUMENTO_PDF = "DOCUMENTO_PDF"
    FOTO_CAMPO = "FOTO_CAMPO"
    DADO_SATELITE = "DADO_SATELITE"
    OUTRO = "OUTRO"


class SeveridadeNaoConformidade(str, enum.Enum):
    MENOR = "MENOR"
    MAIOR = "MAIOR"
    CRITICA = "CRITICA"


class StatusNaoConformidade(str, enum.Enum):
    ABERTA = "ABERTA"
    EM_ANALISE = "EM_ANALISE"
    EM_CORRECAO = "EM_CORRECAO"
    RESOLVIDA = "RESOLVIDA"
    CANCELADA = "CANCELADA"


class PrioridadePlanoAcao(str, enum.Enum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    URGENTE = "URGENTE"


class StatusPlanoAcao(str, enum.Enum):
    PENDENTE = "PENDENTE"
    EM_ANDAMENTO = "EM_ANDAMENTO"
    CONCLUIDO = "CONCLUIDO"
    ATRASADO = "ATRASADO"
    CANCELADO = "CANCELADO"


class StatusRelatorioESG(str, enum.Enum):
    RASCUNHO = "RASCUNHO"
    EM_REVISAO = "EM_REVISAO"
    PUBLICADO = "PUBLICADO"
    CANCELADO = "CANCELADO"


class StatusPassaporte(str, enum.Enum):
    RASCUNHO = "RASCUNHO"
    EM_VALIDACAO = "EM_VALIDACAO"
    PUBLICADO = "PUBLICADO"
    REVOGADO = "REVOGADO"


class TipoEventoPassaporte(str, enum.Enum):
    GERADO = "GERADO"
    VALIDADO = "VALIDADO"
    PUBLICADO = "PUBLICADO"
    REVOGADO = "REVOGADO"
    ATUALIZADO = "ATUALIZADO"


status_programa_enum = sa.Enum(StatusProgramaCertificacao, name="status_programa_enum")
tipo_certificacao_enum = sa.Enum(TipoCertificacao, name="tipo_certificacao_enum")
status_checklist_enum = sa.Enum(StatusChecklistCertificacao, name="status_checklist_enum")
resultado_avaliacao_enum = sa.Enum(ResultadoAvaliacao, name="resultado_avaliacao_enum")
tipo_evidencia_enum = sa.Enum(TipoEvidencia, name="tipo_evidencia_enum")
severidade_nao_conformidade_enum = sa.Enum(
    SeveridadeNaoConformidade, name="severidade_nao_conformidade_enum"
)
status_nao_conformidade_enum = sa.Enum(
    StatusNaoConformidade, name="status_nao_conformidade_enum"
)
prioridade_plano_acao_enum = sa.Enum(PrioridadePlanoAcao, name="prioridade_plano_acao_enum")
status_plano_acao_enum = sa.Enum(StatusPlanoAcao, name="status_plano_acao_enum")
status_relatorio_esg_enum = sa.Enum(StatusRelatorioESG, name="status_relatorio_esg_enum")
status_passaporte_enum = sa.Enum(StatusPassaporte, name="status_passaporte_enum")
tipo_evento_passaporte_enum = sa.Enum(TipoEventoPassaporte, name="tipo_evento_passaporte_enum")


class ProgramaCertificacao(Base):
    __tablename__ = "certificacao_programas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    propriedade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_propriedades.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    imovel_rural_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("imoveis_rurais.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_imovel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("propriedade_imovel.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo_certificacao: Mapped[TipoCertificacao] = mapped_column(
        tipo_certificacao_enum, nullable=False
    )
    status_programa: Mapped[StatusProgramaCertificacao] = mapped_column(
        status_programa_enum, nullable=False
    )
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    organismo_certificador: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    escopo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.func.current_timestamp(),
    )

    checklists: Mapped[List["ChecklistCertificacao"]] = relationship(
        back_populates="programa",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_certificacao_programas_tenant_status", "tenant_id", "status_programa"),
        Index("ix_certificacao_programas_tenant_tipo", "tenant_id", "tipo_certificacao"),
        CheckConstraint(
            "data_fim IS NULL OR data_fim >= data_inicio",
            name="ck_certificacao_programas_datas_validas",
        ),
    )


class ChecklistCertificacao(Base):
    __tablename__ = "certificacao_checklists"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    programa_certificacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("certificacao_programas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    norma_versao: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status_checklist: Mapped[StatusChecklistCertificacao] = mapped_column(
        status_checklist_enum, nullable=False
    )
    percentual_conformidade: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        server_default=sa.text("0"),
    )
    data_abertura: Mapped[date] = mapped_column(Date, nullable=False)
    data_fechamento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.func.current_timestamp(),
    )

    programa: Mapped["ProgramaCertificacao"] = relationship(back_populates="checklists", lazy="noload")
    criterios: Mapped[List["CriterioCertificacao"]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="noload",
    )
    avaliacoes: Mapped[List["AvaliacaoCertificacao"]] = relationship(
        back_populates="checklist",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="noload",
    )

    __table_args__ = (
        CheckConstraint(
            "percentual_conformidade BETWEEN 0 AND 100",
            name="ck_certificacao_checklists_percentual_conformidade",
        ),
        Index("ix_certificacao_checklists_tenant_status", "tenant_id", "status_checklist"),
    )


class CriterioCertificacao(Base):
    __tablename__ = "certificacao_criterios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checklist_certificacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("certificacao_checklists.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    codigo: Mapped[str] = mapped_column(String(80), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    peso: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    obrigatorio: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("TRUE"),
    )
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.func.current_timestamp(),
    )

    checklist: Mapped["ChecklistCertificacao"] = relationship(back_populates="criterios", lazy="noload")

    __table_args__ = (
        CheckConstraint("peso >= 0", name="ck_certificacao_criterios_peso_nao_negativo"),
        Index("ix_certificacao_criterios_tenant_codigo", "tenant_id", "codigo"),
        sa.UniqueConstraint(
            "tenant_id",
            "checklist_certificacao_id",
            "codigo",
            name="uq_certificacao_criterios_codigo_por_checklist",
        ),
    )


class AvaliacaoCertificacao(Base):
    __tablename__ = "certificacao_avaliacoes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    checklist_certificacao_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("certificacao_checklists.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    avaliador_pessoa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cadastros_pessoas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    resultado_avaliacao: Mapped[ResultadoAvaliacao] = mapped_column(
        resultado_avaliacao_enum, nullable=False
    )
    nota: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    parecer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.func.current_timestamp(),
    )

    checklist: Mapped["ChecklistCertificacao"] = relationship(back_populates="avaliacoes", lazy="noload")

    __table_args__ = (
        CheckConstraint("nota >= 0", name="ck_certificacao_avaliacoes_nota_nao_negativa"),
        Index("ix_certificacao_avaliacoes_tenant_resultado", "tenant_id", "resultado_avaliacao"),
        Index(
            "ix_certificacao_avaliacoes_checklist_avaliador",
            "checklist_certificacao_id",
            "avaliador_pessoa_id",
        ),
    )


class EvidenciaCertificacao(Base):
    __tablename__ = "certificacao_evidencias"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    programa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("certificacao_programas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    checklist_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_checklists.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    criterio_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_criterios.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    avaliacao_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_avaliacoes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_propriedades.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    imovel_rural_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("imoveis_rurais.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_imovel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("propriedade_imovel.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    responsavel_pessoa_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_pessoas.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    tipo_evidencia: Mapped[TipoEvidencia] = mapped_column(tipo_evidencia_enum, nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    origem_tipo: Mapped[str] = mapped_column(String(80), nullable=False)
    origem_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)
    arquivo_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    arquivo_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    snapshot_json: Mapped[Optional[dict]] = mapped_column(sa.JSON, nullable=True)
    snapshot_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    publico: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("FALSE"),
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.func.current_timestamp(),
    )

    __table_args__ = (
        CheckConstraint("btrim(titulo) <> ''", name="ck_certificacao_evidencias_titulo_nao_vazio"),
        CheckConstraint(
            "snapshot_json IS NULL OR snapshot_hash IS NOT NULL",
            name="ck_certificacao_evidencias_snapshot_hash_dependente",
        ),
        CheckConstraint(
            "arquivo_url IS NULL OR arquivo_hash IS NOT NULL",
            name="ck_certificacao_evidencias_arquivo_hash_dependente",
        ),
        CheckConstraint(
            "(origem_tipo IS NULL) = (origem_id IS NULL)",
            name="ck_certificacao_evidencias_origem_consistente",
        ),
        Index("ix_certificacao_evidencias_tenant_programa", "tenant_id", "programa_id"),
        Index("ix_certificacao_evidencias_tenant_tipo", "tenant_id", "tipo_evidencia"),
        Index("ix_certificacao_evidencias_tenant_publico", "tenant_id", "publico"),
    )


class NaoConformidadeCertificacao(Base):
    __tablename__ = "certificacao_nao_conformidades"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    programa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("certificacao_programas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    checklist_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_checklists.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    criterio_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_criterios.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    avaliacao_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_avaliacoes.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    evidencia_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_evidencias.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_propriedades.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    imovel_rural_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("imoveis_rurais.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_imovel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("propriedade_imovel.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    responsavel_pessoa_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_pessoas.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    severidade: Mapped[SeveridadeNaoConformidade] = mapped_column(
        severidade_nao_conformidade_enum,
        nullable=False,
    )
    status: Mapped[StatusNaoConformidade] = mapped_column(
        status_nao_conformidade_enum,
        nullable=False,
    )
    detectada_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    prazo_correcao: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolvida_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.func.current_timestamp(),
    )

    __table_args__ = (
        CheckConstraint("btrim(titulo) <> ''", name="ck_certificacao_nc_titulo_nao_vazio"),
        CheckConstraint(
            "prazo_correcao IS NULL OR prazo_correcao >= detectada_em",
            name="ck_certificacao_nc_prazo_correcao_valido",
        ),
        CheckConstraint(
            "resolvida_em IS NULL OR resolvida_em >= detectada_em",
            name="ck_certificacao_nc_resolucao_valida",
        ),
        Index("ix_certificacao_nc_tenant_programa", "tenant_id", "programa_id"),
        Index("ix_certificacao_nc_tenant_status", "tenant_id", "status"),
        Index("ix_certificacao_nc_tenant_severidade", "tenant_id", "severidade"),
        Index("ix_certificacao_nc_tenant_prazo", "tenant_id", "prazo_correcao"),
    )


class PlanoAcaoCertificacao(Base):
    __tablename__ = "certificacao_planos_acao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    programa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("certificacao_programas.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    nao_conformidade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_nao_conformidades.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    evidencia_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_evidencias.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    responsavel_pessoa_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_pessoas.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_propriedades.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    imovel_rural_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("imoveis_rurais.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_imovel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("propriedade_imovel.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    prioridade: Mapped[PrioridadePlanoAcao] = mapped_column(
        prioridade_plano_acao_enum,
        nullable=False,
    )
    status: Mapped[StatusPlanoAcao] = mapped_column(status_plano_acao_enum, nullable=False)
    prazo: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    concluido_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.func.current_timestamp(),
    )

    __table_args__ = (
        CheckConstraint("btrim(titulo) <> ''", name="ck_certificacao_pa_titulo_nao_vazio"),
        CheckConstraint(
            "concluido_em IS NULL OR concluido_em >= created_at",
            name="ck_certificacao_pa_conclusao_valida",
        ),
        Index("ix_certificacao_pa_tenant_programa", "tenant_id", "programa_id"),
        Index("ix_certificacao_pa_tenant_status", "tenant_id", "status"),
        Index("ix_certificacao_pa_tenant_prioridade", "tenant_id", "prioridade"),
        Index("ix_certificacao_pa_tenant_prazo", "tenant_id", "prazo"),
    )


class RelatorioESG(Base):
    __tablename__ = "esg_relatorios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    programa_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_programas.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_propriedades.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    imovel_rural_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("imoveis_rurais.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_imovel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("propriedade_imovel.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    responsavel_pessoa_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_pessoas.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    periodo_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    periodo_fim: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[StatusRelatorioESG] = mapped_column(status_relatorio_esg_enum, nullable=False)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sa.text("1"))
    snapshot_json: Mapped[Optional[dict]] = mapped_column(sa.JSON, nullable=True)
    snapshot_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    publico: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("FALSE"),
    )
    publicado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.func.current_timestamp(),
    )

    indicadores: Mapped[List["RelatorioESGIndicador"]] = relationship(
        back_populates="relatorio",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="noload",
    )
    evidencias: Mapped[List["RelatorioESGEvidencia"]] = relationship(
        back_populates="relatorio",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="noload",
    )

    __table_args__ = (
        CheckConstraint("btrim(titulo) <> ''", name="ck_esg_relatorios_titulo_nao_vazio"),
        CheckConstraint(
            "(periodo_inicio IS NULL AND periodo_fim IS NULL) OR (periodo_inicio <= periodo_fim)",
            name="ck_esg_relatorios_periodo_valido",
        ),
        CheckConstraint("versao >= 1", name="ck_esg_relatorios_versao_minima"),
        CheckConstraint(
            "(publico IS FALSE AND publicado_em IS NULL) OR (snapshot_json IS NOT NULL AND snapshot_hash IS NOT NULL)",
            name="ck_esg_relatorios_snapshot_publicado",
        ),
        CheckConstraint(
            "(status != 'PUBLICADO') OR (publicado_em IS NOT NULL)",
            name="ck_esg_relatorios_publicado_em_obrigatorio",
        ),
        CheckConstraint(
            "status <> 'CANCELADO' OR cancelado_em IS NOT NULL",
            name="ck_esg_relatorios_cancelado_em_obrigatorio",
        ),
        Index("ix_esg_relatorios_tenant_status", "tenant_id", "status"),
        Index("ix_esg_relatorios_tenant_publico", "tenant_id", "publico"),
        Index("ix_esg_relatorios_programa_id", "programa_id"),
        Index("ix_esg_relatorios_propriedade_id", "propriedade_id"),
        Index("ix_esg_relatorios_imovel_rural_id", "imovel_rural_id"),
        Index("ix_esg_relatorios_propriedade_imovel_id", "propriedade_imovel_id"),
    )


class RelatorioESGIndicador(Base):
    __tablename__ = "esg_relatorio_indicadores"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relatorio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("esg_relatorios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidencia_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_evidencias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    categoria: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    valor: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    unidade: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    score: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    metodologia: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.func.current_timestamp(),
    )

    relatorio: Mapped["RelatorioESG"] = relationship(back_populates="indicadores", lazy="noload")

    __table_args__ = (
        CheckConstraint("btrim(nome) <> ''", name="ck_esg_relatorio_indicadores_nome_nao_vazio"),
        CheckConstraint("valor IS NULL OR valor >= 0", name="ck_esg_relatorio_indicadores_valor_nao_negativo"),
        CheckConstraint("score IS NULL OR score >= 0", name="ck_esg_relatorio_indicadores_score_nao_negativo"),
        Index("ix_esg_relatorio_indicadores_tenant_relatorio", "tenant_id", "relatorio_id"),
        Index("ix_esg_relatorio_indicadores_evidencia_id", "evidencia_id"),
    )


class RelatorioESGEvidencia(Base):
    __tablename__ = "esg_relatorio_evidencias"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relatorio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("esg_relatorios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("certificacao_evidencias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    relatorio: Mapped["RelatorioESG"] = relationship(back_populates="evidencias", lazy="noload")

    __table_args__ = (
        Index("ix_esg_relatorio_evidencias_tenant_relatorio", "tenant_id", "relatorio_id"),
        Index("ix_esg_relatorio_evidencias_evidencia_id", "evidencia_id"),
    )


class PassaporteRastreabilidade(Base):
    __tablename__ = "rastreabilidade_passaportes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    programa_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("certificacao_programas.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_propriedades.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    imovel_rural_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("imoveis_rurais.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    propriedade_imovel_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("propriedade_imovel.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    lote_rastreabilidade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("lotes_rastreabilidade.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    caderno_lote_comercial_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("caderno_lotes_comerciais.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    responsavel_pessoa_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cadastros_pessoas.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[StatusPassaporte] = mapped_column(status_passaporte_enum, nullable=False)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, server_default=sa.text("1"))
    snapshot_json: Mapped[Optional[dict]] = mapped_column(sa.JSON, nullable=True)
    snapshot_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    publico: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("FALSE"),
    )
    public_token: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid(as_uuid=True),
        unique=True,
        index=True,
        nullable=True,
    )
    publicado_publicamente_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    publicado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revogado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
        onupdate=sa.func.current_timestamp(),
    )

    # lazy default (não "noload"): estas duas relações são carregadas via
    # selectinload() explícito em public_router.py — "noload" no mapper
    # bloquearia esses eager-loads explícitos.
    eventos: Mapped[List["PassaporteRastreabilidadeEvento"]] = relationship(
        back_populates="passaporte",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    evidencias: Mapped[List["PassaporteRastreabilidadeEvidencia"]] = relationship(
        back_populates="passaporte",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint("btrim(titulo) <> ''", name="ck_rastreabilidade_passaportes_titulo_nao_vazio"),
        CheckConstraint("versao >= 1", name="ck_rastreabilidade_passaportes_versao_minima"),
        CheckConstraint(
            "status <> 'PUBLICADO' OR snapshot_hash IS NOT NULL",
            name="ck_rastreabilidade_passaportes_snapshot_publicado",
        ),
        CheckConstraint(
            "status <> 'PUBLICADO' OR publicado_em IS NOT NULL",
            name="ck_rastreabilidade_passaportes_publicado_em_obrigatorio",
        ),
        CheckConstraint(
            "status <> 'REVOGADO' OR revogado_em IS NOT NULL",
            name="ck_rastreabilidade_passaportes_revogado_em_obrigatorio",
        ),
        Index("ix_rastreabilidade_passaportes_tenant_status", "tenant_id", "status"),
        Index("ix_rastreabilidade_passaportes_tenant_publico", "tenant_id", "publico"),
        Index("ix_rastreabilidade_passaportes_programa_id", "programa_id"),
        Index("ix_rastreabilidade_passaportes_propriedade_id", "propriedade_id"),
        Index("ix_rastreabilidade_passaportes_imovel_rural_id", "imovel_rural_id"),
        Index("ix_rastreabilidade_passaportes_propriedade_imovel_id", "propriedade_imovel_id"),
        Index("ix_rastreabilidade_passaportes_lote_rastreabilidade_id", "lote_rastreabilidade_id"),
        Index("ix_rastreabilidade_passaportes_caderno_lote_comercial_id", "caderno_lote_comercial_id"),
    )


class PassaporteRastreabilidadeEvento(Base):
    __tablename__ = "rastreabilidade_passaporte_eventos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    passaporte_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rastreabilidade_passaportes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_evento: Mapped[TipoEventoPassaporte] = mapped_column(
        tipo_evento_passaporte_enum,
        nullable=False,
    )
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    origem_tipo: Mapped[str] = mapped_column(String(80), nullable=False)
    origem_id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), nullable=False)
    snapshot_json: Mapped[Optional[dict]] = mapped_column(sa.JSON, nullable=True)
    snapshot_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    passaporte: Mapped["PassaporteRastreabilidade"] = relationship(back_populates="eventos", lazy="noload")

    __table_args__ = (
        CheckConstraint("btrim(titulo) <> ''", name="ck_passaporte_eventos_titulo_nao_vazio"),
        CheckConstraint(
            "snapshot_json IS NULL OR snapshot_hash IS NOT NULL",
            name="ck_passaporte_eventos_snapshot_hash_dependente",
        ),
        Index("ix_passaporte_eventos_tenant_passaporte", "tenant_id", "passaporte_id"),
        Index("ix_passaporte_eventos_tenant_tipo_evento", "tenant_id", "tipo_evento"),
        Index("ix_passaporte_eventos_tipo_evento", "tipo_evento"),
    )


class PassaporteRastreabilidadeEvidencia(Base):
    __tablename__ = "rastreabilidade_passaporte_evidencias"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    passaporte_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rastreabilidade_passaportes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidencia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("certificacao_evidencias.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    passaporte: Mapped["PassaporteRastreabilidade"] = relationship(back_populates="evidencias", lazy="noload")

    __table_args__ = (
        Index("ix_passaporte_evidencias_tenant_passaporte", "tenant_id", "passaporte_id"),
        Index("ix_passaporte_evidencias_evidencia_id", "evidencia_id"),
    )
