"""stepGrowth17 — Assistente comercial/CS consultivo (IA-Growth-17)

Registra interações do assistente comercial para orientar upgrades de forma
consultiva, sem alterar billing real.

Revision ID: stepGrowth17
Revises: stepGrowth16
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = "stepGrowth17"
down_revision = "stepGrowth16"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_growth_assistente_interacoes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("plano_atual", sa.String(20), nullable=False),
        sa.Column("plano_recomendado", sa.String(20), nullable=False),
        sa.Column("persona", sa.String(40), nullable=True),
        sa.Column("churn_risk_level", sa.String(10), nullable=True),
        sa.Column("mensagem_usuario", sa.Text(), nullable=False),
        sa.Column("resposta_ia", sa.Text(), nullable=False),
        sa.Column("cta_sugerido", sa.String(120), nullable=False),
        sa.Column("acao_sugerida", sa.String(60), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_iagrowth_assistente_tenant_data",
        "ia_growth_assistente_interacoes",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_iagrowth_assistente_usuario",
        "ia_growth_assistente_interacoes",
        ["usuario_id", "created_at"],
    )


def downgrade():
    op.drop_index("ix_iagrowth_assistente_usuario", table_name="ia_growth_assistente_interacoes")
    op.drop_index("ix_iagrowth_assistente_tenant_data", table_name="ia_growth_assistente_interacoes")
    op.drop_table("ia_growth_assistente_interacoes")
