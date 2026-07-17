-- TENANT-FK-REPAIR-01A — Resolução de quarentena
-- Uso: definir :action e :quarantine_ids antes de executar
--
-- Ações disponíveis:
--   'delete'   — descarte definitivo (sem restauração)
--   'restore'  — restaura o registro na tabela original (com tenant_id original)
--   'reassign' — restaura atribuindo o tenant_id do pai (corrigindo o cruzamento)
--
-- Exemplo de execução por tabela:
--   psql $DATABASE_URL \
--     -v action=delete \
--     -v note="'Cruzamento confirmado, dados de teste — aprovado em 2026-07-17'" \
--     -v operator="'dba@borgus.com.br'" \
--     -f 01a_resolve.sql

BEGIN;

SET search_path = farms, public;

-- ============================================================
-- OPÇÃO A: DELETE — descarte definitivo de todos pendentes
-- (ajustar WHERE para filtrar por source_table ou source_id)
-- ============================================================
/*
UPDATE farms.tenant_fk_quarantine
SET
    resolved          = true,
    resolution_action = 'delete',
    resolution_note   = :note,
    resolved_at       = now(),
    resolved_by       = :operator
WHERE resolved = false
  -- AND source_table = 'cadastros_areas_rurais'  -- opcional: filtrar por tabela
  -- AND source_id = ANY(ARRAY[...])              -- opcional: filtrar por IDs
;
*/

-- ============================================================
-- OPÇÃO B: RESTORE — restaurar na tabela original
-- Suporta as 7 tabelas críticas do repair-01A
-- ============================================================
/*
DO $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN
        SELECT * FROM farms.tenant_fk_quarantine
        WHERE resolved = false
          -- AND source_table = 'cadastros_areas_rurais'
    LOOP
        CASE rec.source_table
            WHEN 'cadastros_areas_rurais' THEN
                INSERT INTO farms.cadastros_areas_rurais
                SELECT * FROM jsonb_populate_record(null::farms.cadastros_areas_rurais, rec.row_snapshot)
                ON CONFLICT (id) DO NOTHING;
            WHEN 'estoque_depositos' THEN
                INSERT INTO farms.estoque_depositos
                SELECT * FROM jsonb_populate_record(null::farms.estoque_depositos, rec.row_snapshot)
                ON CONFLICT (id) DO NOTHING;
            WHEN 'cadastros_equipamentos' THEN
                INSERT INTO farms.cadastros_equipamentos
                SELECT * FROM jsonb_populate_record(null::farms.cadastros_equipamentos, rec.row_snapshot)
                ON CONFLICT (id) DO NOTHING;
            WHEN 'compras_pedidos' THEN
                INSERT INTO farms.compras_pedidos
                SELECT * FROM jsonb_populate_record(null::farms.compras_pedidos, rec.row_snapshot)
                ON CONFLICT (id) DO NOTHING;
            WHEN 'frota_apontamentos_uso' THEN
                INSERT INTO farms.frota_apontamentos_uso
                SELECT * FROM jsonb_populate_record(null::farms.frota_apontamentos_uso, rec.row_snapshot)
                ON CONFLICT (id) DO NOTHING;
            WHEN 'frota_jornadas_equipamento' THEN
                INSERT INTO farms.frota_jornadas_equipamento
                SELECT * FROM jsonb_populate_record(null::farms.frota_jornadas_equipamento, rec.row_snapshot)
                ON CONFLICT (id) DO NOTHING;
            WHEN 'frota_abastecimentos' THEN
                INSERT INTO farms.frota_abastecimentos
                SELECT * FROM jsonb_populate_record(null::farms.frota_abastecimentos, rec.row_snapshot)
                ON CONFLICT (id) DO NOTHING;
        END CASE;

        UPDATE farms.tenant_fk_quarantine
        SET
            resolved          = true,
            resolution_action = 'restore',
            resolution_note   = 'restaurado por operador',
            resolved_at       = now(),
            resolved_by       = 'dba'
        WHERE id = rec.id;
    END LOOP;
END $$;
*/

-- ============================================================
-- OPÇÃO C: REASSIGN — corrigir tenant_id para coincidir com pai
-- Restaura o registro com tenant_id = parent_tenant_id
-- ============================================================
/*
DO $$
DECLARE
    rec RECORD;
    corrected jsonb;
BEGIN
    FOR rec IN
        SELECT * FROM farms.tenant_fk_quarantine
        WHERE resolved = false
          -- AND source_table = 'estoque_depositos'
    LOOP
        corrected := rec.row_snapshot || jsonb_build_object('tenant_id', rec.parent_tenant_id);

        CASE rec.source_table
            WHEN 'cadastros_areas_rurais' THEN
                INSERT INTO farms.cadastros_areas_rurais
                SELECT * FROM jsonb_populate_record(null::farms.cadastros_areas_rurais, corrected)
                ON CONFLICT (id) DO UPDATE SET tenant_id = EXCLUDED.tenant_id;
            WHEN 'estoque_depositos' THEN
                INSERT INTO farms.estoque_depositos
                SELECT * FROM jsonb_populate_record(null::farms.estoque_depositos, corrected)
                ON CONFLICT (id) DO UPDATE SET tenant_id = EXCLUDED.tenant_id;
            WHEN 'frota_jornadas_equipamento' THEN
                INSERT INTO farms.frota_jornadas_equipamento
                SELECT * FROM jsonb_populate_record(null::farms.frota_jornadas_equipamento, corrected)
                ON CONFLICT (id) DO UPDATE SET tenant_id = EXCLUDED.tenant_id;
            WHEN 'frota_apontamentos_uso' THEN
                INSERT INTO farms.frota_apontamentos_uso
                SELECT * FROM jsonb_populate_record(null::farms.frota_apontamentos_uso, corrected)
                ON CONFLICT (id) DO UPDATE SET tenant_id = EXCLUDED.tenant_id;
            WHEN 'frota_abastecimentos' THEN
                INSERT INTO farms.frota_abastecimentos
                SELECT * FROM jsonb_populate_record(null::farms.frota_abastecimentos, corrected)
                ON CONFLICT (id) DO UPDATE SET tenant_id = EXCLUDED.tenant_id;
        END CASE;

        UPDATE farms.tenant_fk_quarantine
        SET
            resolved          = true,
            resolution_action = 'reassign',
            resolution_note   = 'tenant_id corrigido para coincidir com pai',
            resolved_at       = now(),
            resolved_by       = 'dba'
        WHERE id = rec.id;
    END LOOP;
END $$;
*/

-- ============================================================
-- Status final da quarentena
-- ============================================================
SELECT
    source_table,
    COUNT(*) FILTER (WHERE NOT resolved) AS pendentes,
    COUNT(*) FILTER (WHERE resolved AND resolution_action = 'delete')   AS deletados,
    COUNT(*) FILTER (WHERE resolved AND resolution_action = 'restore')  AS restaurados,
    COUNT(*) FILTER (WHERE resolved AND resolution_action = 'reassign') AS reatribuidos
FROM farms.tenant_fk_quarantine
GROUP BY source_table
ORDER BY pendentes DESC;

COMMIT;
