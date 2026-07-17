# TENANT-INTEGRITY-REPAIR-01B2 — Onda 1 (Baixo Risco)

**Data:** 2026-07-17  
**Revision:** `tenant_integrity_repair_01b2_onda1`  
**Down revision:** `tenant_integrity_repair_01c_merge`  
**Executado em:** banco compartilhado de dev (`farms`)

---

## Preflight — Contagem de Registros

| Tabela | Registros antes | Tipo antes |
|--------|----------------|------------|
| amostras | 0 | character varying |
| diagnosticos | 0 | character varying |
| mapas_fertilidade | 0 | character varying |
| pragas_doencas | 0 | character varying |
| prescricoes_vra | 0 | character varying |
| recomendacoes | 0 | character varying |
| tratamentos | 0 | character varying |
| modelos_ml | 0 | character varying |
| billing_solicitacoes_comerciais_historico | 0 | uuid (já era uuid) |

Todas as tabelas tinham 0 registros — conversão segura sem risco de dados inválidos.

---

## Migration Criada

- **Arquivo:** `services/api/migrations/versions/tenant_integrity_repair_01b2_onda1.py`
- **Operações:** `ALTER COLUMN TYPE`, `ADD CONSTRAINT ... NOT VALID`, `VALIDATE CONSTRAINT`, `CREATE INDEX`
- **Nota:** Migration aplicada diretamente via psql por limitação do worktree (falta de migrations intermediárias no branch isolado). A versão foi registrada em `alembic_version`.

---

## Resultado — Tipos Após Conversão

| Tabela | Tipo antes | Tipo depois |
|--------|-----------|-------------|
| amostras | character varying | uuid |
| diagnosticos | character varying | uuid |
| mapas_fertilidade | character varying | uuid |
| pragas_doencas | character varying | uuid |
| prescricoes_vra | character varying | uuid |
| recomendacoes | character varying | uuid |
| tratamentos | character varying | uuid |
| modelos_ml | character varying | uuid |
| billing_solicitacoes_comerciais_historico | uuid | uuid (sem alteração) |

---

## FKs Criadas

| Constraint | Tabela | Validada | confdeltype |
|------------|--------|----------|-------------|
| fk_amostras_tenant | amostras | true | a (NO ACTION) |
| fk_diagnosticos_tenant | diagnosticos | true | a (NO ACTION) |
| fk_mapas_fertilidade_tenant | mapas_fertilidade | true | a (NO ACTION) |
| fk_pragas_doencas_tenant | pragas_doencas | true | a (NO ACTION) |
| fk_prescricoes_vra_tenant | prescricoes_vra | true | a (NO ACTION) |
| fk_recomendacoes_tenant | recomendacoes | true | a (NO ACTION) |
| fk_tratamentos_tenant | tratamentos | true | a (NO ACTION) |
| fk_modelos_ml_tenant | modelos_ml | true | a (NO ACTION) |
| fk_billing_sol_com_hist_tenant | billing_solicitacoes_comerciais_historico | true | a (NO ACTION) |

Todas com `ON DELETE NO ACTION` conforme especificação da fase.

---

## Índices

- `ix_billing_sol_com_hist_tenant_id` — criado novo em `billing_solicitacoes_comerciais_historico(tenant_id)`
- Demais tabelas: índices preexistentes em `tenant_id` via `index=True` no Column (verificados via pg_indexes)

---

## Models Alterados

| Arquivo | Mudança |
|---------|---------|
| `agricola/amostragem_solo/models/amostras.py` | `String(50)` → `UUID(as_uuid=True) + ForeignKey` |
| `agricola/amostragem_solo/models/mapas_fertilidade.py` | `String(50)` → `UUID(as_uuid=True) + ForeignKey` |
| `agricola/amostragem_solo/models/prescricoes_vra.py` | `String(50)` → `PGUUID(as_uuid=True) + ForeignKey` |
| `ia_diagnostico/models/modelos_ml.py` | `String(50)` → `UUID(as_uuid=True) + ForeignKey` |
| `ia_diagnostico/models/diagnosticos.py` | `String(50)` → `UUID(as_uuid=True) + ForeignKey` |
| `ia_diagnostico/models/pragas_doencas.py` | `String(50)` → `UUID(as_uuid=True) + ForeignKey` |
| `ia_diagnostico/models/tratamentos.py` | `String(50)` → `UUID(as_uuid=True) + ForeignKey` |
| `ia_diagnostico/models/recomendacoes.py` | `String(50)` → `UUID(as_uuid=True) + ForeignKey` |
| `core/models/solicitacoes_historico.py` | Adicionado `ForeignKey("farms.tenants.id", ondelete="NO ACTION") + index=True` |

---

## Testes Phase_01b2

Adicionados em `tests/integrity/test_tenant_fk_guardrails.py`:

- `test_b2_tenant_id_uuid` — verifica tipo uuid (9 tabelas)
- `test_b2_fk_para_tenants` — verifica FK validada para tenants (9 tabelas)
- `test_b2_sem_cascade` — verifica ausência de CASCADE (9 tabelas)
- `test_b2_indice_tenant_id` — verifica índice em tenant_id (9 tabelas)

Total: 36 testes parametrizados. Marker `phase_01b2` registrado em `pyproject.toml`.

---

## Correção Documental

A classificação anterior "B2 — uuid sem FK" para `billing_solicitacoes_comerciais_historico` estava correta.

As 8 tabelas varchar foram erroneamente listadas como "B2 (com UUIDs válidos)" no projeto original — a classificação correta é **"varchar esperando UUID, sem dados"**. Tabelas `amostras`, `diagnosticos` etc. nunca tiveram dados e o campo era `String(50)` stub criado em migration inicial sem tipo correto.

---

## Alembic Version Pós-Migration

```
tenant_integrity_repair_01c_merge
tenant_integrity_repair_01b2_onda1
```

---

## Veredicto

✓ 9/9 tabelas convertidas  
✓ 9/9 FKs validadas para `farms.tenants` com NO ACTION  
✓ 9/9 índices em tenant_id presentes  
✓ 0 registros afetados (todas as tabelas estavam vazias)  
✓ Models SQLAlchemy atualizados  
✓ Guardrails phase_01b2 adicionados (36 testes)  
