"""step41 — cria billing_solicitacoes_comerciais_historico

Revision ID: step41_sol_historico
Revises: step40_solicitacoes_resp
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "step41_sol_historico"
down_revision = "step40_solicitacoes_resp"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "billing_solicitacoes_comerciais_historico",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("solicitacao_id", sa.Uuid(as_uuid=True), nullable=False, index=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("usuario_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("tipo_evento", sa.String(50), nullable=False),
        sa.Column("valor_anterior", sa.Text(), nullable=True),
        sa.Column("valor_novo", sa.Text(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_table("billing_solicitacoes_comerciais_historico")
