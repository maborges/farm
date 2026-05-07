"""stepGrowth19 — Autopilot de Growth com auditoria de ações (IA-Growth-19)

Adiciona a flag tenant-level de autopilot, registra ações executadas
automaticamente e preserva rastreabilidade para o dashboard.

Revision ID: stepGrowth19
Revises: stepGrowth17
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "stepGrowth19"
down_revision = "stepGrowth17"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ia_autopilot_config",
        sa.Column("autopilot_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute("UPDATE ia_autopilot_config SET autopilot_enabled = COALESCE(ativo, false)")
    op.alter_column("ia_autopilot_config", "autopilot_enabled", server_default=None)

    op.create_table(
        "ia_growth_autopilot_acoes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("tipo_acao", sa.String(length=50), nullable=False),
        sa.Column("contexto", sa.String(length=40), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("score_oportunidade", sa.Float(), nullable=False, server_default="0"),
        sa.Column("churn_risk", sa.Float(), nullable=False, server_default="0"),
        sa.Column("impacto_estimado", sa.Float(), nullable=False, server_default="0"),
        sa.Column("resultado", JSONB(), nullable=True),
        sa.Column(
            "executada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_ia_growth_autopilot_tenant_exec",
        "ia_growth_autopilot_acoes",
        ["tenant_id", "executada_em"],
    )
    op.create_index(
        "ix_ia_growth_autopilot_tenant_usuario",
        "ia_growth_autopilot_acoes",
        ["tenant_id", "usuario_id"],
    )
    op.create_index(
        "ix_ia_growth_autopilot_tenant_tipo",
        "ia_growth_autopilot_acoes",
        ["tenant_id", "tipo_acao"],
    )


def downgrade():
    op.drop_index("ix_ia_growth_autopilot_tenant_tipo", table_name="ia_growth_autopilot_acoes")
    op.drop_index("ix_ia_growth_autopilot_tenant_usuario", table_name="ia_growth_autopilot_acoes")
    op.drop_index("ix_ia_growth_autopilot_tenant_exec", table_name="ia_growth_autopilot_acoes")
    op.drop_table("ia_growth_autopilot_acoes")

    op.drop_column("ia_autopilot_config", "autopilot_enabled")
