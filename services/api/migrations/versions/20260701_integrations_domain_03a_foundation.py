"""integrations domain 03a foundation

Revision ID: 20260701_integrations_domain_03a
Revises: 20260630_wizard_foundation
Create Date: 2026-07-01 00:00:00.000000
"""

from __future__ import annotations

# ruff: noqa: E501, S608
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260701_integrations_domain_03a"
down_revision = "20260630_wizard_foundation"
branch_labels = None
depends_on = None


SCHEMA = "farms"
PROVIDER_TABLE = "marketplace_integracoes"
CONFIG_TABLE = "tenant_integracoes"
CREDENTIAL_TABLE = "integration_credentials"
VERSION_TABLE = "integration_versions"

SCOPE_SQL = (
    "scope_type IN ('PLATFORM', 'TENANT', 'ESTABELECIMENTO', 'USUARIO')"
)
LIFECYCLE_SQL = (
    "lifecycle_state IN ('NOT_CONFIGURED', 'CONFIGURED', 'VALIDATING', "
    "'VALID', 'INVALID', 'ACTIVE', 'SYNCING', 'PARTIALLY_DEGRADED', "
    "'DEGRADED', 'SUSPENDED', 'DISABLED', 'REVOKED', 'REMOVED')"
)


def _enable_string_tenant_rls(table_name: str) -> None:
    policy_prefix = f"{SCHEMA}_{table_name}"
    table_ref = f"{SCHEMA}.{table_name}"
    tenant_expr = "current_setting('app.current_tenant_id', true)::text"
    op.execute(sa.text(f"ALTER TABLE {table_ref} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {table_ref} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_select_tenant
            ON {table_ref}
            FOR SELECT
            USING (tenant_id = {tenant_expr})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_insert_tenant
            ON {table_ref}
            FOR INSERT
            WITH CHECK (tenant_id = {tenant_expr})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_update_tenant
            ON {table_ref}
            FOR UPDATE
            USING (tenant_id = {tenant_expr})
            WITH CHECK (tenant_id = {tenant_expr})
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE POLICY {policy_prefix}_delete_tenant
            ON {table_ref}
            FOR DELETE
            USING (tenant_id = {tenant_expr})
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


def _drop_constraint_if_exists(table_name: str, constraint_name: str) -> None:
    op.execute(
        sa.text(
            f"ALTER TABLE {SCHEMA}.{table_name} DROP CONSTRAINT IF EXISTS {constraint_name}"
        )
    )


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(table_name, schema=SCHEMA)


def _create_provider_table() -> None:
    op.create_table(
        PROVIDER_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("descricao_curta", sa.String(length=200), nullable=True),
        sa.Column("categoria", sa.String(length=50), nullable=True),
        sa.Column("subcategoria", sa.String(length=50), nullable=True),
        sa.Column("fornecedor", sa.String(length=100), nullable=True),
        sa.Column("fornecedor_logo", sa.String(length=500), nullable=True),
        sa.Column("site_fornecedor", sa.String(length=500), nullable=True),
        sa.Column("suporte_email", sa.String(length=200), nullable=True),
        sa.Column("ativa", sa.Boolean(), nullable=True),
        sa.Column("oficial", sa.Boolean(), nullable=True),
        sa.Column("versao", sa.String(length=20), nullable=True),
        sa.Column("requisitos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("configuracoes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("total_instalacoes", sa.Integer(), nullable=True),
        sa.Column("avaliacao_media", sa.Float(), nullable=True),
        sa.Column("total_avaliacoes", sa.Integer(), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("screenshots", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("documentacao_url", sa.String(length=500), nullable=True),
        sa.Column("provider_type", sa.String(length=50), nullable=False, server_default=sa.text("'GENERIC'")),
        sa.Column("provider_definition", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("connection_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("credential_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("feature_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sync_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("health_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_marketplace_integracoes_id",
        PROVIDER_TABLE,
        ["id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_marketplace_integracoes_provider_type",
        PROVIDER_TABLE,
        ["provider_type"],
        unique=False,
        schema=SCHEMA,
    )


def _create_config_table() -> None:
    op.create_table(
        CONFIG_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("integracao_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("configuracoes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("credenciais", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("webhook_url", sa.String(length=500), nullable=True),
        sa.Column("webhook_secret", sa.String(length=200), nullable=True),
        sa.Column("ultima_sincronizacao", sa.DateTime(), nullable=True),
        sa.Column("total_sincronizacoes", sa.Integer(), nullable=True),
        sa.Column("installed_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("scope_type", sa.String(length=30), nullable=False, server_default=sa.text("'TENANT'")),
        sa.Column("scope_id", sa.String(length=50), nullable=True),
        sa.Column("lifecycle_state", sa.String(length=30), nullable=False, server_default=sa.text("'CONFIGURED'")),
        sa.Column("connection_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("credential_ref_id", sa.Integer(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(SCOPE_SQL, name="ck_tenant_integracoes_scope_type"),
        sa.CheckConstraint(LIFECYCLE_SQL, name="ck_tenant_integracoes_lifecycle_state"),
        sa.ForeignKeyConstraint(["integracao_id"], [f"{PROVIDER_TABLE}.id"]),
        sa.ForeignKeyConstraint(["credential_ref_id"], [f"{CREDENTIAL_TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tenant_integracoes_id",
        CONFIG_TABLE,
        ["id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tenant_integracoes_tenant_id",
        CONFIG_TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tenant_integracoes_scope",
        CONFIG_TABLE,
        ["tenant_id", "scope_type", "scope_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tenant_integracoes_lifecycle_state",
        CONFIG_TABLE,
        ["lifecycle_state"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_tenant_integracoes_credential_ref_id",
        CONFIG_TABLE,
        ["credential_ref_id"],
        unique=False,
        schema=SCHEMA,
    )


def upgrade() -> None:
    if _has_table(PROVIDER_TABLE):
        op.add_column(
            PROVIDER_TABLE,
            sa.Column("provider_type", sa.String(length=50), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            PROVIDER_TABLE,
            sa.Column("provider_definition", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            PROVIDER_TABLE,
            sa.Column("connection_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            PROVIDER_TABLE,
            sa.Column("credential_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            PROVIDER_TABLE,
            sa.Column("feature_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            PROVIDER_TABLE,
            sa.Column("sync_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            PROVIDER_TABLE,
            sa.Column("health_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            schema=SCHEMA,
        )
        op.execute(
            sa.text(
                f"""
                UPDATE {SCHEMA}.{PROVIDER_TABLE}
                SET provider_type = CASE lower(coalesce(categoria, ''))
                    WHEN 'erp' THEN 'ERP'
                    WHEN 'financeiro' THEN 'FINANCEIRO'
                    WHEN 'fiscal' THEN 'FISCAL'
                    WHEN 'iot' THEN 'IOT'
                    WHEN 'clima' THEN 'CLIMA'
                    WHEN 'satelite' THEN 'SATELITE'
                    WHEN 'satélite' THEN 'SATELITE'
                    WHEN 'comunicacao' THEN 'COMUNICACAO'
                    WHEN 'comunicação' THEN 'COMUNICACAO'
                    WHEN 'webhooks' THEN 'WEBHOOK'
                    ELSE 'GENERIC'
                END
                WHERE provider_type IS NULL
                """
            )
        )
        op.alter_column(
            PROVIDER_TABLE,
            "provider_type",
            existing_type=sa.String(length=50),
            nullable=False,
            server_default=sa.text("'GENERIC'"),
            schema=SCHEMA,
        )
        op.create_index(
            "ix_marketplace_integracoes_provider_type",
            PROVIDER_TABLE,
            ["provider_type"],
            unique=False,
            schema=SCHEMA,
        )
    else:
        _create_provider_table()

    op.create_table(
        CREDENTIAL_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("scope_type", sa.String(length=30), nullable=False, server_default=sa.text("'TENANT'")),
        sa.Column("scope_id", sa.String(length=50), nullable=True),
        sa.Column("segredo_criptografado", sa.Text(), nullable=False),
        sa.Column("mask_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_usuario_id", sa.String(length=50), nullable=True),
        sa.Column("rotated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(SCOPE_SQL, name="ck_integration_credentials_scope_type"),
        sa.CheckConstraint("version_number >= 1", name="ck_integration_credentials_version_number"),
        sa.ForeignKeyConstraint(["provider_id"], [f"{PROVIDER_TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "provider_id",
            "scope_type",
            "scope_id",
            "version_number",
            name="uq_integration_credentials_version_scope",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_credentials_id",
        CREDENTIAL_TABLE,
        ["id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_credentials_tenant_id",
        CREDENTIAL_TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_credentials_provider_scope",
        CREDENTIAL_TABLE,
        ["provider_id", "scope_type", "scope_id"],
        unique=False,
        schema=SCHEMA,
    )

    if _has_table(CONFIG_TABLE):
        op.add_column(
            CONFIG_TABLE,
            sa.Column("scope_type", sa.String(length=30), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            CONFIG_TABLE,
            sa.Column("scope_id", sa.String(length=50), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            CONFIG_TABLE,
            sa.Column("lifecycle_state", sa.String(length=30), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            CONFIG_TABLE,
            sa.Column("connection_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            CONFIG_TABLE,
            sa.Column("credential_ref_id", sa.Integer(), nullable=True),
            schema=SCHEMA,
        )
        op.add_column(
            CONFIG_TABLE,
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            schema=SCHEMA,
        )
        op.execute(
            sa.text(
                f"""
                UPDATE {SCHEMA}.{CONFIG_TABLE}
                SET scope_type = 'TENANT'
                WHERE scope_type IS NULL
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                UPDATE {SCHEMA}.{CONFIG_TABLE}
                SET lifecycle_state = CASE lower(coalesce(status, ''))
                    WHEN 'ativa' THEN 'ACTIVE'
                    WHEN 'inativa' THEN 'DISABLED'
                    WHEN 'pendente' THEN 'CONFIGURED'
                    ELSE 'CONFIGURED'
                END
                WHERE lifecycle_state IS NULL
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                UPDATE {SCHEMA}.{CONFIG_TABLE}
                SET connection_payload = configuracoes
                WHERE connection_payload IS NULL
                  AND configuracoes IS NOT NULL
                """
            )
        )
        op.alter_column(
            CONFIG_TABLE,
            "scope_type",
            existing_type=sa.String(length=30),
            nullable=False,
            server_default=sa.text("'TENANT'"),
            schema=SCHEMA,
        )
        op.alter_column(
            CONFIG_TABLE,
            "lifecycle_state",
            existing_type=sa.String(length=30),
            nullable=False,
            server_default=sa.text("'CONFIGURED'"),
            schema=SCHEMA,
        )
        op.create_foreign_key(
            "fk_tenant_integracoes_credential_ref_id",
            CONFIG_TABLE,
            CREDENTIAL_TABLE,
            ["credential_ref_id"],
            ["id"],
            source_schema=SCHEMA,
            referent_schema=SCHEMA,
        )
        op.create_check_constraint(
            "ck_tenant_integracoes_scope_type",
            CONFIG_TABLE,
            SCOPE_SQL,
            schema=SCHEMA,
        )
        op.create_check_constraint(
            "ck_tenant_integracoes_lifecycle_state",
            CONFIG_TABLE,
            LIFECYCLE_SQL,
            schema=SCHEMA,
        )
        op.create_index(
            "ix_tenant_integracoes_scope",
            CONFIG_TABLE,
            ["tenant_id", "scope_type", "scope_id"],
            unique=False,
            schema=SCHEMA,
        )
        op.create_index(
            "ix_tenant_integracoes_lifecycle_state",
            CONFIG_TABLE,
            ["lifecycle_state"],
            unique=False,
            schema=SCHEMA,
        )
        op.create_index(
            "ix_tenant_integracoes_credential_ref_id",
            CONFIG_TABLE,
            ["credential_ref_id"],
            unique=False,
            schema=SCHEMA,
        )
    else:
        _create_config_table()

    op.create_table(
        VERSION_TABLE,
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=50), nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("credential_ref_id", sa.Integer(), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("snapshot_mascarado", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("motivo", sa.String(length=200), nullable=True),
        sa.Column("autor_usuario_id", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("version_number >= 1", name="ck_integration_versions_version_number"),
        sa.ForeignKeyConstraint(["config_id"], [f"{CONFIG_TABLE}.id"]),
        sa.ForeignKeyConstraint(["credential_ref_id"], [f"{CREDENTIAL_TABLE}.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("config_id", "version_number", name="uq_integration_versions_config_version"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_versions_id",
        VERSION_TABLE,
        ["id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_versions_tenant_id",
        VERSION_TABLE,
        ["tenant_id"],
        unique=False,
        schema=SCHEMA,
    )
    op.create_index(
        "ix_integration_versions_config_id",
        VERSION_TABLE,
        ["config_id"],
        unique=False,
        schema=SCHEMA,
    )

    _enable_string_tenant_rls(CONFIG_TABLE)
    _enable_string_tenant_rls(CREDENTIAL_TABLE)
    _enable_string_tenant_rls(VERSION_TABLE)


def downgrade() -> None:
    _disable_rls(VERSION_TABLE)
    _disable_rls(CREDENTIAL_TABLE)
    _disable_rls(CONFIG_TABLE)

    op.drop_index("ix_integration_versions_config_id", table_name=VERSION_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_versions_tenant_id", table_name=VERSION_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_versions_id", table_name=VERSION_TABLE, schema=SCHEMA)
    op.drop_table(VERSION_TABLE, schema=SCHEMA)

    op.drop_index("ix_tenant_integracoes_credential_ref_id", table_name=CONFIG_TABLE, schema=SCHEMA)
    op.drop_index("ix_tenant_integracoes_lifecycle_state", table_name=CONFIG_TABLE, schema=SCHEMA)
    op.drop_index("ix_tenant_integracoes_scope", table_name=CONFIG_TABLE, schema=SCHEMA)
    _drop_constraint_if_exists(CONFIG_TABLE, "ck_tenant_integracoes_lifecycle_state")
    _drop_constraint_if_exists(CONFIG_TABLE, "ck_tenant_integracoes_scope_type")
    _drop_constraint_if_exists(CONFIG_TABLE, "fk_tenant_integracoes_credential_ref_id")
    op.drop_column(CONFIG_TABLE, "deleted_at", schema=SCHEMA)
    op.drop_column(CONFIG_TABLE, "credential_ref_id", schema=SCHEMA)
    op.drop_column(CONFIG_TABLE, "connection_payload", schema=SCHEMA)
    op.drop_column(CONFIG_TABLE, "lifecycle_state", schema=SCHEMA)
    op.drop_column(CONFIG_TABLE, "scope_id", schema=SCHEMA)
    op.drop_column(CONFIG_TABLE, "scope_type", schema=SCHEMA)

    op.drop_index(
        "ix_integration_credentials_provider_scope",
        table_name=CREDENTIAL_TABLE,
        schema=SCHEMA,
    )
    op.drop_index("ix_integration_credentials_tenant_id", table_name=CREDENTIAL_TABLE, schema=SCHEMA)
    op.drop_index("ix_integration_credentials_id", table_name=CREDENTIAL_TABLE, schema=SCHEMA)
    op.drop_table(CREDENTIAL_TABLE, schema=SCHEMA)

    op.drop_index(
        "ix_marketplace_integracoes_provider_type",
        table_name=PROVIDER_TABLE,
        schema=SCHEMA,
    )
    op.drop_column(PROVIDER_TABLE, "health_schema", schema=SCHEMA)
    op.drop_column(PROVIDER_TABLE, "sync_schema", schema=SCHEMA)
    op.drop_column(PROVIDER_TABLE, "feature_schema", schema=SCHEMA)
    op.drop_column(PROVIDER_TABLE, "credential_schema", schema=SCHEMA)
    op.drop_column(PROVIDER_TABLE, "connection_schema", schema=SCHEMA)
    op.drop_column(PROVIDER_TABLE, "provider_definition", schema=SCHEMA)
    op.drop_column(PROVIDER_TABLE, "provider_type", schema=SCHEMA)
