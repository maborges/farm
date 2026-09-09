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
    )


class PlanoOperacionalTarefaInsumo(Base):
    """
    Produto comercial escolhido para atender uma necessidade agronômica dentro de
    um item de plano (Fase 3 do PLANO-OPERACIONAL-01).

    Ponte entre a necessidade técnica (`SafraTarefaNecessidade` — quanto preciso)
    e o produto real do catálogo (`Produto` — o que vou usar), com um snapshot de
    disponibilidade/custo. Antes de reservar (Fase 3), `quantidade_reservada`
    reflete apenas o saldo já reservado por OUTROS fluxos, lido de `ReservaEstoque`
    via `SaldoEstoque.quantidade_reservada` — nenhuma reserva nova é criada até
    `reserva_estoque_id` ser preenchido (Fase 4, `PlanoOperacionalService.
    reservar_insumo`, que reaproveita `ReservaEstoque`/`EstoqueService.
    criar_reserva` já existentes em vez de recriar o conceito).
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

    # Preenchido pela Fase 4 ao reservar de fato (`reservar_insumo`). NULL =
    # ainda em simulação ou reserva já liberada/consumida e desvinculada.
    reserva_estoque_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("estoque_reservas.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_plano_op_tarefa_insumos_tenant_item", "tenant_id", "plano_operacional_tarefa_id"),
    )


class PlanoOperacionalTarefaMaoObra(Base):
    """
    Necessidade de mão de obra estimada para um item de plano (Fase 6).

    Separa deliberadamente 4 conceitos que o relatório de auditoria pediu para
    NUNCA colapsar em um único `operador_id`: necessidade estimada (aqui),
    equipe planejada (`pessoa_id`, opcional — pode não estar definida ainda),
    operador que efetivamente executa (`OperacaoAgricola.operador_id`, só
    existe depois, na OS) e horas realizadas (`OperacaoExecucao`, também só na
    execução real). Este registro é só a estimativa de planejamento.
    """
    __tablename__ = "planos_operacionais_tarefas_mao_obra"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plano_operacional_tarefa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("planos_operacionais_tarefas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo_servico_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("cadastros_tipos_servico.id"), nullable=False, index=True
    )
    pessoa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("cadastros_pessoas.id", ondelete="SET NULL"), nullable=True
    )
    # Rastreia de qual necessidade técnica (categoria MAO_DE_OBRA/SERVICO do
    # template) este registro veio, quando criado via aplicação em lote no
    # Plano Operacional — mesmo padrão de PlanoOperacionalTarefaInsumo.
    safra_tarefa_necessidade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("safra_tarefa_necessidades.id", ondelete="SET NULL"), nullable=True, index=True
    )

    funcao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantidade_pessoas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    horas_estimadas: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    custo_hora_snapshot: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    custo_total_estimado: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    # Ex.: "PESSOA_VALOR_HORA" | "TIPO_SERVICO_CUSTO_REFERENCIA" | "CUSTO_INCOMPLETO"
    fonte_custo: Mapped[str | None] = mapped_column(String(30), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_plano_op_tarefa_mao_obra_tenant_item", "tenant_id", "plano_operacional_tarefa_id"),
    )


class PlanoOperacionalTarefaMaquinario(Base):
    """
    Necessidade de maquinário (máquina + implemento) estimada para um item de
    plano — espelha `PlanoOperacionalTarefaMaoObra`, mas para custo de frota.

    Reaproveita o mesmo `SnapshotCustoService` (`origem_tipo="MAQUINA"`) já
    usado por `_capturar_maquina`, que calcula custo/hora real via
    `FrotaCustoService.obter_custo_equipamento` (custo acumulado / horímetro
    do `Equipamento`) — implemento é o mesmo cadastro de Equipamento, só outro
    registro. Nunca inventa valor: sem custo/hora confiável ou sem
    `horas_estimadas`, `custo_total_estimado=None` e `fonte_custo` sinaliza a
    lacuna (mesma disciplina defensiva da mão de obra).
    """
    __tablename__ = "planos_operacionais_tarefas_maquinario"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plano_operacional_tarefa_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("planos_operacionais_tarefas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    maquina_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("cadastros_equipamentos.id", ondelete="SET NULL"), nullable=True
    )
    implemento_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("cadastros_equipamentos.id", ondelete="SET NULL"), nullable=True
    )
    safra_tarefa_necessidade_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("safra_tarefa_necessidades.id", ondelete="SET NULL"), nullable=True, index=True
    )

    horas_estimadas: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    custo_hora_maquina_snapshot: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    custo_hora_implemento_snapshot: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    custo_total_estimado: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    # Ex.: "MAQUINA_E_IMPLEMENTO" | "SO_MAQUINA" | "SO_IMPLEMENTO" | "CUSTO_INCOMPLETO"
    fonte_custo: Mapped[str | None] = mapped_column(String(30), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_plano_op_tarefa_maquinario_tenant_item", "tenant_id", "plano_operacional_tarefa_id"),
    )
