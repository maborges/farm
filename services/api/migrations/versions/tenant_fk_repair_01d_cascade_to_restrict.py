"""tenant_fk_repair_01d: substituir ON DELETE CASCADE por RESTRICT nas FKs diretas para tenants

Revision ID: tenant_fk_repair_01d
Revises: tenant_integrity_repair_01b3_multiprovider
Create Date: 2026-07-17

Escopo: ~200 FKs diretas farms.X.tenant_id → farms.tenants(id) com ON DELETE CASCADE
Objetivo: impedir exclusão destrutiva em cascata ao deletar um Tenant

Estratégia:
  - PL/pgSQL loop: itera sobre pg_constraint em tempo de execução
  - Cada FK: DROP + ADD RESTRICT NOT VALID (lock brevíssimo por tabela)
  - VALIDATE em lote separado (ShareUpdateExclusiveLock — sem bloqueio de leitura/escrita)
  - Exceções deliberadas (ON DELETE NO ACTION já existentes) não são tocadas
  - 2 FKs com NO ACTION são preservadas (email_logs e similares)

Lotes por domínio (ordem de menor para maior impacto operacional):
  1. Técnicas/infra: logs, outbox, quarentena, notificações
  2. Auth/billing: assinaturas, cobranças, convites, perfis
  3. Core/cadastros: pessoas, produtos, equipamentos, áreas
  4. Agrícola/operacional: safras, cultivos, operações, colheita
  5. Financeiro/estoque: compras, movimentos, rateios
  6. Frota/campo: jornadas, apontamentos, abastecimentos
  7. Enterprise/ESG: certificações, alertas, integrações
"""
from alembic import op

revision = "tenant_fk_repair_01d"
down_revision = "tenant_integrity_repair_01b4_iot_auxiliares"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    DO $$
    DECLARE
        r RECORD;
        col_list TEXT;
    BEGIN
        -- Iterar sobre todas as FKs CASCADE para tenants
        FOR r IN
            SELECT
                c.oid,
                c.conname,
                c.conrelid::regclass::text AS child_table,
                string_agg(a.attname, ', ' ORDER BY x.n) AS col_names
            FROM pg_constraint c
            CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS x(attnum, n)
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = x.attnum
            WHERE c.contype     = 'f'
              AND c.confrelid   = 'farms.tenants'::regclass
              AND c.confdeltype = 'c'  -- CASCADE apenas
            GROUP BY c.oid, c.conname, c.conrelid
            ORDER BY c.conrelid::regclass::text
        LOOP
            RAISE NOTICE 'Convertendo % em %', r.conname, r.child_table;

            -- DROP constraint existente (CASCADE)
            EXECUTE format(
                'ALTER TABLE %s DROP CONSTRAINT %I',
                r.child_table, r.conname
            );

            -- ADD com RESTRICT NOT VALID (sem scan de linhas)
            EXECUTE format(
                'ALTER TABLE %s ADD CONSTRAINT %I FOREIGN KEY (%s) REFERENCES farms.tenants(id) ON DELETE RESTRICT NOT VALID',
                r.child_table, r.conname, r.col_names
            );
        END LOOP;

        RAISE NOTICE 'DROP+ADD concluído. Iniciando VALIDATE em lote...';

        -- VALIDATE separado: lock mínimo (ShareUpdateExclusiveLock)
        FOR r IN
            SELECT c.conname, c.conrelid::regclass::text AS child_table
            FROM pg_constraint c
            WHERE c.contype      = 'f'
              AND c.confrelid    = 'farms.tenants'::regclass
              AND c.confdeltype  = 'r'   -- RESTRICT (já convertidas)
              AND NOT c.convalidated     -- apenas NOT VALID
            ORDER BY c.conrelid::regclass::text
        LOOP
            RAISE NOTICE 'Validando % em %', r.conname, r.child_table;
            EXECUTE format(
                'ALTER TABLE %s VALIDATE CONSTRAINT %I',
                r.child_table, r.conname
            );
        END LOOP;

        RAISE NOTICE 'TENANT-FK-REPAIR-01D concluído.';
    END $$;
    """)

    op.execute("COMMIT")


def downgrade() -> None:
    # Reversão: CASCADE → RESTRICT é intencional e difícil de reverter automaticamente.
    # Executar 01d_diagnose_cascade.sql (pós-downgrade) para verificar estado.
    op.execute("""
    DO $$
    DECLARE
        r RECORD;
        col_list TEXT;
    BEGIN
        FOR r IN
            SELECT
                c.conname,
                c.conrelid::regclass::text AS child_table,
                string_agg(a.attname, ', ' ORDER BY x.n) AS col_names
            FROM pg_constraint c
            CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS x(attnum, n)
            JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = x.attnum
            WHERE c.contype     = 'f'
              AND c.confrelid   = 'farms.tenants'::regclass
              AND c.confdeltype = 'r'  -- RESTRICT → reverter para CASCADE
            GROUP BY c.oid, c.conname, c.conrelid
            ORDER BY c.conrelid::regclass::text
        LOOP
            EXECUTE format(
                'ALTER TABLE %s DROP CONSTRAINT %I',
                r.child_table, r.conname
            );
            EXECUTE format(
                'ALTER TABLE %s ADD CONSTRAINT %I FOREIGN KEY (%s) REFERENCES farms.tenants(id) ON DELETE CASCADE NOT VALID',
                r.child_table, r.conname, r.col_names
            );
        END LOOP;

        FOR r IN
            SELECT c.conname, c.conrelid::regclass::text AS child_table
            FROM pg_constraint c
            WHERE c.contype = 'f' AND c.confrelid = 'farms.tenants'::regclass
              AND c.confdeltype = 'c' AND NOT c.convalidated
            ORDER BY c.conrelid::regclass::text
        LOOP
            EXECUTE format('ALTER TABLE %s VALIDATE CONSTRAINT %I', r.child_table, r.conname);
        END LOOP;
    END $$;
    """)

    op.execute("COMMIT")
