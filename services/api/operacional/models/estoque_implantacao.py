from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUID

from core.database import Base


class EstoqueImplantacaoSessao(Base):
    __tablename__ = "estoque_implantacao_sessoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unidade_produtiva_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("unidades_produtivas.id", ondelete="SET NULL"), nullable=True, index=True
    )
    arquivo_nome: Mapped[str] = mapped_column(String(255), nullable=False)
    arquivo_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RASCUNHO", index=True)
    mapeamento_colunas: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    colunas_detectadas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    total_linhas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    linhas_validas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    linhas_com_erro: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    linhas_com_aviso: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valor_total_estimado: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    criado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    cancelado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmado_por: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True, index=True
    )


class EstoqueImplantacaoItem(Base):
    __tablename__ = "estoque_implantacao_itens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sessao_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estoque_implantacao_sessoes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    numero_linha: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_original: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    dados_normalizados: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    produto_id_resolvido: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cadastros_produtos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    deposito_id_resolvido: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estoque_depositos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ERRO", index=True)
    erros: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    avisos: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sugestoes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    ignorado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
