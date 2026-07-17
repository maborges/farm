-- TENANT-FK-REPAIR-01D — Inventário das FKs CASCADE para tenants
-- Somente leitura. Lista as 200 FKs que serão convertidas para RESTRICT.
-- Útil para revisar antes da migration e para validação pós-execução.

SET search_path = farms, public;

\echo '=== FKs diretas para farms.tenants com ON DELETE CASCADE ==='
SELECT
    c.conname                                       AS constraint_name,
    c.conrelid::regclass                            AS tabela_filho,
    pg_get_constraintdef(c.oid)                     AS definicao_atual,
    CASE c.confdeltype
        WHEN 'a' THEN 'NO ACTION'
        WHEN 'r' THEN 'RESTRICT'
        WHEN 'c' THEN 'CASCADE'
        WHEN 'n' THEN 'SET NULL'
        WHEN 'd' THEN 'SET DEFAULT'
    END                                              AS on_delete
FROM pg_constraint c
WHERE c.contype        = 'f'
  AND c.confrelid      = 'farms.tenants'::regclass
  AND c.confdeltype    = 'c'   -- CASCADE
ORDER BY tabela_filho;

\echo ''
\echo '=== Contagem por ação de exclusão ==='
SELECT
    CASE confdeltype
        WHEN 'a' THEN 'NO ACTION'
        WHEN 'r' THEN 'RESTRICT'
        WHEN 'c' THEN 'CASCADE'
        WHEN 'n' THEN 'SET NULL'
        WHEN 'd' THEN 'SET DEFAULT'
    END AS on_delete,
    COUNT(*) AS total
FROM pg_constraint
WHERE contype   = 'f'
  AND confrelid = 'farms.tenants'::regclass
GROUP BY confdeltype
ORDER BY total DESC;

\echo ''
\echo '=== DDL gerado para revisão manual (sem executar) ==='
SELECT
    format(
        'ALTER TABLE %s DROP CONSTRAINT %I; ALTER TABLE %s ADD CONSTRAINT %I FOREIGN KEY (%s) REFERENCES farms.tenants(id) ON DELETE RESTRICT NOT VALID;',
        c.conrelid::regclass, c.conname,
        c.conrelid::regclass, c.conname,
        string_agg(a.attname, ', ' ORDER BY x.n)
    ) AS ddl_replace
FROM pg_constraint c
CROSS JOIN LATERAL unnest(c.conkey) WITH ORDINALITY AS x(attnum, n)
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = x.attnum
WHERE c.contype     = 'f'
  AND c.confrelid   = 'farms.tenants'::regclass
  AND c.confdeltype = 'c'
GROUP BY c.oid, c.conname, c.conrelid
ORDER BY c.conrelid::regclass::text;
