# PROVIDER-DOMAIN-01 — OpenWeather

## 1. Resumo Executivo
O primeiro provider climático oficial foi materializado com o OpenWeather como prova prática de que o domínio de Integrações suporta um provider não-ERP sem redesign estrutural. A implementação reutiliza `IntegrationConfig`, `IntegrationCredential`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationJob`, `IntegrationHealth`, eventos oficiais, `Alert Engine`, observabilidade e RLS, sem alterar Sankhya ou criar infraestrutura paralela.

## 2. Arquivos Criados e Alterados
Backend:
- `services/api/integracoes/openweather/__init__.py`
- `services/api/integracoes/openweather/client.py`
- `services/api/integracoes/openweather/routers.py`
- `services/api/integracoes/openweather/schemas.py`
- `services/api/integracoes/openweather/services.py`
- `services/api/main.py`
- `services/api/tests/unit/integracoes/test_openweather_domain.py`

Frontend:
- `apps/web/src/lib/integracoes/openweather-api.ts`
- `apps/web/src/components/integracoes/openweather-console.tsx`
- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/clima/openweather/page.tsx`
- `apps/web/src/app/(dashboard)/dashboard/settings/integracoes/clima/openweather/loading.tsx`
- `apps/web/src/app/integracoes/openweather/page.tsx`
- `apps/web/src/app/integracoes/page.tsx`
- `apps/web/src/components/layout/app-sidebar.tsx`

Documentação:
- `docs/implementation/reports/PROVIDER-VALIDATION-01-VALIDACAO-ARQUITETURA-PROVIDER-CLIMATICO.md`
- `docs/implementation/reports/PROVIDER-DOMAIN-01-OPENWEATHER.md`

## 3. Adapter
O adapter OpenWeather foi implementado como uma camada oficial complementar, com responsabilidade de materializar a configuração do provider, executar teste de conexão, consultar o clima atual, emitir jobs oficiais, atualizar health e publicar eventos de domínio.

Pontos centrais:
- provider slug: `openweather`
- tipo: `CLIMA`
- escopo: `TENANT`
- conexão: REST com `api_base_url`, `environment`, `location_query`, `units`, `language`, `timeout_seconds`, `cache_ttl_seconds`, `api_version`
- credencial: API key criptografada via `integracoes/security.py`

## 4. Provider Definition
O `ProviderDefinition` do OpenWeather foi modelado de forma genérica, sem campos universais específicos de clima. A configuração concreta permanece no envelope do provider, preservando a abstração do domínio.

## 5. Features
Foram materializadas as features:
- `current_weather` como funcional
- `forecast`, `rainfall`, `temperature`, `humidity`, `wind` como preparadas

Isso valida que `IntegrationFeature` suporta capacidades incrementais por provider.

## 6. Policies
As policies oficiais foram definidas como:
- `current_weather` -> `PULL`
- `forecast` -> `PULL`
- `rainfall` -> `PULL`

Periodicidade-base:
- 30 minutos

## 7. Jobs
Cada consulta gera `IntegrationJob`, com:
- início e fim
- duração
- sucesso/erro
- payload mascarado
- feature
- trigger

O job oficial não substitui o Outbox; ele representa a execução operacional.

## 8. Health
O provider atualiza `IntegrationHealth` com estado operacional e resumo de falhas/sucessos. A implementação usa o enum oficial existente, sem criar enum paralelo.

Estados observados na prática:
- `CONNECTED`
- `AUTH_ERROR`
- `RATE_LIMITED`
- `DEGRADED`
- `TIMEOUT`
- `API_UNAVAILABLE` via mapeamento operacional e resumo, sem expandir a enumeração oficial

## 9. Eventos
Foram reutilizados os eventos oficiais já existentes:
- `IntegrationConfigured`
- `IntegrationSyncStarted`
- `IntegrationSyncCompleted`
- `IntegrationSyncFailed`
- `IntegrationHealthChanged`
- `IntegrationCredentialRotated`

Não houve criação de eventos específicos do OpenWeather.

## 10. Alertas
O OpenWeather aciona o `Alert Engine` existente para indisponibilidade, credencial inválida, rate limit e falhas consecutivas, sem criar um motor paralelo.

## 11. Observabilidade
O provider passou a aparecer naturalmente em:
- timeline operacional
- diagnóstico
- jobs
- health

Isso comprova que a arquitetura de Integrações não está acoplada ao Sankhya.

## 12. Compatibilidade
Compatibilidades preservadas:
- Sankhya não foi alterado
- `IntegrationJob`, `IntegrationHealth` e eventos oficiais foram reutilizados
- RLS e `tenant_id` continuam sendo a base de isolamento
- frontend do tenant recebeu uma entrada própria em Administração -> Integrações -> Clima -> OpenWeather

## 13. Testes
Validações executadas:
- `services/api/.venv/bin/pytest services/api/tests/unit/integracoes/test_openweather_domain.py -q` -> `8 passed`
- `services/api/.venv/bin/pytest services/api/tests/unit/integracoes -q` -> `65 passed`
- `services/api/.venv/bin/ruff check services/api/integracoes/openweather services/api/tests/unit/integracoes/test_openweather_domain.py` -> ok
- `./.venv/bin/alembic upgrade head` -> ok
- `pnpm exec eslint` no escopo alterado -> ok, com warning preexistente em `<img>` no sidebar
- `git diff --check` -> ok

## 14. Conclusões
O OpenWeather confirmou que o domínio oficial de Integrações é genérico de fato:
- aceita provider não-ERP
- separa conexão de credencial
- suporta features e policies por provider
- materializa jobs, health, eventos, alertas e observabilidade sem duplicar infraestrutura

O principal ajuste feito foi a implementação do adapter e da UX mínima do provider; não houve necessidade de alterar Sankhya nem de criar novos serviços transversais.

## 15. Próxima Execução
Recomendação: `PROVIDER-DOMAIN-02`, para validar um segundo provider não-ERP com perfil diferente, reforçando que o domínio suporta múltiplas integrações heterogêneas sem acoplamento ao primeiro caso real.
