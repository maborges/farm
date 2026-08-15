"""compras item unidade_produtiva_id p/ item de servico (OPERATIONS-GAP-01 §21.31)

Revision ID: 20260815_compras_item_up_servico
Revises: 20260815_estoque_contagens
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260815_compras_item_up_servico"
down_revision = "20260815_estoque_contagens"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "compras_itens_pedido",
        sa.Column(
            "unidade_produtiva_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("unidades_produtivas.id"), nullable=True,
        ),
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_column("compras_itens_pedido", "unidade_produtiva_id")
    op.execute("COMMIT")
