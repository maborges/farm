"""balanca: campos de peso oficial em PedidoCompra e ComercializacaoCommodity

Vínculo Balança ↔ Compras/Vendas — mesmo padrão já usado em romaneios de
colheita e pecuária (evento balanca.pesagem.concluida). Campos aditivos,
nullable, sem impacto em fluxos existentes de quantidade/valor.

Revision ID: 20260817_balanca_compras_vendas
Revises: 20260816_balanca_operadores
Create Date: 2026-08-17
"""
from alembic import op
import sqlalchemy as sa

revision = "20260817_balanca_compras_vendas"
down_revision = "20260816_balanca_operadores"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("compras_pedidos", sa.Column("peso_bruto_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("compras_pedidos", sa.Column("peso_tara_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("compras_pedidos", sa.Column("peso_liquido_kg", sa.Numeric(12, 3), nullable=True))

    op.add_column("financeiro_comercializacoes", sa.Column("peso_bruto_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("financeiro_comercializacoes", sa.Column("peso_tara_kg", sa.Numeric(12, 3), nullable=True))
    op.add_column("financeiro_comercializacoes", sa.Column("peso_liquido_kg", sa.Numeric(12, 3), nullable=True))

    op.execute("COMMIT")


def downgrade():
    op.drop_column("financeiro_comercializacoes", "peso_liquido_kg")
    op.drop_column("financeiro_comercializacoes", "peso_tara_kg")
    op.drop_column("financeiro_comercializacoes", "peso_bruto_kg")

    op.drop_column("compras_pedidos", "peso_liquido_kg")
    op.drop_column("compras_pedidos", "peso_tara_kg")
    op.drop_column("compras_pedidos", "peso_bruto_kg")

    op.execute("COMMIT")
