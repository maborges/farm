"""step37 — billing_solicitacoes_comerciais

Revision ID: step37_billing_solicitacoes_comerciais
Revises: step36_ia_creditos_pacotes
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "step37_billing_sol"
down_revision = "step36_ia_creditos_pacotes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "billing_solicitacoes_comerciais",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("usuario_id", sa.UUID(), nullable=True),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("origem", sa.String(100), nullable=False),
        sa.Column("detalhes", JSONB(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ABERTA"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_solicitacoes_tenant_tipo", "billing_solicitacoes_comerciais", ["tenant_id", "tipo"])
    op.create_index("ix_solicitacoes_status", "billing_solicitacoes_comerciais", ["status"])
    op.execute("COMMIT")


def downgrade():
    op.drop_table("billing_solicitacoes_comerciais")
