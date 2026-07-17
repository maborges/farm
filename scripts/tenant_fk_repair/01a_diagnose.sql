-- TENANT-FK-REPAIR-01A — Diagnóstico de cruzamentos A→B
-- Execução: psql $DATABASE_URL -f 01a_diagnose.sql
-- Somente leitura. Nenhum dado é alterado.
-- Tabelas críticas: 7 | Cruzamentos esperados: ~103

SET search_path = farms, public;

-- ============================================================
-- 1. cadastros_areas_rurais (43 cruzamentos esperados)
--    Pais: unidades_produtivas, cadastros_areas_rurais (auto-ref)
-- ============================================================
\echo '--- cadastros_areas_rurais x unidades_produtivas ---'
SELECT
    car.id                   AS filho_id,
    car.tenant_id            AS filho_tenant,
    up.tenant_id             AS pai_tenant_up,
    car.unidade_produtiva_id AS pai_id
FROM farms.cadastros_areas_rurais car
JOIN farms.unidades_produtivas up ON up.id = car.unidade_produtiva_id
WHERE car.tenant_id <> up.tenant_id
ORDER BY car.tenant_id, car.id;

\echo '--- cadastros_areas_rurais x cadastros_areas_rurais (auto-ref) ---'
SELECT
    filho.id        AS filho_id,
    filho.tenant_id AS filho_tenant,
    pai.tenant_id   AS pai_tenant,
    filho.parent_id AS pai_id
FROM farms.cadastros_areas_rurais filho
JOIN farms.cadastros_areas_rurais pai ON pai.id = filho.parent_id
WHERE filho.parent_id IS NOT NULL
  AND filho.tenant_id <> pai.tenant_id
ORDER BY filho.tenant_id, filho.id;

-- ============================================================
-- 2. estoque_depositos (14 cruzamentos esperados)
--    Pai: unidades_produtivas
-- ============================================================
\echo '--- estoque_depositos x unidades_produtivas ---'
SELECT
    ed.id                   AS filho_id,
    ed.tenant_id            AS filho_tenant,
    up.tenant_id            AS pai_tenant,
    ed.unidade_produtiva_id AS pai_id
FROM farms.estoque_depositos ed
JOIN farms.unidades_produtivas up ON up.id = ed.unidade_produtiva_id
WHERE ed.tenant_id <> up.tenant_id
ORDER BY ed.tenant_id, ed.id;

-- ============================================================
-- 3. cadastros_equipamentos (4 cruzamentos esperados)
--    Pai: unidades_produtivas
-- ============================================================
\echo '--- cadastros_equipamentos x unidades_produtivas ---'
SELECT
    ce.id                   AS filho_id,
    ce.tenant_id            AS filho_tenant,
    up.tenant_id            AS pai_tenant,
    ce.unidade_produtiva_id AS pai_id
FROM farms.cadastros_equipamentos ce
JOIN farms.unidades_produtivas up ON up.id = ce.unidade_produtiva_id
WHERE ce.unidade_produtiva_id IS NOT NULL
  AND ce.tenant_id <> up.tenant_id
ORDER BY ce.tenant_id, ce.id;

-- ============================================================
-- 4. compras_pedidos (3 cruzamentos esperados)
--    Pais: estoque_depositos, compras_cotacoes, compras_solicitacoes, cadastros_produtos
-- ============================================================
\echo '--- compras_pedidos x estoque_depositos ---'
SELECT
    cp.id               AS filho_id,
    cp.tenant_id        AS filho_tenant,
    ed.tenant_id        AS pai_tenant,
    cp.deposito_id      AS pai_id,
    'estoque_depositos' AS pai_tabela
FROM farms.compras_pedidos cp
JOIN farms.estoque_depositos ed ON ed.id = cp.deposito_id
WHERE cp.deposito_id IS NOT NULL
  AND cp.tenant_id <> ed.tenant_id
UNION ALL
SELECT
    cp.id,
    cp.tenant_id,
    cc.tenant_id,
    cp.cotacao_id,
    'compras_cotacoes'
FROM farms.compras_pedidos cp
JOIN farms.compras_cotacoes cc ON cc.id = cp.cotacao_id
WHERE cp.cotacao_id IS NOT NULL
  AND cp.tenant_id <> cc.tenant_id
UNION ALL
SELECT
    cp.id,
    cp.tenant_id,
    cs.tenant_id,
    cp.solicitacao_id,
    'compras_solicitacoes'
FROM farms.compras_pedidos cp
JOIN farms.compras_solicitacoes cs ON cs.id = cp.solicitacao_id
WHERE cp.solicitacao_id IS NOT NULL
  AND cp.tenant_id <> cs.tenant_id
ORDER BY filho_tenant, filho_id;

-- ============================================================
-- 5. frota_jornadas_equipamento (15 cruzamentos esperados)
--    Pais: cadastros_areas_rurais, cadastros_equipamentos,
--           cadastros_pessoas, safras, unidades_produtivas
-- ============================================================
\echo '--- frota_jornadas_equipamento x unidades_produtivas ---'
SELECT
    fje.id                   AS filho_id,
    fje.tenant_id            AS filho_tenant,
    up.tenant_id             AS pai_tenant,
    fje.unidade_produtiva_id AS pai_id,
    'unidades_produtivas'    AS pai_tabela
FROM farms.frota_jornadas_equipamento fje
JOIN farms.unidades_produtivas up ON up.id = fje.unidade_produtiva_id
WHERE fje.unidade_produtiva_id IS NOT NULL
  AND fje.tenant_id <> up.tenant_id
UNION ALL
SELECT
    fje.id,
    fje.tenant_id,
    ce.tenant_id,
    fje.equipamento_id,
    'cadastros_equipamentos'
FROM farms.frota_jornadas_equipamento fje
JOIN farms.cadastros_equipamentos ce ON ce.id = fje.equipamento_id
WHERE fje.equipamento_id IS NOT NULL
  AND fje.tenant_id <> ce.tenant_id
UNION ALL
SELECT
    fje.id,
    fje.tenant_id,
    car.tenant_id,
    fje.area_rural_id,
    'cadastros_areas_rurais'
FROM farms.frota_jornadas_equipamento fje
JOIN farms.cadastros_areas_rurais car ON car.id = fje.area_rural_id
WHERE fje.area_rural_id IS NOT NULL
  AND fje.tenant_id <> car.tenant_id
ORDER BY filho_tenant, filho_id;

-- ============================================================
-- 6. frota_apontamentos_uso (16 cruzamentos esperados)
--    Pais: cadastros_areas_rurais, cadastros_equipamentos,
--           cadastros_pessoas, frota_jornadas_equipamento,
--           operacoes_agricolas, production_units, safras, unidades_produtivas
-- ============================================================
\echo '--- frota_apontamentos_uso x frota_jornadas_equipamento ---'
SELECT
    fau.id          AS filho_id,
    fau.tenant_id   AS filho_tenant,
    fje.tenant_id   AS pai_tenant,
    fau.jornada_id  AS pai_id,
    'frota_jornadas_equipamento' AS pai_tabela
FROM farms.frota_apontamentos_uso fau
JOIN farms.frota_jornadas_equipamento fje ON fje.id = fau.jornada_id
WHERE fau.jornada_id IS NOT NULL
  AND fau.tenant_id <> fje.tenant_id
UNION ALL
SELECT
    fau.id,
    fau.tenant_id,
    up.tenant_id,
    fau.unidade_produtiva_id,
    'unidades_produtivas'
FROM farms.frota_apontamentos_uso fau
JOIN farms.unidades_produtivas up ON up.id = fau.unidade_produtiva_id
WHERE fau.unidade_produtiva_id IS NOT NULL
  AND fau.tenant_id <> up.tenant_id
ORDER BY filho_tenant, filho_id;

-- ============================================================
-- 7. frota_abastecimentos (8 cruzamentos esperados)
--    Pais: cadastros_areas_rurais, cadastros_equipamentos,
--           cadastros_pessoas, safras
-- ============================================================
\echo '--- frota_abastecimentos x cadastros_equipamentos ---'
SELECT
    fa.id            AS filho_id,
    fa.tenant_id     AS filho_tenant,
    ce.tenant_id     AS pai_tenant,
    fa.equipamento_id AS pai_id,
    'cadastros_equipamentos' AS pai_tabela
FROM farms.frota_abastecimentos fa
JOIN farms.cadastros_equipamentos ce ON ce.id = fa.equipamento_id
WHERE fa.equipamento_id IS NOT NULL
  AND fa.tenant_id <> ce.tenant_id
UNION ALL
SELECT
    fa.id,
    fa.tenant_id,
    car.tenant_id,
    fa.area_rural_id,
    'cadastros_areas_rurais'
FROM farms.frota_abastecimentos fa
JOIN farms.cadastros_areas_rurais car ON car.id = fa.area_rural_id
WHERE fa.area_rural_id IS NOT NULL
  AND fa.tenant_id <> car.tenant_id
ORDER BY filho_tenant, filho_id;

-- ============================================================
-- RESUMO CONSOLIDADO
-- ============================================================
\echo '--- RESUMO: total de cruzamentos por tabela ---'
SELECT source_table, COUNT(*) AS cruzamentos FROM (
    SELECT 'cadastros_areas_rurais' AS source_table FROM farms.cadastros_areas_rurais car
    JOIN farms.unidades_produtivas up ON up.id = car.unidade_produtiva_id
    WHERE car.tenant_id <> up.tenant_id
    UNION ALL
    SELECT 'estoque_depositos' FROM farms.estoque_depositos ed
    JOIN farms.unidades_produtivas up ON up.id = ed.unidade_produtiva_id
    WHERE ed.tenant_id <> up.tenant_id
    UNION ALL
    SELECT 'cadastros_equipamentos' FROM farms.cadastros_equipamentos ce
    JOIN farms.unidades_produtivas up ON up.id = ce.unidade_produtiva_id
    WHERE ce.unidade_produtiva_id IS NOT NULL AND ce.tenant_id <> up.tenant_id
    UNION ALL
    SELECT 'compras_pedidos' FROM farms.compras_pedidos cp
    JOIN farms.estoque_depositos ed ON ed.id = cp.deposito_id
    WHERE cp.deposito_id IS NOT NULL AND cp.tenant_id <> ed.tenant_id
    UNION ALL
    SELECT 'frota_jornadas_equipamento' FROM farms.frota_jornadas_equipamento fje
    JOIN farms.unidades_produtivas up ON up.id = fje.unidade_produtiva_id
    WHERE fje.unidade_produtiva_id IS NOT NULL AND fje.tenant_id <> up.tenant_id
    UNION ALL
    SELECT 'frota_apontamentos_uso' FROM farms.frota_apontamentos_uso fau
    JOIN farms.frota_jornadas_equipamento fje ON fje.id = fau.jornada_id
    WHERE fau.jornada_id IS NOT NULL AND fau.tenant_id <> fje.tenant_id
    UNION ALL
    SELECT 'frota_abastecimentos' FROM farms.frota_abastecimentos fa
    JOIN farms.cadastros_equipamentos ce ON ce.id = fa.equipamento_id
    WHERE fa.equipamento_id IS NOT NULL AND fa.tenant_id <> ce.tenant_id
) t
GROUP BY source_table
ORDER BY cruzamentos DESC;
