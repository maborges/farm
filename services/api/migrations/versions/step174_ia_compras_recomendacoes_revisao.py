"""step174: adiciona campos de revisão manual ao ia_compras_recomendacoes

Revision ID: step174
Revises: step170
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = "step174"
down_revision = "step170"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ia_compras_recomendacoes") as batch_op:
        batch_op.add_column(sa.Column("feedback_revisado", sa.Boolean(), nullable=False, server_default="false"))
        batch_op.add_column(sa.Column("feedback_revisado_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("feedback_revisao_observacao", sa.Text(), nullable=True))
    op.execute("COMMIT")


def downgrade():
    with op.batch_alter_table("ia_compras_recomendacoes") as batch_op:
        batch_op.drop_column("feedback_revisao_observacao")
        batch_op.drop_column("feedback_revisado_at")
        batch_op.drop_column("feedback_revisado")
