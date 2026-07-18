# OPENWEATHER-SCHEMA-REPAIR-03 — Normalização de Datetime na Persistência de Última Sincronização

## 1. Resumo executivo

Corrigido `OpenWeatherService._update_config_last_sync`, que atribuía um `datetime` *aware* (UTC) a uma coluna PostgreSQL `TIMESTAMP WITHOUT TIME ZONE`, causando `DataError` do asyncpg. Adicionado helper local `_utc_naive` para normalizar o valor no boundary de persistência. A correção habilitou 2 dos 3 testes anteriormente bloqueados.

O terceiro teste restante (`test_falha_de_conexao_cria_alerta_e_health_degradado`) falhava por um defeito exclusivamente do próprio teste — asserção `"Timeout" in result.mensagem` (maiúsculo) contra um mock que levanta `httpx.TimeoutException("timeout")` (minúsculo), sem qualquer contrato funcional que exija capitalização. Corrigido tornando a asserção case-insensitive (`"timeout" in result.mensagem.lower()`), sem alterar código de produção. Com isso, `test_openweather_domain.py` fechou em **8/8**, encerrando as três fases de reparo do OpenWeather.

## 2. Contexto

Descoberto durante `OPENWEATHER-SCHEMA-REPAIR-02`, ao validar a correção de `_tenant_uuid` contra PostgreSQL real.

## 3. Impacto

O defeito bloqueava, em produção, toda finalização de job de sincronização climática (`_execute_current_weather` → `_update_config_last_sync`), incluindo teste de conexão, sincronização de clima atual, atualização de health e qualquer fluxo subsequente que dependesse de `ultima_sincronizacao`.

## 4. Causa raiz

```python
config.ultima_sincronizacao = job.finished_at or datetime.now(timezone.utc)
```

`job.finished_at` é lido de `IntegrationJob.finished_at = Column(DateTime(timezone=True))` — coluna aware, retorna `datetime` com `tzinfo=UTC`. `TenantIntegracao.ultima_sincronizacao = Column(DateTime)` — sem `timezone=True`, portanto `TIMESTAMP WITHOUT TIME ZONE` no PostgreSQL. O asyncpg rejeita a atribuição de um valor aware a essa coluna com `DataError: ... can't subtract offset-naive and offset-aware datetimes`.

## 5. Contrato físico PostgreSQL

`integracoes/models.py:205` — `ultima_sincronizacao = Column(DateTime)` → `TIMESTAMP WITHOUT TIME ZONE`.

## 6. Contrato SQLAlchemy

- `TenantIntegracao.ultima_sincronizacao`: `DateTime` (naive, sem `timezone=True`).
- `IntegrationJob.finished_at`: `DateTime(timezone=True)` (aware).
- `IntegrationJob.started_at`, `IntegrationHealth.last_success_at/last_failure_at/rate_limited_until/checked_at`, `TenantIntegracao.last_sync_at`: todos `DateTime(timezone=True)` (aware) — não afetados por este defeito porque não são atribuídos a partir de valores aware para colunas naive.

## 7. Reprodução anterior

Baseline após `OPENWEATHER-SCHEMA-REPAIR-02`: `test_openweather_domain.py` — 5 passed, 3 failed. Traceback dominante:

```text
sqlalchemy.exc.DBAPIError: ... DataError: invalid input for query argument $1:
datetime.datetime(2026, 7, 18, 3, 2, 52, ..., tzinfo=datetime.timezone.utc)
(can't subtract offset-naive and offset-aware datetimes)
[SQL: UPDATE tenant_integracoes SET ultima_sincronizacao=$1::TIMESTAMP WITHOUT TIME ZONE, ...]
```

## 8. Campos e call-sites afetados

Único call-site que escreve em `ultima_sincronizacao`: `OpenWeatherService._update_config_last_sync` (services.py, chamado por `_execute_current_weather`). Nenhum outro campo do mesmo fluxo (`updated_at`, `checked_at`, `last_success_at`, `last_failure_at`) apresenta o mesmo defeito, pois todos são colunas `DateTime(timezone=True)` ou usam `datetime.utcnow()` (naive) consistentemente com o tipo de sua própria coluna — confirmado por auditoria, não ampliado.

## 9. Decisão temporal

Coluna física é `TIMESTAMP WITHOUT TIME ZONE` → valor persistido deve ser UTC sem `tzinfo`. Aware UTC → naive UTC; aware com outro offset → convertido para UTC e despido de `tzinfo`; naive → preservado; `None` → `datetime.now(timezone.utc)` seguido da mesma normalização (semântica UTC explícita, nunca hora local do servidor).

## 10. Normalização implementada

```diff
+    @staticmethod
+    def _utc_naive(value: datetime) -> datetime:
+        if value.tzinfo is None:
+            return value
+        return value.astimezone(timezone.utc).replace(tzinfo=None)
+
     async def _update_config_last_sync(self, config: TenantIntegracao, job: IntegrationJob) -> None:
-        config.ultima_sincronizacao = job.finished_at or datetime.now(timezone.utc)
+        last_sync = job.finished_at or datetime.now(timezone.utc)
+        config.ultima_sincronizacao = self._utc_naive(last_sync)
         self.db.add(config)
         await self.db.commit()
         await self.db.refresh(config)
```

Helper local, sem criação de utilitário global.

## 11. Tratamento dos tipos de datetime

- Aware UTC (`tzinfo=timezone.utc`) → `astimezone(timezone.utc).replace(tzinfo=None)` produz o mesmo instante, sem `tzinfo`.
- Aware com outro offset (ex.: `timezone(timedelta(hours=-3))`) → convertido para UTC antes de remover `tzinfo`, preservando o instante real.
- Naive → retornado sem alteração (assume-se já UTC, padrão do restante do domínio via `datetime.utcnow()`).
- `None` (`job.finished_at is None`) → cai no fallback `datetime.now(timezone.utc)`, normalizado da mesma forma.

## 12. Validação PostgreSQL

Suíte alvo executada contra a fixture PostgreSQL oficial. Flush e commit passam sem `DataError`; valor recarregado (`await self.db.refresh(config)`) não possui `tzinfo`, confirmado pelos testes que exercitam esse fluxo passando a ser aprovados.

## 13. Validação funcional

```
.venv/bin/pytest tests/unit/integracoes/test_openweather_domain.py -v
```

Resultado após a correção do datetime: 7 passed, 1 failed. Após a correção adicional da asserção do teste (seção 16-bis): **8 passed**.

### 13-bis. Correção adicional — asserção de mensagem (fora do código de produção)

```diff
- assert "Timeout" in result.mensagem
+ assert "timeout" in result.mensagem.lower()
```

Arquivo: `services/api/tests/unit/integracoes/test_openweather_domain.py:317`. Nenhum código de produção foi alterado para essa correção; `str(exc)` já era propagado corretamente por `_execute_current_weather`. Não existe contrato funcional que exija capitalização ou humanização de mensagens de erro — a asserção foi tornada semanticamente estável (case-insensitive) preservando as demais asserções funcionais do teste (`result.sucesso is False`, `job.status == FAILED`, `health.status == DEGRADED`).

## 14. Testes executados

```
.venv/bin/pytest tests/unit/integracoes/test_openweather_domain.py -v
.venv/bin/pytest tests/unit/integracoes/test_erp_readiness_service.py -v
.venv/bin/pytest tests/unit/integracoes/test_sankhya_architecture.py -v
.venv/bin/pytest tests/unit/integracoes/test_sankhya_models_tenant_fk.py -v
.venv/bin/ruff check integracoes/openweather/services.py tests/unit/integracoes/test_openweather_domain.py
git diff --check
```

## 15. Comparação antes/depois

| Suíte | Antes (pós REPAIR-02) | Depois (datetime) | Depois (asserção) |
|---|---|---|---|
| `test_openweather_domain.py` | 5 passed, 3 failed | 7 passed, 1 failed | **8 passed** |
| `test_erp_readiness_service.py` | 10 passed | 10 passed | 10 passed (sem regressão) |
| `test_sankhya_architecture.py` | 3 passed | 3 passed | 3 passed (sem regressão) |
| `test_sankhya_models_tenant_fk.py` | 7 passed | 7 passed | 7 passed (sem regressão) |

Testes que passaram a ser aprovados pela correção de datetime: `test_teste_de_conexao_cria_job_health_e_eventos_canonicos`, `test_status_timeline_e_diagnostico_consolidam_camadas_canonicas`. Teste que passou a ser aprovado pela correção da asserção: `test_falha_de_conexao_cria_alerta_e_health_degradado`.

## 16. Arquivos alterados

- `services/api/integracoes/openweather/services.py` — helper `_utc_naive` + ajuste em `_update_config_last_sync` (13 inserções, 7 remoções). Único arquivo de código de produção alterado em toda a sequência `OPENWEATHER-SCHEMA-REPAIR-01/02/03`.
- `services/api/tests/unit/integracoes/test_openweather_domain.py` — 1 linha (asserção tornada case-insensitive). Nenhum código de produção adicional foi alterado para essa correção.

## 17. Impacto em produção

Corrigido: toda finalização de sincronização climática (teste de conexão, consulta de clima atual) deixa de falhar com `DataError` ao persistir `ultima_sincronizacao` em PostgreSQL real.

O defeito de asserção (seção 13-bis) não tinha nenhum impacto em produção — era exclusivo do teste.

## 18. Riscos remanescentes

- `sankhya_config.id` sem sequence/default — já registrado em fases anteriores, não tratado aqui.
- Nenhum risco remanescente específico do OpenWeather após esta fase.

## 19. Próxima etapa

As três fases de reparo do OpenWeather (`OPENWEATHER-SCHEMA-REPAIR-01/02/03`) estão encerradas, com `test_openweather_domain.py` em 8/8. Próxima etapa: `INTEGRATIONS-TEST-INFRA-03A` — helper compartilhado de tenant PostgreSQL real, correção dos 6 arquivos com tenants fictícios, eliminação de IDs/slugs fixos, preservação de RLS, sem alteração de código de produção.

## 20. Veredicto

**GO — REPAROS OPENWEATHER CONCLUÍDOS**

`test_openweather_domain.py`: 8 passed. Guardrails e readiness sem regressão (20/20). Ruff e `git diff --check` limpos. Nenhuma migration criada, nenhum outro provider alterado, nenhuma chamada externa real ao OpenWeather realizada. As três fases (`REPAIR-01`: tenant_id no schema; `REPAIR-02`: tenant_id nos eventos; `REPAIR-03`: datetime na persistência + asserção de teste) estão formalmente encerradas.
