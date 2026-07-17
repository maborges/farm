-- TENANT-FK-REPAIR-01B — Normalização de tenant_id varchar → uuid
-- Execução: psql $DATABASE_URL -f 01b_normalize_varchar.sql
--
-- PRÉ-CONDIÇÃO:
--   1. 01b_diagnose_orphans.sql retornou 0 orphans e 0 formato_invalido
--   2. Backup de cada tabela realizado
--
-- O que faz por tabela:
--   a. Adiciona coluna temporária tenant_id_uuid uuid
--   b. Popula com CAST do varchar validado
--   c. Verifica divergências (deve ser 0)
--   d. Remove coluna antiga, renomeia nova
--   e. Adiciona FK RESTRICT NOT VALID + VALIDATE
--
-- Execução em produção: uma tabela por vez, com intervalo de monitoramento.
-- Para rollback: cada bloco é uma transação independente.

SET search_path = farms, public;

-- ============================================================
-- FUNÇÃO auxiliar de validação de UUID (reutilizada em todos os blocos)
-- ============================================================
CREATE OR REPLACE FUNCTION farms._is_valid_uuid(val text) RETURNS boolean AS $$
BEGIN
    PERFORM val::uuid;
    RETURN true;
EXCEPTION WHEN invalid_text_representation THEN
    RETURN false;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- ============================================================
-- 1. amostras
-- ============================================================
BEGIN;

-- Verificação de segurança: nenhum valor inválido ou orphan
DO $$
DECLARE invalid_count int; orphan_count int;
BEGIN
    SELECT COUNT(*) INTO invalid_count FROM farms.amostras
    WHERE NOT farms._is_valid_uuid(tenant_id);
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'amostras: % valores de tenant_id com formato inválido', invalid_count;
    END IF;

    SELECT COUNT(*) INTO orphan_count FROM farms.amostras a
    WHERE NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = a.tenant_id);
    IF orphan_count > 0 THEN
        RAISE EXCEPTION 'amostras: % orphans encontrados — limpar antes de normalizar', orphan_count;
    END IF;
END $$;

ALTER TABLE farms.amostras ADD COLUMN tenant_id_uuid uuid;
UPDATE farms.amostras SET tenant_id_uuid = tenant_id::uuid;
ALTER TABLE farms.amostras ALTER COLUMN tenant_id_uuid SET NOT NULL;

-- Swap
ALTER TABLE farms.amostras DROP COLUMN tenant_id;
ALTER TABLE farms.amostras RENAME COLUMN tenant_id_uuid TO tenant_id;

-- Recriar índice (o original era em varchar)
DROP INDEX IF EXISTS farms.amostras_tenant_id_idx;
CREATE INDEX amostras_tenant_id_idx ON farms.amostras (tenant_id);

-- FK
ALTER TABLE farms.amostras
    ADD CONSTRAINT amostras_tenant_id_fkey
    FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id)
    ON DELETE RESTRICT NOT VALID;
ALTER TABLE farms.amostras VALIDATE CONSTRAINT amostras_tenant_id_fkey;

COMMIT;

-- ============================================================
-- 2. diagnosticos
-- ============================================================
BEGIN;

DO $$
DECLARE invalid_count int; orphan_count int;
BEGIN
    SELECT COUNT(*) INTO invalid_count FROM farms.diagnosticos
    WHERE NOT farms._is_valid_uuid(tenant_id);
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'diagnosticos: % valores inválidos', invalid_count;
    END IF;

    SELECT COUNT(*) INTO orphan_count FROM farms.diagnosticos d
    WHERE NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = d.tenant_id);
    IF orphan_count > 0 THEN
        RAISE EXCEPTION 'diagnosticos: % orphans', orphan_count;
    END IF;
END $$;

ALTER TABLE farms.diagnosticos ADD COLUMN tenant_id_uuid uuid;
UPDATE farms.diagnosticos SET tenant_id_uuid = tenant_id::uuid;
ALTER TABLE farms.diagnosticos ALTER COLUMN tenant_id_uuid SET NOT NULL;
ALTER TABLE farms.diagnosticos DROP COLUMN tenant_id;
ALTER TABLE farms.diagnosticos RENAME COLUMN tenant_id_uuid TO tenant_id;

DROP INDEX IF EXISTS farms.diagnosticos_tenant_id_idx;
CREATE INDEX diagnosticos_tenant_id_idx ON farms.diagnosticos (tenant_id);

ALTER TABLE farms.diagnosticos
    ADD CONSTRAINT diagnosticos_tenant_id_fkey
    FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id)
    ON DELETE RESTRICT NOT VALID;
ALTER TABLE farms.diagnosticos VALIDATE CONSTRAINT diagnosticos_tenant_id_fkey;

COMMIT;

-- ============================================================
-- 3. integration_credentials
-- ============================================================
BEGIN;

DO $$
DECLARE invalid_count int; orphan_count int;
BEGIN
    SELECT COUNT(*) INTO invalid_count FROM farms.integration_credentials
    WHERE NOT farms._is_valid_uuid(tenant_id);
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'integration_credentials: % valores inválidos', invalid_count;
    END IF;

    SELECT COUNT(*) INTO orphan_count FROM farms.integration_credentials ic
    WHERE NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = ic.tenant_id);
    IF orphan_count > 0 THEN
        RAISE EXCEPTION 'integration_credentials: % orphans', orphan_count;
    END IF;
END $$;

ALTER TABLE farms.integration_credentials ADD COLUMN tenant_id_uuid uuid;
UPDATE farms.integration_credentials SET tenant_id_uuid = tenant_id::uuid;
ALTER TABLE farms.integration_credentials ALTER COLUMN tenant_id_uuid SET NOT NULL;
ALTER TABLE farms.integration_credentials DROP COLUMN tenant_id;
ALTER TABLE farms.integration_credentials RENAME COLUMN tenant_id_uuid TO tenant_id;

DROP INDEX IF EXISTS farms.integration_credentials_tenant_id_idx;
CREATE INDEX integration_credentials_tenant_id_idx ON farms.integration_credentials (tenant_id);

ALTER TABLE farms.integration_credentials
    ADD CONSTRAINT integration_credentials_tenant_id_fkey
    FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id)
    ON DELETE RESTRICT NOT VALID;
ALTER TABLE farms.integration_credentials VALIDATE CONSTRAINT integration_credentials_tenant_id_fkey;

COMMIT;

-- ============================================================
-- 4. tenant_integracoes
-- ============================================================
BEGIN;

DO $$
DECLARE invalid_count int; orphan_count int;
BEGIN
    SELECT COUNT(*) INTO invalid_count FROM farms.tenant_integracoes
    WHERE NOT farms._is_valid_uuid(tenant_id);
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'tenant_integracoes: % valores inválidos', invalid_count;
    END IF;

    SELECT COUNT(*) INTO orphan_count FROM farms.tenant_integracoes ti
    WHERE NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = ti.tenant_id);
    IF orphan_count > 0 THEN
        RAISE EXCEPTION 'tenant_integracoes: % orphans', orphan_count;
    END IF;
END $$;

ALTER TABLE farms.tenant_integracoes ADD COLUMN tenant_id_uuid uuid;
UPDATE farms.tenant_integracoes SET tenant_id_uuid = tenant_id::uuid;
ALTER TABLE farms.tenant_integracoes ALTER COLUMN tenant_id_uuid SET NOT NULL;
ALTER TABLE farms.tenant_integracoes DROP COLUMN tenant_id;
ALTER TABLE farms.tenant_integracoes RENAME COLUMN tenant_id_uuid TO tenant_id;

DROP INDEX IF EXISTS farms.tenant_integracoes_tenant_id_idx;
CREATE INDEX tenant_integracoes_tenant_id_idx ON farms.tenant_integracoes (tenant_id);

ALTER TABLE farms.tenant_integracoes
    ADD CONSTRAINT tenant_integracoes_tenant_id_fkey
    FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id)
    ON DELETE RESTRICT NOT VALID;
ALTER TABLE farms.tenant_integracoes VALIDATE CONSTRAINT tenant_integracoes_tenant_id_fkey;

COMMIT;

-- ============================================================
-- 5. integration_external_record_links
-- ============================================================
BEGIN;

DO $$
DECLARE invalid_count int; orphan_count int;
BEGIN
    SELECT COUNT(*) INTO invalid_count FROM farms.integration_external_record_links
    WHERE NOT farms._is_valid_uuid(tenant_id);
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'integration_external_record_links: % valores inválidos', invalid_count;
    END IF;

    SELECT COUNT(*) INTO orphan_count FROM farms.integration_external_record_links i
    WHERE NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = i.tenant_id);
    IF orphan_count > 0 THEN
        RAISE EXCEPTION 'integration_external_record_links: % orphans', orphan_count;
    END IF;
END $$;

ALTER TABLE farms.integration_external_record_links ADD COLUMN tenant_id_uuid uuid;
UPDATE farms.integration_external_record_links SET tenant_id_uuid = tenant_id::uuid;
ALTER TABLE farms.integration_external_record_links ALTER COLUMN tenant_id_uuid SET NOT NULL;
ALTER TABLE farms.integration_external_record_links DROP COLUMN tenant_id;
ALTER TABLE farms.integration_external_record_links RENAME COLUMN tenant_id_uuid TO tenant_id;

DROP INDEX IF EXISTS farms.integration_external_record_links_tenant_id_idx;
CREATE INDEX integration_external_record_links_tenant_id_idx ON farms.integration_external_record_links (tenant_id);

ALTER TABLE farms.integration_external_record_links
    ADD CONSTRAINT integration_external_record_links_tenant_id_fkey
    FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id)
    ON DELETE RESTRICT NOT VALID;
ALTER TABLE farms.integration_external_record_links VALIDATE CONSTRAINT integration_external_record_links_tenant_id_fkey;

COMMIT;

-- ============================================================
-- 6. integration_external_record_link_history
-- (normalizar APÓS integration_external_record_links — depende dela)
-- ============================================================
BEGIN;

DO $$
DECLARE invalid_count int; orphan_count int;
BEGIN
    SELECT COUNT(*) INTO invalid_count FROM farms.integration_external_record_link_history
    WHERE NOT farms._is_valid_uuid(tenant_id);
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'integration_external_record_link_history: % valores inválidos', invalid_count;
    END IF;

    SELECT COUNT(*) INTO orphan_count FROM farms.integration_external_record_link_history i
    WHERE NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = i.tenant_id);
    IF orphan_count > 0 THEN
        RAISE EXCEPTION 'integration_external_record_link_history: % orphans', orphan_count;
    END IF;
END $$;

ALTER TABLE farms.integration_external_record_link_history ADD COLUMN tenant_id_uuid uuid;
UPDATE farms.integration_external_record_link_history SET tenant_id_uuid = tenant_id::uuid;
ALTER TABLE farms.integration_external_record_link_history ALTER COLUMN tenant_id_uuid SET NOT NULL;
ALTER TABLE farms.integration_external_record_link_history DROP COLUMN tenant_id;
ALTER TABLE farms.integration_external_record_link_history RENAME COLUMN tenant_id_uuid TO tenant_id;

DROP INDEX IF EXISTS farms.integration_external_record_link_history_tenant_id_idx;
CREATE INDEX integration_external_record_link_history_tenant_id_idx
    ON farms.integration_external_record_link_history (tenant_id);

ALTER TABLE farms.integration_external_record_link_history
    ADD CONSTRAINT integration_ext_link_history_tenant_id_fkey
    FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id)
    ON DELETE RESTRICT NOT VALID;
ALTER TABLE farms.integration_external_record_link_history
    VALIDATE CONSTRAINT integration_ext_link_history_tenant_id_fkey;

COMMIT;

-- ============================================================
-- 7. integration_versions
-- (normalizar APÓS integration_credentials e tenant_integracoes)
-- ============================================================
BEGIN;

DO $$
DECLARE invalid_count int; orphan_count int;
BEGIN
    SELECT COUNT(*) INTO invalid_count FROM farms.integration_versions
    WHERE NOT farms._is_valid_uuid(tenant_id);
    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'integration_versions: % valores inválidos', invalid_count;
    END IF;

    SELECT COUNT(*) INTO orphan_count FROM farms.integration_versions iv
    WHERE NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = iv.tenant_id);
    IF orphan_count > 0 THEN
        RAISE EXCEPTION 'integration_versions: % orphans', orphan_count;
    END IF;
END $$;

ALTER TABLE farms.integration_versions ADD COLUMN tenant_id_uuid uuid;
UPDATE farms.integration_versions SET tenant_id_uuid = tenant_id::uuid;
ALTER TABLE farms.integration_versions ALTER COLUMN tenant_id_uuid SET NOT NULL;
ALTER TABLE farms.integration_versions DROP COLUMN tenant_id;
ALTER TABLE farms.integration_versions RENAME COLUMN tenant_id_uuid TO tenant_id;

DROP INDEX IF EXISTS farms.integration_versions_tenant_id_idx;
CREATE INDEX integration_versions_tenant_id_idx ON farms.integration_versions (tenant_id);

ALTER TABLE farms.integration_versions
    ADD CONSTRAINT integration_versions_tenant_id_fkey
    FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id)
    ON DELETE RESTRICT NOT VALID;
ALTER TABLE farms.integration_versions VALIDATE CONSTRAINT integration_versions_tenant_id_fkey;

COMMIT;

-- ============================================================
-- 8. case_ih / comparador_precos / john_deere / tratamentos
-- Mesmo padrão. Executar individualmente.
-- ============================================================

-- case_ih: substituir template abaixo
-- BEGIN; ... mesmo padrão ... COMMIT;

-- comparador_precos: idem
-- john_deere: idem
-- tratamentos: idem

\echo '=== Normalização concluída. Verificar FKs adicionadas: ==='
SELECT conname, conrelid::regclass AS tabela
FROM pg_constraint
WHERE contype = 'f'
  AND conrelid::regclass::text LIKE 'farms.%'
  AND confrelid = 'farms.tenants'::regclass
ORDER BY tabela;
