"""step29: adiciona campo categoria em financeiro_lancamentos

Revision ID: step29_lancamento_categoria
Revises: step28_financeiro_lancamentos
Create Date: 2026-05-01
"""

from alembic import op
import sqlalchemy as sa

revision = "step29_lancamento_categoria"
down_revision = "step28_financeiro_lancamentos"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "financeiro_lancamentos",
        sa.Column("categoria", sa.String(30), nullable=True, server_default="OPERACOES"),
    )
    op.execute(sa.text("UPDATE financeiro_lancamentos SET categoria = 'OPERACOES' WHERE categoria IS NULL"))


def downgrade():
    op.drop_column("financeiro_lancamentos", "categoria")
