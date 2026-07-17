-- TENANT-FK-REPAIR-01C — Verificação pós-implantação
-- Confirma que as FKs compostas estão ativas e sem violações.

SET search_path = farms, public;

\echo '=== FKs compostas criadas (deve listar 7) ==='
SELECT
    conname                    AS constraint_name,
    conrelid::regclass         AS filho,
    confrelid::regclass        AS pai,
    array_agg(a.attname ORDER BY x.n) AS colunas_filho,
    array_agg(b.attname ORDER BY x.n) AS colunas_pai
FROM pg_constraint c
CROSS JOIN LATERAL unnest(c.conkey, c.confkey) WITH ORDINALITY AS x(ck, fk, n)
JOIN pg_attribute a ON a.attrelid = c.conrelid  AND a.attnum = x.ck
JOIN pg_attribute b ON b.attrelid = c.confrelid AND b.attnum = x.fk
WHERE c.contype = 'f'
  AND conname IN (
    'fk_car_tenant_unidade_produtiva',
    'fk_ed_tenant_unidade_produtiva',
    'fk_ce_tenant_unidade_produtiva',
    'fk_cp_tenant_deposito',
    'fk_fje_tenant_unidade_produtiva',
    'fk_fau_tenant_jornada',
    'fk_fa_tenant_equipamento'
  )
GROUP BY conname, conrelid, confrelid
ORDER BY filho;

\echo '=== UNIQUE compostos nos pais (deve listar 4) ==='
SELECT
    conname         AS constraint_name,
    conrelid::regclass AS tabela
FROM pg_constraint
WHERE contype = 'u'
  AND conname IN (
    'uq_unidades_produtivas_tenant_id',
    'uq_estoque_depositos_tenant_id',
    'uq_cadastros_equipamentos_tenant_id',
    'uq_frota_jornadas_equipamento_tenant_id'
  )
ORDER BY tabela;

\echo '=== Cruzamentos residuais pós-01C (deve ser 0 em tudo) ==='
SELECT 'cadastros_areas_rurais' AS tabela, COUNT(*) AS cruzamentos
FROM farms.cadastros_areas_rurais car
JOIN farms.unidades_produtivas up ON up.id = car.unidade_produtiva_id
WHERE car.unidade_produtiva_id IS NOT NULL AND car.tenant_id <> up.tenant_id
UNION ALL
SELECT 'estoque_depositos', COUNT(*)
FROM farms.estoque_depositos ed
JOIN farms.unidades_produtivas up ON up.id = ed.unidade_produtiva_id
WHERE ed.unidade_produtiva_id IS NOT NULL AND ed.tenant_id <> up.tenant_id
UNION ALL
SELECT 'cadastros_equipamentos', COUNT(*)
FROM farms.cadastros_equipamentos ce
JOIN farms.unidades_produtivas up ON up.id = ce.unidade_produtiva_id
WHERE ce.unidade_produtiva_id IS NOT NULL AND ce.tenant_id <> up.tenant_id
UNION ALL
SELECT 'compras_pedidos', COUNT(*)
FROM farms.compras_pedidos cp
JOIN farms.estoque_depositos ed ON ed.id = cp.deposito_id
WHERE cp.deposito_id IS NOT NULL AND cp.tenant_id <> ed.tenant_id
UNION ALL
SELECT 'frota_jornadas_equipamento', COUNT(*)
FROM farms.frota_jornadas_equipamento fje
JOIN farms.unidades_produtivas up ON up.id = fje.unidade_produtiva_id
WHERE fje.unidade_produtiva_id IS NOT NULL AND fje.tenant_id <> up.tenant_id
UNION ALL
SELECT 'frota_apontamentos_uso', COUNT(*)
FROM farms.frota_apontamentos_uso fau
JOIN farms.frota_jornadas_equipamento fje ON fje.id = fau.jornada_id
WHERE fau.jornada_id IS NOT NULL AND fau.tenant_id <> fje.tenant_id
UNION ALL
SELECT 'frota_abastecimentos', COUNT(*)
FROM farms.frota_abastecimentos fa
JOIN farms.cadastros_equipamentos ce ON ce.id = fa.equipamento_id
WHERE fa.equipamento_id IS NOT NULL AND fa.tenant_id <> ce.tenant_id;

\echo '=== 01C concluído ==='
