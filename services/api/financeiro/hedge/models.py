"""
Modelos de domínio — Hedge e Proteção de Preço (BUSINESS-DOMAIN-09)

Decisões de arquitetura aprovadas:
- ContratoFuturo: representa o instrumento (qual contrato, qual mercado).
- HedgeRegistro: representa a operação (evento materializado).
- HedgePosition: NÃO é tabela no MVP — projeção calculada via HedgeExposureService.
- Módulo: F4_HEDGING (não EXT_IA).
"""
from __future__ import annotations

import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING
from sqlalchemy import (
    String, Numeric, Boolean, Date, Text, ForeignKey, text, Index, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid as UUID

from core.database import Base

if TYPE_CHECKING:
    from agricola.safras.models import Safra


class ContratoFuturo(Base):
    """Representa o instrumento de hedge — um contrato futuro de commodity.

    É o Aggregate Root operacional (instrumento, não posição).
    Um contrato pode ter múltiplos registros de hedge vinculados.

    Args:
        tenant_id: Isolamento multi-tenant obrigatório.
        safra_id: Vinculação com a safra a ser protegida.
        commodity_id: Referência ao cadastro canônico de commodities.
        commodity: Identificação textual da commodity (ex: SOJA, MILHO).
        mercado: Bolsa de operação (B3, CBOT, BMF etc.).
        codigo_contrato: Código de identificação do contrato na bolsa.
        mes_vencimento: Vencimento no formato YYYY-MM.
        tipo_posicao: Direção da operação — COMPRA ou VENDA.
        quantidade: Quantidade em sacas (sc 60kg) ou unidade da commodity.
        unidade: Unidade de medida (sc, bushel, ton etc.).
        preco_contratado: Preço acordado no contrato.
        status: Estado do contrato — ABERTO, ENCERRADO, LIQUIDADO.
        data_liquidacao: Data de liquidação, se aplicável.
        preco_liquidacao: Preço de liquidação, se aplicável.
        resultado: Resultado financeiro do contrato, se liquidado.
    """
    __tablename__ = "contratos_futuros_v2"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("safras.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    commodity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cadastros_commodities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Identificação do instrumento
    commodity: Mapped[str] = mapped_column(String(50), nullable=False)
    mercado: Mapped[str | None] = mapped_column(String(50), nullable=True)
    codigo_contrato: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mes_vencimento: Mapped[str | None] = mapped_column(String(7), nullable=True)

    # Posição
    tipo_posicao: Mapped[str] = mapped_column(
        String(10), nullable=False, default="VENDA"
    )  # COMPRA | VENDA
    quantidade: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    unidade: Mapped[str | None] = mapped_column(String(20), nullable=True, default="sc")

    # Preço e resultado
    preco_contratado: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="ABERTO"
    )  # ABERTO | ENCERRADO | LIQUIDADO
    data_liquidacao: Mapped[date | None] = mapped_column(Date, nullable=True)
    preco_liquidacao: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    resultado: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)

    # Auditoria
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))
    updated_at: Mapped[datetime] = mapped_column(
        server_default=text("(CURRENT_TIMESTAMP)"), onupdate=datetime.utcnow
    )

    # Relacionamentos
    # Há uma classe legada `enterprise.models.sprints_27_33.HedgeRegistro` no mesmo registry.
    # O caminho totalmente qualificado evita ambiguidade na resolução do mapper.
    registros: Mapped[list["HedgeRegistro"]] = relationship(
        "financeiro.hedge.models.HedgeRegistro",
        back_populates="contrato_futuro",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_contratos_futuros_v2_tenant_status", "tenant_id", "status"),
        Index("ix_contratos_futuros_v2_tenant_safra", "tenant_id", "safra_id"),
    )


class HedgeRegistro(Base):
    """Representa uma operação individual de hedge — evento materializado.

    Cada registro é uma operação executada dentro de um ContratoFuturo.
    HedgeRegistro acumula na HedgePosition (calculada, não persistida).

    Args:
        tenant_id: Isolamento multi-tenant obrigatório.
        contrato_futuro_id: FK para o instrumento de hedge.
        safra_id: Vinculação direta com a safra (redundante mas útil para query).
        tipo: Classificação da operação (ABERTURA, ROLAGEM, ENCERRAMENTO etc.).
        quantidade: Quantidade operada em sacas ou unidade do contrato.
        preco: Preço da operação.
        data_operacao: Data da execução da operação.
        base: Diferencial base (preco físico - preco futuro).
        resultado_papel: Resultado financeiro teórico (mark-to-model).
        resultado_fisico: Resultado financeiro na entrega física.
        resultado_liquido: Resultado líquido (papel + físico).
        observacoes: Notas operacionais livres.
    """
    __tablename__ = "hedge_registros_v2"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contrato_futuro_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contratos_futuros_v2.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("safras.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Classificação da operação
    tipo: Mapped[str] = mapped_column(String(30), nullable=False, default="ABERTURA")
    # ABERTURA | ROLAGEM | ENCERRAMENTO | AJUSTE

    # Dados da operação
    quantidade: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    preco: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    data_operacao: Mapped[date] = mapped_column(Date, nullable=False)

    # Resultados (opcionais no MVP)
    base: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    resultado_papel: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    resultado_fisico: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)
    resultado_liquido: Mapped[float | None] = mapped_column(Numeric(14, 4), nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Auditoria
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))

    # Relacionamentos
    # Resolve explicitamente para evitar colisão com o modelo legado homônimo
    # em enterprise.models.sprints_27_33.
    contrato_futuro: Mapped["ContratoFuturo"] = relationship(
        "financeiro.hedge.models.ContratoFuturo",
        back_populates="registros", lazy="noload"
    )

    __table_args__ = (
        Index("ix_hedge_registros_v2_tenant_contrato", "tenant_id", "contrato_futuro_id"),
        Index("ix_hedge_registros_v2_tenant_safra", "tenant_id", "safra_id"),
    )


class HedgePositionSnapshot(Base):
    """Snapshot diário da posição de hedge (Mark-to-Market).

    Armazena a fotografia do PnL (Lucro/Prejuízo) não realizado baseado
    na cotação de fechamento da data de referência.

    Args:
        tenant_id: Isolamento multi-tenant.
        contrato_futuro_id: FK para o contrato original.
        safra_id: Redundância para facilitar relatórios agregados.
        commodity_id: Redundância para facilitar relatórios agregados.
        data_referencia: Data a qual a cotação pertence.
        quantidade_aberta: Quantidade que não foi liquidada na data.
        preco_contratado: Preço travado na operação.
        preco_mercado: Cotação de fechamento.
        moeda: Moeda do preço (sempre idêntica ao contrato no MVP).
        unidade: Unidade da quantidade/preço.
        mtm_valor: Valor do PnL calculado.
        pnl_nao_realizado: O mesmo que mtm_valor.
        fonte_preco: Fonte (ex: CEPEA, MANUAL, B3).
    """
    __tablename__ = "hedge_position_snapshots_v2"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contrato_futuro_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contratos_futuros_v2.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("safras.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    commodity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cadastros_commodities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    data_referencia: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantidade_aberta: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    preco_contratado: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    preco_mercado: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    moeda: Mapped[str] = mapped_column(String(3), nullable=False, default="BRL")
    unidade: Mapped[str] = mapped_column(String(20), nullable=False, default="sc")
    
    mtm_valor: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    pnl_nao_realizado: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    fonte_preco: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    calculado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("(CURRENT_TIMESTAMP)"))

    # Relacionamento
    contrato_futuro: Mapped["ContratoFuturo"] = relationship(
        "financeiro.hedge.models.ContratoFuturo",
        lazy="noload"
    )

    __table_args__ = (
        Index(
            "uq_hedge_snapshot_tenant_contrato_data",
            "tenant_id", "contrato_futuro_id", "data_referencia",
            unique=True
        ),
        Index("ix_hedge_snapshot_tenant_safra", "tenant_id", "safra_id"),
    )
