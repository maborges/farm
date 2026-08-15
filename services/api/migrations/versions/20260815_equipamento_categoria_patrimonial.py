"""equipamento categoria patrimonial (OPERATIONS-GAP-01 §21.29)

Revision ID: 20260815_equipamento_categoria_patrimonial
Revises: 20260815_fix_ck_estoque_origem_perda_regressao
Create Date: 2026-08-15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260815_equipamento_categoria_patrimonial"
down_revision = "20260815_fix_ck_estoque_origem_perda_regressao"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cadastros_equipamentos",
        sa.Column(
            "categoria_patrimonial",
            sa.String(length=30),
            nullable=False,
            server_default="ATIVO_DEPRECIAVEL",
        ),
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_column("cadastros_equipamentos", "categoria_patrimonial")
    op.execute("COMMIT")
