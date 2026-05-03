"""step39 — adiciona observacao_comercial em billing_solicitacoes_comerciais

Revision ID: step39_solicitacoes_obs
Revises: merge_step38_notificacoes
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "step39_solicitacoes_obs"
down_revision = "merge_step38_notificacoes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "billing_solicitacoes_comerciais",
        sa.Column("observacao_comercial", sa.Text(), nullable=True),
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_column("billing_solicitacoes_comerciais", "observacao_comercial")
