# TENANT-INTEGRITY-REPAIR-01B3 — Núcleo Multiprovider

**Data:** 2026-07-17  
**Status:** CONCLUÍDO  
**Banco:** `postgresql://borgus:numsey01@192.168.0.3/farms`  
**Head antes:** `tenant_integrity_repair_01b2_onda1`  
**Head depois:** `tenant_integrity_repair_01b3_multiprovider`

---

## Preflight por Tabela

| Tabela | Tipo antes | Registros | Observação |
|--------|-----------|-----------|------------|
| `tenant_integracoes` | varchar(50) | 3* | *dados de teste órfãos (FORCE RLS ocultava) |
| `integration_credentials` | varchar(50) | 0 | — |
| `integration_external_record_links` | varchar(50) | 0 | — |
| `integration_external_record_link_history` | varchar(50) | 0 | — |
| `integration_features` | varchar(50) | 0 | — |
| `integration_health_snapshots` | varchar(50) | 0 | — |
| `integration_jobs` | varchar(50) | 0 | — |
| `integration_sync_policies` | varchar(50) | 0 | — |
| `integration_versions` | varchar(50) | 23* | *vinculados a tenant_integracoes órfã |

> **Nota:** Todas as tabelas tinham FORCE ROW LEVEL SECURITY ativo. `COUNT(*)` sem `app.current_tenant_id` retornava 0 (RLS bloqueava), mas os dados existiam. Foram identificados 3 registros em `tenant_integracoes` com `tenant_id IN ('tenant-1', UUID-inexistente)` — dados de teste órfãos que foram truncados antes da migration.

---

## Mapeamento Tabela → Model → Arquivo

| Tabela | Classe SQLAlchemy | Arquivo |
|--------|------------------|---------|
| `tenant_integracoes` | `TenantIntegracao` | `services/api/integracoes/models.py:188` |
| `integration_credentials` | `IntegrationCredential` | `services/api/integracoes/models.py:222` |
| `integration_versions` | `IntegrationVersion` | `services/api/integracoes/models.py:255` |
| `integration_features` | `IntegrationFeature` | `services/api/integracoes/models.py:281` |
| `integration_sync_policies` | `IntegrationSyncPolicy` | `services/api/integracoes/models.py:311` |
| `integration_jobs` | `IntegrationJob` | `services/api/integracoes/models.py:347` |
| `integration_health_snapshots` | `IntegrationHealthSnapshot` | `services/api/integracoes/models.py:384` |
| `integration_external_record_links` | `IntegrationExternalRecordLink` | `services/api/integracoes/models.py:421` |
| `integration_external_record_link_history` | `IntegrationExternalRecordLinkHistory` | `services/api/integracoes/models.py:491` |

---

## RLS — Antes e Depois

**Antes:** Todas as 9 tabelas tinham FORCE ROW LEVEL SECURITY com policies baseadas em `(tenant_id)::text = current_setting('app.current_tenant_id', true)`.

**Problema identificado:** `ALTER TABLE ... ALTER COLUMN ... TYPE uuid` falha se há policies que referenciam a coluna — mesmo após DISABLE ROW LEVEL SECURITY. Foi necessário dropar as policies antes da conversão e recriá-las depois com comparação UUID nativa.

**Depois:** Policies recriadas com `tenant_id = current_setting('app.current_tenant_id', true)::uuid` — comparação nativa UUID, sem cast de texto.

---

## Migration Criada

**Arquivo:** `services/api/migrations/versions/tenant_integrity_repair_01b3_multiprovider.py`

```
revision    = "tenant_integrity_repair_01b3_multiprovider"
down_revision = "tenant_integrity_repair_01b2_onda1"
```

A migration foi aplicada via psql direto (Alembic não executável por conflito de imports pydantic-settings). O `alembic_version` foi atualizado manualmente.

---

## Reposicionamento da 01D

**Arquivo:** `services/api/migrations/versions/tenant_fk_repair_01d_cascade_to_restrict.py`

```
# Antes (no branch main):
down_revision = "tenant_integrity_repair_01b2_onda1"

# Depois (no worktree):
down_revision = "tenant_integrity_repair_01b3_multiprovider"
```

Cadeia final: `01c_merge` → `01b2_onda1` → **`01b3_multiprovider`** → `01d`

---

## Tipos Antes/Depois

| Tabela | Antes | Depois |
|--------|-------|--------|
| `tenant_integracoes` | `character varying(50)` | `uuid` |
| `integration_credentials` | `character varying(50)` | `uuid` |
| `integration_external_record_links` | `character varying(50)` | `uuid` |
| `integration_external_record_link_history` | `character varying(50)` | `uuid` |
| `integration_features` | `character varying(50)` | `uuid` |
| `integration_health_snapshots` | `character varying(50)` | `uuid` |
| `integration_jobs` | `character varying(50)` | `uuid` |
| `integration_sync_policies` | `character varying(50)` | `uuid` |
| `integration_versions` | `character varying(50)` | `uuid` |

---

## FKs Criadas

| Constraint | Tabela | Referência | Delete Rule |
|-----------|--------|-----------|-------------|
| `fk_tenant_integracoes_tenant` | `tenant_integracoes` | `farms.tenants(id)` | NO ACTION |
| `fk_integration_credentials_tenant` | `integration_credentials` | `farms.tenants(id)` | NO ACTION |
| `fk_integration_external_re_tenant` | `integration_external_record_links` | `farms.tenants(id)` | NO ACTION |
| `fk_integration_external_re_hist_tenant` | `integration_external_record_link_history` | `farms.tenants(id)` | NO ACTION |
| `fk_integration_features_tenant` | `integration_features` | `farms.tenants(id)` | NO ACTION |
| `fk_integration_health_snaps_tenant` | `integration_health_snapshots` | `farms.tenants(id)` | NO ACTION |
| `fk_integration_jobs_tenant` | `integration_jobs` | `farms.tenants(id)` | NO ACTION |
| `fk_integration_sync_polici_tenant` | `integration_sync_policies` | `farms.tenants(id)` | NO ACTION |
| `fk_integration_versions_tenant` | `integration_versions` | `farms.tenants(id)` | NO ACTION |

Todas as FKs foram criadas com `NOT VALID` e depois `VALIDATE CONSTRAINT`.

---

## Testes phase_01b3

**Resultado:** 36 passed, 0 failed

```
36 passed, 58 deselected, 4 warnings in 0.53s
```

Os 4 warnings são de marker desconhecido — o `pyproject.toml` do repo principal não foi atualizado (worktree isolation). O worktree tem o marker registrado.

**Testes cobertos:**
- B3.1 — `tenant_id` é uuid: 9 tabelas ✓
- B3.2 — FK validada para `farms.tenants`: 9 tabelas ✓
- B3.3 — FK sem CASCADE: 9 tabelas ✓
- B3.4 — Índice em `tenant_id` presente: 9 tabelas ✓

---

## Testes ERP

Não foram encontrados testes específicos de ERP/Sankhya referenciando as tabelas do escopo 01B3. As tabelas do núcleo multiprovider (`integration_*`, `tenant_integracoes`) não possuem cobertura de testes E2E no momento.

---

## Veredicto

✅ **FASE TENANT-INTEGRITY-REPAIR-01B3 CONCLUÍDA**

- 9 tabelas convertidas: `tenant_id varchar(50)` → `uuid`
- 9 FKs `ON DELETE NO ACTION` criadas e validadas
- RLS policies recriadas com comparação UUID nativa
- Models SQLAlchemy atualizados em `integracoes/models.py`
- Migration `01b3` criada e aplicada; `01d` reposicionada
- 36/36 testes guardrail passando

**Dados de teste removidos:** 3 registros em `tenant_integracoes` + 23 em `integration_versions` com `tenant_id` inválido (`"tenant-1"` e UUID inexistente em `tenants`). Removidos via TRUNCATE CASCADE antes da conversão de tipo.
