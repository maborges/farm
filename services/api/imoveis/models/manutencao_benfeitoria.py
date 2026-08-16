import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Text, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID
from core.database import Base


class PlanoManutencaoBenfeitoria(Base):
    """Regra de periodicidade de manutenção de uma benfeitoria (OPERATIONS-GAP-01 §21.33).

    Espelha `operacional/models/frota.py::PlanoManutencao`, mas sem
    horímetro/km — não fazem sentido para uma cerca, silo ou galpão.
    Módulo paralelo e independente do de frota (não generaliza os models
    de frota, que são fortemente acoplados a `equipamento_id` em várias
    services de negócio); zero risco de regressão em frota.
    """
    __tablename__ = "imoveis_planos_manutencao_benfeitoria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    benfeitoria_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imoveis_benfeitorias.id", ondelete="CASCADE"), nullable=False, index=True
    )

    descricao: Mapped[str] = mapped_column(String(150), nullable=False)
    frequencia_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ultimo_registro_data: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_imoveis_planos_manut_tenant_benfeitoria", "tenant_id", "benfeitoria_id"),
    )


class OrdemServicoBenfeitoria(Base):
    """Workflow de manutenção de uma benfeitoria — equivalente simplificado de `OrdemServico` de frota."""
    __tablename__ = "imoveis_ordens_servico_benfeitoria"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    benfeitoria_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imoveis_benfeitorias.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plano_manutencao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("imoveis_planos_manutencao_benfeitoria.id", ondelete="SET NULL"), nullable=True
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    talhao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"), nullable=True, index=True
    )

    numero_os: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(30), comment="PREVENTIVA | CORRETIVA")
    status: Mapped[str] = mapped_column(String(20), default="ABERTA", comment="ABERTA | EM_EXECUCAO | CONCLUIDA | CANCELADA")

    descricao_problema: Mapped[str] = mapped_column(String(500), nullable=False)

    data_abertura: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    data_conclusao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aberta_por_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    encerrada_por_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    custo_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0)

    __table_args__ = (
        Index("ix_imoveis_os_benfeitoria_tenant_benfeitoria", "tenant_id", "benfeitoria_id"),
        Index("ix_imoveis_os_benfeitoria_tenant_status", "tenant_id", "status"),
    )
