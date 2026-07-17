"""tenant_fk_repair_01b: FKs diretas para tenants nas tabelas UUID sem constraint

Revision ID: tenant_fk_repair_01b
Revises: tenant_fk_repair_01a
Create Date: 2026-07-17

Tabelas cobertas (tenant_id uuid, físicas, sem FK para tenants):
  - billing_solicitacoes_comerciais_historico  (também adiciona índice ausente)

Estratégia:
  - ADD CONSTRAINT ... NOT VALID  → não bloqueia tabela, não varre linhas existentes
  - VALIDATE CONSTRAINT           → validação online, lock mínimo (ShareUpdateExclusiveLock)
  - ON DELETE RESTRICT            → nunca CASCADE em FK direta para tenants
  - Separar ADD e VALIDATE em steps distintos para controle em produção

PRÉ-CONDIÇÃO: 01b_diagnose_orphans.sql deve retornar 0 orphans antes desta migration.
"""
from alembic import op
import sqlalchemy as sa

revision = "tenant_fk_repair_01b"
down_revision = "tenant_fk_repair_01a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ----------------------------------------------------------------
    # billing_solicitacoes_comerciais_historico
    # ----------------------------------------------------------------
    # índice ausente (auditoria: índice: não)
    op.create_index(
        "ix_billing_sol_comerciais_hist_tenant",
        "billing_solicitacoes_comerciais_historico",
        ["tenant_id"],
        schema="farms",
    )
    # FK NOT VALID — não escaneia linhas existentes
    op.execute("""
        ALTER TABLE farms.billing_solicitacoes_comerciais_historico
        ADD CONSTRAINT billing_sol_hist_tenant_id_fkey
        FOREIGN KEY (tenant_id)
        REFERENCES farms.tenants(id)
        ON DELETE RESTRICT
        NOT VALID
    """)
    # Validação online — lock mínimo
    op.execute("""
        ALTER TABLE farms.billing_solicitacoes_comerciais_historico
        VALIDATE CONSTRAINT billing_sol_hist_tenant_id_fkey
    """)

    # ----------------------------------------------------------------
    # Placeholder: demais tabelas UUID identificadas na auditoria
    # Descomentar após confirmar 0 orphans via 01b_diagnose_orphans.sql
    # ----------------------------------------------------------------
    #
    # Padrão para cada tabela:
    #
    # op.execute("""
    #     ALTER TABLE farms.<tabela>
    #     ADD CONSTRAINT <tabela>_tenant_id_fkey
    #     FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id)
    #     ON DELETE RESTRICT NOT VALID
    # """)
    # op.execute("""
    #     ALTER TABLE farms.<tabela>
    #     VALIDATE CONSTRAINT <tabela>_tenant_id_fkey
    # """)

    op.execute("COMMIT")


def downgrade() -> None:
    op.execute("""
        ALTER TABLE farms.billing_solicitacoes_comerciais_historico
        DROP CONSTRAINT IF EXISTS billing_sol_hist_tenant_id_fkey
    """)
    op.drop_index(
        "ix_billing_sol_comerciais_hist_tenant",
        table_name="billing_solicitacoes_comerciais_historico",
        schema="farms",
    )
    op.execute("COMMIT")
