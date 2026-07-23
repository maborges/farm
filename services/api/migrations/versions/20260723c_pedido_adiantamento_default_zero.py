"""pedido compras: valor_adiantamento passa a ser NOT NULL com default 0

Revision ID: 20260723c_pedido_adto_zero
Revises: 20260723b_solicitacao_numero
Create Date: 2026-07-23
"""
from alembic import op
import sqlalchemy as sa

revision = "20260723c_pedido_adto_zero"
down_revision = "20260723b_solicitacao_numero"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE compras_pedidos SET valor_adiantamento = 0 WHERE valor_adiantamento IS NULL")
    op.execute("COMMIT")
    with op.batch_alter_table("compras_pedidos", schema=None) as batch_op:
        batch_op.alter_column(
            "valor_adiantamento",
            existing_type=sa.Numeric(15, 2),
            nullable=False,
            server_default="0",
        )
    op.execute("COMMIT")


def downgrade():
    with op.batch_alter_table("compras_pedidos", schema=None) as batch_op:
        batch_op.alter_column(
            "valor_adiantamento",
            existing_type=sa.Numeric(15, 2),
            nullable=True,
            server_default=None,
        )
    op.execute("COMMIT")
