# TENANT-INTEGRITY-REPAIR — Auditoria Onda 2
## Relatório 01B3A — Inventário Pré-Execução

**Data:** 2026-07-17
**Banco:** `postgresql://borgus@192.168.0.2/farms` (schema `farms`)
**Estado Alembic:** `current = tenant_integrity_repair_01b2_onda1` | `heads = tenant_fk_repair_01d` (unapplied)
**Autor:** Auditoria automatizada — Claude Code

---

## 1. Inventário Físico Remanescente (varchar → uuid pendente)

Total de tabelas com `tenant_id character varying(50)` após Onda 1: **20 tabelas**

| # | Tabela | Grupo | NOT NULL |
|---|--------|-------|----------|
| 1 | `integration_credentials` | Núcleo Multiprovider | SIM |
| 2 | `integration_external_record_link_history` | Núcleo Multiprovider | SIM |
| 3 | `integration_external_record_links` | Núcleo Multiprovider | SIM |
| 4 | `integration_features` | Núcleo Multiprovider | SIM |
| 5 | `integration_health_snapshots` | Núcleo Multiprovider | SIM |
| 6 | `integration_jobs` | Núcleo Multiprovider | SIM |
| 7 | `integration_sync_policies` | Núcleo Multiprovider | SIM |
| 8 | `integration_versions` | Núcleo Multiprovider | SIM |
| 9 | `tenant_integracoes` | Núcleo Multiprovider | SIM |
| 10 | `sankhya_config` | Provider-Specific (ERP) | SIM |
| 11 | `sankhya_sync_logs` | Provider-Specific (ERP) | SIM |
| 12 | `sankhya_lancamentos_financeiros` | Provider-Specific (ERP) | SIM |
| 13 | `sankhya_nfe` | Provider-Specific (ERP) | SIM |
| 14 | `sankhya_pessoas` | Provider-Specific (ERP) | SIM |
| 15 | `sankhya_produtos` | Provider-Specific (ERP) | SIM |
| 16 | `sankhya_tabelas` | Provider-Specific (ERP) | SIM |
| 17 | `case_ih` | IoT / Hardware | SIM |
| 18 | `john_deere` | IoT / Hardware | SIM |
| 19 | `comparador_precos` | Auxiliar / Mercado | SIM |
| 20 | `whatsapp` | Comunicação | SIM |

---

## 2. Dados por Tabela (COUNT, UUIDs, Orphans)

### 2.1 Núcleo Multiprovider (9 tabelas)

| Tabela | Total | uuid_format | Orphans | Índice | FK |
|--------|-------|-------------|---------|--------|----|
| `tenant_integracoes` | 0 | 0 | 0 | SIM | NÃO |
| `integration_credentials` | 0 | 0 | 0 | SIM | NÃO |
| `integration_external_record_links` | 0 | 0 | 0 | SIM | NÃO |
| `integration_external_record_link_history` | 0 | 0 | 0 | SIM | NÃO |
| `integration_features` | 0 | 0 | 0 | SIM | NÃO |
| `integration_health_snapshots` | 0 | 0 | 0 | SIM | NÃO |
| `integration_jobs` | 0 | 0 | 0 | SIM | NÃO |
| `integration_sync_policies` | 0 | 0 | 0 | SIM | NÃO |
| `integration_versions` | 0 | 0 | 0 | SIM | NÃO |

**Observação:** Todas as 9 tabelas estão **vazias** em produção. Índice em `tenant_id` presente em todas. FK para `tenants` ausente em todas — violação G3.

### 2.2 Provider-Specific — Sankhya (7 tabelas)

| Tabela | Total | uuid_format | Orphans |
|--------|-------|-------------|---------|
| `sankhya_config` | 2 | 2 | **1** |
| `sankhya_sync_logs` | 9 | 9 | **7** |
| `sankhya_lancamentos_financeiros` | 0 | 0 | 0 |
| `sankhya_nfe` | 0 | 0 | 0 |
| `sankhya_pessoas` | 0 | 0 | 0 |
| `sankhya_produtos` | 0 | 0 | 0 |
| `sankhya_tabelas` | 0 | 0 | 0 |

**⚠️ ATENÇÃO:** `sankhya_config` tem 2 registros, 1 orphan (tenant_id com formato UUID válido mas sem correspondente em `tenants`). `sankhya_sync_logs` tem 9 registros, **7 orphans** — risco de dados dangling se FK for adicionada sem limpeza prévia.

### 2.3 IoT / Auxiliares (4 tabelas)

| Tabela | Total | uuid_format | Observação |
|--------|-------|-------------|------------|
| `case_ih` | 0 | 0 | Vazia |
| `john_deere` | 0 | 0 | Vazia |
| `comparador_precos` | 0 | 0 | Vazia |
| `whatsapp` | 0 | 0 | Vazia |

---

## 3. Classificação por Categoria

| Classificação | Tabelas |
|---------------|---------|
| **ATIVA_COM_DADOS** | `sankhya_config` (2 rows), `sankhya_sync_logs` (9 rows, 7 orphans) |
| **ATIVA_VAZIA** | `tenant_integracoes`, `integration_credentials`, `integration_external_record_links`, `integration_external_record_link_history`, `integration_features`, `integration_health_snapshots`, `integration_jobs`, `integration_sync_policies`, `integration_versions` |
| **PROVIDER_SPECIFIC** | `sankhya_config`, `sankhya_sync_logs`, `sankhya_lancamentos_financeiros`, `sankhya_nfe`, `sankhya_pessoas`, `sankhya_produtos`, `sankhya_tabelas` |
| **IOT/HARDWARE** | `case_ih`, `john_deere` |
| **AUXILIAR** | `comparador_precos`, `whatsapp` |

---

## 4. Análise — Núcleo Multiprovider

As 9 tabelas do núcleo multiprovider (`tenant_integracoes` + `integration_*`) apresentam:

- **Tipo de coluna:** `character varying(50)` — violação G2 (deve ser `uuid`)
- **Índice:** presente em todas (criado previamente — performance OK)
- **FK para tenants:** **ausente em todas** — violação G3 (sem integridade referencial)
- **Dados:** **zero registros** — conversão pode ser feita de forma limpa, sem backfill
- **Risco:** BAIXO — tabelas vazias eliminam riscos de orphans ou dados incompatíveis
- **Models SQLAlchemy:** não encontrados em diretório `integrations/` dedicado; referências espalhadas em `main.py`, `core/routers/configuration.py`, e scripts de reconciliação Sankhya

**Ação requerida (Onda 01B3 — Núcleo):**
1. `ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid` em todas as 9 tabelas
2. `ADD CONSTRAINT fk_<tabela>_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE RESTRICT` em todas

---

## 5. Análise — IoT e Auxiliares

| Tabela | Risco | Ação |
|--------|-------|------|
| `case_ih` | BAIXO — vazia | Converter varchar→uuid + FK |
| `john_deere` | BAIXO — vazia | Converter varchar→uuid + FK |
| `comparador_precos` | BAIXO — vazia | Converter varchar→uuid + FK |
| `whatsapp` | BAIXO — vazia | Converter varchar→uuid + FK |

Nenhuma das 4 tabelas tem dados. Conversão trivial.

---

## 6. Análise — Sankhya (Confirmação de Orphans)

### sankhya_config
- 2 registros, ambos com formato UUID válido
- **1 orphan confirmado** (tenant_id referencia tenant inexistente em `tenants`)
- Ação pré-migração: `DELETE FROM farms.sankhya_config WHERE tenant_id NOT IN (SELECT id::text FROM farms.tenants);`

### sankhya_sync_logs
- 9 registros, todos com formato UUID válido
- **7 orphans confirmados** — 77% dos registros são dangling
- Provável causa: instâncias de tenant deletadas durante testes de desenvolvimento
- Ação pré-migração: `DELETE FROM farms.sankhya_sync_logs WHERE tenant_id NOT IN (SELECT id::text FROM farms.tenants);`

### sankhya_lancamentos_financeiros, sankhya_nfe, sankhya_pessoas, sankhya_produtos, sankhya_tabelas
- **Todas vazias** — sem risco

**Protocolo obrigatório antes da Onda Sankhya:**
1. Auditoria manual dos 2 registros de `sankhya_config` (qual tenant é válido, qual é orphan)
2. Executar DELETE de orphans (1 em config + 7 em sync_logs)
3. Somente então executar `ALTER COLUMN` + `ADD CONSTRAINT FK`

---

## 7. Violações G2/G3 Restantes

### Violações G2 (varchar em vez de uuid)
**20 tabelas** — listadas na Seção 1.

### Violações G3 (uuid sem FK para tenants)
**0 tabelas** — após Onda 1, todas as tabelas uuid já têm FK. As tabelas varchar ainda pendentes não têm FK (esperado — FK será adicionada junto com conversão de tipo).

### Tabelas uuid sem FK (Parte 5)
**0 tabelas** — resultado da query retornou 0 rows. A Onda 1 cobriu todas as tabelas uuid pendentes. Nenhuma violação G3 residual identificada.

---

## 8. Plano das Próximas Ondas

### Onda 01B3 — Núcleo Multiprovider + IoT (RECOMENDADA IMEDIATO)

**Tabelas (13):** todas vazias, risco mínimo

```
Grupo A — Núcleo Multiprovider (9 tabelas):
  tenant_integracoes, integration_credentials, integration_external_record_links,
  integration_external_record_link_history, integration_features,
  integration_health_snapshots, integration_jobs, integration_sync_policies,
  integration_versions

Grupo B — IoT e Auxiliares (4 tabelas):
  case_ih, john_deere, comparador_precos, whatsapp
```

**Ações por tabela:**
1. `ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid`
2. `ADD CONSTRAINT fk_<tabela>_tenant FOREIGN KEY (tenant_id) REFERENCES farms.tenants(id) ON DELETE RESTRICT`
3. `op.execute("COMMIT")` obrigatório após cada `run_sync`

**Risco:** BAIXO — todas as 13 tabelas têm zero registros; sem risco de falha no CAST ou orphans.

---

### Onda 01B4 — Sankhya Provider-Specific

**Tabelas (7):** 5 vazias + 2 com dados (orphans pendentes)

**Pré-requisito obrigatório (executar ANTES da migration):**
```sql
-- Remover orphans (confirmar manualmente antes)
DELETE FROM farms.sankhya_config
WHERE tenant_id NOT IN (SELECT id::text FROM farms.tenants);
-- Esperado: 1 row deleted

DELETE FROM farms.sankhya_sync_logs
WHERE tenant_id NOT IN (SELECT id::text FROM farms.tenants);
-- Esperado: 7 rows deleted
```

**Ações:**
1. Deletar orphans (manual, com confirmação)
2. `ALTER COLUMN tenant_id TYPE uuid USING tenant_id::uuid` em todas as 7 tabelas
3. `ADD CONSTRAINT FK` para `tenants` em todas

**Risco:** MÉDIO — orphans devem ser eliminados antes; risco de perda de dados de logs de sincronização (aceitável dado que são logs de dev).

---

### Onda 01D — CASCADE → RESTRICT (Fase Futura)

Migration já criada (`tenant_fk_repair_01d_cascade_to_restrict.py`). Aplicar **após** 01B3 e 01B4.

---

## 9. Estratégia para Reposicionar Migration 01D

### Situação atual
```
tenant_integrity_repair_01c_merge
    └── tenant_integrity_repair_01b2_onda1  ← current (aplicado)
            └── tenant_fk_repair_01d        ← head (NÃO aplicado)
```

### Problema
A migration `tenant_fk_repair_01d` está como único head com `down_revision = "tenant_integrity_repair_01b2_onda1"`. As novas migrations 01B3 e 01B4 precisam ser inseridas entre 01B2 e 01D.

### Estratégia Concreta

**Passo 1 — Criar 01B3 com down_revision correto:**
```python
# tenant_integrity_repair_01b3_multiprovider_iot.py
revision = "tenant_integrity_repair_01b3_multiprovider_iot"
down_revision = "tenant_integrity_repair_01b2_onda1"  # herda de 01B2
```

**Passo 2 — Criar 01B4 encadeando de 01B3:**
```python
# tenant_integrity_repair_01b4_sankhya.py
revision = "tenant_integrity_repair_01b4_sankhya"
down_revision = "tenant_integrity_repair_01b3_multiprovider_iot"
```

**Passo 3 — Atualizar down_revision de 01D para apontar para 01B4:**
```python
# tenant_fk_repair_01d_cascade_to_restrict.py
# ANTES:
down_revision = "tenant_integrity_repair_01b2_onda1"

# DEPOIS:
down_revision = "tenant_integrity_repair_01b4_sankhya"
```

**Cadeia final:**
```
01b2_onda1 (current)
    └── 01b3_multiprovider_iot
            └── 01b4_sankhya
                    └── 01d_cascade_to_restrict  ← único head
```

**Nota:** A edição de `down_revision` em 01D não altera lógica de upgrade/downgrade — apenas reposiciona o nó na cadeia. Executar `alembic check` após para validar consistência.

---

## 10. Veredicto

### ✅ GO PARA 01B3 — NÚCLEO MULTIPROVIDER + IOT/INTEGRAÇÕES

**Justificativa:**
- 13 tabelas (9 integration_* + 4 IoT/auxiliares) com **zero registros**
- Conversão varchar→uuid + FK RESTRICT: risco mínimo, sem backfill necessário
- Índices já presentes — sem overhead adicional de criação de índice
- Cadeia Alembic clara: 01B3 descende de 01B2 sem conflitos

### ⚠️ GO COM RESSALVAS PARA 01B4 — SANKHYA

**Ressalvas:**
1. `sankhya_config`: 1 orphan confirmado — DELETE obrigatório antes da migration
2. `sankhya_sync_logs`: 7 orphans confirmados (77% dos dados) — validar se logs são descartáveis; executar DELETE antes
3. Auditoria manual dos 2 registros válidos de `sankhya_config` para garantir continuidade de configuração

### ✅ GO PARA 01D após 01B3 + 01B4 completos

---

## Apêndice — Resumo Executivo

| Categoria | Tabelas | Registros | Orphans | Risco |
|-----------|---------|-----------|---------|-------|
| Núcleo Multiprovider | 9 | 0 | 0 | BAIXO |
| IoT / Auxiliares | 4 | 0 | 0 | BAIXO |
| Sankhya (5 vazias) | 5 | 0 | 0 | BAIXO |
| Sankhya (2 com dados) | 2 | 11 | **8** | MÉDIO |
| **Total** | **20** | **11** | **8** | — |

**Onda 01B2 (aplicada):** 9 tabelas convertidas (8 varchar→uuid + 1 billing)
**Onda 01B3 (próxima):** 13 tabelas — todas vazias — GO imediato
**Onda 01B4 (seguinte):** 7 tabelas Sankhya — limpeza de orphans primeiro
**Onda 01D (futura):** CASCADE→RESTRICT em todas as FKs diretas para tenants
