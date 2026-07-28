import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, Numeric, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid as UUIDType
from core.database import Base


class ReceitaAplicacao(Base):
    """
    Cabeçalho de uma Receita de Aplicação: pacote reutilizável de produto(s) +
    dose/ha e mão de obra padrão, para aplicar em lote a várias tarefas de um
    mesmo Planejamento Operacional (ver `PlanoOperacionalService.aplicar_receita`).

    Não é a mesma coisa que `PrescricaoVRA` (módulo `prescricoes`, desativado):
    aquela é uma grade de taxa variável por talhão específico via shapefile/KML;
    esta é um cadastro simples, reutilizável entre planos/safras, sem geometria.
    """
    __tablename__ = "receitas_aplicacao"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )

    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo_operacao: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(UUIDType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_receitas_aplicacao_tenant_nome", "tenant_id", "nome"),
    )


class ReceitaAplicacaoInsumo(Base):
    """Produto + dose/ha padrão de uma receita. Mesmo par `dose_planejada`/
    `unidade_dose` já existente em `PlanoOperacionalTarefaInsumo` — ao aplicar a
    receita, `quantidade_planejada = dose_ha * SafraTarefa.area_ha`."""
    __tablename__ = "receitas_aplicacao_insumos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    receita_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("receitas_aplicacao.id", ondelete="CASCADE"), nullable=False, index=True
    )
    produto_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("cadastros_produtos.id"), nullable=False, index=True
    )
    deposito_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("estoque_depositos.id", ondelete="SET NULL"), nullable=True
    )

    dose_ha: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    unidade_dose: Mapped[str] = mapped_column(String(20), nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_receitas_aplicacao_insumos_receita", "tenant_id", "receita_id"),
    )


class ReceitaAplicacaoMaoObra(Base):
    """Necessidade de mão de obra padrão de uma receita, na mesma fórmula já
    usada em `PlanoOperacionalTarefaMaoObraCreate` (horas_fixas + horas_por_hectare
    * área), para não duplicar a lógica de cálculo entre lançamento individual
    e aplicação em lote."""
    __tablename__ = "receitas_aplicacao_mao_obra"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    receita_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("receitas_aplicacao.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo_servico_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("cadastros_tipos_servico.id"), nullable=False, index=True
    )

    funcao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantidade_pessoas: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    horas_fixas: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    horas_por_hectare: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_receitas_aplicacao_mao_obra_receita", "tenant_id", "receita_id"),
    )
