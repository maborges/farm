"""create alert engine mvp tables

Revision ID: 20260625_alert_engine_mvp
Revises: 20260624_pecuaria_vacinacao_categoria_cost_allocations
Create Date: 2026-06-25 09:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20260625_alert_engine_mvp"
down_revision = "20260624_pecuaria_vacinacao_categoria_cost_allocations"
branch_labels = None
depends_on = None


DOMAINS = ("AGRICULTURE", "LIVESTOCK", "FINANCE", "OPERATIONS", "FIELD", "SYSTEM")
CATEGORIES = (
    "SANITARIO",
    "OPERACIONAL",
    "ECONOMICO",
    "FINANCEIRO",
    "CLIMATICO",
    "MANUTENCAO",
    "GOVERNANCA",
    "QUALIDADE",
    "COMPLIANCE",
    "PRODUCAO",
)
SEVERITIES = ("INFO", "WARNING", "CRITICAL", "EMERGENCY")
PRIORITIES = ("LOW", "NORMAL", "HIGH", "URGENT")
ALERT_STATUSES = ("OPEN", "ACKNOWLEDGED", "SNOOZED", "RESOLVED", "EXPIRED", "CANCELLED")
TRIGGER_TYPES = ("RULE", "THRESHOLD", "MODEL", "MANUAL", "SCHEDULE")
INSIGHT_GENERATED_BY = ("RULE_ENGINE", "ANALYTICS", "COPILOT", "HUMAN")
LIFECYCLE_ACTIONS = ("ACKNOWLEDGE", "SNOOZE", "RESOLVE", "DISMISS", "EXPIRE", "REOPEN", "CREATE")
ACTIVE_ALERT_STATUSES = ("OPEN", "ACKNOWLEDGED", "SNOOZED")

UUID = postgresql.UUID(as_uuid=True)


def _tenant_rls(table_name: str) -> None:
    policy_prefix = table_name.replace(".", "_")
    op.execute(sa.text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY'))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_select_tenant
            ON "{table_name}"
            FOR SELECT
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_insert_tenant
            ON "{table_name}"
            FOR INSERT
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_update_tenant
            ON "{table_name}"
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
            ON "{table_name}"
            FOR DELETE
            USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
            """
        )
    )


def _drop_tenant_rls(table_name: str) -> None:
    policy_prefix = table_name.replace(".", "_")
    op.execute(sa.text(f'DROP POLICY IF EXISTS {policy_prefix}_delete_tenant ON "{table_name}"'))
    op.execute(sa.text(f'DROP POLICY IF EXISTS {policy_prefix}_update_tenant ON "{table_name}"'))
    op.execute(sa.text(f'DROP POLICY IF EXISTS {policy_prefix}_insert_tenant ON "{table_name}"'))
    op.execute(sa.text(f'DROP POLICY IF EXISTS {policy_prefix}_select_tenant ON "{table_name}"'))
    op.execute(sa.text(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY'))


def _domain_check(column_name: str = "domain") -> str:
    allowed = ", ".join(f"'{value}'" for value in DOMAINS)
    return f"{column_name} IN ({allowed})"


def _category_check(column_name: str = "category") -> str:
    allowed = ", ".join(f"'{value}'" for value in CATEGORIES)
    return f"{column_name} IN ({allowed})"


def _severity_check(column_name: str = "severity") -> str:
    allowed = ", ".join(f"'{value}'" for value in SEVERITIES)
    return f"{column_name} IN ({allowed})"


def _priority_check(column_name: str = "priority") -> str:
    allowed = ", ".join(f"'{value}'" for value in PRIORITIES)
    return f"{column_name} IN ({allowed})"


def _status_check(column_name: str = "status") -> str:
    allowed = ", ".join(f"'{value}'" for value in ALERT_STATUSES)
    return f"{column_name} IN ({allowed})"


def _trigger_type_check(column_name: str = "trigger_type") -> str:
    allowed = ", ".join(f"'{value}'" for value in TRIGGER_TYPES)
    return f"{column_name} IN ({allowed})"


def _generated_by_check(column_name: str = "generated_by") -> str:
    allowed = ", ".join(f"'{value}'" for value in INSIGHT_GENERATED_BY)
    return f"{column_name} IN ({allowed})"


def _lifecycle_action_check(column_name: str = "action_type") -> str:
    allowed = ", ".join(f"'{value}'" for value in LIFECYCLE_ACTIONS)
    return f"{column_name} IN ({allowed})"


def upgrade() -> None:
    op.create_table(
        "alert_events",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("domain", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("source_id", UUID, nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("actor_id", UUID, nullable=True),
        sa.Column("entity_type", sa.String(length=80), nullable=True),
        sa.Column("entity_id", UUID, nullable=True),
        sa.Column("payload", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("correlation_id", UUID, nullable=True),
        sa.Column("causation_id", UUID, nullable=True),
        sa.Column("metadata", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(_domain_check(), name="ck_alert_events_domain"),
        sa.CheckConstraint(_category_check(), name="ck_alert_events_category"),
        sa.CheckConstraint("source <> ''", name="ck_alert_events_source_not_empty"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["causation_id"], ["alert_events.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "alert_indicators",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("domain", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("value_numeric", sa.Numeric(18, 6), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("unit", sa.String(length=40), nullable=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inputs", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("metadata", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True),
        sa.Column("calculation_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(_domain_check(), name="ck_alert_indicators_domain"),
        sa.CheckConstraint(_category_check(), name="ck_alert_indicators_category"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_alert_indicators_confidence_range"),
        sa.CheckConstraint(
            "("
            "CASE WHEN value_numeric IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN value_text IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN value_bool IS NOT NULL THEN 1 ELSE 0 END"
            ") <= 1",
            name="ck_alert_indicators_single_value",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "operational_alerts",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("unidade_produtiva_id", UUID, nullable=True),
        sa.Column("domain", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("trigger_type", sa.String(length=20), nullable=False),
        sa.Column("source_type", sa.String(length=120), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("source_event_ids", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("source_indicator_ids", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("dedupe_key", sa.String(length=160), nullable=False),
        sa.Column("action_label", sa.String(length=120), nullable=True),
        sa.Column("action_url", sa.Text(), nullable=True),
        sa.Column("context", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", UUID, nullable=True),
        sa.Column("resolved_by", UUID, nullable=True),
        sa.CheckConstraint(_domain_check(), name="ck_operational_alerts_domain"),
        sa.CheckConstraint(_category_check(), name="ck_operational_alerts_category"),
        sa.CheckConstraint(_severity_check(), name="ck_operational_alerts_severity"),
        sa.CheckConstraint(_priority_check(), name="ck_operational_alerts_priority"),
        sa.CheckConstraint(_status_check(), name="ck_operational_alerts_status"),
        sa.CheckConstraint(_trigger_type_check(), name="ck_operational_alerts_trigger_type"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_operational_alerts_confidence_range"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unidade_produtiva_id"], ["unidades_produtivas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["acknowledged_by"], ["usuarios.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["usuarios.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "alert_insights",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("domain", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("evidence_event_ids", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("evidence_indicator_ids", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("evidence_alert_ids", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=False),
        sa.Column("generated_by", sa.String(length=40), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(_domain_check(), name="ck_alert_insights_domain"),
        sa.CheckConstraint(_category_check(), name="ck_alert_insights_category"),
        sa.CheckConstraint("severity IS NULL OR " + _severity_check(), name="ck_alert_insights_severity"),
        sa.CheckConstraint("priority IS NULL OR " + _priority_check(), name="ck_alert_insights_priority"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_alert_insights_confidence_range"),
        sa.CheckConstraint(_generated_by_check(), name="ck_alert_insights_generated_by"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "alert_lifecycle_events",
        sa.Column("id", UUID, primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("alert_id", UUID, nullable=False),
        sa.Column("actor_id", UUID, nullable=True),
        sa.Column("action_type", sa.String(length=20), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=False),
        sa.Column("new_status", sa.String(length=20), nullable=False),
        sa.Column("payload", sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"), nullable=True),
        sa.Column("source_channel", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(_lifecycle_action_check(), name="ck_alert_lifecycle_events_action_type"),
        sa.CheckConstraint(_status_check("previous_status"), name="ck_alert_lifecycle_events_previous_status"),
        sa.CheckConstraint(_status_check("new_status"), name="ck_alert_lifecycle_events_new_status"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["alert_id"], ["operational_alerts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["usuarios.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_alert_events_tenant_occurred_at", "alert_events", ["tenant_id", "occurred_at"], unique=False)
    op.create_index("ix_alert_events_tenant_ingested_at", "alert_events", ["tenant_id", "ingested_at"], unique=False)
    op.create_index("ix_alert_events_tenant_domain_occurred_at", "alert_events", ["tenant_id", "domain", "occurred_at"], unique=False)
    op.create_index("ix_alert_events_tenant_category_occurred_at", "alert_events", ["tenant_id", "category", "occurred_at"], unique=False)
    op.create_index("ix_alert_events_tenant_source_source_id", "alert_events", ["tenant_id", "source", "source_id"], unique=False)
    op.create_index("ix_alert_events_tenant_correlation_id", "alert_events", ["tenant_id", "correlation_id"], unique=False)
    op.create_index("ix_alert_events_tenant_causation_id", "alert_events", ["tenant_id", "causation_id"], unique=False)

    op.create_index("ix_alert_indicators_tenant_key_computed_at", "alert_indicators", ["tenant_id", "key", "computed_at"], unique=False)
    op.create_index("ix_alert_indicators_tenant_domain_computed_at", "alert_indicators", ["tenant_id", "domain", "computed_at"], unique=False)
    op.create_index("ix_alert_indicators_tenant_category_computed_at", "alert_indicators", ["tenant_id", "category", "computed_at"], unique=False)
    op.create_index("ix_alert_indicators_tenant_period", "alert_indicators", ["tenant_id", "period_start", "period_end"], unique=False)
    op.create_index("ix_alert_indicators_tenant_calculation_version", "alert_indicators", ["tenant_id", "calculation_version"], unique=False)

    op.create_index("ix_operational_alerts_tenant_status_updated_at", "operational_alerts", ["tenant_id", "status", "updated_at"], unique=False)
    op.create_index("ix_operational_alerts_tenant_severity_priority_updated_at", "operational_alerts", ["tenant_id", "severity", "priority", "updated_at"], unique=False)
    op.create_index("ix_operational_alerts_tenant_domain_category_updated_at", "operational_alerts", ["tenant_id", "domain", "category", "updated_at"], unique=False)
    op.create_index("ix_operational_alerts_tenant_source_type_source_id", "operational_alerts", ["tenant_id", "source_type", "source_id"], unique=False)
    op.create_index("ix_operational_alerts_tenant_dedupe_key", "operational_alerts", ["tenant_id", "dedupe_key"], unique=False)
    op.create_index("ix_operational_alerts_tenant_unit_status", "operational_alerts", ["tenant_id", "unidade_produtiva_id", "status"], unique=False)
    op.create_index("ix_operational_alerts_tenant_expires_at", "operational_alerts", ["tenant_id", "expires_at"], unique=False)
    op.create_index(
        "uq_operational_alerts_active_dedupe",
        "operational_alerts",
        ["tenant_id", "dedupe_key"],
        unique=True,
        postgresql_where=sa.text("status IN ('OPEN','ACKNOWLEDGED','SNOOZED')"),
    )

    op.create_index("ix_alert_insights_tenant_domain_generated_at", "alert_insights", ["tenant_id", "domain", "generated_at"], unique=False)
    op.create_index("ix_alert_insights_tenant_category_generated_at", "alert_insights", ["tenant_id", "category", "generated_at"], unique=False)
    op.create_index("ix_alert_insights_tenant_expires_at", "alert_insights", ["tenant_id", "expires_at"], unique=False)

    op.create_index("ix_alert_lifecycle_events_tenant_alert_created_at", "alert_lifecycle_events", ["tenant_id", "alert_id", "created_at"], unique=False)
    op.create_index("ix_alert_lifecycle_events_tenant_action_created_at", "alert_lifecycle_events", ["tenant_id", "action_type", "created_at"], unique=False)
    op.create_index("ix_alert_lifecycle_events_tenant_actor_created_at", "alert_lifecycle_events", ["tenant_id", "actor_id", "created_at"], unique=False)

    for table_name in (
        "alert_events",
        "alert_indicators",
        "operational_alerts",
        "alert_insights",
        "alert_lifecycle_events",
    ):
        _tenant_rls(table_name)


def downgrade() -> None:
    for table_name in (
        "alert_lifecycle_events",
        "alert_insights",
        "operational_alerts",
        "alert_indicators",
        "alert_events",
    ):
        _drop_tenant_rls(table_name)

    op.drop_index("ix_alert_lifecycle_events_tenant_actor_created_at", table_name="alert_lifecycle_events")
    op.drop_index("ix_alert_lifecycle_events_tenant_action_created_at", table_name="alert_lifecycle_events")
    op.drop_index("ix_alert_lifecycle_events_tenant_alert_created_at", table_name="alert_lifecycle_events")

    op.drop_index("ix_alert_insights_tenant_expires_at", table_name="alert_insights")
    op.drop_index("ix_alert_insights_tenant_category_generated_at", table_name="alert_insights")
    op.drop_index("ix_alert_insights_tenant_domain_generated_at", table_name="alert_insights")

    op.drop_index("uq_operational_alerts_active_dedupe", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_tenant_expires_at", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_tenant_unit_status", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_tenant_dedupe_key", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_tenant_source_type_source_id", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_tenant_domain_category_updated_at", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_tenant_severity_priority_updated_at", table_name="operational_alerts")
    op.drop_index("ix_operational_alerts_tenant_status_updated_at", table_name="operational_alerts")

    op.drop_index("ix_alert_indicators_tenant_calculation_version", table_name="alert_indicators")
    op.drop_index("ix_alert_indicators_tenant_period", table_name="alert_indicators")
    op.drop_index("ix_alert_indicators_tenant_category_computed_at", table_name="alert_indicators")
    op.drop_index("ix_alert_indicators_tenant_domain_computed_at", table_name="alert_indicators")
    op.drop_index("ix_alert_indicators_tenant_key_computed_at", table_name="alert_indicators")

    op.drop_index("ix_alert_events_tenant_causation_id", table_name="alert_events")
    op.drop_index("ix_alert_events_tenant_correlation_id", table_name="alert_events")
    op.drop_index("ix_alert_events_tenant_source_source_id", table_name="alert_events")
    op.drop_index("ix_alert_events_tenant_category_occurred_at", table_name="alert_events")
    op.drop_index("ix_alert_events_tenant_domain_occurred_at", table_name="alert_events")
    op.drop_index("ix_alert_events_tenant_ingested_at", table_name="alert_events")
    op.drop_index("ix_alert_events_tenant_occurred_at", table_name="alert_events")

    op.drop_table("alert_lifecycle_events")
    op.drop_table("alert_insights")
    op.drop_table("operational_alerts")
    op.drop_table("alert_indicators")
    op.drop_table("alert_events")
