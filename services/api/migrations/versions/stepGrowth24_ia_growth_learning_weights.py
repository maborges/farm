"""stepGrowth24 — Aprendizado de pesos do Growth (IA-Growth-24)

Adiciona a tabela de pesos aprendidos e a base para recalibrar timing,
persona, abordagem, oferta e autopilot com métricas reais.

Revision ID: stepGrowth24
Revises: stepGrowth23
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa

revision = "stepGrowth24"
down_revision = "stepGrowth23"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_growth_learning_weights",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("dimensao", sa.String(length=20), nullable=False),
        sa.Column("chave", sa.String(length=80), nullable=False),
        sa.Column("peso_atual", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("amostras", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("conversoes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_ia_growth_learning_tenant_dim_key",
        "ia_growth_learning_weights",
        ["tenant_id", "dimensao", "chave"],
        unique=True,
    )
    op.create_index(
        "ix_ia_growth_learning_tenant_dim",
        "ia_growth_learning_weights",
        ["tenant_id", "dimensao"],
    )


def downgrade():
    op.drop_index("ix_ia_growth_learning_tenant_dim", table_name="ia_growth_learning_weights")
    op.drop_index("ix_ia_growth_learning_tenant_dim_key", table_name="ia_growth_learning_weights")
    op.drop_table("ia_growth_learning_weights")
