from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Numeric, Boolean, DateTime, ForeignKey, text, Uuid, JSON
from uuid import UUID
import uuid
from datetime import datetime
from core.database import Base

# Import necessary models so SQLAlchemy can resolve foreign keys during flush
import agricola.romaneios.models
import core.cadastros.pessoas.models
import core.cadastros.produtos.models
import core.models.auth
import imoveis.models.imovel

class QualidadeProtocolo(Base):
    __tablename__ = "operacional_qualidade_protocolos"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    commodity_id: Mapped[UUID | None] = mapped_column(ForeignKey("cadastros_commodities.id", ondelete="SET NULL"), nullable=True, index=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow)

    # Relacionamentos
    criterios: Mapped[list["QualidadeCriterio"]] = relationship(
        "QualidadeCriterio",
        back_populates="protocolo",
        cascade="all, delete-orphan"
    )

class QualidadeCriterio(Base):
    __tablename__ = "operacional_qualidade_criterios"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    protocolo_id: Mapped[UUID] = mapped_column(ForeignKey("operacional_qualidade_protocolos.id", ondelete="CASCADE"), nullable=False, index=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo_dado: Mapped[str] = mapped_column(String(20), nullable=False, comment="NUMERIC, ENUM, BOOLEAN")
    unidade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    min_aceitavel: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    max_aceitavel: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    valor_padrao: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    regra_ajuste_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow)

    # Relacionamentos
    protocolo: Mapped["QualidadeProtocolo"] = relationship("QualidadeProtocolo", back_populates="criterios")

class QualidadeLaudo(Base):
    __tablename__ = "operacional_qualidade_laudos"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    unidade_produtiva_id: Mapped[UUID | None] = mapped_column(ForeignKey("production_units.id", ondelete="SET NULL"), nullable=True)
    protocolo_id: Mapped[UUID] = mapped_column(ForeignKey("operacional_qualidade_protocolos.id", ondelete="RESTRICT"), nullable=False, index=True)
    romaneio_id: Mapped[UUID | None] = mapped_column(ForeignKey("romaneios_colheita.id", ondelete="CASCADE"), nullable=True, index=True)
    avaliador_id: Mapped[UUID | None] = mapped_column(ForeignKey("cadastros_pessoas.id", ondelete="SET NULL"), nullable=True)
    
    data_avaliacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="RASCUNHO", nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow)

    # Relacionamentos
    protocolo: Mapped["QualidadeProtocolo"] = relationship("QualidadeProtocolo")
    resultados: Mapped[list["QualidadeResultado"]] = relationship(
        "QualidadeResultado",
        back_populates="laudo",
        cascade="all, delete-orphan"
    )
    ajustes: Mapped[list["QualidadeAjuste"]] = relationship(
        "QualidadeAjuste",
        back_populates="laudo",
        cascade="all, delete-orphan"
    )

class QualidadeResultado(Base):
    __tablename__ = "operacional_qualidade_resultados"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    laudo_id: Mapped[UUID] = mapped_column(ForeignKey("operacional_qualidade_laudos.id", ondelete="CASCADE"), nullable=False, index=True)
    criterio_id: Mapped[UUID] = mapped_column(ForeignKey("operacional_qualidade_criterios.id", ondelete="RESTRICT"), nullable=False, index=True)
    
    valor_numerico: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    valor_texto: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    updated_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow)

    # Relacionamentos
    laudo: Mapped["QualidadeLaudo"] = relationship("QualidadeLaudo", back_populates="resultados")
    criterio: Mapped["QualidadeCriterio"] = relationship("QualidadeCriterio")

class QualidadeAjuste(Base):
    __tablename__ = "operacional_qualidade_ajustes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    laudo_id: Mapped[UUID] = mapped_column(ForeignKey("operacional_qualidade_laudos.id", ondelete="CASCADE"), nullable=False, index=True)
    criterio_id: Mapped[UUID | None] = mapped_column(ForeignKey("operacional_qualidade_criterios.id", ondelete="SET NULL"), nullable=True)
    
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    valor_numerico: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    valor_unidade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)

    # Relacionamentos
    laudo: Mapped["QualidadeLaudo"] = relationship("QualidadeLaudo", back_populates="ajustes")
    criterio: Mapped["QualidadeCriterio"] = relationship("QualidadeCriterio")
