# TENANT-INTEGRITY-REPAIR-01B2A — Fechamento da Cadeia Alembic da Onda 1

**Data:** 2026-07-17
**Status:** GO — ONDA 1 ENCERRADA COM HEAD ÚNICO

---

## Contexto

Após a implementação da Onda 1 (`tenant_integrity_repair_01b2_onda1`), o estado do Alembic
apresentava dois problemas:

1. `alembic_version` tinha 2 linhas (já corrigido antes desta fase)
2. `alembic heads` mostrava múltiplos heads no código fonte

Esta fase corrigiu os dois problemas.

---

## Problema 1 — `alembic_version` com 2 linhas

**Causa:** O banco recebeu o DDL por SQL direto e o agente inseriu manualmente a linha
`tenant_integrity_repair_01b2_onda1` sem remover `tenant_integrity_repair_01c_merge`.

**Estado anterior:**
```
tenant_integrity_repair_01c_merge
tenant_integrity_repair_01b2_onda1
```

**Correção** (executada ainda durante a fase 01B2):
```sql
DELETE FROM alembic_version WHERE version_num = 'tenant_integrity_repair_01c_merge';
```

**Estado resultante:**
```
tenant_integrity_repair_01b2_onda1
```

---

## Problema 2 — `alembic current` bloqueado por migration sem variáveis Python

**Arquivo:** `migrations/versions/tenant_fk_repair_01d_cascade_to_restrict.py`

**Causa:** O arquivo foi criado com as informações de revisão apenas no docstring,
sem declarar as variáveis Python `revision` e `down_revision`. O Alembic não conseguia
ler o arquivo e lançava:

```
FAILED: Could not determine revision id from filename tenant_fk_repair_01d_cascade_to_restrict.py.
```

**Correção:** Adicionadas as variáveis obrigatórias:
```python
revision = "tenant_fk_repair_01d"
down_revision = "tenant_integrity_repair_01b2_onda1"
branch_labels = None
depends_on = None
```

O `down_revision` foi apontado para `tenant_integrity_repair_01b2_onda1` (head atual),
colocando 01D na posição correta na cadeia — como próxima fase planejada (CASCADE→RESTRICT),
não aplicada ainda.

---

## Problema 3 — Migrations órfãs criando múltiplos heads

Após a correção de 01D, `alembic heads` ainda mostrava 2 heads:

```
tenant_fk_repair_01b (head)
tenant_fk_repair_01d (head)
```

**Causa:** Migrations do plano original de 01C e 01B foram supersedidas mas não removidas:

| Arquivo removido | Motivo |
|-----------------|--------|
| `tenant_fk_repair_01a_quarantine_table.py` | Plano original 01A — nunca aplicado, `down_revision = None` (raiz orphan) |
| `tenant_fk_repair_01b_uuid_fks.py` | Plano original 01B — nunca aplicado, apontava para 01a |
| `tenant_fk_repair_01c_step1_unique_parents.py` | Plano original 01C step1 — supersedido por `tenant_integrity_repair_01c_composite_fks` |
| `tenant_fk_repair_01c_step2_composite_fks.py` | Plano original 01C step2 — supersedido |

Nenhum dos quatro estava em `alembic_version` — nunca foram aplicados.

**Correção:** Remoção dos quatro arquivos.

---

## Estado final do grafo Alembic

```
... → 20260716_config_up_security_freeze
    → 20260717_remove_area_matriculas_legacy  ─┐
    → 265b28773962 → tenant_integrity_repair_01c ─┤→ tenant_integrity_repair_01c_merge
                                                   ↓
                                    tenant_integrity_repair_01b2_onda1
                                                   ↓
                                    tenant_fk_repair_01d (HEAD — não aplicado)
```

**`alembic heads`:**
```
tenant_fk_repair_01d (head)
```

**`alembic current`:**
```
tenant_integrity_repair_01b2_onda1
```

**`alembic_version` (banco):**
```
tenant_integrity_repair_01b2_onda1
```

---

## Comparação migration × banco físico

| Constraint / alteração | Migration `01b2_onda1` | Banco (pg_constraint) | Match |
|------------------------|------------------------|----------------------|-------|
| `amostras.tenant_id` = uuid | ✓ converte | ✓ uuid | ✓ |
| `diagnosticos.tenant_id` = uuid | ✓ converte | ✓ uuid | ✓ |
| `mapas_fertilidade.tenant_id` = uuid | ✓ converte | ✓ uuid | ✓ |
| `pragas_doencas.tenant_id` = uuid | ✓ converte | ✓ uuid | ✓ |
| `prescricoes_vra.tenant_id` = uuid | ✓ converte | ✓ uuid | ✓ |
| `recomendacoes.tenant_id` = uuid | ✓ converte | ✓ uuid | ✓ |
| `tratamentos.tenant_id` = uuid | ✓ converte | ✓ uuid | ✓ |
| `modelos_ml.tenant_id` = uuid | ✓ converte | ✓ uuid | ✓ |
| `fk_amostras_tenant` (NO ACTION) | ✓ cria | convalidated=t, confdeltype=a | ✓ |
| `fk_diagnosticos_tenant` | ✓ cria | convalidated=t, confdeltype=a | ✓ |
| `fk_mapas_fertilidade_tenant` | ✓ cria | convalidated=t, confdeltype=a | ✓ |
| `fk_pragas_doencas_tenant` | ✓ cria | convalidated=t, confdeltype=a | ✓ |
| `fk_prescricoes_vra_tenant` | ✓ cria | convalidated=t, confdeltype=a | ✓ |
| `fk_recomendacoes_tenant` | ✓ cria | convalidated=t, confdeltype=a | ✓ |
| `fk_tratamentos_tenant` | ✓ cria | convalidated=t, confdeltype=a | ✓ |
| `fk_modelos_ml_tenant` | ✓ cria | convalidated=t, confdeltype=a | ✓ |
| `fk_billing_sol_com_hist_tenant` | ✓ cria | convalidated=t, confdeltype=a | ✓ |
| `ix_billing_sol_com_hist_tenant_id` | ✓ cria | ✓ presente | ✓ |

---

## Testes

```bash
pytest -m 'phase_01b2 or phase_01c' -q
```

```
55 passed, 3 deselected
```

| Suite | Resultado |
|-------|-----------|
| `phase_01b2` (36 testes) | PASS |
| `phase_01c` (19 testes) | PASS |
| `phase_other` G1/G2/G3 | FAIL esperado — débito 01D/01B ondas futuras |

---

## Reprodução em banco limpo

**Pendente** — o banco compartilhado de dev não pode receber downgrade.
A migration `tenant_integrity_repair_01b2_onda1` está declarada com downgrade reversível:
- Remove FKs;
- Reconverte uuid → varchar via `::text`;
- Remove o índice criado (`ix_billing_sol_com_hist_tenant_id`).

O comando `alembic upgrade head` aplicaria até `tenant_fk_repair_01d` (fase 01D, unapplied).
Para aplicar apenas até 01B2: `alembic upgrade tenant_integrity_repair_01b2_onda1`.

---

## Arquivos alterados nesta fase

| Arquivo | Alteração |
|---------|-----------|
| `migrations/versions/tenant_fk_repair_01d_cascade_to_restrict.py` | Adicionadas variáveis `revision`/`down_revision` ausentes |
| `migrations/versions/tenant_fk_repair_01a_quarantine_table.py` | **Removido** (órfão, nunca aplicado) |
| `migrations/versions/tenant_fk_repair_01b_uuid_fks.py` | **Removido** (órfão, nunca aplicado) |
| `migrations/versions/tenant_fk_repair_01c_step1_unique_parents.py` | **Removido** (supersedido por 01C integrado) |
| `migrations/versions/tenant_fk_repair_01c_step2_composite_fks.py` | **Removido** (supersedido por 01C integrado) |
| `docs/implementation/reports/TENANT-INTEGRITY-REPAIR-01B2A-FECHAMENTO-ALEMBIC.md` | Este relatório |

---

## Veredicto

```
GO — ONDA 1 ENCERRADA COM HEAD ÚNICO
```

- `alembic_version`: 1 linha — `tenant_integrity_repair_01b2_onda1`
- `alembic heads`: 1 head — `tenant_fk_repair_01d` (fase 01D, não aplicada)
- `alembic current`: `tenant_integrity_repair_01b2_onda1` ✓
- 55 testes de integridade aprovados
- Migration × banco: 100% coerente
- Próxima fase: `TENANT-INTEGRITY-REPAIR-01B3` (Onda 2 — módulos ativos com dados reais)
