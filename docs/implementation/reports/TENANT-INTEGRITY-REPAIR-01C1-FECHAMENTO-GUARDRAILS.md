# TENANT-INTEGRITY-REPAIR-01C1 — Fechamento dos Guardrails e da Migration 01C

**Data:** 2026-07-17
**Status:** GO — 01C ENCERRADA E REPRODUZÍVEL VIA ALEMBIC

---

## Contexto

A fase `TENANT-INTEGRITY-REPAIR-01C` criou 7 FKs compostas e 3 constraints UNIQUE nos
pais críticos. Esta fase de fechamento (01C1) corrigiu dois problemas remanescentes:

1. **G6 falhava por nomes divergentes** — teste usava nomes hardcoded que não existiam
2. **Alembic tinha dois heads paralelos** — migration 01C foi criada a partir de ancestral
   errado (`265b28773962` em vez de `20260717_remove_area_matriculas_legacy`)

---

## Problema 1 — Divergência de nomes em G6

### Causa

O guardrail G6 usava `@pytest.mark.parametrize("constraint_name, tabela", [...])` com
nomes esperados que não correspondiam aos nomes físicos:

| Esperado (teste) | Físico (banco) |
|------------------|----------------|
| `uq_unidades_produtivas_tenant_id` | `uq_unidades_produtivas_tenant_id_id` (pré-existente) |
| `uq_frota_jornadas_equipamento_tenant_id` | `uq_frota_jornadas_tenant_id` (criado em 01C) |

### Decisão

Não renomear constraints físicas (sem benefício arquitetural e cria nova migration).
Validar por **estrutura** (presença das colunas `tenant_id` + `id` em constraint UNIQUE
de exatamente 2 colunas), independente do nome atribuído.

### Implementação

G6 reescrito para consultar `pg_constraint` + `pg_attribute` por colunas:

```sql
SELECT COUNT(*) FROM pg_constraint c
WHERE c.contype  = 'u'
  AND c.conrelid = ('farms.' || :tabela)::regclass
  AND array_length(c.conkey, 1) = 2
  AND EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid = c.conrelid
              AND a.attnum = ANY(c.conkey) AND a.attname = 'tenant_id')
  AND EXISTS (SELECT 1 FROM pg_attribute a WHERE a.attrelid = c.conrelid
              AND a.attnum = ANY(c.conkey) AND a.attname = 'id')
```

---

## Problema 2 — Branch paralela no Alembic

### Causa

A migration `tenant_integrity_repair_01c_composite_fks.py` foi criada com:
```python
down_revision = "265b28773962"
```

Mas `20260717_remove_area_matriculas_legacy` (que limpou os cruzamentos em 01A)
tem `down_revision = "20260716_config_up_security_freeze"`. Os dois descendem de
ancestrais diferentes, gerando dois heads simultâneos na tabela `alembic_version`.

### Solução

Migration de merge criada:

```python
# tenant_integrity_repair_01c_merge.py
revision = "tenant_integrity_repair_01c_merge"
down_revision = (
    "20260717_remove_area_matriculas_legacy",
    "tenant_integrity_repair_01c",
)
# upgrade/downgrade: pass  — sem DDL
```

Aplicada ao banco via:
```sql
INSERT INTO alembic_version VALUES ('tenant_integrity_repair_01c_merge');
DELETE FROM alembic_version WHERE version_num IN (
  '20260717_remove_area_matriculas_legacy',
  'tenant_integrity_repair_01c'
);
```

`alembic_version` agora tem exatamente **1 linha**: `tenant_integrity_repair_01c_merge`.

---

## Organização dos testes por fase

Markers pytest registrados em `pyproject.toml`:

| Marker | Guardrails | Fases responsáveis |
|--------|------------|--------------------|
| `phase_01c` | G4, G5, G6, G7 | 01C — FKs compostas |
| `phase_other` | G1, G2, G3 | 01B (FKs diretas), 01D (CASCADE→RESTRICT) |

Execução isolada da 01C:
```bash
cd services/api
.venv/bin/pytest tests/integrity/test_tenant_fk_guardrails.py -m phase_01c -v
```

---

## Resultado dos testes

### Guardrails da fase 01C (`-m phase_01c`)

```
19 passed, 3 deselected
```

| Guardrail | Resultado |
|-----------|-----------|
| G4 — zero cruzamentos (7 relações) | **PASS** (7/7) |
| G5 — nenhuma FK NOT VALID pendente | **PASS** |
| G6 — UNIQUE(tenant_id, id) nos 4 pais | **PASS** (4/4) |
| G7 — 7 FKs compostas presentes e validadas | **PASS** (7/7) |

### Débitos de outras fases (`-m phase_other`)

| Guardrail | Status | Fase responsável |
|-----------|--------|------------------|
| G1 — nenhuma FK CASCADE para tenants | FAIL (débito) | 01D |
| G2 — toda tabela tenant-scoped tem FK | FAIL (débito) | 01B |
| G3 — toda tabela tem índice em tenant_id | FAIL (débito) | 01B |

---

## Estado da cadeia Alembic

| Item | Antes | Depois |
|------|-------|--------|
| `alembic_version` linhas | 2 (heads paralelos) | 1 |
| Head ativo | `20260717_…` e `tenant_integrity_repair_01c` | `tenant_integrity_repair_01c_merge` |
| Migration de merge | ausente | `tenant_integrity_repair_01c_merge.py` |

---

## Comparação migration × banco físico

| Constraint | Arquivo `01c_composite_fks.py` | Banco (pg_constraint) | Match |
|------------|-------------------------------|----------------------|-------|
| `uq_estoque_depositos_tenant_id` | ✓ cria | ✓ presente, convalidated=t | ✓ |
| `uq_frota_jornadas_tenant_id` | ✓ cria | ✓ presente, convalidated=t | ✓ |
| `uq_cadastros_equipamentos_tenant_id` | ✓ cria | ✓ presente, convalidated=t | ✓ |
| `uq_unidades_produtivas_tenant_id_id` | documenta como pré-existente | ✓ presente | ✓ |
| `fk_car_tenant_unidade_produtiva` | CASCADE | confdeltype=c | ✓ |
| `fk_ed_tenant_unidade_produtiva` | NO ACTION | confdeltype=a | ✓ |
| `fk_ce_tenant_unidade_produtiva` | NO ACTION | confdeltype=a | ✓ |
| `fk_cp_tenant_deposito` | NO ACTION | confdeltype=a | ✓ |
| `fk_fje_tenant_unidade_produtiva` | NO ACTION | confdeltype=a | ✓ |
| `fk_fau_tenant_jornada` | NO ACTION | confdeltype=a | ✓ |
| `fk_fa_tenant_equipamento` | CASCADE | confdeltype=c | ✓ |

Todas as 11 constraints coincidem entre migration versionada e banco físico.

---

## Arquivos alterados nesta fase

| Arquivo | Alteração |
|---------|-----------|
| `tests/integrity/test_tenant_fk_guardrails.py` | G6 reescrito (estrutural); markers `phase_01c`/`phase_other` adicionados |
| `pyproject.toml` | Markers registrados em `[tool.pytest.ini_options]` |
| `migrations/versions/tenant_integrity_repair_01c_merge.py` | Nova migration de merge (sem DDL) |

---

## Veredicto

```
GO — 01C ENCERRADA E REPRODUZÍVEL VIA ALEMBIC
```

- Banco protegido: 7 FKs compostas validadas, zero cruzamentos A→B
- Cadeia Alembic: 1 head único (`tenant_integrity_repair_01c_merge`)
- Testes da fase 01C: 19/19 passando
- Débitos G1/G2/G3 isolados e documentados como fases futuras (01B, 01D)

**Próximo passo:** TENANT-INTEGRITY-REPAIR-01B — normalização `tenant_id varchar` → `uuid`
e FKs diretas para tenants nas tabelas Classe F.
