"""step43 — adiciona origem e origem_id em financeiro_lancamentos"""
from alembic import op
import sqlalchemy as sa

revision = "step43_lancamentos_origem"
down_revision = "step42_solicitacoes_crm_sync"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "financeiro_lancamentos",
        sa.Column("origem", sa.String(50), nullable=True),
    )
    op.add_column(
        "financeiro_lancamentos",
        sa.Column("origem_id", sa.Uuid(as_uuid=True), nullable=True),
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_column("financeiro_lancamentos", "origem_id")
    op.drop_column("financeiro_lancamentos", "origem")
