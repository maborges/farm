# INTEGRATIONS-DOMAIN-03B — Operação Oficial do Domínio de Integrações

## 1. Resumo Executivo

Esta execução materializou a camada operacional genérica do domínio oficial de Integrações sem convergir o provider Sankhya e sem criar infraestrutura paralela de fila, alerta, notificação ou auditoria.

Foram adicionados:

- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationJob`
- `IntegrationHealth`
- contratos oficiais de eventos do domínio
- migration operacional com constraints e RLS
- testes unitários/estáticos da camada operacional

## 2. Componentes Materializados

### Modelos

- `services/api/integracoes/models.py`
  - `IntegrationFeature`
  - `IntegrationSyncPolicy`
  - `IntegrationJob`
  - `IntegrationHealth`
  - enums:
    - `IntegrationSyncMode`
    - `IntegrationPolicyPriority`
    - `IntegrationJobStatus`
    - `IntegrationJobTrigger`
    - `IntegrationHealthStatus`

### Eventos oficiais

- `services/api/integracoes/events.py`
  - `IntegrationConfigured`
  - `IntegrationActivated`
  - `IntegrationDisabled`
  - `IntegrationCredentialRotated`
  - `IntegrationSyncStarted`
  - `IntegrationSyncCompleted`
  - `IntegrationSyncFailed`
  - `IntegrationHealthChanged`

### Migration

- `services/api/migrations/versions/20260701_integrations_domain_03b_operations.py`

## 3. Modelos

### `IntegrationFeature`

Representa capacidades habilitadas por configuração, desacopladas de provider específico.

Campos principais:

- `tenant_id`
- `config_id`
- `provider_id`
- `codigo`
- `nome`
- `habilitada`
- `obrigatoria`
- `settings_payload`

### `IntegrationSyncPolicy`

Representa a política operacional de sincronização por feature.

Campos principais:

- `mode`
- `prioridade`
- `retry_ativo`
- `retry_limite`
- `batch_size`
- `backoff_seconds`
- `timeout_seconds`
- `idempotencia_ativa`
- `trigger_expression`

### `IntegrationJob`

Representa a execução operacional do sync.

Campos principais:

- `status`
- `trigger_type`
- `outbox_event_id`
- `correlation_id`
- `causation_id`
- `retry_count`
- `processados`
- `sucessos`
- `erros`
- `request_payload`
- `result_payload`

### `IntegrationHealth`

Representa snapshot persistente do estado operacional.

Campos principais:

- `status`
- `summary`
- `details_payload`
- `latency_ms`
- `consecutive_failures`
- `last_success_at`
- `last_failure_at`
- `rate_limited_until`
- `checked_at`

## 4. Relação com Outbox

`IntegrationJob` não substitui `DomainEventOutbox`.

Decisão aplicada:

- `DomainEventOutbox` continua sendo a infraestrutura de transporte de eventos.
- `IntegrationJob` representa a execução operacional da sincronização.
- o vínculo entre os dois é opcional via `outbox_event_id`.

Isso preserva a arquitetura definida em `INTEGRATIONS-LIFECYCLE-01` e evita segunda fila paralela.

## 5. Relação com Alert Engine

Foi adicionado o domínio `INTEGRATIONS` ao enum `Domain` do Alert Engine em:

- `services/api/alert_engine/models.py`

Não foi criado engine paralelo de alertas.

O domínio de Integrações passa a poder emitir eventos oficiais compatíveis com a infraestrutura existente para cenários como:

- credencial inválida
- sync falho
- health degradado
- indisponibilidade do provider

## 6. Relação com Notification Engine

Nenhuma infraestrutura de notificação foi duplicada.

Decisão preservada:

- Integrações continua consumindo `Notificacao` e `Notification Dispatcher` existentes por meio dos eventos oficiais.
- não foi criado `integration_notifications`.

## 7. Relação com Auditoria

Nenhum audit log específico foi criado.

Decisão preservada:

- `TenantAuditLog`
- `AdminAuditLog`
- `write_audit_log(...)`

continuam sendo a infraestrutura oficial de auditoria do domínio.

## 8. Eventos Oficiais

Os contratos adicionados em `services/api/integracoes/events.py` formalizam os fatos operacionais mínimos:

- configuração
- ativação
- desativação
- rotação de credencial
- início de sync
- conclusão de sync
- falha de sync
- mudança de health

Todos permanecem genéricos, sem acoplamento ao Sankhya.

## 9. Compatibilidade

Compatibilidade preservada:

- `SankhyaConfig` não foi migrado
- `SankhyaSyncLog` não foi migrado
- nenhuma rota Sankhya foi alterada
- nenhum adapter de provider foi criado
- `MarketplaceIntegracao` e `TenantIntegracao` seguem compatíveis

## 10. Testes

Arquivo criado:

- `services/api/tests/unit/integracoes/test_integrations_operational_models.py`

Cobertura adicionada:

- estabilidade dos enums operacionais
- colunas oficiais dos modelos
- persistência básica de `Feature` e `SyncPolicy`
- vínculo opcional com Outbox
- domínio `INTEGRATIONS` no Alert Engine
- contratos oficiais de eventos
- ausência de infraestrutura paralela de notificações e auditoria
- RLS e constraints na migration
- import dos modelos no metadata do Alembic
- preservação do Sankhya como provider-specific
- relacionamentos básicos dos modelos

## 11. Limitações

Continuam fora desta fase:

- adapters de provider
- convergência do Sankhya para o domínio oficial
- `IntegrationFeature` automática por provider
- `IntegrationHealth` calculado por runtime
- scheduler próprio do domínio
- automação de alertas/notificações

Também permanece uma limitação de lint fora do escopo novo:

- `services/api/migrations/env.py`
- `services/api/alert_engine/models.py`

esses arquivos já possuem dívida preexistente ampla e não foram normalizados integralmente nesta execução.

## 12. Próxima Execução

Próxima execução recomendada:

**`SANKHYA-DOMAIN-01`**

Objetivo recomendado:

- adaptar o provider Sankhya para consumir `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationJob` e `IntegrationHealth` sem quebra funcional
- iniciar convergência incremental de `SankhyaConfig` e `SankhyaSyncLog`
- passar a emitir eventos oficiais reais durante sync e health
