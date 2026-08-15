"""fin_rateios: valor_rateado/percentual de Float para Numeric

Revision ID: 20260815_rateio_numeric
Revises: 20260815_produto_colhido_cost_alloc
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_rateio_numeric"
down_revision = "20260815_produto_colhido_cost_alloc"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "fin_rateios",
        "valor_rateado",
        type_=sa.Numeric(15, 2),
        existing_type=sa.Float(),
        postgresql_using="valor_rateado::numeric(15,2)",
        existing_nullable=False,
    )
    op.alter_column(
        "fin_rateios",
        "percentual",
        type_=sa.Numeric(7, 4),
        existing_type=sa.Float(),
        postgresql_using="percentual::numeric(7,4)",
        existing_nullable=False,
    )
    op.execute("COMMIT")


def downgrade():
    op.alter_column(
        "fin_rateios",
        "valor_rateado",
        type_=sa.Float(),
        existing_type=sa.Numeric(15, 2),
        existing_nullable=False,
    )
    op.alter_column(
        "fin_rateios",
        "percentual",
        type_=sa.Float(),
        existing_type=sa.Numeric(7, 4),
        existing_nullable=False,
    )
    op.execute("COMMIT")
