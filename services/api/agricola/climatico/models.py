import uuid
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import JSON, Date, ForeignKey, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class RegistroClima(Base):
    __tablename__ = "registros_clima"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "unidade_produtiva_id",
            "data_registro",
            "fonte",
            name="uq_registros_clima_tenant_unidade_data_fonte",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    unidade_produtiva_id: Mapped[UUID] = mapped_column(ForeignKey("unidades_produtivas.id", ondelete="CASCADE"), nullable=False, index=True)

    data_registro: Mapped[date] = mapped_column(Date, nullable=False)

    precipitacao_mm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    temp_max_c: Mapped[float | None] = mapped_column(Numeric(5, 2))
    temp_min_c: Mapped[float | None] = mapped_column(Numeric(5, 2))
    temp_media_c: Mapped[float | None] = mapped_column(Numeric(5, 2))
    umidade_rel_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    evapotranspiracao_mm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    vento_kmh: Mapped[float | None] = mapped_column(Numeric(5, 2))

    gdu_calculado: Mapped[float | None] = mapped_column(Numeric(5, 2)) # Graus-Dia Acumulados diário (Base 10 graus ex)

    fonte: Mapped[str] = mapped_column(String(50), default="ESTACAO_LOCAL") # ou OPEN_METEO

    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))


class PrevisaoClima(Base):
    __tablename__ = "previsoes_clima"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "unidade_produtiva_id",
            "data_previsao",
            name="uq_previsoes_clima_tenant_unidade_data",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    unidade_produtiva_id: Mapped[UUID] = mapped_column(ForeignKey("unidades_produtivas.id", ondelete="CASCADE"), nullable=False, index=True)

    data_previsao: Mapped[date] = mapped_column(Date, nullable=False)

    precipitacao_mm: Mapped[float | None] = mapped_column(Numeric(6, 2))
    temp_max_c: Mapped[float | None] = mapped_column(Numeric(5, 2))
    temp_min_c: Mapped[float | None] = mapped_column(Numeric(5, 2))
    probabilidade_chuva_pct: Mapped[float | None] = mapped_column(Numeric(5, 2))
    periodos: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")

    atualizado_em: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow)
