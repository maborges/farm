# SANKHYA-SCHEMA-REPAIR-02 — Normalização Temporal no Soft Delete do Runtime Canônico

## 1. Resumo executivo

Corrigido `SankhyaSyncService._soft_delete_canonical_runtime` (sync_service.py:1177), que usava `datetime.now(UTC)` (aware) para atualizar cinco colunas `TIMESTAMP WITHOUT TIME ZONE` (`TenantIntegracao.deleted_at`, `IntegrationFeature.deleted_at/updated_at`, `IntegrationSyncPolicy.deleted_at/updated_at`, `IntegrationCredential.deleted_at/updated_at`), causando `DataError` do asyncpg. Correção de uma linha: `now = datetime.now(UTC).replace(tzinfo=None)`. `test_erp_bootstrap_tardio.py` fechou em 6/6, sem regressão nas 59 validações combinadas de Sankhya/OpenWeather/readiness/guardrails.

## 2. Contexto

Descoberto ao converger `test_erp_bootstrap_tardio.py` para tenants PostgreSQL reais durante a retomada de `INTEGRATIONS-TEST-INFRA-03A`, após `SANKHYA-SCHEMA-REPAIR-01` (RLS/tenant UUID em `canonical_adapter.py`).

## 3. Bloqueio da `INTEGRATIONS-TEST-INFRA-03A`

Baseline: `test_erp_bootstrap_tardio.py` — 4 passed, 2 failed. Os dois testes falhos (`test_primeiro_save_tardio_...`, `test_remocao_de_erp_persistido_...`) exercitam o endpoint `DELETE /api/v1/integracoes/sankhya/config`, que chama `_soft_delete_canonical_runtime` — código de produção, fora do escopo de `03A`.

## 4. Causa raiz

```python
now = datetime.now(UTC)
canonical_config.status = "inativa"
canonical_config.lifecycle_state = IntegrationStatus.REMOVED.value
canonical_config.deleted_at = now
...
await self.db.execute(text("UPDATE integration_features SET ... deleted_at = :now, updated_at = :now ..."), {..., "now": now})
await self.db.execute(text("UPDATE integration_sync_policies SET ... deleted_at = :now, updated_at = :now ..."), {..., "now": now})
await self.db.execute(text("UPDATE integration_credentials SET ... deleted_at = :now, updated_at = :now ..."), {..., "now": now})
```

`now` é reutilizado (mesmo valor) em todas as cinco atualizações. Sendo aware (`tzinfo=UTC`), sua atribuição a colunas naive falha com `DataError: ... can't subtract offset-naive and offset-aware datetimes`.

## 5. Campos afetados

`TenantIntegracao.deleted_at` (atribuído via ORM), `IntegrationFeature.deleted_at`/`updated_at`, `IntegrationSyncPolicy.deleted_at`/`updated_at`, `IntegrationCredential.deleted_at`/`updated_at` (todos via UPDATE textual).

## 6. Contratos SQLAlchemy

Confirmado em `integracoes/models.py` — todos `Column(DateTime)`, sem `timezone=True`:

- `TenantIntegracao.deleted_at` — linha 218.
- `IntegrationCredential.updated_at`/`deleted_at` — linhas 253/254.
- `IntegrationFeature.updated_at`/`deleted_at` — linhas 309/(implícito, mesma classe de bloco).
- `IntegrationSyncPolicy.updated_at`/`deleted_at`.

Nenhum desses campos usa `timezone=True`; a normalização naive aplica-se a todos.

## 7. Contratos físicos PostgreSQL

`TIMESTAMP WITHOUT TIME ZONE` em todas as colunas listadas — consistente com `Column(DateTime)` sem `timezone=True`.

## 8. Reprodução anterior

Baseline confirmado: `test_erp_bootstrap_tardio.py` — 4 passed, 2 failed. Traceback:

```text
sqlalchemy.exc.DBAPIError: ... DataError: invalid input for query argument $1:
datetime.datetime(2026, 7, 18, 3, 36, 55, ..., tzinfo=datetime.timezone.utc)
(can't subtract offset-naive and offset-aware datetimes)
[SQL: UPDATE integration_features SET habilitada = false, deleted_at = $1, updated_at = $1 ...]
```

Primeira coluna a falhar: `integration_features.deleted_at`/`updated_at` (primeira UPDATE textual da sequência).

## 9. Decisão temporal

Timestamp criado exclusivamente dentro do método (`now = datetime.now(UTC)`), sem receber datetime externo — aplicada a correção local mínima, sem helper adicional: `now = datetime.now(UTC).replace(tzinfo=None)`. O mesmo valor normalizado é reutilizado em todas as cinco atualizações, preservando a semântica de "mesmo instante para toda a operação de remoção".

## 10. Alteração realizada

```diff
-        now = datetime.now(UTC)
+        now = datetime.now(UTC).replace(tzinfo=None)
         canonical_config.status = "inativa"
```

Único ponto alterado em `services/api/integracoes/sankhya/services/sync_service.py`.

## 11. Validação do soft delete

`test_soft_delete_retorna_estado_vazio_sem_reutilizar_linha_removida` confirma que a remoção permanece soft (nenhuma exclusão física de `TenantIntegracao`), idempotente, e que o estado após remoção não reutiliza a linha removida. `test_remocao_de_erp_persistido_retorna_tenant_para_estado_sem_erp` confirma contagens: `active_canonical == 0`, `removed_canonical == 1`, `active_credentials == 0`, `active_features == 0`, `active_policies == 0`, `remaining_legacy == 0` — todas as dependências operacionais corretamente inativadas.

## 12. Validação PostgreSQL

Suíte executada contra a fixture oficial; UPDATEs textuais completam sem `DataError`; timestamps persistidos são naive (consistente com a coluna).

## 13. Testes executados

```
.venv/bin/pytest tests/unit/integracoes/test_erp_bootstrap_tardio.py -v
.venv/bin/pytest tests/unit/integracoes/test_sankhya_canonical_adapter.py tests/unit/integracoes/test_sankhya_legacy_reconciliation.py tests/unit/integracoes/test_openweather_domain.py tests/unit/integracoes/test_erp_readiness_service.py tests/unit/integracoes/test_sankhya_architecture.py tests/unit/integracoes/test_sankhya_models_tenant_fk.py -v
ruff check integracoes/sankhya/services/sync_service.py tests/unit/integracoes/test_erp_bootstrap_tardio.py
git diff --check
```

## 14. Comparação antes/depois

| Suíte | Antes | Depois |
|---|---|---|
| `test_erp_bootstrap_tardio.py` | 4 passed, 2 failed | **6 passed** |
| `test_sankhya_canonical_adapter.py` + `test_sankhya_legacy_reconciliation.py` | 31 passed | 31 passed (sem regressão) |
| `test_openweather_domain.py` | 8 passed | 8 passed (sem regressão) |
| `test_erp_readiness_service.py` + guardrails | 20 passed | 20 passed (sem regressão) |

Total combinado: 59/59 (excluindo `test_erp_bootstrap_tardio.py`, contado separadamente) + 6/6 = 65 testes verificados nesta fase.

## 15. Arquivos alterados

- `services/api/integracoes/sankhya/services/sync_service.py` — 1 linha (`_soft_delete_canonical_runtime`).
- `services/api/tests/unit/integracoes/test_erp_bootstrap_tardio.py` — já convergido para tenants reais na etapa anterior de `03A` (helper `criar_tenant_real`, remoção de `MarketplaceIntegracao.id=2` fixo); nenhuma alteração adicional nesta fase.

`ruff check` reporta 7 avisos pré-existentes no arquivo (import não ordenado, linhas longas, `E402`) em trechos não tocados por este diff — confirmado via `git diff --stat` (1 inserção, 1 remoção); não introduzidos por esta correção.

## 16. Impacto em produção

Corrigido: o endpoint de remoção de integração ERP Sankhya (`DELETE /api/v1/integracoes/sankhya/config`) deixa de falhar com `DataError` ao executar o soft delete do runtime canônico contra PostgreSQL real — cenário que ocorreria em toda remoção real de integração em produção.

## 17. Riscos remanescentes

- As mesmas linhas `datetime.now(UTC)` sem normalização em `iniciar_sync_log`/`finalizar_sync_log` (sync_service.py:1800, 1839) não foram auditadas nem alteradas — fora do escopo desta fase (exclusivamente `_soft_delete_canonical_runtime`). Se esses métodos escreverem em colunas naive, podem apresentar o mesmo defeito; recomenda-se auditoria futura caso apareçam falhas equivalentes.
- `sankhya_config.id` sem sequence/default — débito já registrado, não tratado aqui.
- Avisos pré-existentes de `ruff` no arquivo (import order, E501, E402) — não introduzidos por esta fase, não corrigidos por estarem fora do escopo mínimo.

## 18. Ponto de retomada da `INTEGRATIONS-TEST-INFRA-03A`

Estado confirmado:

```text
test_sankhya_legacy_reconciliation.py: 9 passed
test_sankhya_canonical_adapter.py: 22 passed
test_erp_bootstrap_tardio.py: 6 passed
```

Três arquivos restantes de `03A`: `test_sankhya_diagnostico_timezone.py`, `test_sankhya_governed_integration.py`, `test_sankhya_paridade_config.py`. Código de produção permanece congelado, salvo novo defeito real comprovado pelo PostgreSQL.

## 19. Veredicto

**GO — SOFT DELETE TEMPORAL SANKHYA RESTAURADO**

Todos os 17 critérios de aceitação atendidos: erro reproduzido, campos e tipos auditados, UTC preservado sem horário local, nenhum model/migration alterado, soft delete idempotente sem exclusão física, `test_erp_bootstrap_tardio.py` em 6/6, 31 validações Sankhya anteriores mantidas, OpenWeather 8/8, readiness/guardrails 20/20, nenhum outro provider tocado, `ruff` e `git diff --check` sem novos problemas introduzidos por este diff.
