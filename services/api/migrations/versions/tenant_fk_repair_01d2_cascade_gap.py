"""tenant_fk_repair_01d2: fecha lacuna de cobertura do 01d — 17 FKs CASCADE criadas após a migration original

Revision ID: tenant_fk_repair_01d2
Revises: 20260814_notif_leituras_acao
Create Date: 2026-08-14

Escopo: 17 FKs diretas farms.X.tenant_id → farms.tenants(id) com ON DELETE
CASCADE encontradas pela auditoria 01F em 2026-08-14 — tabelas criadas
DEPOIS da migration tenant_fk_repair_01d (2026-07-17), então nunca
converteram pra RESTRICT: cadastros_tipos_servico, compras_pedidos_confirmacoes,
core_sequenciais, estoque_localizacoes, estoque_requisicao_confirmacoes,
fin_itens_ordem_pagamento, fin_ordens_pagamento, notificacoes_leituras,
planos_operacionais (+ tarefas/insumos/mao_obra/maquinario), receitas_aplicacao
(+ insumos/mao_obra), safra_tarefa_necessidades.

Reaplica exatamente a mesma estratégia genérica da 01d original (que já
itera dinamicamente sobre pg_constraint, então não precisa hardcodar nomes
de tabela): DROP + ADD RESTRICT NOT VALID, depois VALIDATE em lote.
"""
from alembic import op

revision = "tenant_fk_repair_01d2"
down_revision = "20260814_notif_leituras_acao"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    DO $$
    DECLARE
        r RECORD;
    BEGIN
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

            EXECUTE format(
                'ALTER TABLE %s DROP CONSTRAINT %I',
                r.child_table, r.conname
            );

            EXECUTE format(
                'ALTER TABLE %s ADD CONSTRAINT %I FOREIGN KEY (%s) REFERENCES farms.tenants(id) ON DELETE RESTRICT NOT VALID',
                r.child_table, r.conname, r.col_names
            );
        END LOOP;

        RAISE NOTICE 'DROP+ADD concluído. Iniciando VALIDATE em lote...';

        FOR r IN
            SELECT c.conname, c.conrelid::regclass::text AS child_table
            FROM pg_constraint c
            WHERE c.contype      = 'f'
              AND c.confrelid    = 'farms.tenants'::regclass
              AND c.confdeltype  = 'r'
              AND NOT c.convalidated
            ORDER BY c.conrelid::regclass::text
        LOOP
            RAISE NOTICE 'Validando % em %', r.conname, r.child_table;
            EXECUTE format(
                'ALTER TABLE %s VALIDATE CONSTRAINT %I',
                r.child_table, r.conname
            );
        END LOOP;

        RAISE NOTICE 'TENANT-FK-REPAIR-01D2 concluído.';
    END $$;
    """)

    op.execute("COMMIT")


def downgrade() -> None:
    # Não há como saber, de forma genérica, quais eram exatamente as 17 FKs
    # originais desta migration (o loop de upgrade converte QUALQUER CASCADE
    # remanescente, não só essas 17) — reversão automática não é segura.
    # Se necessário reverter, usar 01d_diagnose_cascade.sql pra decidir
    # manualmente quais constraints voltar para CASCADE.
    pass
