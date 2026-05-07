"""stepGrowth21 — Incentivos controlados e trials temporários (IA-Growth-21)

Adiciona a tabela de incentivos controlados, com auditoria completa, e a
feature flag tenant-level para habilitar o motor de incentivos sem alterar
billing automaticamente.

Revision ID: stepGrowth21
Revises: stepGrowth20
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "stepGrowth21"
down_revision = "stepGrowth20"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ia_autopilot_config",
        sa.Column("growth_incentivos_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute("UPDATE ia_autopilot_config SET growth_incentivos_enabled = false WHERE growth_incentivos_enabled IS NULL")
    op.alter_column("ia_autopilot_config", "growth_incentivos_enabled", server_default=None)

    op.create_table(
        "ia_growth_incentivos",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("usuario_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("tipo_incentivo", sa.String(length=30), nullable=False),
        sa.Column("plano_alvo", sa.String(length=20), nullable=False),
        sa.Column("origem", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OFERECIDO"),
        sa.Column("validade_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validade_fim", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_ia_growth_incentivos_tenant_usuario",
        "ia_growth_incentivos",
        ["tenant_id", "usuario_id"],
    )
    op.create_index(
        "ix_ia_growth_incentivos_tenant_status",
        "ia_growth_incentivos",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_ia_growth_incentivos_tenant_validade",
        "ia_growth_incentivos",
        ["tenant_id", "validade_fim"],
    )


def downgrade():
    op.drop_index("ix_ia_growth_incentivos_tenant_validade", table_name="ia_growth_incentivos")
    op.drop_index("ix_ia_growth_incentivos_tenant_status", table_name="ia_growth_incentivos")
    op.drop_index("ix_ia_growth_incentivos_tenant_usuario", table_name="ia_growth_incentivos")
    op.drop_table("ia_growth_incentivos")

    op.drop_column("ia_autopilot_config", "growth_incentivos_enabled")
