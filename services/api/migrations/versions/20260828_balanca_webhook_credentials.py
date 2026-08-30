"""persist TARA webhook HMAC credentials per consumer account"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260828_balanca_webhook_credentials"
down_revision = "20260828_balanca_inbound_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "balanca_webhook_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("balanca_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segredo_criptografado", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ATIVO"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("rotated_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="NO ACTION"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("balanca_account_id", name="uq_balanca_webhook_credentials_account"),
        schema="farms",
    )
    op.create_index("ix_balanca_webhook_credentials_tenant_id", "balanca_webhook_credentials", ["tenant_id"], schema="farms")
    op.create_index("ix_balanca_webhook_credentials_balanca_account_id", "balanca_webhook_credentials", ["balanca_account_id"], schema="farms")
    op.execute("ALTER TABLE farms.balanca_webhook_credentials ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE farms.balanca_webhook_credentials FORCE ROW LEVEL SECURITY")
    op.execute("""CREATE POLICY balanca_webhook_credentials_tenant ON farms.balanca_webhook_credentials
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)""")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS balanca_webhook_credentials_tenant ON farms.balanca_webhook_credentials")
    op.drop_index("ix_balanca_webhook_credentials_balanca_account_id", table_name="balanca_webhook_credentials", schema="farms")
    op.drop_index("ix_balanca_webhook_credentials_tenant_id", table_name="balanca_webhook_credentials", schema="farms")
    op.drop_table("balanca_webhook_credentials", schema="farms")
