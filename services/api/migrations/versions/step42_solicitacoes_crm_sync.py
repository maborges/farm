"""step42 — adiciona crm_sync_status e crm_sync_at em billing_solicitacoes_comerciais"""
from alembic import op
import sqlalchemy as sa

revision = "step42_solicitacoes_crm_sync"
down_revision = "step42_solicitacoes_followup"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "billing_solicitacoes_comerciais",
        sa.Column(
            "crm_sync_status",
            sa.String(20),
            nullable=False,
            server_default="NAO_ENVIADO",
        ),
    )
    op.add_column(
        "billing_solicitacoes_comerciais",
        sa.Column("crm_sync_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("COMMIT")


def downgrade():
    op.drop_column("billing_solicitacoes_comerciais", "crm_sync_at")
    op.drop_column("billing_solicitacoes_comerciais", "crm_sync_status")
