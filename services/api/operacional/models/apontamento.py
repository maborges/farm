import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, ForeignKeyConstraint, Float, Numeric, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid as UUID
from core.database import Base


class TurnoEnum(str, enum.Enum):
    MANHA = "MANHA"
    TARDE = "TARDE"
    NOITE = "NOITE"
    INTEGRAL = "INTEGRAL"


class ApontamentoUso(Base):
    """
    Diário de bordo: registra uso de equipamento por operador/turno.

    - Atualiza automaticamente horimetro_atual e km_atual do Equipamento.
    - implementos: lista de UUIDs de equipamentos do tipo IMPLEMENTO acoplados
      no turno (armazenados em JSON para evitar tabela M2M desnecessária).
    """
    __tablename__ = "frota_apontamentos_uso"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipamento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_equipamentos.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    jornada_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("frota_jornadas_equipamento.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Quem / quando
    operador_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_pessoas.id", ondelete="SET NULL"), nullable=True
    )
    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    turno: Mapped[str] = mapped_column(String(10), default="INTEGRAL", nullable=False)

    # Hodômetro / horímetro
    horimetro_inicio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    horimetro_fim: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    km_inicio: Mapped[float | None] = mapped_column(Float, nullable=True)
    km_fim: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Onde / o quê
    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unidades_produtivas.id", ondelete="SET NULL"), nullable=True
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("safras.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    production_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("production_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    talhao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"),
        nullable=True,
        comment="Talhão onde a operação foi realizada"
    )
    operacao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("operacoes_agricolas.id", ondelete="SET NULL"),
        nullable=True,
        comment="Tipo de operação realizada (plantio, pulverização, etc)"
    )
    area_ha_trabalhada: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    quantidade_produzida: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    quantidade_aplicada: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    custo_total: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    custo_por_ha: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)

    # Implementos acoplados (lista de UUIDs de Equipamento tipo IMPLEMENTO)
    implementos_ids: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="Lista de UUIDs de implementos acoplados no turno"
    )

    # Consumo declarado (opcional — pode ser lançado via Abastecimento)
    combustivel_consumido_l: Mapped[float | None] = mapped_column(Float, nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "jornada_id"],
            ["frota_jornadas_equipamento.tenant_id", "frota_jornadas_equipamento.id"],
            name="fk_fau_tenant_jornada",
            ondelete="NO ACTION",
        ),
    )


ApontamentoOperacional = ApontamentoUso


class ApontamentoMaoObra(Base):
    """
    OPERATIONS-GAP-01 §21.14: equivalente de ApontamentoUso para mão de obra
    manual (sem equipamento) — elo estruturado que faltava entre execução real
    de trabalho manual e OperacaoAgricola/CostAllocation. Diferente de
    ApontamentoUso, aqui `pessoa_id` é obrigatório e não existe equipamento_id;
    diferente de LancamentoDiaria (RH, financeiro), este registro é operacional
    (o que foi feito, onde, por quanto tempo), não o pagamento em si.
    """
    __tablename__ = "operacional_apontamentos_mao_obra"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pessoa_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_pessoas.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    data: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    turno: Mapped[str] = mapped_column(String(10), default="INTEGRAL", nullable=False)
    horas_trabalhadas: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)

    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unidades_produtivas.id", ondelete="SET NULL"), nullable=True
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    production_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("production_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    talhao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"), nullable=True
    )
    operacao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operacoes_agricolas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tipo_operacao: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Tipo de operação realizada (capina, colheita manual, etc)"
    )

    quantidade_pessoas: Mapped[int] = mapped_column(default=1, nullable=False)
    custo_hora_snapshot: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    custo_total: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
