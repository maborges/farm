"""step33: automacoes_configuracoes

Revision ID: step33_automacoes_configuracoes
Revises: step32_automacoes_execucoes
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = "step33_automacoes_configuracoes"
down_revision = "step32_automacoes_execucoes"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "automacoes_configuracoes",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("safra_id", sa.UUID(as_uuid=True), sa.ForeignKey("safras.id", ondelete="CASCADE"), nullable=True),
        sa.Column("regra", sa.String(60), nullable=False),
        sa.Column("ativa", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "safra_id", "regra", name="uq_automacao_config_regra"),
    )
    op.create_index("ix_automacoes_conf_tenant", "automacoes_configuracoes", ["tenant_id"])


def downgrade():
    op.drop_index("ix_automacoes_conf_tenant")
    op.drop_table("automacoes_configuracoes")
