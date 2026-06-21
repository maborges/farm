from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid as UUID

from core.database import Base
from core.cadastros.propriedades.propriedade_models import Propriedade
from imoveis.models.imovel import ImovelRural


class TipoVinculoPropriedadeImovel(str, enum.Enum):
    """Tipos oficiais de vínculo entre Propriedade e Imóvel Rural."""

    PROPRIEDADE_PRINCIPAL = "PROPRIEDADE_PRINCIPAL"
    PROPRIEDADE_SECUNDARIA = "PROPRIEDADE_SECUNDARIA"
    ARRENDAMENTO = "ARRENDAMENTO"
    PARCERIA_RURAL = "PARCERIA_RURAL"
    COMODATO = "COMODATO"
    USO_COMPARTILHADO = "USO_COMPARTILHADO"
    USO_TEMPORARIO = "USO_TEMPORARIO"
    INTEGRACAO = "INTEGRACAO"
    OUTRO = "OUTRO"


class PropriedadeImovel(Base):
    """Vínculo canônico entre o domínio operacional e o domínio fundiário."""

    __tablename__ = "propriedade_imovel"
    __table_args__ = (
        CheckConstraint(
            "tipo_vinculo IN ('PROPRIEDADE_PRINCIPAL', 'PROPRIEDADE_SECUNDARIA', 'ARRENDAMENTO', 'PARCERIA_RURAL', 'COMODATO', 'USO_COMPARTILHADO', 'USO_TEMPORARIO', 'INTEGRACAO', 'OUTRO')",
            name="ck_propriedade_imovel_tipo_vinculo",
        ),
        CheckConstraint(
            "data_fim IS NULL OR data_fim >= data_inicio",
            name="ck_propriedade_imovel_datas_validas",
        ),
        CheckConstraint(
            "percentual_vinculado IS NULL OR (percentual_vinculado >= 0 AND percentual_vinculado <= 100)",
            name="ck_propriedade_imovel_percentual_intervalo",
        ),
        CheckConstraint(
            "area_vinculada IS NULL OR area_vinculada >= 0",
            name="ck_propriedade_imovel_area_nao_negativa",
        ),
        Index("ix_propriedade_imovel_tenant_id", "tenant_id"),
        Index("ix_propriedade_imovel_propriedade_id", "propriedade_id"),
        Index("ix_propriedade_imovel_imovel_rural_id", "imovel_rural_id"),
        Index("ix_propriedade_imovel_tenant_propriedade", "tenant_id", "propriedade_id"),
        Index("ix_propriedade_imovel_tenant_imovel_rural", "tenant_id", "imovel_rural_id"),
        Index("ix_propriedade_imovel_tipo_vinculo", "tipo_vinculo"),
        Index("ix_propriedade_imovel_ativo", "ativo"),
        Index("ix_propriedade_imovel_data_inicio", "data_inicio"),
        Index("ix_propriedade_imovel_data_fim", "data_fim"),
        Index("ix_propriedade_imovel_vinculo_principal", "vinculo_principal"),
        Index(
            "uq_propriedade_imovel_principal_ativo",
            "tenant_id",
            "propriedade_id",
            unique=True,
            postgresql_where=text("vinculo_principal IS TRUE AND ativo IS TRUE AND data_fim IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    propriedade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_propriedades.id", ondelete="RESTRICT"), nullable=False
    )
    imovel_rural_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imoveis_rurais.id", ondelete="RESTRICT"), nullable=False
    )
    tipo_vinculo: Mapped[str] = mapped_column(String(40), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    origem_documental: Mapped[str] = mapped_column(Text, nullable=False)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_vinculada: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    percentual_vinculado: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    vinculo_principal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    origem_referencia: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_documental: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"))

    propriedade: Mapped[Propriedade] = relationship("Propriedade", back_populates="propriedade_imoveis", lazy="noload")
    imovel_rural: Mapped[ImovelRural] = relationship("ImovelRural", back_populates="propriedade_imoveis", lazy="noload")
