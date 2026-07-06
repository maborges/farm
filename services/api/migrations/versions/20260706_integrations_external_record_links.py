"""integrations external record links foundation

Revision ID: 20260706_integrations_external_record_links
Revises: 20260704_sankhya_gateway_auth
Create Date: 2026-07-06 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260706_integrations_external_record_links"
down_revision = "20260704_sankhya_gateway_auth"
branch_labels = None
depends_on = None


SCHEMA = "farms"
LINK_TABLE = "integration_external_record_links"
HISTORY_TABLE = "integration_external_record_link_history"
PROVIDER_TABLE = "marketplace_integracoes"
CONFIG_TABLE = "tenant_integracoes"
FEATURE_TABLE = "integration_features"
JOB_TABLE = "integration_jobs"
SCOPE_TENANT_EXPR = "current_setting('app.current_tenant_id', true)::text"
LINK_STATUS_SQL = "status IN ('ACTIVE', 'PENDING', 'CONFLICT', 'SUPERSEDED', 'INACTIVE')"
LINK_ORIGIN_SQL = (
    "origin IN ('IMPORT', 'EXPORT', 'MANUAL_RECONCILIATION', 'MIGRATION', 'SYNC_JOB')"
)
LINK_CONFIDENCE_SQL = "confidence IN ('HIGH', 'MEDIUM', 'LOW', 'MANUAL_CONFIRMED')"
LINK_SCOPE_SQL = "scope_type IN ('PLATFORM', 'TENANT', 'ESTABELECIMENTO', 'USUARIO')"
HISTORY_EVENT_SQL = (
    "event_type IN ('CREATED', 'UPDATED', 'CONFLICT_MARKED', 'RECONCILED', "
    "'SUPERSEDED', 'DEACTIVATED', 'REACTIVATED')"
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
        LINK_TABLE,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Identificador interno da associacao oficial.",
        ),
        sa.Column("tenant_id", sa.String(length=50), nullable=False, comment="Tenant dono da associacao."),
        sa.Column(
            "provider_id",
            sa.Integer(),
            nullable=False,
            comment="Provider do sistema externo.",
        ),
        sa.Column(
            "config_id",
            sa.Integer(),
            nullable=False,
            comment="Configuracao da integracao usada pela associacao.",
        ),
        sa.Column(
            "feature_id",
            sa.Integer(),
            nullable=True,
            comment="Feature de integracao relacionada, quando aplicavel.",
        ),
        sa.Column("environment", sa.String(length=50), nullable=False, comment="Ambiente do sistema externo."),
        sa.Column(
            "scope_type",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'TENANT'"),
            comment="Escopo de configuracao da associacao.",
        ),
        sa.Column("scope_id", sa.String(length=50), nullable=True, comment="Escopo especifico, como estabelecimento."),
        sa.Column(
            "external_company_id",
            sa.String(length=50),
            nullable=True,
            comment="Codigo de empresa externa, como CODEMP.",
        ),
        sa.Column(
            "external_branch_id",
            sa.String(length=50),
            nullable=True,
            comment="Codigo de filial externa, como CODFILIAL.",
        ),
        sa.Column(
            "local_entity",
            sa.String(length=100),
            nullable=False,
            comment="Nome da entidade local do AgroSaaS.",
        ),
        sa.Column(
            "local_record_id",
            sa.String(length=100),
            nullable=False,
            comment="Identificador do registro local.",
        ),
        sa.Column(
            "external_entity",
            sa.String(length=100),
            nullable=False,
            comment="Nome da entidade no sistema externo.",
        ),
        sa.Column(
            "external_record_id",
            sa.String(length=255),
            nullable=False,
            comment="Identificador externo principal.",
        ),
        sa.Column(
            "secondary_keys",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Chaves auxiliares para deduplicacao e reconciliacao.",
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
            comment="Estado operacional da associacao.",
        ),
        sa.Column(
            "origin",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'SYNC_JOB'"),
            comment="Origem da criacao da associacao.",
        ),
        sa.Column(
            "confidence",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'MEDIUM'"),
            comment="Confianca atual da associacao.",
        ),
        sa.Column(
            "last_sync_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Ultima sincronizacao que validou a associacao.",
        ),
        sa.Column(
            "last_job_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Job de integracao mais recente relacionado.",
        ),
        sa.Column("notes", sa.Text(), nullable=True, comment="Observacoes operacionais."),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Metadados adicionais do provider.",
        ),
        sa.Column(
            "created_by_usuario_id",
            sa.String(length=50),
            nullable=True,
            comment="Usuario que criou a associacao manualmente, quando houver.",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True, comment="Soft delete logico da associacao."),
        sa.CheckConstraint(LINK_STATUS_SQL, name="ck_external_record_links_status"),
        sa.CheckConstraint(LINK_ORIGIN_SQL, name="ck_external_record_links_origin"),
        sa.CheckConstraint(LINK_CONFIDENCE_SQL, name="ck_external_record_links_confidence"),
        sa.CheckConstraint(LINK_SCOPE_SQL, name="ck_external_record_links_scope_type"),
        sa.ForeignKeyConstraint(["provider_id"], [f"{PROVIDER_TABLE}.id"]),
        sa.ForeignKeyConstraint(["config_id"], [f"{CONFIG_TABLE}.id"]),
        sa.ForeignKeyConstraint(["feature_id"], [f"{FEATURE_TABLE}.id"]),
        sa.ForeignKeyConstraint(["last_job_id"], [f"{JOB_TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
        comment="Associacao oficial entre um registro local e um registro em sistema externo.",
    )
    op.create_index(
        "ix_external_record_links_tenant_id",
        LINK_TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_external_record_links_tenant_local",
        LINK_TABLE,
        ["tenant_id", "local_entity", "local_record_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_external_record_links_tenant_external",
        LINK_TABLE,
        ["tenant_id", "provider_id", "external_entity", "external_record_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_external_record_links_tenant_status",
        LINK_TABLE,
        ["tenant_id", "status"],
        unique=False,
        schema=SCHEMA,
    )
    op.execute(
        sa.text(
            f"""
            CREATE UNIQUE INDEX uq_external_record_links_active_external
            ON {SCHEMA}.{LINK_TABLE} (
                tenant_id,
                config_id,
                environment,
                external_entity,
                external_record_id,
                coalesce(external_company_id, ''),
                coalesce(external_branch_id, '')
            )
            WHERE status = 'ACTIVE' AND deleted_at IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE UNIQUE INDEX uq_external_record_links_active_local
            ON {SCHEMA}.{LINK_TABLE} (
                tenant_id,
                config_id,
                environment,
                local_entity,
                local_record_id,
                external_entity
            )
            WHERE status = 'ACTIVE' AND deleted_at IS NULL
            """
        )
    )

    op.create_table(
        HISTORY_TABLE,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Identificador do evento historico.",
        ),
        sa.Column("tenant_id", sa.String(length=50), nullable=False, comment="Tenant dono do historico."),
        sa.Column(
            "link_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment="Associacao oficial afetada.",
        ),
        sa.Column(
            "event_type",
            sa.String(length=30),
            nullable=False,
            comment="Tipo do evento historico.",
        ),
        sa.Column(
            "previous_external_record_id",
            sa.String(length=255),
            nullable=True,
            comment="Identificador externo anterior, quando mudou.",
        ),
        sa.Column(
            "new_external_record_id",
            sa.String(length=255),
            nullable=True,
            comment="Identificador externo novo ou atual.",
        ),
        sa.Column("previous_status", sa.String(length=30), nullable=True, comment="Status anterior."),
        sa.Column("new_status", sa.String(length=30), nullable=True, comment="Novo status."),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Job relacionado a alteracao.",
        ),
        sa.Column(
            "actor_usuario_id",
            sa.String(length=50),
            nullable=True,
            comment="Usuario responsavel pela alteracao manual, quando houver.",
        ),
        sa.Column("reason", sa.String(length=255), nullable=True, comment="Motivo resumido da alteracao."),
        sa.Column(
            "details_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Detalhes adicionais do evento.",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(HISTORY_EVENT_SQL, name="ck_external_record_link_history_event_type"),
        sa.ForeignKeyConstraint(["link_id"], [f"{LINK_TABLE}.id"]),
        sa.ForeignKeyConstraint(["job_id"], [f"{JOB_TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
        comment="Historico de alteracoes da associacao oficial com sistemas externos.",
    )
    op.create_index(
        "ix_external_record_link_history_tenant_id",
        HISTORY_TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_external_record_link_history_tenant_link",
        HISTORY_TABLE,
        ["tenant_id", "link_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_external_record_link_history_tenant_event",
        HISTORY_TABLE,
        ["tenant_id", "event_type"],
        unique=False,
        schema=SCHEMA,
    )

    _enable_string_tenant_rls(LINK_TABLE)
    _enable_string_tenant_rls(HISTORY_TABLE)


def downgrade() -> None:
    _disable_rls(HISTORY_TABLE)
    _disable_rls(LINK_TABLE)
    op.drop_index("ix_external_record_link_history_tenant_event", table_name=HISTORY_TABLE, schema=SCHEMA)
    op.drop_index("ix_external_record_link_history_tenant_link", table_name=HISTORY_TABLE, schema=SCHEMA)
    op.drop_index("ix_external_record_link_history_tenant_id", table_name=HISTORY_TABLE, schema=SCHEMA)
    op.drop_table(HISTORY_TABLE, schema=SCHEMA)
    op.execute(sa.text(f"DROP INDEX IF EXISTS {SCHEMA}.uq_external_record_links_active_local"))
    op.execute(sa.text(f"DROP INDEX IF EXISTS {SCHEMA}.uq_external_record_links_active_external"))
    op.drop_index("ix_external_record_links_tenant_status", table_name=LINK_TABLE, schema=SCHEMA)
    op.drop_index("ix_external_record_links_tenant_external", table_name=LINK_TABLE, schema=SCHEMA)
    op.drop_index("ix_external_record_links_tenant_local", table_name=LINK_TABLE, schema=SCHEMA)
    op.drop_index("ix_external_record_links_tenant_id", table_name=LINK_TABLE, schema=SCHEMA)
    op.drop_table(LINK_TABLE, schema=SCHEMA)
