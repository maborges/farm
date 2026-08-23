import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint, text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ModeloZoosanitario(Base):
    """Armazena as regras e pesos para cálculo de estresse térmico e ectoparasitas por espécie."""
    __tablename__ = "modelos_zoosanitarios"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "especie",
            "tipo_risco",
            name="uq_modelos_zoo_especie_risco",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True)
    especie: Mapped[str] = mapped_column(String(100), nullable=False, index=True) # Bovino de Leite, Bovino de Corte, etc
    tipo_risco: Mapped[str] = mapped_column(String(150), nullable=False) # Ex: Estresse Térmico, Mosca do Chifre
    
    # Ex: {"temp_min": 20, "umidade_min": 85, "condicoes": [{"variavel": "ITH", "operador": ">=", "valor": 72}]}
    regras_risco: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    is_global: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
