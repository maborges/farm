import uuid
from datetime import datetime, date
from sqlalchemy import String, Text, ForeignKey, Date, DateTime, Integer, Numeric, Index, UniqueConstraint
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


class PlanoOperacionalTarefaInsumo(Base):
    """
    Produto comercial escolhido para atender uma necessidade agronômica dentro de
    um item de plano (Fase 3 do PLANO-OPERACIONAL-01).

    Ponte entre a necessidade técnica (`SafraTarefaNecessidade` — quanto preciso)
    e o produto real do catálogo (`Produto` — o que vou usar), com um snapshot de
    disponibilidade/custo tirado no momento da simulação. Nesta fase é só
    SIMULAÇÃO: nenhuma reserva de estoque é criada (isso só entra na Fase 4,
    estendendo `ReservaEstoque` já existente em operacional/models/estoque.py) —
    os campos `quantidade_reservada`/`quantidade_faltante` aqui refletem o saldo
    já reservado por OUTROS fluxos no momento da leitura, não uma reserva nova.
    """
    __tablename__ = "planos_operacionais_tarefas_insumos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plano_operacional_tarefa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("planos_operacionais_tarefas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    safra_tarefa_necessidade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("safra_tarefa_necessidades.id", ondelete="SET NULL"), nullable=True
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("cadastros_produtos.id"), nullable=False, index=True
    )
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("estoque_depositos.id", ondelete="SET NULL"), nullable=True
    )

    dose_planejada: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    unidade_dose: Mapped[str] = mapped_column(String(20), nullable=False)
    quantidade_planejada: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    # Snapshot tirado no momento do cálculo (recalculável em RASCUNHO via
    # "recalcular disponibilidade" — nunca gravado por trigger/movimento real).
    quantidade_disponivel_snapshot: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    quantidade_reservada: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    quantidade_faltante: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)

    custo_unitario_snapshot: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    custo_total_estimado: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    # Ex.: "PRODUTO_PRECO_MEDIO" | "CUSTO_INCOMPLETO" | "MANUAL" — nunca inventa
    # valor: se não há preço confiável, fonte_custo="CUSTO_INCOMPLETO" e o custo
    # fica None (sinalização explícita, ver relatório de auditoria §7).
    fonte_custo: Mapped[str | None] = mapped_column(String(30), nullable=True)

    substitui_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("planos_operacionais_tarefas_insumos.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_plano_op_tarefa_insumos_tenant_item", "tenant_id", "plano_operacional_tarefa_id"),
        Index("ix_plano_op_tarefa_insumos_produto", "produto_id"),
    )
