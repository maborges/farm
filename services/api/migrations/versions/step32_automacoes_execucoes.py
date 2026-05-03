"""step32: automacoes_execucoes

Revision ID: step32_automacoes_execucoes
Revises: step31_notificacoes_extend
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = "step32_automacoes_execucoes"
down_revision = "step31_notificacoes_extend"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "automacoes_execucoes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("safra_id", sa.UUID(as_uuid=True), sa.ForeignKey("safras.id", ondelete="CASCADE"), nullable=False),
        sa.Column("executado_por", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("regras_disparadas", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("acoes_criadas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("notificacoes_criadas", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(10), nullable=False, server_default="SUCESSO"),
        sa.Column("mensagem", sa.String(500), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_automacoes_execucoes_tenant_safra", "automacoes_execucoes", ["tenant_id", "safra_id"])


def downgrade():
    op.drop_index("ix_automacoes_execucoes_tenant_safra")
    op.drop_table("automacoes_execucoes")
