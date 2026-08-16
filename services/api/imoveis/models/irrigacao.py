"""Sistema de Irrigação — infraestrutura fixa do imóvel rural (OPERATIONS-GAP-01 §21.34).

Reposicionado a partir do stub morto em `agricola/ndvi_avancado/` (nunca funcionou:
model só tinha id/tenant_id, service vazio, router retornava listas/dicts fixos,
código síncrono legado). Aqui vive junto de `Benfeitoria`, que é o domínio real
de infraestrutura fixa do imóvel (imoveis/models/imovel.py).
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID

from core.database import Base


class SistemaIrrigacao(Base):
    __tablename__ = "imoveis_sistemas_irrigacao"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    imovel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imoveis_rurais.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unidades_produtivas.id", ondelete="SET NULL"), nullable=True, index=True
    )

    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)  # PIVO_CENTRAL, GOTEJAMENTO, ASPERSAO, MICROASPERSAO, SULCO, OUTRO
    fonte_agua: Mapped[str | None] = mapped_column(String(30), nullable=True)  # POCO, RIO, ACUDE, REDE_PUBLICA, ACUDE_PARTICULAR

    area_irrigada_ha: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    vazao_m3h: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    pressao_bar: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    potencia_motor_cv: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ATIVO")  # ATIVO, INATIVO, MANUTENCAO
    data_instalacao: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
