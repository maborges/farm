"""step34: automacoes_agendamento — frequencia e proxima_execucao

Revision ID: step34_automacoes_agendamento
Revises: step33_automacoes_configuracoes
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = "step34_automacoes_agendamento"
down_revision = "step33_automacoes_configuracoes"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "automacoes_configuracoes",
        sa.Column("frequencia", sa.String(10), nullable=True, server_default="MANUAL"),
    )
    op.add_column(
        "automacoes_configuracoes",
        sa.Column("proxima_execucao", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("automacoes_configuracoes", "proxima_execucao")
    op.drop_column("automacoes_configuracoes", "frequencia")
