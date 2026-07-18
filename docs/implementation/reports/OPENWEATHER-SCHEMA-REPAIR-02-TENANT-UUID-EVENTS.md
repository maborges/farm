# OPENWEATHER-SCHEMA-REPAIR-02 — Normalização de `tenant_id` na Publicação de Eventos

## 1. Resumo executivo

Corrigido `OpenWeatherCanonicalAdapter._tenant_uuid` para aceitar tanto `str` quanto `uuid.UUID` (incluindo `asyncpg.pgproto.pgproto.UUID`, confirmado como subclasse de `uuid.UUID`), eliminando o `AttributeError` que ocorria ao tratar um objeto UUID nativo do driver PostgreSQL como string. A correção habilitou 2 dos 5 testes anteriormente bloqueados. Os 3 restantes falham por um **terceiro defeito, de classe diferente** (datetime naive vs aware), descoberto durante a validação e fora do escopo desta fase.

## 2. Contexto

Descoberto durante `OPENWEATHER-SCHEMA-REPAIR-01`, ao validar a correção de `obter_config_response` contra PostgreSQL real: `_tenant_uuid` — usado exclusivamente na publicação de eventos de domínio do OpenWeather — assumia `tenant_id: str`, mas recebe em runtime um objeto UUID do driver.

## 3. Severidade

Alta. `_tenant_uuid` é chamado em todo fluxo que publica evento de domínio do provider: configuração, rotação de credencial, início/conclusão/falha de sincronização, mudança de health, alerta operacional e sincronização climática por unidade produtiva — ou seja, praticamente todo o ciclo de vida operacional do OpenWeather em produção.

## 4. Causa raiz

```python
@staticmethod
def _tenant_uuid(tenant_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(tenant_id)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"openweather-tenant:{tenant_id}")
```

`uuid.UUID(tenant_id)` espera uma string; ao receber um objeto UUID (`config.tenant_id`, já tipado como UUID pelo driver PostgreSQL), o construtor tenta `hex.replace(...)` e falha com `AttributeError: '<tipo UUID>' object has no attribute 'replace'` — exceção não capturada pelo `except ValueError`, portanto não mascarada pelo fallback de uuid5.

## 5. Call-sites afetados

| Método chamador | Origem do `tenant_id` | Tipo real (PostgreSQL) | Evento publicado |
|---|---|---|---|
| `_publish_configured_event` | `config.tenant_id` | UUID (driver) | `IntegrationConfigured` |
| `_publish_credential_rotated_event` | `config.tenant_id` | UUID (driver) | `IntegrationCredentialRotated` |
| `_publish_sync_started_event` | `config.tenant_id` | UUID (driver) | `IntegrationSyncStarted` |
| `_publish_sync_completed_event` | `config.tenant_id` | UUID (driver) | `IntegrationSyncCompleted` |
| `_publish_sync_failed_event` | `config.tenant_id` | UUID (driver) | `IntegrationSyncFailed` |
| `_publish_health_changed_event` | `config.tenant_id` | UUID (driver) | `IntegrationHealthChanged` |
| `_create_operational_alert` | `config.tenant_id` | UUID (driver) | `OperationalAlertCreate` (alert_engine) |
| `_execute_current_weather` (filtro de query) | `config.tenant_id` | UUID (driver) | n/a |
| `_execute_current_weather` (por unidade produtiva) | `config.tenant_id` | UUID (driver) | `ClimaSyncRealizado` |

Confirmado via `grep -n "_tenant_uuid" integracoes/openweather/services.py` — 10 ocorrências, todas com a mesma origem (`config.tenant_id`). O helper é `@staticmethod` privado da classe `OpenWeatherCanonicalAdapter`, usado exclusivamente pelo provider OpenWeather.

## 6. Reprodução anterior

Baseline após `OPENWEATHER-SCHEMA-REPAIR-01`: `test_openweather_domain.py` — 3 passed, 5 failed. Traceback dominante:

```text
AttributeError: 'asyncpg.pgproto.pgproto.UUID' object has no attribute 'replace'
```

Reprodução mínima confirmada:

```python
>>> import asyncpg.pgproto.pgproto as p, uuid
>>> issubclass(p.UUID, uuid.UUID)
True
```

Ou seja, o tipo do driver **já é** um `uuid.UUID` — a normalização correta é checar `isinstance` antes de tentar reconstruir a partir de string.

## 7. Tipos de entrada identificados

- `str` (formato UUID válido) — usado nos poucos call-sites que ainda passam string manualmente.
- `uuid.UUID` — objeto Python nativo.
- `asyncpg.pgproto.pgproto.UUID` — subclasse de `uuid.UUID` retornada pelo driver ao ler colunas UUID do PostgreSQL; coberta automaticamente pelo `isinstance(tenant_id, uuid.UUID)`.

## 8. Decisão de normalização

```python
@staticmethod
def _tenant_uuid(tenant_id: str | uuid.UUID) -> uuid.UUID:
    if isinstance(tenant_id, uuid.UUID):
        return tenant_id
    return uuid.UUID(str(tenant_id))
```

Removido o fallback silencioso (`uuid.uuid5(uuid.NAMESPACE_URL, f"openweather-tenant:{tenant_id}")`) que mascarava tenants em formato inválido gerando um UUID determinístico não correspondente ao tenant real — comportamento explicitamente proibido no escopo desta fase. Nenhum uso legítimo desse fallback foi encontrado nos 10 call-sites (todos alimentados por `config.tenant_id`, sempre um UUID real após a convergência para PostgreSQL).

## 9. Alteração realizada

```diff
 @staticmethod
-def _tenant_uuid(tenant_id: str) -> uuid.UUID:
-    try:
-        return uuid.UUID(tenant_id)
-    except ValueError:
-        return uuid.uuid5(uuid.NAMESPACE_URL, f"openweather-tenant:{tenant_id}")
+def _tenant_uuid(tenant_id: str | uuid.UUID) -> uuid.UUID:
+    if isinstance(tenant_id, uuid.UUID):
+        return tenant_id
+    return uuid.UUID(str(tenant_id))
```

## 10. Tratamento de entradas inválidas

`uuid.UUID(str(tenant_id))` propaga `ValueError` para strings malformadas, string vazia e `None` (`uuid.UUID("None")` é inválido e levanta `ValueError`). Nenhum UUID novo é gerado como fallback; o erro é claro e não mascarado, conforme exigido.

## 11. Validação PostgreSQL

Suíte alvo executada contra a fixture PostgreSQL oficial, sem alteração de infraestrutura de testes. `config.tenant_id` chega como `asyncpg.pgproto.pgproto.UUID` real após `flush`/`refresh` em todos os testes que exercitam publicação de eventos.

## 12. Validação dos eventos

Os testes que passaram a ser aprovados (`test_atualizacao_sem_nova_api_key_preserva_credencial_existente`, `test_rotacao_de_api_key_cria_nova_credencial_e_desativa_a_anterior`) exercitam `sync_provider_config` → `_publish_configured_event`/`_publish_credential_rotated_event`, confirmando que os eventos são publicados com o `tenant_id` correto (o UUID real do tenant, não mais um uuid5 derivado). Nenhum contrato de evento, payload, `dedupe_key` ou nome de evento foi alterado — apenas o tipo de entrada aceito pelo helper.

## 13. Testes executados

```
.venv/bin/pytest tests/unit/integracoes/test_openweather_domain.py -v
.venv/bin/pytest tests/unit/integracoes/test_erp_readiness_service.py -v
.venv/bin/pytest tests/unit/integracoes/test_sankhya_architecture.py -v
.venv/bin/pytest tests/unit/integracoes/test_sankhya_models_tenant_fk.py -v
.venv/bin/ruff check integracoes/openweather/services.py tests/unit/integracoes/test_openweather_domain.py
git diff --check
```

## 14. Comparação antes/depois

| Suíte | Antes (pós REPAIR-01) | Depois (pós REPAIR-02) |
|---|---|---|
| `test_openweather_domain.py` | 3 passed, 5 failed | 5 passed, 3 failed |
| `test_erp_readiness_service.py` | 10 passed | 10 passed (sem regressão) |
| `test_sankhya_architecture.py` | 3 passed | 3 passed (sem regressão) |
| `test_sankhya_models_tenant_fk.py` | 7 passed | 7 passed (sem regressão) |

Testes que passaram a ser aprovados: `test_atualizacao_sem_nova_api_key_preserva_credencial_existente`, `test_rotacao_de_api_key_cria_nova_credencial_e_desativa_a_anterior`.

## 15. Arquivos alterados

- `services/api/integracoes/openweather/services.py` — método `_tenant_uuid` (5 inserções, 6 remoções).

Nenhum outro arquivo alterado nesta fase.

## 16. Impacto em produção

Corrigido: publicação de eventos de domínio do OpenWeather (configuração, rotação de credencial) deixa de falhar com `AttributeError` quando `tenant_id` chega como UUID nativo do driver — cenário que ocorre em toda chamada real contra PostgreSQL.

**Descoberto, não corrigido (fora do escopo autorizado)**: `OpenWeatherService._update_config_last_sync` grava `config.ultima_sincronizacao = job.finished_at or datetime.now(timezone.utc)` — um `datetime` *aware* (com `tzinfo=UTC`) — na coluna `TIMESTAMP WITHOUT TIME ZONE` de `tenant_integracoes`, resultando em:

```text
sqlalchemy.exc.DBAPIError: ... DataError: invalid input for query argument $1: ... (can't subtract offset-naive and offset-aware datetimes)
```

Esse é um **terceiro defeito, de classe distinta** (naive vs aware datetime, não UUID/str), que bloqueia os fluxos de teste de conexão, sincronização climática e diagnóstico/timeline (3 testes). Não foi tratado por estar fora do escopo mapeado nesta fase (exclusivamente `_tenant_uuid`).

## 17. Riscos remanescentes

- `OpenWeatherService._update_config_last_sync` (e possivelmente outros pontos que gravam `datetime.now(timezone.utc)` em colunas naive do módulo OpenWeather) precisa de uma fase dedicada de normalização de timezone.
- 3 testes de `test_openweather_domain.py` continuam falhando por esse motivo: `test_teste_de_conexao_cria_job_health_e_eventos_canonicos`, `test_falha_de_conexao_cria_alerta_e_health_degradado`, `test_status_timeline_e_diagnostico_consolidam_camadas_canonicas`.
- `sankhya_config.id` sem sequence/default — já registrado em fases anteriores, não tratado aqui.

## 18. Próxima etapa

Recomenda-se decidir, antes de `INTEGRATIONS-TEST-INFRA-03A`, se o novo defeito de datetime naive/aware merece uma fase dedicada (`OPENWEATHER-SCHEMA-REPAIR-03`) ou se será tratado em conjunto com a convergência dos demais arquivos. A sequência formal aguarda essa decisão.

## 19. Veredicto

**GO COM RESSALVAS — HELPER CORRIGIDO, EVENTOS PARCIALMENTE VALIDADOS**

Todos os critérios relativos a `_tenant_uuid` foram atendidos: call-sites mapeados, falha reproduzida, strings e objetos UUID (incluindo o tipo do driver PostgreSQL) aceitos, valores inválidos continuam rejeitados sem fallback silencioso, nenhum UUID novo gerado artificialmente, nenhuma regressão em guardrails/readiness, ruff e `git diff --check` limpos. A suíte não atingiu 8/8 porque expõe um terceiro defeito de natureza diferente, fora do escopo autorizado.
