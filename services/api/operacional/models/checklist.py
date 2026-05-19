import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Text, Boolean, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid as UUID, Index
from core.database import Base


class StatusItemChecklist(str, enum.Enum):
    OK = "OK"
    NOK = "NOK"       # não conforme — bloqueia liberação
    NA = "NA"         # não aplicável


class ChecklistModelo(Base):
    """
    Template de checklist pré-operação por tipo de equipamento.

    Exemplo:
      tipo_equipamento = "TRATOR"
      itens = [
        {"ordem": 1, "descricao": "Nível óleo motor",  "obrigatorio": true},
        {"ordem": 2, "descricao": "Calibragem pneus",  "obrigatorio": true},
        {"ordem": 3, "descricao": "Nível água radiador","obrigatorio": false},
      ]
    """
    __tablename__ = "frota_checklist_modelos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo_equipamento: Mapped[str | None] = mapped_column(
        String(30), nullable=True, index=True,
        comment="Tipo de equipamento alvo (TRATOR, COLHEDORA…); NULL = genérico"
    )
    # Estrutura: [{"ordem": int, "descricao": str, "obrigatorio": bool}]
    itens: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    realizados: Mapped[list["ChecklistRealizado"]] = relationship(
        back_populates="modelo", lazy="noload"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ChecklistRealizado(Base):
    """
    Preenchimento de checklist por operador antes de usar o equipamento.

    - Se algum item obrigatório tiver status NOK → liberado_para_uso = False
    - O router pode bloquear ApontamentoUso se não houver checklist liberado no dia
    """
    __tablename__ = "frota_checklists_realizados"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    equipamento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_equipamentos.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    modelo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_checklist_modelos.id", ondelete="RESTRICT"),
        nullable=False
    )
    operador_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_pessoas.id", ondelete="SET NULL"), nullable=True
    )

    data_hora: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Respostas: [{"ordem": int, "descricao": str, "status": "OK"|"NOK"|"NA", "observacao": str|null}]
    respostas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    liberado_para_uso: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    observacoes_gerais: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Se NOK → pode gerar OS automaticamente
    os_gerada_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_ordens_servico.id", ondelete="SET NULL"), nullable=True
    )

    modelo: Mapped["ChecklistModelo"] = relationship(back_populates="realizados", lazy="noload")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ChecklistOperacional(Base):
    """Modelo operacional de checklist por tipo de equipamento e momento da jornada."""

    __tablename__ = "frota_checklists_operacionais"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo_equipamento: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    tipo_jornada: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True, comment="ABERTURA | ENCERRAMENTO"
    )
    exige_antes_operacao: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    bloqueia_falha_critica: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    itens: Mapped[list["ChecklistOperacionalItem"]] = relationship(
        back_populates="checklist", lazy="selectin", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_frota_checklists_oper_tenant_tipo", tenant_id, tipo_equipamento, tipo_jornada, ativo),
    )


class ChecklistOperacionalItem(Base):
    """Item normalizado do checklist operacional."""

    __tablename__ = "frota_checklists_operacionais_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_checklists_operacionais.id", ondelete="CASCADE"), nullable=False, index=True
    )
    categoria: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    descricao: Mapped[str] = mapped_column(String(255), nullable=False)
    obrigatorio: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    checklist: Mapped["ChecklistOperacional"] = relationship(back_populates="itens", lazy="noload")

    __table_args__ = (
        Index("ix_frota_checklist_itens_tenant_checklist", tenant_id, checklist_id),
    )


class ChecklistOperacionalResposta(Base):
    """Resposta por item com contexto operacional congelado para rastreabilidade."""

    __tablename__ = "frota_checklists_operacionais_respostas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_checklists_operacionais.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_checklists_operacionais_itens.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    equipamento_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_equipamentos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jornada_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_jornadas_equipamento.id", ondelete="SET NULL"), nullable=True, index=True
    )
    operador_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_pessoas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    executado_por_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    reportado_por_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unidades_produtivas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    tipo_jornada: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="CONFORME | NAO_CONFORME | NAO_APLICAVEL")
    falha: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    criticidade: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    alerta_operacional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    os_gerada_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("frota_ordens_servico.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    __table_args__ = (
        Index("ix_frota_check_resp_tenant_equip_data", tenant_id, equipamento_id, created_at),
        Index("ix_frota_check_resp_tenant_operador", tenant_id, operador_id),
        Index("ix_frota_check_resp_tenant_up", tenant_id, unidade_produtiva_id),
        Index("ix_frota_check_resp_tenant_safra", tenant_id, safra_id),
    )
