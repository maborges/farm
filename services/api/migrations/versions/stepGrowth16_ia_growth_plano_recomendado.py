"""stepGrowth16 — Log de recomendações de plano (IA-Growth-16)

Persiste cada recomendação consultiva emitida pelo Growth, para permitir
cálculo de distribuição, CTR e taxa de conversão por plano recomendado.

Revision ID: stepGrowth16
Revises: stepGrowth10
Create Date: 2026-05-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "stepGrowth16"
down_revision = "stepGrowth10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ia_growth_plano_recomendado_log",
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
        sa.Column("score_fit", sa.Float(), nullable=False, server_default="0"),
        sa.Column("nivel_urgencia", sa.String(10), nullable=False, server_default="BAIXA"),
        sa.Column("persona", sa.String(40), nullable=True),
        sa.Column("churn_risk_level", sa.String(10), nullable=True),
        sa.Column("motivos", JSONB(), nullable=True),
        sa.Column("funcionalidades_relevantes", JSONB(), nullable=True),
        sa.Column("sinais", JSONB(), nullable=True),
        sa.Column(
            "exibida_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("clicada_em", sa.DateTime(timezone=True), nullable=True),
        sa.Column("convertida_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_iagrowth_plano_rec_tenant_data",
        "ia_growth_plano_recomendado_log",
        ["tenant_id", "exibida_em"],
    )
    op.create_index(
        "ix_iagrowth_plano_rec_plano",
        "ia_growth_plano_recomendado_log",
        ["plano_recomendado"],
    )
    op.create_index(
        "ix_iagrowth_plano_rec_usuario",
        "ia_growth_plano_recomendado_log",
        ["usuario_id"],
    )


def downgrade():
    op.drop_index("ix_iagrowth_plano_rec_usuario", table_name="ia_growth_plano_recomendado_log")
    op.drop_index("ix_iagrowth_plano_rec_plano", table_name="ia_growth_plano_recomendado_log")
    op.drop_index("ix_iagrowth_plano_rec_tenant_data", table_name="ia_growth_plano_recomendado_log")
    op.drop_table("ia_growth_plano_recomendado_log")
