"""store TARA webhook deliveries for idempotent consumer processing"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260828_balanca_inbound_events"
down_revision = "20260827_sane_passaporte_uuid_vazios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "balanca_inbound_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("idempotency_key", sa.String(180), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="NO ACTION"),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint("tenant_id", "event_id", name="uq_balanca_inbound_events_tenant_event"),
        schema="farms",
    )
    op.create_index("ix_balanca_inbound_events_tenant_id", "balanca_inbound_events", ["tenant_id"], schema="farms")
    op.create_index("ix_balanca_inbound_events_tenant_received", "balanca_inbound_events", ["tenant_id", "received_at"], schema="farms")
    op.execute("ALTER TABLE farms.balanca_inbound_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE farms.balanca_inbound_events FORCE ROW LEVEL SECURITY")
    op.execute("""CREATE POLICY balanca_inbound_events_tenant ON farms.balanca_inbound_events
        USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)""")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS balanca_inbound_events_tenant ON farms.balanca_inbound_events")
    op.drop_index("ix_balanca_inbound_events_tenant_received", table_name="balanca_inbound_events", schema="farms")
    op.drop_index("ix_balanca_inbound_events_tenant_id", table_name="balanca_inbound_events", schema="farms")
    op.drop_table("balanca_inbound_events", schema="farms")
