"""tenant_integrity_repair_01b4: IoT e auxiliares — varchar→uuid + FKs

Revision ID: tenant_integrity_repair_01b4_iot_auxiliares
Revises: tenant_integrity_repair_01b3_multiprovider
Create Date: 2026-07-17

Escopo: case_ih, john_deere, comparador_precos, whatsapp
        tenant_id varchar(50) → uuid + FK farms.tenants(id) ON DELETE NO ACTION.
"""
from alembic import op

revision = "tenant_integrity_repair_01b4_iot_auxiliares"
down_revision = "tenant_integrity_repair_01b3_multiprovider"
branch_labels = None
depends_on = None

TABELAS = [
    "case_ih",
    "john_deere",
    "comparador_precos",
    "whatsapp",
]


def upgrade() -> None:
    for tabela in TABELAS:
        nome_fk = f"fk_{tabela}_tenant"
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
        nome_fk = f"fk_{tabela}_tenant"
        op.execute(f"ALTER TABLE farms.{tabela} DROP CONSTRAINT IF EXISTS {nome_fk}")
        op.execute(f"""
            ALTER TABLE farms.{tabela}
            ALTER COLUMN tenant_id TYPE character varying(50)
            USING tenant_id::text
        """)
