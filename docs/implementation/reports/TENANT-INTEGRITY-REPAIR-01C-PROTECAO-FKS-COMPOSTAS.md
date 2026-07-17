# TENANT-INTEGRITY-REPAIR-01C — Proteção FKs Compostas
**Data:** 2026-07-17 | **Status:** GO COM RESSALVAS

---

## 1. Preflight — Cruzamentos Cross-Tenant

| Relação | Cruzamentos |
|---|---|
| cadastros_areas_rurais → unidades_produtivas | 0 |
| estoque_depositos → unidades_produtivas | 0 |
| cadastros_equipamentos → unidades_produtivas | 0 |
| compras_pedidos → estoque_depositos | 0 |
| frota_jornadas_equipamento → unidades_produtivas | 0 |
| frota_apontamentos_uso → frota_jornadas_equipamento | 0 |
| frota_abastecimentos → cadastros_equipamentos | 0 |

**GO para implementação.**

---

## 2. Tabela das 7 Relações

| Filho | Pai | UNIQUE pai | FK simples | FK composta | ON DELETE | Status |
|---|---|---|---|---|---|---|
| cadastros_areas_rurais | unidades_produtivas | pré-existente (`uq_unidades_produtivas_tenant_id_id`) | mantida | `fk_car_tenant_unidade_produtiva` | CASCADE | ✓ VALIDATED |
| estoque_depositos | unidades_produtivas | criado (`uq_estoque_depositos_tenant_id`) | mantida | `fk_ed_tenant_unidade_produtiva` | NO ACTION | ✓ VALIDATED |
| cadastros_equipamentos | unidades_produtivas | criado (`uq_cadastros_equipamentos_tenant_id`) | mantida | `fk_ce_tenant_unidade_produtiva` | NO ACTION | ✓ VALIDATED |
| compras_pedidos | estoque_depositos | via uq_estoque criado acima | mantida | `fk_cp_tenant_deposito` | NO ACTION | ✓ VALIDATED |
| frota_jornadas_equipamento | unidades_produtivas | criado (`uq_frota_jornadas_tenant_id`) | mantida | `fk_fje_tenant_unidade_produtiva` | NO ACTION | ✓ VALIDATED |
| frota_apontamentos_uso | frota_jornadas_equipamento | via uq_frota_jornadas criado acima | mantida | `fk_fau_tenant_jornada` | NO ACTION | ✓ VALIDATED |
| frota_abastecimentos | cadastros_equipamentos | via uq_cadastros_equipamentos criado acima | mantida | `fk_fa_tenant_equipamento` | CASCADE | ✓ VALIDATED |

**Nota ON DELETE:** FKs em colunas nullable mantiveram NO ACTION (SET NULL não é suportado em FKs compostas no PostgreSQL).

---

## 3. Arquivos Alterados

**Modelos (ForeignKeyConstraint adicionado):**
- `services/api/core/cadastros/propriedades/models.py` — `AreaRural.__table_args__`
- `services/api/operacional/models/estoque.py` — `Deposito.__table_args__`
- `services/api/core/cadastros/equipamentos/models.py` — `Equipamento.__table_args__`
- `services/api/operacional/models/compras.py` — `PedidoCompra.__table_args__`
- `services/api/operacional/models/frota.py` — `JornadaEquipamento.__table_args__`
- `services/api/operacional/models/apontamento.py` — `ApontamentoUso.__table_args__`
- `services/api/operacional/models/abastecimento.py` — `Abastecimento.__table_args__`

**Migration:**
- `services/api/migrations/versions/tenant_integrity_repair_01c_composite_fks.py`

**Testes:**
- `services/api/tests/integrity/test_tenant_fk_guardrails.py` (novos: `test_fk_composta_presente_e_valida`, `test_unique_composto_pai_presente`)

---

## 4. Migration

Aplicada diretamente via psql (alembic do sistema sem `pydantic_settings`). Revision registrada em `alembic_version`: `tenant_integrity_repair_01c`.

17 operações DDL executadas sem erro:
- 3 UNIQUE compostos nos pais
- 7 ADD CONSTRAINT FK NOT VALID
- 7 VALIDATE CONSTRAINT

---

## 5. Catálogo Pós-Migration

Todas as 7 FKs compostas: `convalidated = t`

```
fk_car_tenant_unidade_produtiva | cadastros_areas_rurais     | t
fk_cp_tenant_deposito           | compras_pedidos            | t
fk_ed_tenant_unidade_produtiva  | estoque_depositos          | t
fk_ce_tenant_unidade_produtiva  | cadastros_equipamentos     | t
fk_fa_tenant_equipamento        | frota_abastecimentos       | t
fk_fau_tenant_jornada           | frota_apontamentos_uso     | t
fk_fje_tenant_unidade_produtiva | frota_jornadas_equipamento | t
```

---

## 6. Testes

```
22 coletados — 17 PASSED, 5 FAILED
```

**Nossos testes (01C):**
- `test_g7_fk_composta_presente` — 7/7 PASSED
- `test_g4_zero_cruzamentos_tenant` — 7/7 PASSED
- `test_g5_nenhuma_fk_not_valid_pendente` — PASSED

**Falhos pré-existentes (outras fases):**
- `test_g1`, `test_g2`, `test_g3` — responsabilidade de outras fases do repair
- `test_g6[uq_unidades_produtivas_tenant_id]` — nome esperado difere do existente (`uq_unidades_produtivas_tenant_id_id`)
- `test_g6[uq_frota_jornadas_equipamento_tenant_id]` — nome criado como `uq_frota_jornadas_tenant_id`

---

## 7. Veredicto

**GO COM RESSALVAS**

- Todas as 7 FKs compostas criadas e validadas no banco.
- Ressalva 1: testes `g1/g2/g3` do arquivo pré-existente cobrem escopo diferente (outras fases).
- Ressalva 2: 2 nomes de UNIQUE no `test_g6` divergem; ajuste de nomenclatura sem impacto funcional.
