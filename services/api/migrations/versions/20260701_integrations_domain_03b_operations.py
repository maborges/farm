"""integrations domain 03b operations

Revision ID: 20260701_integrations_domain_03b
Revises: 20260701_integrations_domain_03a
Create Date: 2026-07-01 00:30:00.000000
"""

from __future__ import annotations

# ruff: noqa: E501, S608
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260701_integrations_domain_03b"
down_revision = "20260701_integrations_domain_03a"
branch_labels = None
depends_on = None


SCHEMA = "farms"
PROVIDER_TABLE = "marketplace_integracoes"
CONFIG_TABLE = "tenant_integracoes"
FEATURE_TABLE = "integration_features"
SYNC_POLICY_TABLE = "integration_sync_policies"
JOB_TABLE = "integration_jobs"
HEALTH_TABLE = "integration_health_snapshots"
OUTBOX_TABLE = "domain_event_outbox"

SCOPE_TENANT_EXPR = "current_setting('app.current_tenant_id', true)::text"
SYNC_MODE_SQL = "mode IN ('MANUAL', 'AGENDADO', 'EVENTO', 'WEBHOOK', 'PULL', 'PUSH')"
PRIORIDADE_SQL = "prioridade IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')"
JOB_STATUS_SQL = "status IN ('PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'CANCELLED', 'RETRYING')"
JOB_TRIGGER_SQL = "trigger_type IN ('MANUAL', 'SCHEDULED', 'EVENT', 'WEBHOOK', 'PULL', 'PUSH')"
HEALTH_STATUS_SQL = (
    "status IN ('CONNECTED', 'DISCONNECTED', 'DEGRADED', 'AUTH_ERROR', "
    "'CONFIG_ERROR', 'PARTIAL_FAILURE', 'RATE_LIMITED')"
)


def _enable_string_tenant_rls(table_name: str) -> None:
    policy_prefix = f"{SCHEMA}_{table_name}"
    table_ref = f"{SCHEMA}.{table_name}"
    op.execute(sa.text(f"ALTER TABLE {table_ref} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_ref} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_select_tenant
            ON {table_ref}
            FOR SELECT
            USING (tenant_id = {SCOPE_TENANT_EXPR})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_insert_tenant
            ON {table_ref}
            FOR INSERT
            WITH CHECK (tenant_id = {SCOPE_TENANT_EXPR})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_update_tenant
            ON {table_ref}
            FOR UPDATE
            USING (tenant_id = {SCOPE_TENANT_EXPR})
            WITH CHECK (tenant_id = {SCOPE_TENANT_EXPR})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_delete_tenant
            ON {table_ref}
            FOR DELETE
            USING (tenant_id = {SCOPE_TENANT_EXPR})
            """
        )
    )


def _disable_rls(table_name: str) -> None:
    policy_prefix = f"{SCHEMA}_{table_name}"
    table_ref = f"{SCHEMA}.{table_name}"
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_delete_tenant ON {table_ref}"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_update_tenant ON {table_ref}"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_insert_tenant ON {table_ref}"))
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy_prefix}_select_tenant ON {table_ref}"))
    op.execute(sa.text(f"ALTER TABLE {table_ref} DISABLE ROW LEVEL SECURITY"))


def upgrade() -> None:
    op.create_table(
        FEATURE_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=80), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("habilitada", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("obrigatoria", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("settings_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["config_id"], [f"{CONFIG_TABLE}.id"]),
        sa.ForeignKeyConstraint(["provider_id"], [f"{PROVIDER_TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_id", "codigo", name="uq_integration_features_config_codigo"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_features_id",
        FEATURE_TABLE,
        ["id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_features_tenant_id",
        FEATURE_TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_features_config_id",
        FEATURE_TABLE,
        ["config_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_features_provider_id",
        FEATURE_TABLE,
        ["provider_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        SYNC_POLICY_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=30), nullable=False, server_default=sa.text("'MANUAL'")),
        sa.Column("prioridade", sa.String(length=20), nullable=False, server_default=sa.text("'NORMAL'")),
        sa.Column("retry_ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("retry_limite", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("batch_size", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("backoff_seconds", sa.Integer(), nullable=False, server_default=sa.text("30")),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default=sa.text("300")),
        sa.Column("idempotencia_ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("trigger_expression", sa.String(length=120), nullable=True),
        sa.Column("settings_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(SYNC_MODE_SQL, name="ck_integration_sync_policies_mode"),
        sa.CheckConstraint(PRIORIDADE_SQL, name="ck_integration_sync_policies_prioridade"),
        sa.CheckConstraint("retry_limite >= 0", name="ck_integration_sync_policies_retry_limite"),
        sa.CheckConstraint("batch_size >= 1", name="ck_integration_sync_policies_batch_size"),
        sa.CheckConstraint("backoff_seconds >= 0", name="ck_integration_sync_policies_backoff_seconds"),
        sa.CheckConstraint("timeout_seconds >= 1", name="ck_integration_sync_policies_timeout_seconds"),
        sa.ForeignKeyConstraint(["config_id"], [f"{CONFIG_TABLE}.id"]),
        sa.ForeignKeyConstraint(["feature_id"], [f"{FEATURE_TABLE}.id"]),
        sa.ForeignKeyConstraint(["provider_id"], [f"{PROVIDER_TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feature_id", name="uq_integration_sync_policies_feature_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_sync_policies_id",
        SYNC_POLICY_TABLE,
        ["id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_sync_policies_tenant_id",
        SYNC_POLICY_TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_sync_policies_config_id",
        SYNC_POLICY_TABLE,
        ["config_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_sync_policies_provider_id",
        SYNC_POLICY_TABLE,
        ["provider_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        JOB_TABLE,
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("feature_id", sa.Integer(), nullable=True),
        sa.Column("sync_policy_id", sa.Integer(), nullable=True),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("trigger_type", sa.String(length=20), nullable=False, server_default=sa.text("'MANUAL'")),
        sa.Column("outbox_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("causation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("processados", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("sucessos", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("erros", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(JOB_STATUS_SQL, name="ck_integration_jobs_status"),
        sa.CheckConstraint(JOB_TRIGGER_SQL, name="ck_integration_jobs_trigger_type"),
        sa.CheckConstraint("retry_count >= 0", name="ck_integration_jobs_retry_count"),
        sa.CheckConstraint("processados >= 0", name="ck_integration_jobs_processados"),
        sa.CheckConstraint("sucessos >= 0", name="ck_integration_jobs_sucessos"),
        sa.CheckConstraint("erros >= 0", name="ck_integration_jobs_erros"),
        sa.ForeignKeyConstraint(["config_id"], [f"{CONFIG_TABLE}.id"]),
        sa.ForeignKeyConstraint(["feature_id"], [f"{FEATURE_TABLE}.id"]),
        sa.ForeignKeyConstraint(["sync_policy_id"], [f"{SYNC_POLICY_TABLE}.id"]),
        sa.ForeignKeyConstraint(["provider_id"], [f"{PROVIDER_TABLE}.id"]),
        sa.ForeignKeyConstraint(["outbox_event_id"], [f"{OUTBOX_TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_jobs_tenant_id",
        JOB_TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_jobs_config_id",
        JOB_TABLE,
        ["config_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_jobs_feature_id",
        JOB_TABLE,
        ["feature_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_jobs_provider_id",
        JOB_TABLE,
        ["provider_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_jobs_status",
        JOB_TABLE,
        ["status"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_jobs_outbox_event_id",
        JOB_TABLE,
        ["outbox_event_id"],
        unique=False,
        schema=SCHEMA,
    )

    op.create_table(
        HEALTH_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("last_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'DISCONNECTED'")),
        sa.Column("summary", sa.String(length=200), nullable=True),
        sa.Column("details_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rate_limited_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(HEALTH_STATUS_SQL, name="ck_integration_health_snapshots_status"),
        sa.CheckConstraint("consecutive_failures >= 0", name="ck_integration_health_consecutive_failures"),
        sa.CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_integration_health_latency_ms"),
        sa.ForeignKeyConstraint(["config_id"], [f"{CONFIG_TABLE}.id"]),
        sa.ForeignKeyConstraint(["provider_id"], [f"{PROVIDER_TABLE}.id"]),
        sa.ForeignKeyConstraint(["last_job_id"], [f"{JOB_TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_id", name="uq_integration_health_config_id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_health_snapshots_id",
        HEALTH_TABLE,
        ["id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_health_snapshots_tenant_id",
        HEALTH_TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_health_snapshots_provider_id",
        HEALTH_TABLE,
        ["provider_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_health_snapshots_status",
        HEALTH_TABLE,
        ["status"],
        unique=False,
        schema=SCHEMA,
    )

    _enable_string_tenant_rls(FEATURE_TABLE)
    _enable_string_tenant_rls(SYNC_POLICY_TABLE)
    _enable_string_tenant_rls(JOB_TABLE)
    _enable_string_tenant_rls(HEALTH_TABLE)


def downgrade() -> None:
    _disable_rls(HEALTH_TABLE)
    _disable_rls(JOB_TABLE)
    _disable_rls(SYNC_POLICY_TABLE)
    _disable_rls(FEATURE_TABLE)

    op.drop_index("ix_integration_health_snapshots_status", table_name=HEALTH_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_health_snapshots_provider_id", table_name=HEALTH_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_health_snapshots_tenant_id", table_name=HEALTH_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_health_snapshots_id", table_name=HEALTH_TABLE, schema=SCHEMA)
    op.drop_table(HEALTH_TABLE, schema=SCHEMA)

    op.drop_index("ix_integration_jobs_outbox_event_id", table_name=JOB_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_jobs_status", table_name=JOB_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_jobs_provider_id", table_name=JOB_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_jobs_feature_id", table_name=JOB_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_jobs_config_id", table_name=JOB_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_jobs_tenant_id", table_name=JOB_TABLE, schema=SCHEMA)
    op.drop_table(JOB_TABLE, schema=SCHEMA)

    op.drop_index("ix_integration_sync_policies_provider_id", table_name=SYNC_POLICY_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_sync_policies_config_id", table_name=SYNC_POLICY_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_sync_policies_tenant_id", table_name=SYNC_POLICY_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_sync_policies_id", table_name=SYNC_POLICY_TABLE, schema=SCHEMA)
    op.drop_table(SYNC_POLICY_TABLE, schema=SCHEMA)

    op.drop_index("ix_integration_features_provider_id", table_name=FEATURE_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_features_config_id", table_name=FEATURE_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_features_tenant_id", table_name=FEATURE_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_features_id", table_name=FEATURE_TABLE, schema=SCHEMA)
    op.drop_table(FEATURE_TABLE, schema=SCHEMA)
