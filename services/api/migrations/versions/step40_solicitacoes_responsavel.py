"""step40 — adiciona responsavel_usuario_id em billing_solicitacoes_comerciais

Revision ID: step40_solicitacoes_resp
Revises: step39_solicitacoes_obs
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "step40_solicitacoes_resp"
down_revision = "step39_solicitacoes_obs"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "billing_solicitacoes_comerciais",
        sa.Column("responsavel_usuario_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_column("billing_solicitacoes_comerciais", "responsavel_usuario_id")
