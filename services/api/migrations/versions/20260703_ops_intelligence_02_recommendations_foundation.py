"""create recommendations foundation tables

Revision ID: 20260703_ops_intelligence_02_recommendations_foundation
Revises: 23b548507313
Create Date: 2026-07-03 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260703_ops_intelligence_02_recommendations_foundation"
down_revision = "23b548507313"
branch_labels = None
depends_on = None


DOMAINS = ("AGRICULTURE", "LIVESTOCK", "FINANCE", "OPERATIONS", "FIELD", "INTEGRATIONS", "SYSTEM")
STATUSES = (
    "CREATED",
    "VIEWED",
    "ACCEPTED",
    "DISMISSED",
    "POSTPONED",
    "EXECUTED",
    "EXPIRED",
    "AUTO_EXPIRED",
    "SUPERSEDED",
    "REOPENED",
)
PRIORITIES = ("LOW", "NORMAL", "HIGH", "URGENT")
SOURCE_TYPES = ("SIGNAL", "EVENT", "INDICATOR", "ANALYTICS", "MANUAL", "SYSTEM")
ACTION_TYPES = ("NONE", "OPEN_ROUTE", "OPEN_URL", "REVIEW", "EXECUTE_ASSISTED")
LIFECYCLE_ACTIONS = (
    "CREATE",
    "VIEW",
    "ACCEPT",
    "DISMISS",
    "POSTPONE",
    "EXECUTE",
    "EXPIRE",
    "AUTO_EXPIRE",
    "SUPERSEDE",
    "REOPEN",
)
ACTIVE_STATUSES = ("CREATED", "VIEWED", "ACCEPTED", "POSTPONED", "REOPENED")

UUID = postgresql.UUID(as_uuid=True)


def _tenant_rls(table_name: str) -> None:
    prefix = table_name.replace(".", "_")
    op.execute(sa.text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY'))
    for action, clause in (
        ("select", "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)"),
        ("insert", "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)"),
        (
            "update",
            "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid) "
            "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)",
        ),
        ("delete", "USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)"),
    ):
        op.execute(
            sa.text(
                f"""
                CREATE POLICY {prefix}_{action}_tenant
                ON "{table_name}"
                FOR {action.upper()}
                {clause}
                """
            )
        )


def _drop_tenant_rls(table_name: str) -> None:
    prefix = table_name.replace(".", "_")
    for action in ("delete", "update", "insert", "select"):
        op.execute(sa.text(f'DROP POLICY IF EXISTS {prefix}_{action}_tenant ON "{table_name}"'))
    op.execute(sa.text(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY'))


def _check(column_name: str, values: tuple[str, ...]) -> str:
    allowed = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({allowed})"


def upgrade() -> None:
    op.create_table(
        "recommendation_results",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("unidade_produtiva_id", UUID, nullable=True),
        sa.Column("domain", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("action_type", sa.String(length=20), nullable=False),
        sa.Column("provider_name", sa.String(length=120), nullable=False),
        sa.Column("rule_code", sa.String(length=120), nullable=False),
        sa.Column("scope_type", sa.String(length=80), nullable=False),
        sa.Column("scope_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=160), nullable=False),
        sa.Column("source_signal_ids", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("action_label", sa.String(length=120), nullable=True),
        sa.Column("action_target", sa.Text(), nullable=True),
        sa.Column("context", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("postponed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by_id", UUID, nullable=True),
        sa.CheckConstraint(_check("domain", DOMAINS), name="ck_recommendation_results_domain"),
        sa.CheckConstraint(_check("status", STATUSES), name="ck_recommendation_results_status"),
        sa.CheckConstraint(_check("priority", PRIORITIES), name="ck_recommendation_results_priority"),
        sa.CheckConstraint(_check("source_type", SOURCE_TYPES), name="ck_recommendation_results_source_type"),
        sa.CheckConstraint(_check("action_type", ACTION_TYPES), name="ck_recommendation_results_action_type"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_recommendation_results_confidence_range"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unidade_produtiva_id"], ["unidades_produtivas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["superseded_by_id"], ["recommendation_results.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_recommendation_results_tenant_status", "recommendation_results", ["tenant_id", "status"])
    op.create_index("ix_recommendation_results_tenant_domain", "recommendation_results", ["tenant_id", "domain"])
    op.create_index("ix_recommendation_results_tenant_scope", "recommendation_results", ["tenant_id", "scope_type", "scope_id"])
    op.create_index("ix_recommendation_results_tenant_dedupe", "recommendation_results", ["tenant_id", "dedupe_key"])
    op.create_index(
        "ix_recommendation_results_active_dedupe",
        "recommendation_results",
        ["tenant_id", "dedupe_key"],
        unique=True,
        postgresql_where=sa.text(
            "status IN (" + ", ".join(f"'{value}'" for value in ACTIVE_STATUSES) + ")"
        ),
    )

    op.create_table(
        "recommendation_lifecycle_events",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("recommendation_id", UUID, nullable=False),
        sa.Column("actor_id", UUID, nullable=True),
        sa.Column("action_type", sa.String(length=20), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=False),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True),
        sa.Column("source_channel", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(_check("action_type", LIFECYCLE_ACTIONS), name="ck_recommendation_lifecycle_action_type"),
        sa.CheckConstraint(_check("previous_status", STATUSES), name="ck_recommendation_lifecycle_previous_status"),
        sa.CheckConstraint(_check("new_status", STATUSES), name="ck_recommendation_lifecycle_new_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommendation_id"], ["recommendation_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["usuarios.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_recommendation_lifecycle_events_tenant_recommendation",
        "recommendation_lifecycle_events",
        ["tenant_id", "recommendation_id"],
    )

    _tenant_rls("recommendation_results")
    _tenant_rls("recommendation_lifecycle_events")


def downgrade() -> None:
    _drop_tenant_rls("recommendation_lifecycle_events")
    _drop_tenant_rls("recommendation_results")
    op.drop_index("ix_recommendation_lifecycle_events_tenant_recommendation", table_name="recommendation_lifecycle_events")
    op.drop_table("recommendation_lifecycle_events")
    op.drop_index("ix_recommendation_results_active_dedupe", table_name="recommendation_results")
    op.drop_index("ix_recommendation_results_tenant_dedupe", table_name="recommendation_results")
    op.drop_index("ix_recommendation_results_tenant_scope", table_name="recommendation_results")
    op.drop_index("ix_recommendation_results_tenant_domain", table_name="recommendation_results")
    op.drop_index("ix_recommendation_results_tenant_status", table_name="recommendation_results")
    op.drop_table("recommendation_results")
