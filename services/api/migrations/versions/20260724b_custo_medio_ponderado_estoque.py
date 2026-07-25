"""Custo Médio Ponderado Móvel (CMPM/Kardex) de estoque.

- Adiciona estoque_saldos.custo_medio: CMPM vigente por produto/depósito.
  Atualizado só em entradas (ver EstoqueService.registrar_entrada); nunca
  zerado quando o saldo esgota.
- Adiciona estoque_movimentos.custo_medio_anterior/custo_medio_resultante:
  snapshot do CMPM antes/depois de cada movimento — dá o kardex completo
  direto pelo ledger, e permite reverter o custo médio com precisão em
  estornos (ver ComprasService.estornar_recebimento).

Revision ID: 20260724b_custo_medio_kardex
Revises: 20260724a_prodref_estloc
Create Date: 2026-07-24
"""
from alembic import op
import sqlalchemy as sa

revision = "20260724b_custo_medio_kardex"
down_revision = "20260724a_prodref_estloc"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "estoque_saldos",
        sa.Column("custo_medio", sa.Numeric(15, 4), nullable=True),
    )
    op.add_column(
        "estoque_movimentos",
        sa.Column("custo_medio_anterior", sa.Numeric(15, 4), nullable=True),
    )
    op.add_column(
        "estoque_movimentos",
        sa.Column("custo_medio_resultante", sa.Numeric(15, 4), nullable=True),
    )

    op.execute("COMMIT")


def downgrade():
    op.drop_column("estoque_movimentos", "custo_medio_resultante")
    op.drop_column("estoque_movimentos", "custo_medio_anterior")
    op.drop_column("estoque_saldos", "custo_medio")
