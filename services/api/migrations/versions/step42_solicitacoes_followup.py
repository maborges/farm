"""step42_solicitacoes_followup

Revision ID: step42_solicitacoes_followup
Revises: step41_solicitacoes_historico
Create Date: 2026-05-02 21:09:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "step42_solicitacoes_followup"
down_revision = "step41_sol_historico"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "billing_solicitacoes_comerciais",
        sa.Column("proximo_followup_em", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "billing_solicitacoes_comerciais",
        sa.Column("followup_observacao", sa.String(), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("billing_solicitacoes_comerciais", "followup_observacao")
    op.drop_column("billing_solicitacoes_comerciais", "proximo_followup_em")
