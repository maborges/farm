import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, Text, Numeric, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID

from core.database import Base


class TipoServico(Base):
    """Cadastro mestre de tipos de serviço (mão de obra terceirizada, prestação de serviço).

    Serve como origem de custo tipo SERVICO no orçamento de safra
    (agricola/a1_planejamento), análogo a Produto/Equipamento/ColaboradorRH.
    """
    __tablename__ = "cadastros_tipos_servico"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    """NULL = catálogo global (sugestão padrão, visível a todos os tenants); ver Produto/Marca/CategoriaProduto."""

    nome: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    unidade_medida: Mapped[str] = mapped_column(String(20), nullable=False, default="UN")
    custo_referencia: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("ix_cadastros_tipos_servico_tenant_nome", tenant_id, nome),
    )
