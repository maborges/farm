# TENANT-FK-REPAIR — Plano de Correção de Integridade Referencial Multi-Tenant

**Origem:** TENANT-FK-AUDIT-01 (2026-07-17) — Veredicto NO-GO
**Status:** Scripts e migrations prontos — aguarda execução em staging

---

## Resumo dos problemas corrigidos

| Problema | Impacto | Fase |
|----------|---------|------|
| 103 cruzamentos A→B (filho.tenant ≠ pai.tenant) | Vazamento de dados entre tenants | 01A |
| 29 tabelas sem FK para `tenants` | Orphans de tenant inexistente | 01B |
| 376 relações sem proteção composta | Cruzamento silencioso filho≠pai | 01C |
| 200 FKs com `ON DELETE CASCADE` | Exclusão destrutiva em cascata | 01D |
| Ausência de guardrails no CI | Regressão silenciosa | 01E |

---

## Fases e artefatos

### REPAIR-01A — Quarentena de cruzamentos A→B

**Tabelas:** `cadastros_areas_rurais` (43), `frota_apontamentos_uso` (16),
`frota_jornadas_equipamento` (15), `estoque_depositos` (14),
`frota_abastecimentos` (8), `cadastros_equipamentos` (4), `compras_pedidos` (3)

| Artefato | Propósito |
|----------|-----------|
| `scripts/tenant_fk_repair/01a_diagnose.sql` | Leitura: mapeia cruzamentos por ID |
| `scripts/tenant_fk_repair/01a_quarantine.sql` | Snapshot JSON → `tenant_fk_quarantine` → DELETE |
| `scripts/tenant_fk_repair/01a_resolve.sql` | Resolução: delete / restore / reassign |
| `migrations/.../tenant_fk_repair_01a_quarantine_table.py` | Cria tabela `tenant_fk_quarantine` |

**Sequência:**
```bash
alembic upgrade tenant_fk_repair_01a
psql $DB -f scripts/tenant_fk_repair/01a_diagnose.sql   # revisar
psql $DB -f scripts/tenant_fk_repair/01a_quarantine.sql # quarentenar
# Decidir ação por tabela (delete/restore/reassign)
psql $DB -f scripts/tenant_fk_repair/01a_resolve.sql    # resolver
```

---

### REPAIR-01B — FKs diretas para tenants (29 tabelas)

**Grupos:**
- **UUID (direto):** `billing_solicitacoes_comerciais_historico` → migration Alembic
- **VARCHAR (normalização):** `amostras`, `diagnosticos`, `integration_credentials`,
  `tenant_integracoes`, `integration_external_record_links`,
  `integration_external_record_link_history`, `integration_versions`,
  `case_ih`, `comparador_precos`, `john_deere`, `tratamentos`

| Artefato | Propósito |
|----------|-----------|
| `scripts/tenant_fk_repair/01b_diagnose_orphans.sql` | Verifica 0 orphans e formatos inválidos |
| `migrations/.../tenant_fk_repair_01b_uuid_fks.py` | FK RESTRICT NOT VALID + VALIDATE (uuid) |
| `scripts/tenant_fk_repair/01b_normalize_varchar.sql` | Normalização varchar→uuid + FK por tabela |

**Ordem de normalização varchar (dependências):**
1. `integration_credentials` e `tenant_integracoes` (sem dependentes)
2. `integration_external_record_links` (sem dependentes)
3. `integration_external_record_link_history` (depende de #2)
4. `integration_versions` (depende de #1)
5. `amostras`, `diagnosticos`, `case_ih`, `comparador_precos`, `john_deere`, `tratamentos` (independentes)

---

### REPAIR-01C — FKs compostas (7 agregados críticos)

**Pais que recebem UNIQUE(tenant_id, id):**
`unidades_produtivas`, `estoque_depositos`, `cadastros_equipamentos`, `frota_jornadas_equipamento`

**Filhos que recebem FK composta (tenant_id, parent_id):**
`cadastros_areas_rurais`, `estoque_depositos`, `cadastros_equipamentos`,
`compras_pedidos`, `frota_jornadas_equipamento`, `frota_apontamentos_uso`, `frota_abastecimentos`

| Artefato | Propósito |
|----------|-----------|
| `scripts/tenant_fk_repair/01c_diagnose_pre_composite.sql` | Verifica 0 cruzamentos e 0 duplicatas |
| `migrations/.../tenant_fk_repair_01c_step1_unique_parents.py` | UNIQUE CONCURRENTLY nos 4 pais |
| `migrations/.../tenant_fk_repair_01c_step2_composite_fks.py` | 7 FKs compostas RESTRICT NOT VALID + VALIDATE |
| `scripts/tenant_fk_repair/01c_verify_post.sql` | Confirma 7 FKs, 4 UNIQUEs, 0 cruzamentos |

**Atenção:** `UNIQUE CONCURRENTLY` não pode rodar dentro de transação. Em produção,
criar os índices manualmente via psql antes de aplicar a migration step1.

---

### REPAIR-01D — CASCADE → RESTRICT (200 FKs diretas)

| Artefato | Propósito |
|----------|-----------|
| `scripts/tenant_fk_repair/01d_diagnose_cascade.sql` | Lista FKs CASCADE + gera DDL de revisão |
| `migrations/.../tenant_fk_repair_01d_cascade_to_restrict.py` | Loop PL/pgSQL: DROP + ADD RESTRICT + VALIDATE |
| `scripts/tenant_fk_repair/01d_verify_post.sql` | Confirma 0 CASCADE, 0 NOT VALID + smoke test |

---

### REPAIR-01E — Guardrails automatizados

| Artefato | Propósito |
|----------|-----------|
| `tests/integrity/test_tenant_fk_guardrails.py` | 7 guardrails pytest contra catálogo PostgreSQL |
| `scripts/tenant_fk_repair/01e_ci_check.sh` | Script CI: executa testes de integridade |

**Guardrails (G1–G7):**

| ID | Verifica | Falha quando |
|----|----------|--------------|
| G1 | Nenhuma FK CASCADE para tenants | Qualquer FK nova usar CASCADE |
| G2 | Toda tabela uuid tem FK para tenants | Nova tabela sem FK |
| G3 | Toda tabela tenant-scoped tem índice | Nova tabela sem índice |
| G4 | Zero cruzamentos A→B nos 7 agregados | Novo dado com tenant errado |
| G5 | Nenhuma FK NOT VALID pendente | VALIDATE esquecido |
| G6 | UNIQUE(tenant_id, id) nos 4 pais | UNIQUE removido |
| G7 | 7 FKs compostas presentes e válidas | FK composta ausente |

```yaml
# CI (GitHub Actions):
- name: Tenant FK Integrity Guardrails
  run: ./scripts/tenant_fk_repair/01e_ci_check.sh
```

---

### REPAIR-01F — Auditoria final de convergência

| Artefato | Propósito |
|----------|-----------|
| `scripts/tenant_fk_repair/01f_final_audit.sql` | 9 critérios C1–C9 com PASS/FAIL por linha |

**Critérios de GO:**

| Critério | Condição |
|----------|----------|
| C1 — Cruzamentos A→B | 0 em todas as 7 relações |
| C2 — Orphans | 0 em todas as tabelas com FK |
| C3 — FKs CASCADE | 0 |
| C4 — FKs NOT VALID | 0 |
| C5 — FKs compostas | 7 presentes e validadas |
| C6 — UNIQUE compostos | 4 presentes |
| C7 — Tabelas uuid sem FK | 0 (exceto `territory_legacy_backup_01h2`) |
| C8 — Quarentena pendente | 0 não resolvidos |
| C9 — Ações de exclusão | Apenas RESTRICT e NO ACTION |

```bash
psql $DATABASE_URL -f scripts/tenant_fk_repair/01f_final_audit.sql \
  > docs/implementation/reports/01f_result_$(date +%Y%m%d).txt
```

---

## Ordem de execução em produção

```
staging:
  01A diagnose → revisar → 01A quarantine → 01A resolve
  01B diagnose_orphans → 01B uuid_fks (migration) → 01B normalize_varchar
  01C diagnose_pre → 01C step1 (CONCURRENTLY manual) → 01C step2 → 01C verify
  01D diagnose → 01D migration → 01D verify
  01E ci_check (confirmar PASS em todos os guardrails)
  01F final_audit → confirmar GO

produção:
  Repetir mesma sequência com janela de manutenção para 01A e 01D
  01F final_audit → publicar evidência sanitizada
```

---

## Exceções documentadas

| Tabela | Motivo | Prazo |
|--------|--------|-------|
| `territory_legacy_backup_01h2` | Backup territorial legado; acesso somente administrativo | Definir data de descarte |
| `email_logs` | `ON DELETE NO ACTION` deliberado (log histórico) | Manter |

---

**Última atualização:** 2026-07-17
**Responsável:** Borgus Software Ltda
