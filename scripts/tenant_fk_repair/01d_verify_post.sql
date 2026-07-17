-- TENANT-FK-REPAIR-01D — Verificação pós-conversão CASCADE → RESTRICT
-- Esperado: 0 CASCADE, ~200 RESTRICT, 2 NO ACTION preservados

SET search_path = farms, public;

\echo '=== Contagem por ação de exclusão (pós-01D) ==='
SELECT
    CASE confdeltype
        WHEN 'a' THEN 'NO ACTION'
        WHEN 'r' THEN 'RESTRICT'
        WHEN 'c' THEN 'CASCADE'
        WHEN 'n' THEN 'SET NULL'
    END AS on_delete,
    COUNT(*) AS total
FROM pg_constraint
WHERE contype   = 'f'
  AND confrelid = 'farms.tenants'::regclass
GROUP BY confdeltype
ORDER BY total DESC;

\echo ''
\echo '=== FKs ainda CASCADE (deve ser 0) ==='
SELECT conname, conrelid::regclass AS tabela
FROM pg_constraint
WHERE contype     = 'f'
  AND confrelid   = 'farms.tenants'::regclass
  AND confdeltype = 'c'
ORDER BY tabela;

\echo ''
\echo '=== FKs NOT VALID pendentes (deve ser 0) ==='
SELECT conname, conrelid::regclass AS tabela
FROM pg_constraint
WHERE contype   = 'f'
  AND confrelid = 'farms.tenants'::regclass
  AND NOT convalidated
ORDER BY tabela;

\echo ''
\echo '=== Teste de exclusão segura: tenant sem dados ==='
-- Cria tenant temporário, testa exclusão lógica (sem dados = OK com RESTRICT)
-- NÃO executar em produção com tenant real
DO $$
DECLARE
    test_tenant_id uuid := gen_random_uuid();
    deleted_count  int;
BEGIN
    -- Inserir tenant de teste
    INSERT INTO farms.tenants (id, nome, status)
    VALUES (test_tenant_id, '_TEST_RESTRICT_01D', 'INATIVA')
    ON CONFLICT DO NOTHING;

    -- Tentar excluir (deve funcionar pois não tem filhos)
    DELETE FROM farms.tenants WHERE id = test_tenant_id AND nome = '_TEST_RESTRICT_01D';
    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    IF deleted_count = 1 THEN
        RAISE NOTICE 'OK: tenant sem dados excluído corretamente';
    ELSE
        RAISE WARNING 'tenant de teste não encontrado — verificar manualmente';
    END IF;
END $$;

\echo '=== 01D verificado ==='
