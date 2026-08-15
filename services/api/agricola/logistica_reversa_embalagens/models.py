import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUIDType

from core.database import Base


class StatusDevolucaoEmbalagem(str, enum.Enum):
    PENDENTE = "PENDENTE"
    DEVOLVIDO = "DEVOLVIDO"
    VENCIDO = "VENCIDO"


class DevolucaoEmbalagem(Base):
    """OPERATIONS-GAP-01 §21.16/§21.20: pendência de logística reversa de
    embalagens vazias de defensivos (Lei 9.974/2000) — 1 registro por compra
    (`ItemRecebimento`) de produto com `ProdutoEstoque.requer_receituario=True`
    e `quantidade_embalagens` informado. Criado automaticamente no recebimento
    (ver `operacional/services/compras_service.py::receber_pedido`), nunca via
    POST manual — toda pendência nasce de uma compra real."""
    __tablename__ = "agricola_devolucoes_embalagens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    item_recebimento_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("compras_recebimentos_itens.id", ondelete="CASCADE"), nullable=False, index=True
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("cadastros_produtos.id"), nullable=False, index=True
    )

    quantidade_embalagens_compradas: Mapped[int] = mapped_column(Integer, nullable=False)
    quantidade_embalagens_devolvidas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    data_compra: Mapped[date] = mapped_column(Date, nullable=False)
    prazo_limite: Mapped[date] = mapped_column(Date, nullable=False)

    destino_pessoa_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("cadastros_pessoas.id"), nullable=True, index=True
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=StatusDevolucaoEmbalagem.PENDENTE.value, index=True)

    comprovante_pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_devolucao_embalagem_tenant_status_prazo", "tenant_id", "status", "prazo_limite"),
    )
