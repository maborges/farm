import uuid
from datetime import datetime, date, timezone

# As FKs compostas abaixo precisam que as tabelas-pai estejam no metadata antes
# de qualquer configuração antecipada dos mappers (alguns routers configuram
# Produto antes de importar todo o catálogo de modelos).
import agricola.operacoes.models  # noqa: F401
import agricola.planejamento_operacional.models  # noqa: F401
import agricola.safras.models  # noqa: F401
import agricola.tarefas.models  # noqa: F401
import core.cadastros.pessoas.models  # noqa: F401

from sqlalchemy import CheckConstraint, String, Boolean, DateTime, Date, ForeignKey, ForeignKeyConstraint, JSON, Integer, Numeric, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym
from sqlalchemy import Uuid as UUID
from core.database import Base

class Deposito(Base):
    """Armazéns, galpões ou tanques de combustível."""
    __tablename__ = "estoque_depositos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    unidade_produtiva_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("unidades_produtivas.id"), index=True)
    
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), default="GERAL") # GERAL, COMBUSTIVEL, DEFENSIVOS, PECAS
    localizacao_desc: Mapped[str | None] = mapped_column(String(200))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_estoque_depositos_tenant_id"),
        ForeignKeyConstraint(
            ["tenant_id", "unidade_produtiva_id"],
            ["unidades_produtivas.tenant_id", "unidades_produtivas.id"],
            name="fk_ed_tenant_unidade_produtiva",
            ondelete="NO ACTION",
        ),
    )

class SaldoEstoque(Base):
    """Ponte entre Produto e Depósito para controle de quantidade atual."""
    __tablename__ = "estoque_saldos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deposito_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), index=True)
    
    quantidade_atual: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    quantidade_reservada: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    estoque_minimo: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    estoque_maximo: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    # Custo Médio Ponderado Móvel (CMPM/Kardex) — só muda em entradas; saídas,
    # transferências e ajustes negativos consomem a este custo sem alterá-lo.
    # Nunca é zerado quando o saldo esgota (fica "congelado" até a próxima
    # entrada recalcular). Ver EstoqueService.registrar_entrada.
    custo_medio: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    ultima_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class EstoqueLocalizacao(Base):
    """Endereço físico (corredor/prateleira/posição) de um produto dentro de um
    depósito. Um mesmo produto pode ter várias localizações no mesmo depósito
    (quantidade fracionada entre elas)."""
    __tablename__ = "estoque_localizacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    deposito_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), index=True)

    corredor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    prateleira: Mapped[str | None] = mapped_column(String(20), nullable=True)
    posicao: Mapped[str | None] = mapped_column(String(20), nullable=True)
    codigo_localizacao: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True, comment="Etiqueta/código do endereço físico, para leitor de código de barras")
    observacao_livre: Mapped[str | None] = mapped_column(String(200), nullable=True)

    quantidade: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_estloc_produto_deposito", produto_id, deposito_id),
    )

class LoteEstoque(Base):
    """Rastreabilidade por lote de produto (defensivos, sementes, ração)."""
    __tablename__ = "estoque_lotes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), index=True)
    deposito_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="CASCADE"), index=True)

    numero_lote: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    data_fabricacao: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_validade: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    quantidade_inicial: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    quantidade_atual: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0)
    custo_unitario: Mapped[float] = mapped_column(Numeric(15, 6), default=0.0)
    nota_fiscal_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    qualidade_laudo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("operacional_qualidade_laudos.id", ondelete="SET NULL"), nullable=True, index=True)
    qualidade_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    peso_desconto_qualidade_kg: Mapped[float] = mapped_column(Numeric(12, 3), default=0.0, nullable=False, server_default="0")
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # ATIVO, VENCIDO, ESGOTADO, BLOQUEADO
    status: Mapped[str] = mapped_column(String(20), default="ATIVO")
    lote_beneficiamento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True, comment="FK rastreabilidade: qual lote beneficiamento originou este estoque")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class RequisicaoMaterial(Base):
    """Solicitação interna de material ao almoxarifado."""
    __tablename__ = "estoque_requisicoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)

    # Código de referência legível (ex: REQ-2026-000123). Ver core/sequenciais_config.py.
    numero: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)

    unidade_produtiva_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("unidades_produtivas.id"), index=True)
    solicitante_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    aprovador_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    operacao_agricola_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operacoes_agricolas.id", ondelete="SET NULL"), nullable=True, index=True,
        comment="Vínculo formal com a OS que originou esta requisição (auto-gerada ao confirmar a OS). Pode haver mais de uma requisição por OS (complementos)."
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    safra_tarefa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("safra_tarefas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    plano_operacional_tarefa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("planos_operacionais_tarefas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    responsavel_pessoa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_pessoas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    data_solicitacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    data_necessidade: Mapped[date | None] = mapped_column(Date, nullable=True)
    # PENDENTE, APROVADA, SEPARANDO, SEPARADA, ENTREGUE, RECUSADA, CANCELADA
    status: Mapped[str] = mapped_column(String(20), default="PENDENTE")
    # ORDEM_SERVICO, MANUTENCAO, PRODUCAO, OUTRO
    origem_tipo: Mapped[str] = mapped_column(String(30), default="OUTRO")
    origem_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    compatibilidade_legado: Mapped[str | None] = mapped_column(String(24), nullable=True)

    itens: Mapped[list["ItemRequisicao"]] = relationship(back_populates="requisicao", lazy="noload")

    __table_args__ = (
        UniqueConstraint("tenant_id", "numero", name="uq_estoque_requisicoes_tenant_numero"),
        UniqueConstraint("tenant_id", "id", name="uq_estoque_requisicoes_tenant_id"),
        CheckConstraint("version >= 1", name="ck_estoque_requisicoes_version_positiva"),
        CheckConstraint(
            "compatibilidade_legado IS NULL OR compatibilidade_legado IN "
            "('LEGACY_OPEN','LEGACY_DELIVERED','LEGACY_RETURNED')",
            name="ck_estoque_requisicoes_compatibilidade_legado",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "operacao_agricola_id"],
            ["operacoes_agricolas.tenant_id", "operacoes_agricolas.id"],
            name="fk_req_tenant_operacao_agricola",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "safra_id"],
            ["safras.tenant_id", "safras.id"],
            name="fk_req_tenant_safra",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "safra_tarefa_id"],
            ["safra_tarefas.tenant_id", "safra_tarefas.id"],
            name="fk_req_tenant_safra_tarefa",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "plano_operacional_tarefa_id"],
            ["planos_operacionais_tarefas.tenant_id", "planos_operacionais_tarefas.id"],
            name="fk_req_tenant_plano_tarefa",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "responsavel_pessoa_id"],
            ["cadastros_pessoas.tenant_id", "cadastros_pessoas.id"],
            name="fk_req_tenant_responsavel_pessoa",
            ondelete="NO ACTION",
        ),
    )


class ItemRequisicao(Base):
    __tablename__ = "estoque_requisicoes_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requisicao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id"))
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id"), nullable=True)
    lote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_lotes.id"), nullable=True)
    quantidade_solicitada: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    quantidade_aprovada: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    quantidade_entregue: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    quantidade_devolvida: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    natureza_item: Mapped[str | None] = mapped_column(String(20), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    requisicao: Mapped["RequisicaoMaterial"] = relationship(back_populates="itens")

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_estoque_requisicoes_itens_tenant_id"),
        CheckConstraint(
            "natureza_item IS NULL OR natureza_item IN ('CONSUMIVEL','RETORNAVEL')",
            name="ck_estoque_requisicoes_itens_natureza",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "requisicao_id"],
            ["estoque_requisicoes.tenant_id", "estoque_requisicoes.id"],
            name="fk_item_req_tenant_requisicao",
            ondelete="CASCADE",
        ),
    )


class RequisicaoConfirmacao(Base):
    """Assinatura eletrônica (reautenticação) de retirada ou devolução de
    material de uma requisição — REQUISICAO-MATERIAL-01 Fase 2."""
    __tablename__ = "estoque_requisicao_confirmacoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    requisicao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_requisicoes.id", ondelete="CASCADE"), index=True)
    # RETIRADA | DEVOLUCAO
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)
    # SENHA (web, e-mail+senha) | TOKEN_DISPOSITIVO (app de campo)
    metodo: Mapped[str] = mapped_column(String(20), nullable=False)
    email_informado: Mapped[str | None] = mapped_column(String(255), nullable=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campo_dispositivos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_operation_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    versao_requisicao: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resultado: Mapped[str | None] = mapped_column(String(30), nullable=True)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    confirmado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "client_operation_id",
            name="uq_estoque_requisicao_confirmacao_tenant_client_operation",
        ),
    )


class ReservaEstoque(Base):
    """Bloqueio de saldo para uso futuro garantido (OS, safra, pedido)."""
    __tablename__ = "estoque_reservas"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="CASCADE"), index=True)
    deposito_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="CASCADE"), index=True)
    criado_por_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    item_requisicao_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)

    quantidade: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    quantidade_consumida: Mapped[float] = mapped_column(
        Numeric(18, 6), nullable=False, default=0.0, server_default="0"
    )
    motivo: Mapped[str] = mapped_column(String(255), nullable=False)
    # ORDEM_SERVICO, PEDIDO_COMPRA, SAFRA, REQUISICAO, MANUAL
    referencia_tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    referencia_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # ATIVA, PARCIALMENTE_CONSUMIDA, CONSUMIDA, LIBERADA, CANCELADA
    status: Mapped[str] = mapped_column(String(32), default="ATIVA", index=True)
    client_operation_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "item_requisicao_id"],
            ["estoque_requisicoes_itens.tenant_id", "estoque_requisicoes_itens.id"],
            name="fk_reserva_tenant_item_requisicao",
            ondelete="NO ACTION",
        ),
        UniqueConstraint(
            "tenant_id", "client_operation_id",
            name="uq_estoque_reservas_tenant_client_operation",
        ),
        CheckConstraint("quantidade > 0", name="ck_estoque_reservas_quantidade_positiva"),
        CheckConstraint(
            "quantidade_consumida >= 0 AND quantidade_consumida <= quantidade",
            name="ck_estoque_reservas_quantidade_consumida",
        ),
        CheckConstraint(
            "status IN ('ATIVA','PARCIALMENTE_CONSUMIDA','CONSUMIDA','LIBERADA','CANCELADA')",
            name="ck_estoque_reservas_status",
        ),
    )


class RequisicaoItemEvento(Base):
    """Diário append-only dos fatos operacionais de um item de requisição."""

    __tablename__ = "estoque_requisicao_item_eventos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requisicao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    item_requisicao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    tipo_evento: Mapped[str] = mapped_column(String(30), nullable=False)
    quantidade: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    unidade: Mapped[str] = mapped_column(String(30), nullable=False)
    produto_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    lote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    operacao_agricola_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    operacao_execucao_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    pessoa_operacional_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    dispositivo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    ocorrido_em_dispositivo: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    versao_requisicao: Mapped[int] = mapped_column(Integer, nullable=False)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    causation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    evento_entrega_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        comment="Entrega física exata que originou a conferência ou recusa.",
    )
    resultado_conferencia: Mapped[str | None] = mapped_column(
        String(24), nullable=True,
        comment="Resultado do aceite: integral, parcial, recusa ou divergência.",
    )
    client_operation_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provenance: Mapped[str] = mapped_column(String(24), nullable=False, default="CANONICAL", server_default="CANONICAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_req_item_evento_tenant_id"),
        UniqueConstraint(
            "tenant_id", "client_operation_id",
            name="uq_req_item_evento_tenant_client_operation",
        ),
        CheckConstraint("quantidade > 0", name="ck_req_item_evento_quantidade_positiva"),
        CheckConstraint("versao_requisicao >= 1", name="ck_req_item_evento_versao_positiva"),
        CheckConstraint(
            "tipo_evento IN ('SEPARACAO','ENTREGA','RECEBIMENTO','RECUSA','CONSUMO',"
            "'DEVOLUCAO','PERDA','DANO','EXTRAVIO','AJUSTE_AUTORIZADO')",
            name="ck_req_item_evento_tipo",
        ),
        CheckConstraint(
            "provenance IN ('CANONICAL','LEGACY_BACKFILL')",
            name="ck_req_item_evento_provenance",
        ),
        CheckConstraint(
            "resultado_conferencia IS NULL OR resultado_conferencia IN "
            "('RECEBIDO_INTEGRAL','RECEBIDO_PARCIAL','RECUSADO','DIVERGENTE')",
            name="ck_req_item_evento_resultado_conferencia",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "requisicao_id"],
            ["estoque_requisicoes.tenant_id", "estoque_requisicoes.id"],
            name="fk_req_item_evento_tenant_requisicao",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "item_requisicao_id"],
            ["estoque_requisicoes_itens.tenant_id", "estoque_requisicoes_itens.id"],
            name="fk_req_item_evento_tenant_item",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "operacao_agricola_id"],
            ["operacoes_agricolas.tenant_id", "operacoes_agricolas.id"],
            name="fk_req_item_evento_tenant_operacao",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "operacao_execucao_id"],
            ["operacoes_execucoes.tenant_id", "operacoes_execucoes.id"],
            name="fk_req_item_evento_tenant_execucao",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "pessoa_operacional_id"],
            ["cadastros_pessoas.tenant_id", "cadastros_pessoas.id"],
            name="fk_req_item_evento_tenant_pessoa",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "evento_entrega_id"],
            ["estoque_requisicao_item_eventos.tenant_id", "estoque_requisicao_item_eventos.id"],
            name="fk_req_item_evento_tenant_entrega_origem",
            ondelete="NO ACTION",
        ),
    )


class RequisicaoResponsabilidadeHistorico(Base):
    """Histórico contextual de responsável ou delegado de recebimento."""

    __tablename__ = "estoque_requisicao_responsabilidades"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requisicao_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False, index=True)
    pessoa_operacional_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    pessoa_usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    papel: Mapped[str] = mapped_column(String(20), nullable=False)
    concedido_por_usuario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    vigencia_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    vigencia_fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "requisicao_id"],
            ["estoque_requisicoes.tenant_id", "estoque_requisicoes.id"],
            name="fk_req_responsabilidade_tenant_requisicao",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "papel IN ('RESPONSAVEL','DELEGADO')",
            name="ck_req_responsabilidade_papel",
        ),
        CheckConstraint(
            "vigencia_fim IS NULL OR vigencia_fim > vigencia_inicio",
            name="ck_req_responsabilidade_vigencia",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "pessoa_operacional_id"],
            ["cadastros_pessoas.tenant_id", "cadastros_pessoas.id"],
            name="fk_req_responsabilidade_tenant_pessoa",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "pessoa_usuario_id"],
            ["cadastros_pessoas_usuarios.tenant_id", "cadastros_pessoas_usuarios.id"],
            name="fk_req_responsabilidade_tenant_pessoa_usuario",
            ondelete="NO ACTION",
        ),
    )


class EstoqueMovimento(Base):
    """Ledger append-only de estoque. Correções são novos movimentos via ajuste_de."""
    __tablename__ = "estoque_movimentos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    data_movimento: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    tipo_movimento: Mapped[str] = mapped_column(String(24), nullable=False)

    produto_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="RESTRICT"), nullable=False, index=True)
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="SET NULL"), nullable=True, index=True)
    lote_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("estoque_lotes.id", ondelete="SET NULL"), nullable=True, index=True)

    quantidade: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    unidade_medida_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("unidades_medida.id", ondelete="RESTRICT"), nullable=False)
    custo_unitario: Mapped[float | None] = mapped_column(Numeric(15, 6), nullable=True)
    custo_total: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)

    origem: Mapped[str] = mapped_column(String(32), nullable=False)
    origem_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    requisicao_item_evento_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    operacao_execucao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("operacoes_execucoes.id", ondelete="SET NULL"), nullable=True
    )
    production_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("production_units.id", ondelete="SET NULL"), nullable=True
    )
    fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compras_fornecedores.id", ondelete="SET NULL"), nullable=True, index=True
    )
    numero_lote: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ajuste_de: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estoque_movimentos.id", ondelete="SET NULL"), nullable=True
    )
    # Snapshot do CMPM (SaldoEstoque.custo_medio) antes/depois deste movimento —
    # dá o kardex completo direto pelo ledger, sem recálculo, e permite reverter
    # o custo médio com precisão em estornos (ver ComprasService.estornar_recebimento).
    custo_medio_anterior: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    custo_medio_resultante: Mapped[float | None] = mapped_column(Numeric(15, 4), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "requisicao_item_evento_id"],
            ["estoque_requisicao_item_eventos.tenant_id", "estoque_requisicao_item_eventos.id"],
            name="fk_movimento_tenant_req_item_evento",
            ondelete="NO ACTION",
        ),
        UniqueConstraint(
            "tenant_id", "requisicao_item_evento_id",
            name="uq_estoque_movimentos_tenant_req_item_evento",
        ),
    )

    # Compatibilidade com o nomeado antigo usado em serviços/routers legados.
    data_movimentacao = synonym("data_movimento")
    tipo = synonym("tipo_movimento")
    origem_tipo = synonym("origem")
    motivo = synonym("observacoes")

    def __init__(self, **kwargs):
        legacy_to_current = {
            "data_movimentacao": "data_movimento",
            "tipo": "tipo_movimento",
            "origem_tipo": "origem",
            "motivo": "observacoes",
        }
        for legacy_key, current_key in legacy_to_current.items():
            if legacy_key in kwargs and current_key not in kwargs:
                kwargs[current_key] = kwargs.pop(legacy_key)

        # Chamadas legadas ainda passam usuario_id, mas o ledger atual não usa esse campo.
        kwargs.pop("usuario_id", None)

        super().__init__(**kwargs)
