"""stepGrowth08 — ia_growth_experimentos, variantes e eventos (Growth-08)

Revision ID: stepGrowth08
Revises: stepGrowth06
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "stepGrowth08"
down_revision = "stepGrowth06"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_growth_experimentos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contexto", sa.String(40), nullable=False),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ATIVO"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ia_growth_exp_tenant_ctx_status", "ia_growth_experimentos", ["tenant_id", "contexto", "status"])

    op.create_table(
        "ia_growth_experimento_variantes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("experimento_id", UUID(as_uuid=True), sa.ForeignKey("ia_growth_experimentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nome", sa.String(20), nullable=False),
        sa.Column("config_override", JSONB(), nullable=False, server_default="{}"),
        sa.Column("peso", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_index("ix_ia_growth_variantes_exp", "ia_growth_experimento_variantes", ["experimento_id"])

    op.create_table(
        "ia_growth_experimento_eventos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("experimento_id", UUID(as_uuid=True), sa.ForeignKey("ia_growth_experimentos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variante_id", UUID(as_uuid=True), sa.ForeignKey("ia_growth_experimento_variantes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evento", sa.String(20), nullable=False),  # SHOWN | CLICKED
        sa.Column("contexto", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ia_growth_exp_eventos_exp", "ia_growth_experimento_eventos", ["experimento_id", "evento"])

    op.execute("COMMIT")


def downgrade():
    op.drop_table("ia_growth_experimento_eventos")
    op.drop_table("ia_growth_experimento_variantes")
    op.drop_table("ia_growth_experimentos")
