import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class LandingEvento(Base):
    """Eventos de visitantes anônimos na landing page — sem tenant_id."""

    __tablename__ = "growth_landing_eventos"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sessao_id: Mapped[str] = mapped_column(String(100), nullable=False)
    evento: Mapped[str] = mapped_column(String(60), nullable=False)
    device: Mapped[str | None] = mapped_column(String(20), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(100), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(100), nullable=True)
    headline_variant: Mapped[str | None] = mapped_column(String(5), nullable=True)
    path: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_landing_evento_nome", "evento"),
        Index("ix_landing_evento_created_at", "created_at"),
        Index("ix_landing_evento_variant", "headline_variant"),
        Index("ix_landing_evento_sessao", "sessao_id"),
    )
