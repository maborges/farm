"""adiciona valor_adiantamento em compras_pedidos

Revision ID: 20260722d_pedido_adiantamento
Revises: 20260722c_pedido_confirmacao
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "20260722d_pedido_adiantamento"
down_revision = "20260722c_pedido_confirmacao"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE compras_pedidos ADD COLUMN IF NOT EXISTS valor_adiantamento NUMERIC(15, 2)")
    op.execute("COMMIT")


def downgrade():
    op.execute("ALTER TABLE compras_pedidos DROP COLUMN IF EXISTS valor_adiantamento")
    op.execute("COMMIT")
