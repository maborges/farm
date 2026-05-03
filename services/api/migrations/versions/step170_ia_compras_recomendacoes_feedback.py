"""step170_ia_compras_recomendacoes_feedback

Revision ID: step170
Revises: step169
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = "step170"
down_revision = "step169"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ia_compras_recomendacoes") as batch_op:
        batch_op.add_column(sa.Column("feedback_util", sa.Boolean, nullable=True))
        batch_op.add_column(sa.Column("feedback_comentario", sa.Text, nullable=True))
        batch_op.add_column(sa.Column("feedback_at", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    with op.batch_alter_table("ia_compras_recomendacoes") as batch_op:
        batch_op.drop_column("feedback_at")
        batch_op.drop_column("feedback_comentario")
        batch_op.drop_column("feedback_util")
