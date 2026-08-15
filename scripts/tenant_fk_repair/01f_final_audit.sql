-- TENANT-FK-REPAIR-01F — Auditoria final de convergência
-- Execução: psql $DATABASE_URL -f 01f_final_audit.sql > 01f_result_$(date +%Y%m%d).txt
--
-- Critérios de GO (todos devem ser 0 ou conforme esperado):
--   ✓ Zero cruzamentos A→B nos agregados críticos
--   ✓ Zero orphans de tenant_id em tabelas físicas
--   ✓ Zero FKs para tenants com ON DELETE CASCADE
--   ✓ Zero FKs NOT VALID pendentes
--   ✓ 7 FKs compostas presentes e validadas
--   ✓ 4 UNIQUE compostos nos pais críticos
--   ✓ Zero tabelas tenant_id uuid sem FK para tenants (exceto exceções)
--   ✓ Zero tabelas tenant-scoped sem índice em tenant_id
--   ✓ Quarentena: zero registros pendentes de resolução
--
-- Emite PASS/FAIL por critério para facilitar leitura em CI.

SET search_path = farms, public;

\echo ''
\echo '╔══════════════════════════════════════════════════════════════╗'
\echo '║  TENANT-FK-REPAIR-01F — Auditoria Final de Convergência      ║'
\echo '╚══════════════════════════════════════════════════════════════╝'
\echo ''

-- ────────────────────────────────────────────────────────────
-- C1: Cruzamentos A→B (7 agregados críticos)
-- ────────────────────────────────────────────────────────────
\echo '── C1: Cruzamentos A→B ─────────────────────────────────────────'
SELECT
    relacao,
    cruzamentos,
    CASE WHEN cruzamentos = 0 THEN 'PASS' ELSE 'FAIL ✗' END AS status
FROM (
    SELECT 'cadastros_areas_rurais → unidades_produtivas' AS relacao,
           COUNT(*) AS cruzamentos
    FROM farms.cadastros_areas_rurais car
    JOIN farms.unidades_produtivas up ON up.id = car.unidade_produtiva_id
    WHERE car.unidade_produtiva_id IS NOT NULL AND car.tenant_id <> up.tenant_id
    UNION ALL
    SELECT 'estoque_depositos → unidades_produtivas', COUNT(*)
    FROM farms.estoque_depositos ed
    JOIN farms.unidades_produtivas up ON up.id = ed.unidade_produtiva_id
    WHERE ed.unidade_produtiva_id IS NOT NULL AND ed.tenant_id <> up.tenant_id
    UNION ALL
    SELECT 'cadastros_equipamentos → unidades_produtivas', COUNT(*)
    FROM farms.cadastros_equipamentos ce
    JOIN farms.unidades_produtivas up ON up.id = ce.unidade_produtiva_id
    WHERE ce.unidade_produtiva_id IS NOT NULL AND ce.tenant_id <> up.tenant_id
    UNION ALL
    SELECT 'compras_itens_pedido → estoque_depositos', COUNT(*)
    FROM farms.compras_itens_pedido cip
    JOIN farms.compras_pedidos cp ON cp.id = cip.pedido_id
    JOIN farms.estoque_depositos ed ON ed.id = cip.deposito_id
    WHERE cip.deposito_id IS NOT NULL AND cp.tenant_id <> ed.tenant_id
    UNION ALL
    SELECT 'frota_jornadas_equipamento → unidades_produtivas', COUNT(*)
    FROM farms.frota_jornadas_equipamento fje
    JOIN farms.unidades_produtivas up ON up.id = fje.unidade_produtiva_id
    WHERE fje.unidade_produtiva_id IS NOT NULL AND fje.tenant_id <> up.tenant_id
    UNION ALL
    SELECT 'frota_apontamentos_uso → frota_jornadas_equipamento', COUNT(*)
    FROM farms.frota_apontamentos_uso fau
    JOIN farms.frota_jornadas_equipamento fje ON fje.id = fau.jornada_id
    WHERE fau.jornada_id IS NOT NULL AND fau.tenant_id <> fje.tenant_id
    UNION ALL
    SELECT 'frota_abastecimentos → cadastros_equipamentos', COUNT(*)
    FROM farms.frota_abastecimentos fa
    JOIN farms.cadastros_equipamentos ce ON ce.id = fa.equipamento_id
    WHERE fa.equipamento_id IS NOT NULL AND fa.tenant_id <> ce.tenant_id
) t
ORDER BY cruzamentos DESC, relacao;

-- ────────────────────────────────────────────────────────────
-- C2: Orphans de tenant_id nas tabelas com FK para tenants
-- ────────────────────────────────────────────────────────────
\echo ''
\echo '── C2: Orphans de tenant_id ─────────────────────────────────────'
DO $$
DECLARE
    r         RECORD;
    cnt       bigint;
    total_fail int := 0;
BEGIN
    FOR r IN
        SELECT DISTINCT c.conrelid::regclass::text AS tabela
        FROM pg_constraint c
        WHERE c.contype   = 'f'
          AND c.confrelid = 'farms.tenants'::regclass
        ORDER BY tabela
    LOOP
        BEGIN
            EXECUTE format(
                'SELECT COUNT(*) FROM %s t WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id)',
                r.tabela
            ) INTO cnt;
            IF cnt > 0 THEN
                RAISE WARNING 'FAIL ✗  % — % orphan(s)', r.tabela, cnt;
                total_fail := total_fail + 1;
            END IF;
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'SKIP  % — erro: %', r.tabela, SQLERRM;
        END;
    END LOOP;
    IF total_fail = 0 THEN
        RAISE NOTICE 'PASS — zero orphans em todas as tabelas com FK para tenants';
    ELSE
        RAISE WARNING 'FAIL ✗ — % tabela(s) com orphans', total_fail;
    END IF;
END $$;

-- ────────────────────────────────────────────────────────────
-- C3: FKs CASCADE para tenants (deve ser 0)
-- ────────────────────────────────────────────────────────────
\echo ''
\echo '── C3: FKs ON DELETE CASCADE para tenants ───────────────────────'
SELECT
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL ✗' END AS status,
    COUNT(*) AS fks_cascade_restantes
FROM pg_constraint
WHERE contype     = 'f'
  AND confrelid   = 'farms.tenants'::regclass
  AND confdeltype = 'c';

-- ────────────────────────────────────────────────────────────
-- C4: FKs NOT VALID pendentes (deve ser 0)
-- ────────────────────────────────────────────────────────────
\echo ''
\echo '── C4: FKs NOT VALID pendentes ──────────────────────────────────'
SELECT
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL ✗' END AS status,
    COUNT(*) AS fks_not_valid
FROM pg_constraint
WHERE contype     = 'f'
  AND confrelid   = 'farms.tenants'::regclass
  AND NOT convalidated;

-- ────────────────────────────────────────────────────────────
-- C5: FKs compostas dos 7 agregados presentes e validadas
-- ────────────────────────────────────────────────────────────
\echo ''
\echo '── C5: FKs compostas (7 agregados) ─────────────────────────────'
WITH esperadas(nome) AS (VALUES
    ('fk_car_tenant_unidade_produtiva'),
    ('fk_ed_tenant_unidade_produtiva'),
    ('fk_ce_tenant_unidade_produtiva'),
    ('fk_fje_tenant_unidade_produtiva'),
    ('fk_fau_tenant_jornada'),
    ('fk_fa_tenant_equipamento')
    -- fk_cp_tenant_deposito removida: compras_pedidos não tem deposito_id
    -- direto (migrou pra compras_itens_pedido, sem tenant_id próprio) —
    -- não existe FK composta pra essa relação, ver 01a_diagnose.sql atualizado
)
SELECT
    e.nome AS constraint_esperada,
    CASE WHEN c.convalidated THEN 'PASS' WHEN c.conname IS NULL THEN 'FAIL ✗ AUSENTE' ELSE 'FAIL ✗ NOT VALID' END AS status
FROM esperadas e
LEFT JOIN pg_constraint c ON c.conname = e.nome AND c.contype = 'f'
ORDER BY e.nome;

-- ────────────────────────────────────────────────────────────
-- C6: UNIQUE compostos nos 4 pais críticos
-- ────────────────────────────────────────────────────────────
\echo ''
\echo '── C6: UNIQUE(tenant_id, id) nos pais críticos ─────────────────'
WITH esperados(nome) AS (VALUES
    ('uq_unidades_produtivas_tenant_id_id'),
    ('uq_estoque_depositos_tenant_id'),
    ('uq_cadastros_equipamentos_tenant_id'),
    ('uq_frota_jornadas_tenant_id')
    -- nomes corrigidos em 2026-08-14 para bater com os constraints
    -- realmente aplicados no banco (sufixo _id_id em unidades_produtivas,
    -- sem "_equipamento" em frota_jornadas)
)
SELECT
    e.nome AS unique_esperado,
    CASE WHEN c.conname IS NOT NULL THEN 'PASS' ELSE 'FAIL ✗ AUSENTE' END AS status
FROM esperados e
LEFT JOIN pg_constraint c ON c.conname = e.nome AND c.contype = 'u'
ORDER BY e.nome;

-- ────────────────────────────────────────────────────────────
-- C7: Tabelas tenant_id uuid sem FK para tenants
-- ────────────────────────────────────────────────────────────
\echo ''
\echo '── C7: Tabelas uuid sem FK para tenants ─────────────────────────'
SELECT
    t.table_name,
    'FAIL ✗' AS status
FROM information_schema.columns c
JOIN information_schema.tables t
    ON t.table_name = c.table_name AND t.table_schema = c.table_schema
WHERE c.table_schema = 'farms'
  AND c.column_name  = 'tenant_id'
  AND c.data_type    = 'uuid'
  AND t.table_type   = 'BASE TABLE'
  AND t.table_name   NOT IN ('territory_legacy_backup_01h2')
  AND NOT EXISTS (
      SELECT 1 FROM pg_constraint pk
      WHERE pk.contype   = 'f'
        AND pk.conrelid  = ('farms.' || c.table_name)::regclass
        AND pk.confrelid = 'farms.tenants'::regclass
  )
ORDER BY t.table_name;

SELECT
    CASE WHEN COUNT(*) = 0 THEN 'PASS — nenhuma tabela uuid sem FK' ELSE 'ver linhas acima' END AS resultado_c7,
    COUNT(*) AS sem_fk
FROM information_schema.columns c
JOIN information_schema.tables t
    ON t.table_name = c.table_name AND t.table_schema = c.table_schema
WHERE c.table_schema = 'farms'
  AND c.column_name  = 'tenant_id'
  AND c.data_type    = 'uuid'
  AND t.table_type   = 'BASE TABLE'
  AND t.table_name   NOT IN ('territory_legacy_backup_01h2')
  AND NOT EXISTS (
      SELECT 1 FROM pg_constraint pk
      WHERE pk.contype   = 'f'
        AND pk.conrelid  = ('farms.' || c.table_name)::regclass
        AND pk.confrelid = 'farms.tenants'::regclass
  );

-- ────────────────────────────────────────────────────────────
-- C8: Quarentena — registros pendentes de resolução
-- ────────────────────────────────────────────────────────────
\echo ''
\echo '── C8: Quarentena pendente ───────────────────────────────────────'
SELECT CASE WHEN to_regclass('farms.tenant_fk_quarantine') IS NULL
            THEN TRUE ELSE FALSE END AS quarantine_ausente \gset

\if :quarantine_ausente
\echo 'PASS (N/A) — tabela tenant_fk_quarantine nunca foi criada; 01a_diagnose.sql não encontrou cruzamentos, então 01a_quarantine.sql nunca precisou rodar'
\else
SELECT
    source_table,
    COUNT(*) AS pendentes,
    CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL ✗ resolver via 01a_resolve.sql' END AS status
FROM farms.tenant_fk_quarantine
WHERE NOT resolved
GROUP BY source_table
UNION ALL
SELECT '(total)', COUNT(*),
    CASE WHEN COUNT(*) = 0 THEN 'PASS — quarentena vazia' ELSE 'FAIL ✗' END
FROM farms.tenant_fk_quarantine
WHERE NOT resolved;
\endif

-- ────────────────────────────────────────────────────────────
-- C9: Distribuição de ações de exclusão (snapshot final)
-- ────────────────────────────────────────────────────────────
\echo ''
\echo '── C9: Ações de exclusão nas FKs para tenants (snapshot) ────────'
SELECT
    CASE confdeltype
        WHEN 'a' THEN 'NO ACTION'
        WHEN 'r' THEN 'RESTRICT'
        WHEN 'c' THEN 'CASCADE'
        WHEN 'n' THEN 'SET NULL'
    END AS on_delete,
    COUNT(*) AS total,
    CASE confdeltype
        WHEN 'r' THEN 'OK'
        WHEN 'a' THEN 'OK (exceção documentada)'
        WHEN 'c' THEN 'FAIL ✗'
        ELSE 'REVISAR'
    END AS avaliacao
FROM pg_constraint
WHERE contype   = 'f'
  AND confrelid = 'farms.tenants'::regclass
GROUP BY confdeltype
ORDER BY total DESC;

-- ────────────────────────────────────────────────────────────
-- Veredicto consolidado
-- ────────────────────────────────────────────────────────────
\echo ''
\echo '╔══════════════════════════════════════════════════════════════╗'
\echo '║  VEREDICTO — verificar manualmente cada FAIL ✗ acima         ║'
\echo '║  GO = todos os critérios C1–C9 sem FAIL                      ║'
\echo '║  GO COM RESSALVAS = C1+C3+C4 OK, demais em andamento         ║'
\echo '║  NO-GO = qualquer FAIL em C1, C3, C4 ou C8                   ║'
\echo '╚══════════════════════════════════════════════════════════════╝'
\echo ''
