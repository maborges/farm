"""stepGrowth06 — ia_growth_sugestoes (Growth-06)

Revision ID: stepGrowth06
Revises: stepGrowth03
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "stepGrowth06"
down_revision = "stepGrowth03"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_growth_sugestoes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sugestao_id", sa.String(32), nullable=False),
        sa.Column("contexto", sa.String(40), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=False),
        sa.Column("impacto", sa.String(10), nullable=False),
        sa.Column("confianca", sa.Float(), nullable=False),
        sa.Column("justificativa", sa.Text(), nullable=False),
        sa.Column("acao_sugerida", JSONB(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDENTE"),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ignored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responsavel_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ia_growth_sugestoes_tenant_sid", "ia_growth_sugestoes", ["tenant_id", "sugestao_id"], unique=True)
    op.create_index("ix_ia_growth_sugestoes_tenant_status", "ia_growth_sugestoes", ["tenant_id", "status"])

    op.execute("COMMIT")


def downgrade():
    op.drop_table("ia_growth_sugestoes")
