"""tenant_integrity_repair_01b3: Núcleo multiprovider — varchar→uuid + FKs

Revision ID: tenant_integrity_repair_01b3_multiprovider
Revises: tenant_integrity_repair_01b2_onda1
Create Date: 2026-07-17

Escopo: 9 tabelas do núcleo multiprovider, todas com 0 registros.
        tenant_id varchar(50) → uuid + FK farms.tenants(id) ON DELETE NO ACTION.
"""
from alembic import op

revision = "tenant_integrity_repair_01b3_multiprovider"
down_revision = "tenant_integrity_repair_01b2_onda1"
branch_labels = None
depends_on = None

TABELAS = [
    "tenant_integracoes",
    "integration_credentials",
    "integration_external_record_links",
    "integration_external_record_link_history",
    "integration_features",
    "integration_health_snapshots",
    "integration_jobs",
    "integration_sync_policies",
    "integration_versions",
]


def upgrade() -> None:
    for tabela in TABELAS:
        nome_fk = f"fk_{tabela[:25]}_tenant"
        op.execute(f"""
            ALTER TABLE farms.{tabela}
            ALTER COLUMN tenant_id TYPE uuid
            USING tenant_id::uuid
        """)
        op.execute(f"""
            ALTER TABLE farms.{tabela}
            ADD CONSTRAINT {nome_fk}
            FOREIGN KEY (tenant_id)
            REFERENCES farms.tenants(id)
            ON DELETE NO ACTION
            NOT VALID
        """)
        op.execute(f"""
            ALTER TABLE farms.{tabela}
            VALIDATE CONSTRAINT {nome_fk}
        """)


def downgrade() -> None:
    for tabela in reversed(TABELAS):
        nome_fk = f"fk_{tabela[:25]}_tenant"
        op.execute(f"ALTER TABLE farms.{tabela} DROP CONSTRAINT IF EXISTS {nome_fk}")
        op.execute(f"""
            ALTER TABLE farms.{tabela}
            ALTER COLUMN tenant_id TYPE character varying(50)
            USING tenant_id::text
        """)
