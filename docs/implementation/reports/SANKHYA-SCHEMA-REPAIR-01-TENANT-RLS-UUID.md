# SANKHYA-SCHEMA-REPAIR-01 — Normalização de Tenant UUID no Contexto RLS e Eventos

## 1. Resumo executivo

Corrigidos dois defeitos de produção em `SankhyaCanonicalAdapter` (`canonical_adapter.py`), descobertos ao converger `test_sankhya_canonical_adapter.py` para tenants PostgreSQL reais durante `INTEGRATIONS-TEST-INFRA-03A`: (1) `_restore_rls_context` passava um objeto `uuid.UUID` diretamente ao bind param textual de `set_config`, e (2) `_tenant_uuid` mascarava tenants inválidos com um fallback `uuid5`. Ambos corrigidos com o mesmo padrão já validado nas três fases `OPENWEATHER-SCHEMA-REPAIR`. `test_sankhya_canonical_adapter.py` fechou em 22/22 (mais 3 correções de fixture de teste, mesma classe de débito já tratada em `test_sankhya_legacy_reconciliation.py`). Nenhuma regressão em `test_sankhya_legacy_reconciliation.py`, OpenWeather, readiness ou guardrails.

## 2. Contexto

`INTEGRATIONS-TEST-INFRA-03A` está convergindo os 6 arquivos com tenants fictícios para o helper `criar_tenant_real` (PostgreSQL oficial). Ao aplicar isso em `test_sankhya_canonical_adapter.py`, 11 dos 22 testes passaram a falhar por um defeito de produção, não de fixture.

## 3. Bloqueio causado na `INTEGRATIONS-TEST-INFRA-03A`

Com tenants reais, `config.tenant_id` (de `TenantIntegracao`) e `job.tenant_id`/`provider_config.tenant_id` chegam como `uuid.UUID` real do driver PostgreSQL. `_restore_rls_context`, chamado em quase todo fluxo do adapter, propagava esse objeto para `set_config`, que exige texto — travando a convergência do arquivo. A fase foi pausada e `INTEGRATIONS-TEST-INFRA-03A` formalmente interrompida até esta correção, conforme decisão do usuário.

## 4. Causa raiz de `_restore_rls_context`

```python
async def _restore_rls_context(self, tenant_id: str | None = None) -> None:
    ...
    effective_tenant_id = tenant_id or self.db.info.get("tenant_id")
    ...
    await self.db.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": effective_tenant_id},
    )
```

`effective_tenant_id` podia ser um `uuid.UUID` (vindo de `config.tenant_id`, `provider_config.tenant_id` ou `job.tenant_id`) sem conversão para string antes do bind. `set_config` exige texto; asyncpg rejeitou com `DataError: expected str, got UUID`.

## 5. Causa raiz de `_tenant_uuid`

```python
@staticmethod
def _tenant_uuid(tenant_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(tenant_id)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"sankhya-tenant:{tenant_id}")
```

Mesmo padrão já identificado e removido no OpenWeather (`OPENWEATHER-SCHEMA-REPAIR-02`): ao receber um `uuid.UUID` real, `uuid.UUID(tenant_id)` levantaria `AttributeError` (não capturado pelo `except ValueError`); e o fallback `uuid5` mascarava qualquer tenant_id malformado com um UUID determinístico não correspondente ao tenant real, violando integridade de tenant.

## 6. Call-sites afetados

| Método chamador | Origem do tenant | Tipo possível | Finalidade |
|---|---|---|---|
| `sync_provider_config` (múltiplas linhas: 746, 769, 785, 809) | `provider_config.tenant_id` / `config.tenant_id` / `updated.tenant_id` | `str` (parâmetro) ou `uuid.UUID` (models canônicos) | Restaurar contexto RLS antes de operações subsequentes |
| `iniciar_sync_log`/fluxos de job (822, 856, 874, 946, 1603) | `tenant_id` (parâmetro) ou `job.tenant_id` | idem | Restaurar contexto RLS |
| `_publish_*_event` (1483, 1500, 1519, 1541, 1567, 1590) | `config.tenant_id` | `uuid.UUID` (canônico) | Normalizar `tenant_id` para os eventos de domínio Sankhya |

Confirmado via `rg -n "_restore_rls_context|_tenant_uuid"` — 16 ocorrências totais, todas internas ao próprio `SankhyaCanonicalAdapter`.

## 7. Tipos reais identificados

- `str`: parâmetros de método vindos diretamente do service layer (ex.: `tenant_id` explícito em `iniciar_sync_log`).
- `uuid.UUID`/`asyncpg.pgproto.pgproto.UUID` (subclasse confirmada em `OPENWEATHER-SCHEMA-REPAIR-02`): atributos `.tenant_id` de `TenantIntegracao`, `IntegrationJob`, `SankhyaConfig` lidos do PostgreSQL real.
- `None`: ausência de tenant — `_restore_rls_context` já tratava esse caso (early return via `not effective_tenant_id`), preservado sem alteração.

## 8. Reprodução anterior

Baseline: `test_sankhya_canonical_adapter.py` — 11 passed, 11 failed. Traceback dominante:

```text
sqlalchemy.exc.DBAPIError: ... DataError: invalid input for query argument $1:
UUID('...') (expected str, got UUID)
[SQL: SELECT set_config('app.current_tenant_id', $1, true)]
```

## 9. Decisão de normalização

Idêntica à adotada em `OPENWEATHER-SCHEMA-REPAIR-02`: `isinstance(tenant_id, uuid.UUID)` cobre tanto `uuid.UUID` puro quanto a subclasse do driver PostgreSQL; conversão para string ocorre exclusivamente no boundary SQL (`set_config`), sem alterar o tipo interno de `tenant_id` em nenhum outro ponto do adapter.

## 10. Remoção do fallback

Removido `uuid.uuid5(uuid.NAMESPACE_URL, f"sankhya-tenant:{tenant_id}")`. Nenhum call-site interno dependia desse fallback (todos os 6 usos de `_tenant_uuid` recebem `config.tenant_id`, sempre um tenant real após a convergência para PostgreSQL). Valores inválidos agora propagam `ValueError` explicitamente via `uuid.UUID(str(tenant_id))`.

## 11. Alteração realizada

```diff
 @staticmethod
-def _tenant_uuid(tenant_id: str) -> uuid.UUID:
-    try:
-        return uuid.UUID(tenant_id)
-    except ValueError:
-        return uuid.uuid5(uuid.NAMESPACE_URL, f"sankhya-tenant:{tenant_id}")
+def _tenant_uuid(tenant_id: str | uuid.UUID) -> uuid.UUID:
+    if isinstance(tenant_id, uuid.UUID):
+        return tenant_id
+    return uuid.UUID(str(tenant_id))

-async def _restore_rls_context(self, tenant_id: str | None = None) -> None:
+async def _restore_rls_context(self, tenant_id: str | uuid.UUID | None = None) -> None:
     bind = self.db.get_bind()
     dialect = getattr(bind, "dialect", None)
     effective_tenant_id = tenant_id or self.db.info.get("tenant_id")
     if getattr(dialect, "name", "") != "postgresql" or not effective_tenant_id:
         return

     self.db.info["tenant_id"] = effective_tenant_id
     await self.db.execute(
         text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
-        {"tenant_id": effective_tenant_id},
+        {"tenant_id": str(effective_tenant_id)},
     )
```

O terceiro argumento `true` (`is_local`) de `set_config` foi preservado sem alteração — a configuração continua escopada à transação.

Correções adicionais de fixture em `test_sankhya_canonical_adapter.py` (mesma classe de débito de `sankhya_config.id` sem sequence/default, já tratada em `test_sankhya_legacy_reconciliation.py` na fase anterior de `03A`):
- `_next_sankhya_config_id` (helper local, replica o `max(id)+1` já usado em produção por `SankhyaSyncService._next_config_id`) aplicado nos 2 testes que constroem `SankhyaConfig` diretamente (`test_status_detalhado_usa_fallback_legado_sem_camada_canonica`, `test_timeline_funciona_apenas_com_legado`).
- `test_adapter_atualiza_schema_de_provider_existente` convertido de INSERT incondicional para get-or-create por `slug="sankhya"` — colidia com o provider já commitado por testes anteriores do mesmo arquivo (mesma classe de "ID/slug fixo" do escopo de `03A`).

## 12. Validação PostgreSQL

Suíte executada contra a fixture oficial. `_restore_rls_context` agora recebe e converte corretamente tanto `str` quanto `uuid.UUID` real do driver, sem `DataError`.

## 13. Validação RLS

`set_config('app.current_tenant_id', :tenant_id, true)` recebe valor textual (`str(effective_tenant_id)`); `is_local=true` preservado (escopo transacional, não vaza entre sessões); nenhum tenant alternativo é derivado — o valor restaurado é exatamente o tenant real que originou a chamada.

## 14. Testes executados

```
.venv/bin/pytest tests/unit/integracoes/test_sankhya_canonical_adapter.py -v
.venv/bin/pytest tests/unit/integracoes/test_sankhya_legacy_reconciliation.py -v
.venv/bin/pytest tests/unit/integracoes/test_openweather_domain.py -v
.venv/bin/pytest tests/unit/integracoes/test_erp_readiness_service.py tests/unit/integracoes/test_sankhya_architecture.py tests/unit/integracoes/test_sankhya_models_tenant_fk.py -v
.venv/bin/ruff check integracoes/sankhya/services/canonical_adapter.py tests/unit/integracoes/test_sankhya_canonical_adapter.py
git diff --check
```

## 15. Comparação antes/depois

| Suíte | Antes | Depois |
|---|---|---|
| `test_sankhya_canonical_adapter.py` | 11 passed, 11 failed | **22 passed** |
| `test_sankhya_legacy_reconciliation.py` | 9 passed | 9 passed (sem regressão) |
| `test_openweather_domain.py` | 8 passed | 8 passed (sem regressão) |
| `test_erp_readiness_service.py` + guardrails | 20 passed | 20 passed (sem regressão) |

Total combinado nesta validação: 37/37.

## 16. Arquivos alterados

- `services/api/integracoes/sankhya/services/canonical_adapter.py` — `_tenant_uuid` e `_restore_rls_context` (único arquivo de produção alterado).
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py` — helper de tenant real (já iniciado antes desta fase), helper `_next_sankhya_config_id`, get-or-create do provider no teste de atualização de schema.

## 17. Impacto em produção

Corrigido: qualquer fluxo real do provider Sankhya que dependa de `_restore_rls_context` ou `_tenant_uuid` (criação/atualização de config, rotação de credencial, jobs de sincronização, eventos de domínio) deixa de falhar com `DataError` ao operar com tenant real do PostgreSQL, e deixa de mascarar tenant_id inválido com um UUID derivado por hash.

## 18. Riscos remanescentes

- `sankhya_config.id` sem sequence/default — débito já registrado (não corrigido, fora de escopo aqui e em `03A`; produção já contorna via `_next_config_id`, testes agora replicam o mesmo contorno).
- Nenhum outro risco específico deste adapter identificado nesta fase.

## 19. Retomada da `INTEGRATIONS-TEST-INFRA-03A`

Estado de retomada confirmado:

```text
test_sankhya_legacy_reconciliation.py: 9 passed
test_sankhya_canonical_adapter.py: 22 passed
```

Os dois arquivos Sankhya já convergidos não serão reabertos. Código de produção do adapter Sankhya permanece congelado a partir daqui. Próximo passo: retomar `03A` nos 4 arquivos restantes (`test_erp_bootstrap_tardio.py`, `test_sankhya_diagnostico_timezone.py`, `test_sankhya_governed_integration.py`, `test_sankhya_paridade_config.py`), consolidando o mesmo helper `criar_tenant_real`.

## 20. Veredicto

**GO — CONTEXTO RLS E TENANT UUID SANKHYA RESTAURADOS**

Todos os 19 critérios de aceitação foram atendidos: erro reproduzido, call-sites mapeados, `uuid.UUID` (Python e driver) e `str` aceitos, tenant inválido rejeitado com erro explícito, fallback `uuid5` removido, nenhum tenant alternativo gerado, `set_config` recebendo valor textual com `is_local=true` preservado, 22/22 no canonical adapter, 9/9 na reconciliação, 8/8 no OpenWeather, 20/20 em readiness/guardrails, nenhuma migration criada, nenhuma fixture global alterada, nenhum outro provider tocado, ruff e `git diff --check` limpos.
