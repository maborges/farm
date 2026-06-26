"""domain event outbox mvp

Revision ID: 20260626_domain_event_outbox
Revises: 20260625_alert_engine_mvp
Create Date: 2026-06-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260626_domain_event_outbox"
down_revision = "20260625_alert_engine_mvp"
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)


def _enable_tenant_rls(schema_name: str, table_name: str) -> None:
    policy_prefix = f"{schema_name}_{table_name}"
    table_ref = f"{schema_name}.{table_name}"
    op.execute(sa.text(f"ALTER TABLE {table_ref} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_ref} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_select_tenant
            ON {table_ref}
            FOR SELECT
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_insert_tenant
            ON {table_ref}
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_update_tenant
            ON {table_ref}
            FOR UPDATE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_delete_tenant
            ON {table_ref}
            FOR DELETE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )


def _disable_tenant_rls(schema_name: str, table_name: str) -> None:
    policy_prefix = f"{schema_name}_{table_name}"
    table_ref = f"{schema_name}.{table_name}"
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_delete_tenant ON {table_ref}"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_update_tenant ON {table_ref}"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_insert_tenant ON {table_ref}"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_select_tenant ON {table_ref}"))
    op.execute(sa.text(f"ALTER TABLE {table_ref} DISABLE ROW LEVEL SECURITY"))


def upgrade() -> None:
    op.create_table(
        "domain_event_outbox",
        sa.Column("id", UUID, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("unidade_produtiva_id", UUID, nullable=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=120), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
        ),
        sa.Column("correlation_id", UUID, nullable=True),
        sa.Column("causation_id", UUID, nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_domain_event_outbox_tenant_idempotency_key"),
        schema="farms",
    )
    op.create_index(
        "ix_domain_event_outbox_tenant_id",
        "domain_event_outbox",
        ["tenant_id"],
        unique=False,
        schema="farms",
    )
    op.create_index(
        "ix_domain_event_outbox_status",
        "domain_event_outbox",
        ["status"],
        unique=False,
        schema="farms",
    )
    op.create_index(
        "ix_domain_event_outbox_next_attempt_at",
        "domain_event_outbox",
        ["next_attempt_at"],
        unique=False,
        schema="farms",
    )
    op.create_index(
        "ix_domain_event_outbox_event_type",
        "domain_event_outbox",
        ["event_type"],
        unique=False,
        schema="farms",
    )
    op.create_index(
        "ix_domain_event_outbox_tenant_status",
        "domain_event_outbox",
        ["tenant_id", "status"],
        unique=False,
        schema="farms",
    )
    op.create_index(
        "ix_domain_event_outbox_status_next_attempt_at",
        "domain_event_outbox",
        ["status", "next_attempt_at"],
        unique=False,
        schema="farms",
    )
    _enable_tenant_rls("farms", "domain_event_outbox")


def downgrade() -> None:
    _disable_tenant_rls("farms", "domain_event_outbox")
    op.drop_index("ix_domain_event_outbox_status_next_attempt_at", table_name="domain_event_outbox", schema="farms")
    op.drop_index("ix_domain_event_outbox_tenant_status", table_name="domain_event_outbox", schema="farms")
    op.drop_index("ix_domain_event_outbox_event_type", table_name="domain_event_outbox", schema="farms")
    op.drop_index("ix_domain_event_outbox_next_attempt_at", table_name="domain_event_outbox", schema="farms")
    op.drop_index("ix_domain_event_outbox_status", table_name="domain_event_outbox", schema="farms")
    op.drop_index("ix_domain_event_outbox_tenant_id", table_name="domain_event_outbox", schema="farms")
    op.drop_table("domain_event_outbox", schema="farms")
