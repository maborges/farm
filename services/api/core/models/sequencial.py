import uuid
from sqlalchemy import String, Integer, UniqueConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID
from core.database import Base


class SequencialContador(Base):
    """Contador de sequência por tenant/entidade/ano, usado para gerar
    códigos de referência legíveis (ex: PED-2026-000123).

    Ver core/sequenciais_config.py e core/services/sequencial_service.py.
    """
    __tablename__ = "core_sequenciais"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)

    entidade: Mapped[str] = mapped_column(String(50), nullable=False)
    ano: Mapped[int | None] = mapped_column(Integer, nullable=True)  # nulo quando escopo=GLOBAL
    ultimo_numero: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "entidade", "ano", name="uq_core_sequenciais_tenant_entidade_ano"),
    )
