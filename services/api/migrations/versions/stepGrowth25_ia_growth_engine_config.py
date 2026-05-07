"""stepGrowth25_ia_growth_engine_config

Revision ID: stepGrowth25
Revises: stepGrowth24
Create Date: 2026-05-07 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "stepGrowth25"
down_revision = "stepGrowth24"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ia_autopilot_config", sa.Column("growth_engine_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("ia_autopilot_config", sa.Column("growth_llm_copy_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("ia_autopilot_config", sa.Column("growth_learning_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("ia_autopilot_config", sa.Column("growth_max_acoes_dia", sa.Integer(), nullable=False, server_default=sa.text("3")))
    op.add_column("ia_autopilot_config", sa.Column("growth_max_incentivos_mes", sa.Integer(), nullable=False, server_default=sa.text("0")))
    op.add_column("ia_autopilot_config", sa.Column("growth_modo", sa.String(length=20), nullable=False, server_default=sa.text("'BALANCEADO'")))

    op.execute("UPDATE ia_autopilot_config SET growth_engine_enabled = COALESCE(growth_engine_enabled, false)")
    op.execute("UPDATE ia_autopilot_config SET growth_llm_copy_enabled = COALESCE(growth_llm_copy_enabled, false)")
    op.execute("UPDATE ia_autopilot_config SET growth_learning_enabled = COALESCE(growth_learning_enabled, false)")
    op.execute("UPDATE ia_autopilot_config SET growth_max_acoes_dia = COALESCE(growth_max_acoes_dia, 3)")
    op.execute("UPDATE ia_autopilot_config SET growth_max_incentivos_mes = COALESCE(growth_max_incentivos_mes, 0)")
    op.execute("UPDATE ia_autopilot_config SET growth_modo = COALESCE(growth_modo, 'BALANCEADO')")

    op.alter_column("ia_autopilot_config", "growth_engine_enabled", server_default=None)
    op.alter_column("ia_autopilot_config", "growth_llm_copy_enabled", server_default=None)
    op.alter_column("ia_autopilot_config", "growth_learning_enabled", server_default=None)
    op.alter_column("ia_autopilot_config", "growth_max_acoes_dia", server_default=None)
    op.alter_column("ia_autopilot_config", "growth_max_incentivos_mes", server_default=None)
    op.alter_column("ia_autopilot_config", "growth_modo", server_default=None)


def downgrade() -> None:
    op.drop_column("ia_autopilot_config", "growth_modo")
    op.drop_column("ia_autopilot_config", "growth_max_incentivos_mes")
    op.drop_column("ia_autopilot_config", "growth_max_acoes_dia")
    op.drop_column("ia_autopilot_config", "growth_learning_enabled")
    op.drop_column("ia_autopilot_config", "growth_llm_copy_enabled")
    op.drop_column("ia_autopilot_config", "growth_engine_enabled")
