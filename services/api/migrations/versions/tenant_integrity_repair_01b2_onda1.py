"""tenant_integrity_repair_01b2: Onda 1 — converter tenant_id varchar→uuid, adicionar FKs

Revision ID: tenant_integrity_repair_01b2_onda1
Revises: tenant_integrity_repair_01c_merge
Create Date: 2026-07-17

Escopo: 8 tabelas vazias varchar→uuid + FK para farms.tenants (NO ACTION).
        1 tabela billing_solicitacoes_comerciais_historico (já uuid) + FK + índice.
Preflight: todas as 9 tabelas tinham 0 registros antes da execução.
"""
from alembic import op

revision = "tenant_integrity_repair_01b2_onda1"
down_revision = "tenant_integrity_repair_01c_merge"
branch_labels = None
depends_on = None

TABELAS_VARCHAR = [
    "amostras",
    "diagnosticos",
    "mapas_fertilidade",
    "pragas_doencas",
    "prescricoes_vra",
    "recomendacoes",
    "tratamentos",
    "modelos_ml",
]


def upgrade() -> None:
    # 1. Converter varchar → uuid e adicionar FK nas 8 tabelas vazias
    for tabela in TABELAS_VARCHAR:
        nome_fk = f"fk_{tabela[:20]}_tenant"
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

    # 2. billing_solicitacoes_comerciais_historico — já é uuid, só FK e índice
    op.execute("""
        ALTER TABLE farms.billing_solicitacoes_comerciais_historico
        ADD CONSTRAINT fk_billing_sol_com_hist_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES farms.tenants(id)
        ON DELETE NO ACTION
        NOT VALID
    """)
    op.execute("""
        ALTER TABLE farms.billing_solicitacoes_comerciais_historico
        VALIDATE CONSTRAINT fk_billing_sol_com_hist_tenant
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_billing_sol_com_hist_tenant_id
        ON farms.billing_solicitacoes_comerciais_historico (tenant_id)
    """)
    op.execute("COMMIT")


def downgrade() -> None:
    # Remover índice criado
    op.execute(
        "DROP INDEX IF EXISTS farms.ix_billing_sol_com_hist_tenant_id"
    )
    # Remover FK de billing
    op.execute(
        "ALTER TABLE farms.billing_solicitacoes_comerciais_historico "
        "DROP CONSTRAINT IF EXISTS fk_billing_sol_com_hist_tenant"
    )
    # Remover FKs e reverter tipo das 8 tabelas
    for tabela in reversed(TABELAS_VARCHAR):
        nome_fk = f"fk_{tabela[:20]}_tenant"
        op.execute(
            f"ALTER TABLE farms.{tabela} DROP CONSTRAINT IF EXISTS {nome_fk}"
        )
        op.execute(f"""
            ALTER TABLE farms.{tabela}
            ALTER COLUMN tenant_id TYPE character varying
            USING tenant_id::text
        """)
    op.execute("COMMIT")
