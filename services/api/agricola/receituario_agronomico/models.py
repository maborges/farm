import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Uuid as UUIDType

from core.database import Base


class StatusReceituario(str, enum.Enum):
    RASCUNHO = "RASCUNHO"
    EMITIDO = "EMITIDO"
    VENCIDO = "VENCIDO"
    CANCELADO = "CANCELADO"


class ReceituarioAgronomico(Base):
    """Documento legal de Receituário Agronômico (Lei 7.802/1989) — exigido para
    venda/aplicação de defensivos agrícolas, assinado por engenheiro agrônomo
    com registro CREA. Não confundir com `ReceitaAplicacao` (pacote reutilizável
    de produto+dose/ha aplicado a um plano operacional, sem valor legal)."""
    __tablename__ = "agricola_receituarios_agronomicos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    numero: Mapped[str | None] = mapped_column(String(50), nullable=True)

    agronomo_pessoa_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("cadastros_pessoas.id"), nullable=False, index=True
    )
    crea_numero: Mapped[str] = mapped_column(String(30), nullable=False)
    crea_uf: Mapped[str] = mapped_column(String(2), nullable=False)

    unidade_produtiva_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("unidades_produtivas.id"), nullable=False, index=True
    )
    safra_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("safras.id", ondelete="SET NULL"), nullable=True, index=True
    )
    talhao_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("cadastros_areas_rurais.id", ondelete="SET NULL"), nullable=True
    )
    operacao_agricola_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("operacoes_agricolas.id", ondelete="SET NULL"), nullable=True, index=True
    )

    cultura: Mapped[str | None] = mapped_column(String(50), nullable=True)
    praga_alvo: Mapped[str | None] = mapped_column(String(100), nullable=True)

    data_emissao: Mapped[date] = mapped_column(Date, nullable=False)
    data_validade: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=StatusReceituario.RASCUNHO.value, index=True)

    arquivo_pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    arquivo_pdf_tamanho_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo_cancelamento: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    itens: Mapped[list["ReceituarioItem"]] = relationship(
        back_populates="receituario", lazy="noload", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_receituario_tenant_status_validade", "tenant_id", "status", "data_validade"),
    )


class ReceituarioItem(Base):
    """Produto + dose/cultura/praga/carência de um Receituário. Carência é
    snapshot de `ProdutoAgricola.periodo_carencia_dias` no momento da emissão
    (o cadastro do produto pode mudar depois sem afetar receituários já emitidos)."""
    __tablename__ = "agricola_receituario_itens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    receituario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agricola_receituarios_agronomicos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("cadastros_produtos.id"), nullable=False, index=True
    )

    dose: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    unidade_dose: Mapped[str] = mapped_column(String(20), nullable=False)
    cultura: Mapped[str | None] = mapped_column(String(50), nullable=True)
    praga_alvo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    carencia_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    receituario: Mapped["ReceituarioAgronomico"] = relationship(back_populates="itens", lazy="noload")

    __table_args__ = (
        Index("ix_receituario_itens_produto", "tenant_id", "produto_id"),
    )
