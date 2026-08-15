"""SaldoEstoque/LoteEstoque/ItemRequisicao/ReservaEstoque: Float para Numeric

Revision ID: 20260815_estoque_numeric
Revises: 20260815_rateio_numeric
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_estoque_numeric"
down_revision = "20260815_rateio_numeric"
branch_labels = None
depends_on = None


_COLUMNS = [
    ("estoque_saldos", "quantidade_atual", sa.Numeric(18, 6)),
    ("estoque_saldos", "quantidade_reservada", sa.Numeric(18, 6)),
    ("estoque_lotes", "quantidade_inicial", sa.Numeric(18, 6)),
    ("estoque_lotes", "quantidade_atual", sa.Numeric(18, 6)),
    ("estoque_lotes", "custo_unitario", sa.Numeric(15, 6)),
    ("estoque_requisicoes_itens", "quantidade_solicitada", sa.Numeric(18, 6)),
    ("estoque_requisicoes_itens", "quantidade_aprovada", sa.Numeric(18, 6)),
    ("estoque_requisicoes_itens", "quantidade_entregue", sa.Numeric(18, 6)),
    ("estoque_requisicoes_itens", "quantidade_devolvida", sa.Numeric(18, 6)),
    ("estoque_reservas", "quantidade", sa.Numeric(18, 6)),
]


def upgrade():
    for table, column, numeric_type in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=numeric_type,
            existing_type=sa.Float(),
            postgresql_using=f"{column}::numeric({numeric_type.precision},{numeric_type.scale})",
        )
    op.execute("COMMIT")


def downgrade():
    for table, column, _ in _COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.Float(),
            existing_type=sa.Numeric(),
        )
    op.execute("COMMIT")
