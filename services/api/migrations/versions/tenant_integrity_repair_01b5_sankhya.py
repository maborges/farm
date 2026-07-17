# ruff: noqa: S608
"""Fechar integridade de tenant nas tabelas provider-specific Sankhya.

Revision ID: tenant_integrity_repair_01b5_sankhya
Revises: tenant_integrity_repair_01b4_iot_auxiliares
Create Date: 2026-07-17

Converte tenant_id de varchar(50) para uuid, remove somente registros sem
tenant físico e adiciona FKs validadas para farms.tenants(id).
"""

from alembic import op

revision = "tenant_integrity_repair_01b5_sankhya"
down_revision = "tenant_integrity_repair_01b4_iot_auxiliares"
branch_labels = None
depends_on = None

TABELAS = [
    "sankhya_sync_logs",
    "sankhya_config",
    "sankhya_pessoas",
    "sankhya_produtos",
    "sankhya_nfe",
    "sankhya_lancamentos_financeiros",
    "sankhya_tabelas",
]


def _assert_uuid_values(tabela: str) -> None:
    """Abortar antes de qualquer DML se houver tenant_id não conversível."""
    op.execute(f"""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM farms.{tabela}
                WHERE NOT pg_input_is_valid(tenant_id, 'uuid')
            ) THEN
                RAISE EXCEPTION 'tenant_id inválido em farms.{tabela}';
            END IF;
        END $$
    """)


def _delete_orphans(tabela: str) -> None:
    """Remover e contabilizar apenas linhas sem tenant físico correspondente."""
    op.execute(f"""
        DO $$ DECLARE removidos integer; BEGIN
            DELETE FROM farms.{tabela} registro
            WHERE NOT EXISTS (
                SELECT 1 FROM farms.tenants tenant
                WHERE tenant.id = registro.tenant_id::uuid
            );
            GET DIAGNOSTICS removidos = ROW_COUNT;
            RAISE NOTICE '01B5: farms.{tabela}, órfãos removidos=%', removidos;
        END $$
    """)


def _convert_and_constrain(tabela: str) -> None:
    """Converter tenant_id e criar FK validada sem cascade destrutivo."""
    nome_fk = f"fk_{tabela}_tenant"
    op.execute(f"""
        ALTER TABLE farms.{tabela}
        ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid
    """)
    op.execute(f"""
        ALTER TABLE farms.{tabela} ADD CONSTRAINT {nome_fk}
        FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id)
        ON DELETE NO ACTION NOT VALID
    """)
    op.execute(f"ALTER TABLE farms.{tabela} VALIDATE CONSTRAINT {nome_fk}")


def upgrade() -> None:
    """Sanear orphans e implantar integridade física nas sete tabelas."""
    for tabela in TABELAS:
        _assert_uuid_values(tabela)
    for tabela in TABELAS:
        _delete_orphans(tabela)
    for tabela in TABELAS:
        _convert_and_constrain(tabela)


def downgrade() -> None:
    """Remover FKs e restaurar o tipo textual; dados saneados não retornam."""
    for tabela in reversed(TABELAS):
        nome_fk = f"fk_{tabela}_tenant"
        op.execute(f"ALTER TABLE farms.{tabela} DROP CONSTRAINT IF EXISTS {nome_fk}")
        op.execute(f"""
            ALTER TABLE farms.{tabela}
            ALTER COLUMN tenant_id TYPE character varying(50)
            USING tenant_id::text
        """)
