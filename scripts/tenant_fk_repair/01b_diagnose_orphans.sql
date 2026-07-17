-- TENANT-FK-REPAIR-01B — Diagnóstico de orphans nas 29 tabelas sem FK
-- Somente leitura. Verifica se tenant_id aponta para Tenant inexistente.
-- Pré-condição: rodar APÓS 01a_quarantine (cruzamentos já removidos).
--
-- Resultado esperado: 0 orphans em todas. Se > 0, corrigir antes de ADD FK.

SET search_path = farms, public;

\echo '=== GRUPO A: tabelas UUID (FK pode ser adicionada com NOT VALID) ==='

\echo '--- billing_solicitacoes_comerciais_historico ---'
SELECT COUNT(*) AS orphans
FROM farms.billing_solicitacoes_comerciais_historico t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

-- Adicionar demais tabelas UUID conforme identificadas na auditoria

\echo '=== GRUPO B: tabelas VARCHAR (normalização obrigatória antes da FK) ==='

\echo '--- amostras ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.amostras;

\echo '--- case_ih ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.case_ih;

\echo '--- comparador_precos ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.comparador_precos;

\echo '--- diagnosticos ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.diagnosticos;

\echo '--- integration_credentials ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.integration_credentials;

\echo '--- integration_external_record_links ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.integration_external_record_links;

\echo '--- integration_external_record_link_history ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.integration_external_record_link_history;

\echo '--- integration_versions ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.integration_versions;

\echo '--- john_deere ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.john_deere;

\echo '--- tenant_integracoes ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.tenant_integracoes;

\echo '--- tratamentos ---'
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE tenant_id ~ '^[0-9a-f-]{36}$') AS formato_uuid_valido,
       COUNT(*) FILTER (WHERE NOT (tenant_id ~ '^[0-9a-f-]{36}$')) AS formato_invalido,
       COUNT(*) FILTER (
           WHERE tenant_id ~ '^[0-9a-f-]{36}$'
           AND NOT EXISTS (SELECT 1 FROM farms.tenants t WHERE t.id::text = tenant_id)
       ) AS orphans_uuid
FROM farms.tratamentos;

\echo '=== FIM DO DIAGNÓSTICO — todos os orphans_uuid devem ser 0 antes de prosseguir ==='
