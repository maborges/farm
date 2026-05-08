import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid as UUID
from core.database import Base
from core.cadastros.equipamentos.models import Equipamento as Maquinario  # backwards compat


class PlanoManutencao(Base):
    """Regras de periodicidade de manutenção (ex: a cada 250h ou 10.000km)."""
    __tablename__ = "frota_planos_manutencao"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipamento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_equipamentos.id", ondelete="CASCADE"), nullable=False, index=True
    )

    descricao: Mapped[str] = mapped_column(String(150), nullable=False)
    frequencia_dias: Mapped[int | None] = mapped_column(nullable=True)
    frequencia_horas: Mapped[float | None] = mapped_column(Float, nullable=True)
    frequencia_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    ultimo_registro_data: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ultimo_registro_horas: Mapped[float | None] = mapped_column(Float, default=0.0)
    ultimo_registro_km: Mapped[float | None] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    @property
    def maquinario_id(self) -> uuid.UUID:
        return self.equipamento_id

    @maquinario_id.setter
    def maquinario_id(self, value: uuid.UUID) -> None:
        self.equipamento_id = value

    from sqlalchemy import Index
    __table_args__ = (
        Index("ix_frota_planos_tenant_equip", tenant_id, equipamento_id),
    )


class OrdemServico(Base):
    """Workflow de manutenção de oficina."""
    __tablename__ = "frota_ordens_servico"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipamento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_equipamentos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plano_manutencao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_planos_manutencao.id", ondelete="SET NULL"), nullable=True, index=True
    )


    numero_os: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(30), comment="PREVENTIVA | CORRETIVA | REVISAO")
    status: Mapped[str] = mapped_column(String(20), default="ABERTA", comment="ABERTA | EM_EXECUCAO | CONCLUIDA | CANCELADA")
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    talhao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"), nullable=True, index=True
    )

    descricao_problema: Mapped[str] = mapped_column(String(500))
    diagnostico_tecnico: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    data_abertura: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    data_conclusao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    horimetro_na_abertura: Mapped[float] = mapped_column(Float, default=0.0)
    km_na_abertura: Mapped[float | None] = mapped_column(Float, nullable=True)

    tecnico_responsavel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    custo_total_pecas: Mapped[float] = mapped_column(Float, default=0.0)
    custo_mao_obra: Mapped[float] = mapped_column(Float, default=0.0)

    itens: Mapped[list["ItemOrdemServico"]] = relationship(back_populates="os", lazy="noload", cascade="all, delete-orphan")

    @property
    def maquinario_id(self) -> uuid.UUID:
        return self.equipamento_id

    @maquinario_id.setter
    def maquinario_id(self, value: uuid.UUID) -> None:
        self.equipamento_id = value

    from sqlalchemy import Index
    __table_args__ = (
        Index("ix_frota_os_tenant_equip_status", tenant_id, equipamento_id, status),
    )


class ItemOrdemServico(Base):
    """Peças e insumos consumidos na OS — baixa o estoque de almoxarifado."""
    __tablename__ = "frota_os_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    os_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_ordens_servico.id", ondelete="CASCADE"), nullable=False
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_produtos.id"), nullable=False
    )

    quantidade: Mapped[float] = mapped_column(Float, nullable=False)
    preco_unitario_na_data: Mapped[float] = mapped_column(Float, default=0.0)

    os: Mapped["OrdemServico"] = relationship(back_populates="itens", lazy="noload")


class RegistroManutencao(Base):
    """Histórico de manutenções realizadas num equipamento."""
    __tablename__ = "frota_registros_manutencao"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipamento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_equipamentos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    os_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_ordens_servico.id"), nullable=True
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    talhao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"), nullable=True, index=True
    )

    data_realizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    tipo: Mapped[str] = mapped_column(String(30))
    descricao: Mapped[str] = mapped_column(String(500))
    custo_total: Mapped[float] = mapped_column(Float, default=0.0)

    horimetro_na_data: Mapped[float] = mapped_column(Float, default=0.0)
    km_na_data: Mapped[float | None] = mapped_column(Float, nullable=True)

    tecnico_responsavel: Mapped[str | None] = mapped_column(String(100), nullable=True)

    @property
    def maquinario_id(self) -> uuid.UUID:
        return self.equipamento_id

    @maquinario_id.setter
    def maquinario_id(self, value: uuid.UUID) -> None:
        self.equipamento_id = value

    from sqlalchemy import Index
    __table_args__ = (
        Index("ix_frota_reg_manut_tenant_equip_data", tenant_id, equipamento_id, data_realizacao),
    )



class JornadaEquipamento(Base):
    """Jornada operacional aberta/fechada do equipamento em campo ou uso administrativo."""

    __tablename__ = "frota_jornadas_equipamento"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipamento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_equipamentos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    operador_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_pessoas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unidades_produtivas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    talhao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"), nullable=True, index=True
    )

    tipo_operacao: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    data_fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    horimetro_inicial: Mapped[float | None] = mapped_column(Float, nullable=True)
    horimetro_final: Mapped[float | None] = mapped_column(Float, nullable=True)
    km_inicial: Mapped[float | None] = mapped_column(Float, nullable=True)
    km_final: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20),
        default="ABERTA",
        nullable=False,
        index=True,
        comment="ABERTA | FINALIZADA | CANCELADA",
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    from sqlalchemy import Index
    __table_args__ = (
        Index("ix_frota_jornadas_tenant_equip_data", tenant_id, equipamento_id, data_inicio),
        Index("ix_frota_jornadas_tenant_safra", tenant_id, safra_id),
    )


class FrotaRegraInteligente(Base):
    """Configuração de automações baseadas em inteligência de frota."""
    __tablename__ = "frota_regras_inteligentes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    chave: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # ex: OS_AUTOMATICA_PREVENTIVA
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ativa: Mapped[bool] = mapped_column(default=False)

    threshold_valor: Mapped[float | None] = mapped_column(Float, nullable=True)  # ex: 30.0 (%)
    acao_automatica: Mapped[bool] = mapped_column(default=False)
    precisa_confirmacao: Mapped[bool] = mapped_column(default=True)

    notificar_gestor: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class FrotaLogAutomacao(Base):
    """Log de auditoria das ações executadas pelas Regras Inteligentes."""
    __tablename__ = "frota_logs_automacao"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    regra_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_regras_inteligentes.id", ondelete="CASCADE"), nullable=False
    )

    equipamento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    acao_executada: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="EXECUTADA")  # EXECUTADA | PENDENTE | FALHA
    
    justificativa: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="Explicação simples do porquê a ação foi tomada")
    threshold_atingido: Mapped[float | None] = mapped_column(Float, nullable=True, comment="O valor que disparou a regra")
    economia_estimada: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Valor financeiro economizado ou impacto evitado")
    
    detalhe: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
