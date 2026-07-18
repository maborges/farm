# OPENWEATHER-SCHEMA-REPAIR-01 — Alinhamento de `tenant_id` entre ORM e Schema de Resposta

## 1. Resumo executivo

Corrigido o desalinhamento de tipo entre o model SQLAlchemy (`TenantIntegracao.tenant_id: uuid.UUID` no PostgreSQL) e o schema Pydantic de resposta (`OpenWeatherConfigResponse.tenant_id: str`), no único ponto de construção dessa resposta: `OpenWeatherCanonicalAdapter.obter_config_response`. Alteração de uma linha. Todos os testes previamente bloqueados por esse defeito específico passaram a funcionar.

Durante a validação, foi descoberto um **segundo defeito, de mesma classe (UUID vs str), em método diferente** (`_tenant_uuid`, usado na publicação de eventos de domínio) — fora do escopo autorizado desta fase, documentado abaixo como risco remanescente.

## 2. Contexto

Revelado durante `INTEGRATIONS-TEST-INFRA-02`, ao converger `test_openweather_domain.py` da infraestrutura SQLite legada e indevida para a fixture PostgreSQL oficial (`tests/conftest.py::session`). PostgreSQL é o único banco suportado pela aplicação e pelos testes de persistência.

## 3. Impacto

Qualquer chamada real ao endpoint de configuração OpenWeather (`GET` que retorna `OpenWeatherConfigResponse`) falharia com `ValidationError` em ambiente PostgreSQL real, pois o ORM sempre retornou `uuid.UUID` para `tenant_id`, nunca `str`. O bug não era visível sob a infraestrutura de teste legada porque SQLite (tipagem frouxa) devolvia `tenant_id` como string.

## 4. Causa raiz

`OpenWeatherCanonicalAdapter.obter_config_response` (services.py:358) construía `OpenWeatherConfigResponse(tenant_id=config.tenant_id, ...)` passando o valor do ORM diretamente, sem conversão de tipo, para um campo Pydantic declarado como `str`.

## 5. Reprodução anterior

Baseline documentado em `INTEGRATIONS-TEST-INFRA-02`: `test_openweather_domain.py` — 2 passed, 6 failed. Traceback dominante: `pydantic_core._pydantic_core.ValidationError: 1 validation error for OpenWeatherConfigResponse — tenant_id: Input should be a valid string`.

## 6. Contrato ORM

`integracoes/models.py::TenantIntegracao.tenant_id` — `Column(UUIDType(as_uuid=True), ...)`. No PostgreSQL, retorna `uuid.UUID` (ou `asyncpg.pgproto.pgproto.UUID` conforme o caminho de leitura) após flush/refresh.

## 7. Contrato Pydantic

`integracoes/openweather/schemas.py::OpenWeatherConfigResponse.tenant_id: str`. Confirmado como o contrato correto/oficial: é o mesmo padrão usado nos demais schemas de resposta do módulo (`OpenWeatherIntegrationJobResponse.tenant_id: str`, `OpenWeatherWeatherSnapshotResponse.job_id: str | None`), todos com IDs UUID convertidos explicitamente para string na fronteira de saída.

## 8. Decisão de correção

Preservada a abordagem preferencial do escopo: manter `tenant_id: str` no schema público (compatibilidade de API/frontend inalterada) e converter explicitamente no service, na fronteira de saída.

## 9. Alteração realizada

```diff
 return OpenWeatherConfigResponse(
     id=config.id,
-    tenant_id=config.tenant_id,
+    tenant_id=str(config.tenant_id),
     provider_id=config.provider_id,
     ...
 )
```

Único ponto de construção confirmado via busca (`grep -n "OpenWeatherConfigResponse(" integracoes/openweather/services.py` → 1 ocorrência). `OpenWeatherService.obter_config_response`/`_config_response` apenas delegam ao adapter, sem construir o schema diretamente.

## 10. Teste PostgreSQL

Suíte alvo executada contra a fixture PostgreSQL oficial (`tests/conftest.py::session`), sem alteração de infraestrutura de testes.

## 11. Teste do service

`test_salvar_config_materializa_provider_features_policies_e_credential_encriptada` — que exercita `OpenWeatherService.salvar_config` → `_config_response` → `adapter.obter_config_response` — passou a ser aprovado após a correção (antes falhava com o `ValidationError` descrito).

## 12. Teste do endpoint

Endpoint `GET` correspondente (`routers.py:53`, `config = await service.obter_config_response(str(tenant_id))`, `response_model=OpenWeatherConfigResponse`) usa o mesmo método corrigido; nenhuma chamada real ao OpenWeather foi realizada.

## 13. Arquivos alterados

- `services/api/integracoes/openweather/services.py` — 1 linha (conversão explícita de `tenant_id` para `str`).

Nenhum outro arquivo alterado nesta fase.

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

| Suíte | Antes | Depois |
|---|---|---|
| `test_openweather_domain.py` | 2 passed, 6 failed | 3 passed, 5 failed |
| `test_erp_readiness_service.py` | 10 passed | 10 passed (sem regressão) |
| `test_sankhya_architecture.py` | 3 passed | 3 passed (sem regressão) |
| `test_sankhya_models_tenant_fk.py` | 7 passed | 7 passed (sem regressão) |

O teste que passou (`test_salvar_config_materializa_...`) é exatamente o que exercita o boundary corrigido. Os 5 testes que continuam falhando falham por um bug **diferente** (seção 16).

## 16. Impacto em produção

O bug corrigido afetava toda leitura de configuração OpenWeather via API em ambiente PostgreSQL real (`GET` de config) — corrigido.

**Descoberto, não corrigido (fora do escopo autorizado)**: `OpenWeatherCanonicalAdapter._tenant_uuid` (services.py:1224) assume `tenant_id: str` e chama `uuid.UUID(tenant_id)`, mas em runtime real recebe `config.tenant_id` já como objeto UUID (`asyncpg.pgproto.pgproto.UUID`), que não possui atributo `.replace` esperado pelo construtor de `uuid.UUID`, resultando em `AttributeError: 'asyncpg.pgproto.pgproto.UUID' object has no attribute 'replace'`. Esse método é chamado por `_publish_sync_started_event`, `_publish_configured_event`, `_publish_credential_rotated_event`, `_publish_sync_completed_event`, `_publish_sync_failed_event`, `_publish_health_changed_event` — ou seja, **todo fluxo que publica eventos de domínio do OpenWeather** (criação/rotação de credencial, teste de conexão, sincronização, mudança de health). É um defeito real de mesma classe (UUID vs str), em método diferente, que provavelmente afeta chamadas reais em produção sempre que o tenant_id chega como UUID nativo do driver.

## 17. Riscos remanescentes

- `OpenWeatherCanonicalAdapter._tenant_uuid` — bug real de tipo, não corrigido nesta fase por estar fora do escopo autorizado ("corrigir exclusivamente o retorno de tenant_id incompatível... em `obter_config_response`"). Recomenda-se uma fase dedicada (`OPENWEATHER-SCHEMA-REPAIR-02` ou escopo equivalente) para auditar e corrigir todos os call-sites de `_tenant_uuid`.
- 5 testes de `test_openweather_domain.py` continuam falhando por esse motivo: `test_atualizacao_sem_nova_api_key_preserva_credencial_existente`, `test_rotacao_de_api_key_cria_nova_credencial_e_desativa_a_anterior`, `test_teste_de_conexao_cria_job_health_e_eventos_canonicos`, `test_falha_de_conexao_cria_alerta_e_health_degradado`, `test_status_timeline_e_diagnostico_consolidam_camadas_canonicas`.
- `sankhya_config.id` sem sequence/default — já registrado em fase anterior, não tratado aqui (fora de escopo).

## 18. Próxima etapa

Com o veredicto abaixo, a sequência formal continua para `INTEGRATIONS-TEST-INFRA-03A` (helper de tenant real + 6 arquivos com tenants fictícios). O novo bug de `_tenant_uuid` deve ser registrado como pendência a esclarecer com o usuário antes de prosseguir, já que bloqueia 5 dos 8 testes de `test_openweather_domain.py` e pode ser considerado pré-requisito para a convergência total dessa suíte.

## 19. Veredicto

**GO COM RESSALVAS — SERVICE CORRIGIDO, ENDPOINT PARCIALMENTE VALIDADO**

O defeito especificado no escopo (tenant_id em `obter_config_response`) foi corrigido, validado contra PostgreSQL real, sem regressões nos guardrails e no readiness. A suíte `test_openweather_domain.py` não está 100% verde porque expõe um defeito real adicional, de mesma natureza, fora do escopo desta fase.
