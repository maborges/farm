-- TENANT-FK-REPAIR-01A — Quarentena de registros cruzados A→B
-- Execução: psql $DATABASE_URL -f 01a_quarantine.sql
--
-- O que faz:
--   1. Cria tabela tenant_fk_quarantine (idempotente)
--   2. Para cada tabela crítica: snapshot JSON → quarantine → DELETE original
--   3. Tudo em uma única transação — rollback total se qualquer etapa falhar
--
-- PRÉ-REQUISITO: rodar 01a_diagnose.sql e revisar os resultados antes.
-- REVERSÃO: usar 01a_resolve.sql com action='restore'

BEGIN;

SET search_path = farms, public;

-- ============================================================
-- 0. Criar tabela de quarentena (idempotente)
-- ============================================================
CREATE TABLE IF NOT EXISTS farms.tenant_fk_quarantine (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    source_table      text        NOT NULL,
    source_id         uuid        NOT NULL,
    source_tenant_id  uuid        NOT NULL,
    parent_table      text        NOT NULL,
    parent_id         uuid        NOT NULL,
    parent_tenant_id  uuid        NOT NULL,
    row_snapshot      jsonb       NOT NULL,
    quarantined_at    timestamptz NOT NULL DEFAULT now(),
    resolved          boolean     NOT NULL DEFAULT false,
    resolution_action text,       -- 'restore' | 'delete' | 'reassign'
    resolution_note   text,
    resolved_at       timestamptz,
    resolved_by       text
);

CREATE INDEX IF NOT EXISTS idx_tfq_source_table  ON farms.tenant_fk_quarantine (source_table);
CREATE INDEX IF NOT EXISTS idx_tfq_source_tenant  ON farms.tenant_fk_quarantine (source_tenant_id);
CREATE INDEX IF NOT EXISTS idx_tfq_resolved       ON farms.tenant_fk_quarantine (resolved) WHERE NOT resolved;

-- ============================================================
-- 1. cadastros_areas_rurais x unidades_produtivas
-- ============================================================
WITH cruzados AS (
    SELECT car.*
    FROM farms.cadastros_areas_rurais car
    JOIN farms.unidades_produtivas up ON up.id = car.unidade_produtiva_id
    WHERE car.tenant_id <> up.tenant_id
),
pai_info AS (
    SELECT car.id AS filho_id, up.tenant_id AS pai_tenant, up.id AS pai_id
    FROM farms.cadastros_areas_rurais car
    JOIN farms.unidades_produtivas up ON up.id = car.unidade_produtiva_id
    WHERE car.tenant_id <> up.tenant_id
),
inseridos AS (
    INSERT INTO farms.tenant_fk_quarantine
        (source_table, source_id, source_tenant_id, parent_table, parent_id, parent_tenant_id, row_snapshot)
    SELECT
        'cadastros_areas_rurais',
        c.id,
        c.tenant_id,
        'unidades_produtivas',
        p.pai_id,
        p.pai_tenant,
        to_jsonb(c)
    FROM cruzados c
    JOIN pai_info p ON p.filho_id = c.id
    RETURNING source_id
)
DELETE FROM farms.cadastros_areas_rurais
WHERE id IN (SELECT source_id FROM inseridos);

-- ============================================================
-- 2. estoque_depositos x unidades_produtivas
-- ============================================================
WITH cruzados AS (
    SELECT ed.*
    FROM farms.estoque_depositos ed
    JOIN farms.unidades_produtivas up ON up.id = ed.unidade_produtiva_id
    WHERE ed.tenant_id <> up.tenant_id
),
pai_info AS (
    SELECT ed.id AS filho_id, up.tenant_id AS pai_tenant, up.id AS pai_id
    FROM farms.estoque_depositos ed
    JOIN farms.unidades_produtivas up ON up.id = ed.unidade_produtiva_id
    WHERE ed.tenant_id <> up.tenant_id
),
inseridos AS (
    INSERT INTO farms.tenant_fk_quarantine
        (source_table, source_id, source_tenant_id, parent_table, parent_id, parent_tenant_id, row_snapshot)
    SELECT
        'estoque_depositos',
        c.id,
        c.tenant_id,
        'unidades_produtivas',
        p.pai_id,
        p.pai_tenant,
        to_jsonb(c)
    FROM cruzados c
    JOIN pai_info p ON p.filho_id = c.id
    RETURNING source_id
)
DELETE FROM farms.estoque_depositos
WHERE id IN (SELECT source_id FROM inseridos);

-- ============================================================
-- 3. cadastros_equipamentos x unidades_produtivas
-- ============================================================
WITH cruzados AS (
    SELECT ce.*
    FROM farms.cadastros_equipamentos ce
    JOIN farms.unidades_produtivas up ON up.id = ce.unidade_produtiva_id
    WHERE ce.unidade_produtiva_id IS NOT NULL
      AND ce.tenant_id <> up.tenant_id
),
pai_info AS (
    SELECT ce.id AS filho_id, up.tenant_id AS pai_tenant, up.id AS pai_id
    FROM farms.cadastros_equipamentos ce
    JOIN farms.unidades_produtivas up ON up.id = ce.unidade_produtiva_id
    WHERE ce.unidade_produtiva_id IS NOT NULL
      AND ce.tenant_id <> up.tenant_id
),
inseridos AS (
    INSERT INTO farms.tenant_fk_quarantine
        (source_table, source_id, source_tenant_id, parent_table, parent_id, parent_tenant_id, row_snapshot)
    SELECT
        'cadastros_equipamentos',
        c.id,
        c.tenant_id,
        'unidades_produtivas',
        p.pai_id,
        p.pai_tenant,
        to_jsonb(c)
    FROM cruzados c
    JOIN pai_info p ON p.filho_id = c.id
    RETURNING source_id
)
DELETE FROM farms.cadastros_equipamentos
WHERE id IN (SELECT source_id FROM inseridos);

-- ============================================================
-- 4. compras_pedidos x estoque_depositos (relação mais crítica)
-- ============================================================
WITH cruzados AS (
    SELECT cp.*
    FROM farms.compras_pedidos cp
    JOIN farms.estoque_depositos ed ON ed.id = cp.deposito_id
    WHERE cp.deposito_id IS NOT NULL
      AND cp.tenant_id <> ed.tenant_id
),
pai_info AS (
    SELECT cp.id AS filho_id, ed.tenant_id AS pai_tenant, ed.id AS pai_id
    FROM farms.compras_pedidos cp
    JOIN farms.estoque_depositos ed ON ed.id = cp.deposito_id
    WHERE cp.deposito_id IS NOT NULL
      AND cp.tenant_id <> ed.tenant_id
),
inseridos AS (
    INSERT INTO farms.tenant_fk_quarantine
        (source_table, source_id, source_tenant_id, parent_table, parent_id, parent_tenant_id, row_snapshot)
    SELECT
        'compras_pedidos',
        c.id,
        c.tenant_id,
        'estoque_depositos',
        p.pai_id,
        p.pai_tenant,
        to_jsonb(c)
    FROM cruzados c
    JOIN pai_info p ON p.filho_id = c.id
    RETURNING source_id
)
DELETE FROM farms.compras_pedidos
WHERE id IN (SELECT source_id FROM inseridos);

-- ============================================================
-- 5. frota_apontamentos_uso x frota_jornadas_equipamento
-- ============================================================
WITH cruzados AS (
    SELECT fau.*
    FROM farms.frota_apontamentos_uso fau
    JOIN farms.frota_jornadas_equipamento fje ON fje.id = fau.jornada_id
    WHERE fau.jornada_id IS NOT NULL
      AND fau.tenant_id <> fje.tenant_id
),
pai_info AS (
    SELECT fau.id AS filho_id, fje.tenant_id AS pai_tenant, fje.id AS pai_id
    FROM farms.frota_apontamentos_uso fau
    JOIN farms.frota_jornadas_equipamento fje ON fje.id = fau.jornada_id
    WHERE fau.jornada_id IS NOT NULL
      AND fau.tenant_id <> fje.tenant_id
),
inseridos AS (
    INSERT INTO farms.tenant_fk_quarantine
        (source_table, source_id, source_tenant_id, parent_table, parent_id, parent_tenant_id, row_snapshot)
    SELECT
        'frota_apontamentos_uso',
        c.id,
        c.tenant_id,
        'frota_jornadas_equipamento',
        p.pai_id,
        p.pai_tenant,
        to_jsonb(c)
    FROM cruzados c
    JOIN pai_info p ON p.filho_id = c.id
    RETURNING source_id
)
DELETE FROM farms.frota_apontamentos_uso
WHERE id IN (SELECT source_id FROM inseridos);

-- ============================================================
-- 6. frota_jornadas_equipamento x unidades_produtivas
-- ============================================================
WITH cruzados AS (
    SELECT fje.*
    FROM farms.frota_jornadas_equipamento fje
    JOIN farms.unidades_produtivas up ON up.id = fje.unidade_produtiva_id
    WHERE fje.unidade_produtiva_id IS NOT NULL
      AND fje.tenant_id <> up.tenant_id
),
pai_info AS (
    SELECT fje.id AS filho_id, up.tenant_id AS pai_tenant, up.id AS pai_id
    FROM farms.frota_jornadas_equipamento fje
    JOIN farms.unidades_produtivas up ON up.id = fje.unidade_produtiva_id
    WHERE fje.unidade_produtiva_id IS NOT NULL
      AND fje.tenant_id <> up.tenant_id
),
inseridos AS (
    INSERT INTO farms.tenant_fk_quarantine
        (source_table, source_id, source_tenant_id, parent_table, parent_id, parent_tenant_id, row_snapshot)
    SELECT
        'frota_jornadas_equipamento',
        c.id,
        c.tenant_id,
        'unidades_produtivas',
        p.pai_id,
        p.pai_tenant,
        to_jsonb(c)
    FROM cruzados c
    JOIN pai_info p ON p.filho_id = c.id
    RETURNING source_id
)
DELETE FROM farms.frota_jornadas_equipamento
WHERE id IN (SELECT source_id FROM inseridos);

-- ============================================================
-- 7. frota_abastecimentos x cadastros_equipamentos
-- ============================================================
WITH cruzados AS (
    SELECT fa.*
    FROM farms.frota_abastecimentos fa
    JOIN farms.cadastros_equipamentos ce ON ce.id = fa.equipamento_id
    WHERE fa.equipamento_id IS NOT NULL
      AND fa.tenant_id <> ce.tenant_id
),
pai_info AS (
    SELECT fa.id AS filho_id, ce.tenant_id AS pai_tenant, ce.id AS pai_id
    FROM farms.frota_abastecimentos fa
    JOIN farms.cadastros_equipamentos ce ON ce.id = fa.equipamento_id
    WHERE fa.equipamento_id IS NOT NULL
      AND fa.tenant_id <> ce.tenant_id
),
inseridos AS (
    INSERT INTO farms.tenant_fk_quarantine
        (source_table, source_id, source_tenant_id, parent_table, parent_id, parent_tenant_id, row_snapshot)
    SELECT
        'frota_abastecimentos',
        c.id,
        c.tenant_id,
        'cadastros_equipamentos',
        p.pai_id,
        p.pai_tenant,
        to_jsonb(c)
    FROM cruzados c
    JOIN pai_info p ON p.filho_id = c.id
    RETURNING source_id
)
DELETE FROM farms.frota_abastecimentos
WHERE id IN (SELECT source_id FROM inseridos);

-- ============================================================
-- Verificação final (deve mostrar o total quarentenado)
-- ============================================================
SELECT source_table, COUNT(*) AS quarentenados
FROM farms.tenant_fk_quarantine
WHERE resolved = false
GROUP BY source_table
ORDER BY quarentenados DESC;

COMMIT;
