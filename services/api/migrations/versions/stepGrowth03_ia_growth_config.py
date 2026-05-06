"""stepGrowth03 — ia_growth_config e ia_growth_config_historico (Growth-03)

Revision ID: stepGrowth03
Revises: stepGrowth01
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "stepGrowth03"
down_revision = "stepGrowth01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_growth_config",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contexto", sa.String(40), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("cooldown_horas", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("prioridade", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), onupdate=sa.text("NOW()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ia_growth_config_tenant_contexto", "ia_growth_config", ["tenant_id", "contexto"], unique=True)

    op.create_table(
        "ia_growth_config_historico",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contexto", sa.String(40), nullable=False),
        sa.Column("campo_alterado", sa.String(40), nullable=False),
        sa.Column("valor_anterior", sa.String(100), nullable=True),
        sa.Column("valor_novo", sa.String(100), nullable=False),
        sa.Column("alterado_por", UUID(as_uuid=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ia_growth_config_hist_tenant", "ia_growth_config_historico", ["tenant_id", "criado_em"])

    op.execute("COMMIT")


def downgrade():
    op.drop_table("ia_growth_config_historico")
    op.drop_table("ia_growth_config")
