import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, ForeignKey, Date, DateTime, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUIDType
from core.database import Base


class PlanoOperacional(Base):
    """
    Cabeçalho do Planejamento Operacional em Lote (PLANO-OPERACIONAL-01).

    Agrupador administrativo/decisório que consolida N `SafraTarefa` (uma por talhão)
    para planejar produtos/estoque/mão-de-obra de forma agregada, antes da geração da
    OS individual de cada tarefa. NÃO substitui `SafraTarefa`/`OperacaoAgricola` — o
    fluxo econômico oficial (OperacaoAgricola -> OperacaoExecucao -> CostAllocation)
    continua sendo gerado por `TarefaService.gerar_operacao_planejada`, tarefa por
    tarefa, mesmo quando disparado a partir de um plano.

    Sem `talhao_id` no cabeçalho: um plano cobre tarefas de vários talhões.
    """
    __tablename__ = "planos_operacionais"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    safra_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("safras.id", ondelete="CASCADE"), nullable=False, index=True
    )
    production_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("production_units.id", ondelete="SET NULL"), nullable=True
    )

    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)

    data_inicio_prevista: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim_prevista: Mapped[date | None] = mapped_column(Date, nullable=True)

    # RASCUNHO | EM_ANALISE | PARCIALMENTE_PRONTO | PRONTO | APROVADO | EM_EXECUCAO | CONCLUIDO | CANCELADO
    status: Mapped[str] = mapped_column(String(25), nullable=False, default="RASCUNHO", index=True)
    versao: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    criado_por: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
    aprovado_por: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
    aprovado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_planos_operacionais_tenant_safra_status", "tenant_id", "safra_id", "status"),
    )


class PlanoOperacionalTarefa(Base):
    """
    Associação entre um `PlanoOperacional` e uma `SafraTarefa` individual (1 por talhão).

    O agrupamento de várias tarefas dentro do mesmo plano é a camada de consolidação
    (visão + decisão); cada tarefa continua sendo uma entidade própria, com seu próprio
    histórico e ciclo de vida em `OperacaoAgricola`/Campo PWA — este registro não altera
    isso, só rastreia o estado dela DENTRO do plano.
    """
    __tablename__ = "planos_operacionais_tarefas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plano_operacional_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("planos_operacionais.id", ondelete="CASCADE"), nullable=False, index=True
    )
    safra_tarefa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("safra_tarefas.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # NAO_ANALISADA | AGUARDANDO_DEFINICAO | PRONTA | AGUARDANDO_COMPRA |
    # PARCIALMENTE_ATENDIDA | PROGRAMADA | REMOVIDA | CANCELADA
    status_planejamento: Mapped[str] = mapped_column(String(25), nullable=False, default="NAO_ANALISADA")

    data_programada: Mapped[date | None] = mapped_column(Date, nullable=True)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordem_execucao: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        # Uma tarefa só entra 1x no mesmo plano (pode reentrar após remoção lógica
        # apenas reativando a mesma linha, não duplicando — ver service).
        UniqueConstraint("plano_operacional_id", "safra_tarefa_id", name="uq_plano_operacional_tarefa"),
        Index("ix_plano_op_tarefas_tenant_plano", "tenant_id", "plano_operacional_id"),
        Index("ix_plano_op_tarefas_safra_tarefa", "safra_tarefa_id"),
    )
