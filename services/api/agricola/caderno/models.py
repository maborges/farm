from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Date, DateTime, Text, ForeignKey, text, Uuid, Numeric, JSON, UniqueConstraint, Index
from uuid import UUID
import uuid
from datetime import datetime, date
from core.database import Base


class CadernoCampoEntrada(Base):
    __tablename__ = "caderno_campo_entradas"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "origem_evento",
            "origem_id",
            name="uq_caderno_campo_origem_evento",
        ),
        Index("ix_caderno_campo_origem_invalidada", "tenant_id", "origem_invalidada"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    safra_id: Mapped[UUID] = mapped_column(ForeignKey("safras.id", ondelete="CASCADE"), nullable=False, index=True)
    talhao_id: Mapped[UUID] = mapped_column(ForeignKey("cadastros_areas_rurais.id", ondelete="CASCADE"), nullable=False, index=True)

    # Tipo canônico do evento
    tipo: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    tipo_evento: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    data_registro: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    usuario_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    executado_por_pessoa_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("cadastros_pessoas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Referência opcional à operação agrícola que gerou esta entrada automaticamente
    operacao_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("operacoes_agricolas.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Auditoria
    ip_dispositivo: Mapped[str | None] = mapped_column(String(100))
    origem_evento: Mapped[str | None] = mapped_column(String(40), index=True)
    origem_id: Mapped[str | None] = mapped_column(String(80), index=True)
    origem_tecnica: Mapped[str | None] = mapped_column(String(40), index=True)
    device_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    unidade_produtiva_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    client_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    client_updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    payload_operacional: Mapped[dict | None] = mapped_column(JSON, default=dict)
    status_evento: Mapped[str] = mapped_column(String(30), nullable=False, default="CONSOLIDADO")
    excluida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    motivo_exclusao: Mapped[str | None] = mapped_column(Text)
    digitalizacao_retroativa: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    justificativa_retroativa: Mapped[str | None] = mapped_column(Text)
    retifica_evento_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("caderno_campo_entradas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    retificado_por_evento_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("caderno_campo_entradas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    motivo_retificacao: Mapped[str | None] = mapped_column(Text)
    retificado_em: Mapped[datetime | None] = mapped_column(DateTime)
    retificado_por_usuario_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)

    # Invalidação documental da origem operacional
    origem_invalidada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    origem_invalidada_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    origem_invalidada_por: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    motivo_invalidacao_origem: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Campos específicos por tipo
    nivel_severidade: Mapped[str | None] = mapped_column(String(20))  # BAIXO | MEDIO | ALTO | CRITICO
    recomendacao: Mapped[str | None] = mapped_column(Text)
    numero_receituario: Mapped[str | None] = mapped_column(String(50))  # Lei 7.802/89 — texto legado
    receituario_agronomico_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("agricola_receituarios_agronomicos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="OPERATIONS-GAP-01 §21.19: vínculo opcional ao Receituário Agronômico estruturado",
    )

    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow)

    @property
    def status_evento_atualizado_em(self) -> datetime | None:
        return self.updated_at

    @property
    def documental_status(self) -> str:
        return "ORIGEM_INVALIDADA" if self.origem_invalidada else "VIGENTE"

    fotos: Mapped[list["CadernoCampoFoto"]] = relationship(
        back_populates="entrada", cascade="all, delete-orphan", lazy="selectin"
    )
    status_historico: Mapped[list["CadernoEventoStatusHistorico"]] = relationship(
        back_populates="entrada", cascade="all, delete-orphan", lazy="selectin"
    )


class CadernoCampoFoto(Base):
    __tablename__ = "caderno_campo_fotos"
    __table_args__ = (
        UniqueConstraint(
            "entrada_id",
            "device_local_id",
            name="uq_caderno_foto_device_local_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entrada_id: Mapped[UUID] = mapped_column(
        ForeignKey("caderno_campo_entradas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    data_captura: Mapped[datetime | None] = mapped_column(DateTime)
    # Rastreamento de evidência offline — garante idempotência no upload
    device_local_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    device_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    mime_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publica: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))

    entrada: Mapped["CadernoCampoEntrada"] = relationship(back_populates="fotos")


class CadernoEventoStatusHistorico(Base):
    __tablename__ = "caderno_evento_status_historico"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    caderno_entrada_id: Mapped[UUID] = mapped_column(
        ForeignKey("caderno_campo_entradas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status_anterior: Mapped[str | None] = mapped_column(String(30))
    status_novo: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    usuario_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    justificativa: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))

    entrada: Mapped["CadernoCampoEntrada"] = relationship(back_populates="status_historico")


class VisitaTecnica(Base):
    __tablename__ = "visitas_tecnicas"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    safra_id: Mapped[UUID] = mapped_column(ForeignKey("safras.id", ondelete="CASCADE"), nullable=False, index=True)
    talhao_id: Mapped[UUID] = mapped_column(
        ForeignKey("cadastros_areas_rurais.id", ondelete="CASCADE"), nullable=False, index=True
    )

    responsavel_tecnico_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    nome_rt: Mapped[str] = mapped_column(String(200), nullable=False)
    crea: Mapped[str] = mapped_column(String(30), nullable=False)
    data_visita: Mapped[date] = mapped_column(Date, nullable=False)

    observacoes: Mapped[str | None] = mapped_column(Text)
    recomendacoes: Mapped[str | None] = mapped_column(Text)
    constatacoes: Mapped[list[dict]] = mapped_column(JSON, default=list)

    # Assinatura digital
    assinado: Mapped[bool] = mapped_column(Boolean, default=False)
    data_assinatura: Mapped[datetime | None] = mapped_column(DateTime)

    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow)


class EPIEntrega(Base):
    __tablename__ = "epi_entregas"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    trabalhador_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    nome_trabalhador: Mapped[str] = mapped_column(String(200), nullable=False)

    epi_tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    quantidade: Mapped[int] = mapped_column(nullable=False, default=1)
    data_entrega: Mapped[date] = mapped_column(Date, nullable=False)
    validade: Mapped[date | None] = mapped_column(Date)

    assinatura_url: Mapped[str | None] = mapped_column(String(500))
    operacao_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))


class CadernoExportacao(Base):
    __tablename__ = "caderno_exportacoes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    safra_id: Mapped[UUID] = mapped_column(ForeignKey("safras.id", ondelete="CASCADE"), nullable=False, index=True)
    talhao_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)

    url_pdf: Mapped[str] = mapped_column(String(500), nullable=False)
    data_geracao: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    modo_exportacao: Mapped[str] = mapped_column(String(20), default="OFICIAL")
    snapshot_documental: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String(128))
    hash_documental: Mapped[str | None] = mapped_column(String(128))
    assinatura_hash: Mapped[str | None] = mapped_column(String(128))
    protocolo_documental: Mapped[str | None] = mapped_column(String(64), index=True)

    responsavel_tecnico_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    responsavel_tecnico_nome: Mapped[str | None] = mapped_column(String(200))
    responsavel_tecnico_crea: Mapped[str | None] = mapped_column(String(30))
    usuario_assinatura_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    assinado_por: Mapped[str | None] = mapped_column(String(200))
    crea_rt: Mapped[str | None] = mapped_column(String(30))
    crea_validade: Mapped[date | None] = mapped_column(Date)
    assinado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assinatura_origem: Mapped[str | None] = mapped_column(String(40))
    observacao_assinatura: Mapped[str | None] = mapped_column(Text)

    # INTERNO | GLOBALGAP | ORGANICO | MAPA
    modelo_certificacao: Mapped[str] = mapped_column(String(30), default="INTERNO")

    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
