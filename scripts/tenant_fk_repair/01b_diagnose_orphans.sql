-- TENANT-FK-REPAIR-01B — Diagnóstico de orphans nas tabelas sem FK
-- Somente leitura. Verifica se tenant_id aponta para Tenant inexistente.
-- Pré-condição: rodar APÓS 01a_quarantine (cruzamentos já removidos).
--
-- Resultado esperado: 0 orphans em todas. Se > 0, corrigir antes de ADD FK.
--
-- Atualizado em 2026-08-14: todas as 12 tabelas abaixo já têm tenant_id
-- como uuid nativo (a normalização varchar→uuid do plano original de
-- 2026-07-17 já não se aplica — coluna já migrou de tipo desde então).
-- Ver memória do projeto project_tenant_fk_repair.

SET search_path = farms, public;

\echo '=== Orphans: tenant_id sem Tenant correspondente ==='

\echo '--- billing_solicitacoes_comerciais_historico ---'
SELECT COUNT(*) AS orphans
FROM farms.billing_solicitacoes_comerciais_historico t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- amostras ---'
SELECT COUNT(*) AS orphans
FROM farms.amostras t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- case_ih ---'
SELECT COUNT(*) AS orphans
FROM farms.case_ih t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- comparador_precos ---'
SELECT COUNT(*) AS orphans
FROM farms.comparador_precos t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- diagnosticos ---'
SELECT COUNT(*) AS orphans
FROM farms.diagnosticos t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- integration_credentials ---'
SELECT COUNT(*) AS orphans
FROM farms.integration_credentials t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- integration_external_record_links ---'
SELECT COUNT(*) AS orphans
FROM farms.integration_external_record_links t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- integration_external_record_link_history ---'
SELECT COUNT(*) AS orphans
FROM farms.integration_external_record_link_history t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- integration_versions ---'
SELECT COUNT(*) AS orphans
FROM farms.integration_versions t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- john_deere ---'
SELECT COUNT(*) AS orphans
FROM farms.john_deere t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- tenant_integracoes ---'
SELECT COUNT(*) AS orphans
FROM farms.tenant_integracoes t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '--- tratamentos ---'
SELECT COUNT(*) AS orphans
FROM farms.tratamentos t
WHERE NOT EXISTS (SELECT 1 FROM farms.tenants ten WHERE ten.id = t.tenant_id);

\echo '=== FIM DO DIAGNÓSTICO — todos os orphans devem ser 0 antes de prosseguir ==='
\echo '=== ATENÇÃO: plano original cita 29 tabelas sem FK, só 12 estão cobertas aqui — lista completa nunca foi commitada ==='
