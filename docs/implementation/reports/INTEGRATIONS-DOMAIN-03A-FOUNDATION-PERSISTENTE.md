# INTEGRATIONS-DOMAIN-03A — Foundation Persistente do Domínio Canônico de Integrações

## 1. Resumo Executivo

Esta execução materializou a fundação persistente mínima do domínio canônico de Integrações sem migrar Sankhya, sem implementar jobs, health, alerts, policies ou adapters completos.

O foco foi:

- materializar enums oficiais;
- promover a base persistente de provider e config sem quebrar compatibilidade;
- criar persistência canônica para credenciais e versionamento;
- aplicar RLS nas tabelas tenant-scoped novas e evoluídas;
- validar a migration em ciclo completo.

## 2. Modelos implementados

### Arquivo novo

- [services/api/integracoes/models.py](/opt/lampp/htdocs/farm/services/api/integracoes/models.py)

Modelos materializados:

- `IntegrationScope`
- `IntegrationStatus`
- `MarketplaceIntegracao` promovido como catálogo de provider
- `TenantIntegracao` evoluído como configuração canônica por tenant/escopo
- `IntegrationCredential`
- `IntegrationVersion`

### Compatibilidade preservada

- [services/api/iot_integracao/new_holland/models/__init__.py](/opt/lampp/htdocs/farm/services/api/iot_integracao/new_holland/models/__init__.py)
  - passou a reexportar `MarketplaceIntegracao` e `TenantIntegracao` do domínio canônico
  - mantém `MarketplaceAvaliacao`, `IntegracaoNewHolland` e demais modelos legados

## 3. Migrations

### Migration criada

- [services/api/migrations/versions/20260701_integrations_domain_03a_foundation.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/20260701_integrations_domain_03a_foundation.py)

### O que a migration faz

- promove `marketplace_integracoes` com:
  - `provider_type`
  - `provider_definition`
  - `connection_schema`
  - `credential_schema`
  - `feature_schema`
  - `sync_schema`
  - `health_schema`
- evolui `tenant_integracoes` com:
  - `scope_type`
  - `scope_id`
  - `lifecycle_state`
  - `connection_payload`
  - `credential_ref_id`
  - `deleted_at`
- cria:
  - `integration_credentials`
  - `integration_versions`

### Robustez implementada

A migration foi escrita para suportar dois cenários:

- tabelas legadas `marketplace_integracoes` e `tenant_integracoes` já existentes;
- tabelas legadas ausentes no banco atual.

Quando ausentes, a migration cria as bases compatíveis antes de aplicar a evolução canônica.

## 4. Enums

### `IntegrationScope`

Valores materializados:

- `PLATFORM`
- `TENANT`
- `ESTABELECIMENTO`
- `USUARIO`

### `IntegrationStatus`

Valores materializados:

- `NOT_CONFIGURED`
- `CONFIGURED`
- `VALIDATING`
- `VALID`
- `INVALID`
- `ACTIVE`
- `SYNCING`
- `PARTIALLY_DEGRADED`
- `DEGRADED`
- `SUSPENDED`
- `DISABLED`
- `REVOKED`
- `REMOVED`

## 5. Constraints

Foram implementados:

- FK de `tenant_integracoes.credential_ref_id` para `integration_credentials.id`
- FK de `integration_credentials.provider_id` para `marketplace_integracoes.id`
- FK de `integration_versions.config_id` para `tenant_integracoes.id`
- FK de `integration_versions.credential_ref_id` para `integration_credentials.id`
- `check constraint` para `scope_type`
- `check constraint` para `lifecycle_state`
- `check constraint` para `version_number >= 1`
- `unique constraint` em `integration_credentials` por tenant/provider/scope/version
- `unique constraint` em `integration_versions` por `config_id + version_number`
- índices de tenant, provider, scope, lifecycle e relacionamentos

## 6. RLS

RLS foi aplicado em todas as tabelas tenant-scoped desta foundation:

- `tenant_integracoes`
- `integration_credentials`
- `integration_versions`

Regras aplicadas:

- `ENABLE ROW LEVEL SECURITY`
- `FORCE ROW LEVEL SECURITY`
- policies de `SELECT`
- policies de `INSERT`
- policies de `UPDATE`
- policies de `DELETE`

Como `tenant_id` dessas tabelas permanece legado em `String(50)`, a policy compara com:

- `current_setting('app.current_tenant_id', true)::text`

Isso preserva compatibilidade com a base existente sem introduzir migração de UUID nesta fase.

## 7. Compatibilidade

### Sankhya

Compatibilidade preservada:

- [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py)
- nenhum comportamento funcional do Sankhya foi alterado
- `SankhyaConfig` continua existindo
- `SankhyaSyncLog` continua provider-specific
- nenhuma rota Sankhya foi quebrada

### TenantIntegracao

Compatibilidade preservada:

- `status`
- `configuracoes`
- `credenciais`
- `webhook_url`
- `webhook_secret`
- `ultima_sincronizacao`
- `total_sincronizacoes`

Campos novos foram adicionados sem remover os antigos.

### MarketplaceIntegracao

Compatibilidade preservada:

- `slug`
- `categoria`
- `fornecedor`
- `requisitos`
- `configuracoes`
- estatísticas e URLs existentes

Os campos canônicos de provider definition foram adicionados sem remover o shape legado.

## 8. Testes

### Teste novo

- [services/api/tests/unit/integracoes/test_integrations_foundation_models.py](/opt/lampp/htdocs/farm/services/api/tests/unit/integracoes/test_integrations_foundation_models.py)

### Cobertura adicionada

- estabilidade de `IntegrationScope`
- estabilidade de `IntegrationStatus`
- colunas canônicas em `TenantIntegracao`
- persistência básica de provider, credential, config e version
- criptografia e masking com `integracoes/security.py`
- ausência de segredo em texto puro no snapshot versionado
- presença de RLS na migration
- compatibilidade do reexport em `iot_integracao/new_holland/models`
- preservação de `SankhyaConfig` e `SankhyaSyncLog`

### Validações executadas

- `services/api/.venv/bin/pytest services/api/tests/unit/integracoes -q`
- `services/api/.venv/bin/python -m ruff check services/api/integracoes/models.py services/api/iot_integracao/new_holland/models/__init__.py services/api/tests/unit/integracoes/test_integrations_foundation_models.py services/api/migrations/versions/20260701_integrations_domain_03a_foundation.py`
- `cd services/api && .venv/bin/alembic upgrade head`
- `cd services/api && .venv/bin/alembic downgrade -1`
- `cd services/api && .venv/bin/alembic upgrade head`

## 9. Limitações

Itens deliberadamente fora desta fase:

- `IntegrationJob`
- `IntegrationHealth`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- adapters canônicos
- migração do Sankhya para o canônico
- alertas
- observabilidade de integração
- scheduler/worker de sync

Limitações técnicas restantes:

- `tenant_id` continua textual nesta parte do domínio por compatibilidade histórica;
- `tenant_integracoes` ainda carrega campos legados (`configuracoes`, `credenciais`) além do shape canônico novo;
- `marketplace_integracoes` ainda mantém carga semântica de marketplace além do papel de catálogo de provider.

## 10. Próxima execução

Próxima execução recomendada:

`INTEGRATIONS-DOMAIN-03B`

Ela deve atacar:

- `IntegrationJob`
- `IntegrationHealth`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- integração com Outbox sem duplicação
- integração com Alert Engine e Notification Engine
- primeiros adapters canônicos de provider
- início da convergência controlada do Sankhya para o modelo canônico
