# SANKHYA-DOMAIN-01 — Adapter Oficial Sankhya

## 1. Resumo Executivo

Esta execução iniciou a convergência incremental do provider Sankhya para o domínio oficial de Integrações sem remover `SankhyaConfig`, sem remover `SankhyaSyncLog` e sem quebrar rotas existentes.

Foi criada uma camada complementar responsável por:

- localizar ou criar a configuração oficial do Sankhya;
- garantir features padrão do provider;
- garantir policies padrão do provider;
- criar `IntegrationJob` durante syncs existentes;
- atualizar `IntegrationHealth`;
- emitir eventos oficiais;
- preservar integralmente a compatibilidade do provider-specific legado.

## 2. Arquivos alterados

- `services/api/integracoes/sankhya/services/canonical_adapter.py`
- `services/api/integracoes/sankhya/services/sync_service.py`
- `services/api/integracoes/sankhya/services/nfe_financeiro_service.py`
- `services/api/integracoes/sankhya/services/__init__.py`
- `services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py`
- `services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`

## 3. Adapter criado

Arquivo:

- `services/api/integracoes/sankhya/services/canonical_adapter.py`

Responsabilidades implementadas:

- `sync_provider_config(...)`
- `sync_connection_test(...)`
- `start_sync_job(...)`
- `finish_sync_job(...)`

O adapter usa como base provider-specific:

- `SankhyaConfig`
- `SankhyaSyncLog`

E sincroniza isso com o domínio oficial:

- `MarketplaceIntegracao`
- `TenantIntegracao`
- `IntegrationCredential`
- `IntegrationVersion`
- `IntegrationFeature`
- `IntegrationSyncPolicy`
- `IntegrationJob`
- `IntegrationHealth`

## 4. Features oficiais Sankhya

Features garantidas:

- `pessoas`
- `produtos`
- `financeiro`
- `nfe`
- `pedidos`
- `estoque`

Decisão aplicada:

- `pessoas`, `produtos`, `financeiro` e `nfe` nascem habilitadas;
- `pedidos` e `estoque` permanecem desabilitadas como preparação futura;
- nenhuma nova sincronização funcional foi implementada para as features futuras.

## 5. Sync Policies

Policies oficiais garantidas:

- `pessoas` → `MANUAL`, com suporte declarado para `MANUAL` e `AGENDADO`
- `produtos` → `MANUAL`, com suporte declarado para `MANUAL` e `AGENDADO`
- `financeiro` → `PULL`, com suporte declarado para `MANUAL`, `AGENDADO` e `PULL`
- `nfe` → `PULL`, com suporte declarado para `MANUAL`, `AGENDADO` e `PULL`
- `pedidos` → `EVENTO`, marcado como futuro com transporte `OUTBOX`
- `estoque` → `EVENTO`, marcado como futuro com transporte `OUTBOX`

## 6. IntegrationJob

Os syncs existentes passaram a criar `IntegrationJob` oficial como camada complementar.

Mapeamento aplicado:

- início de sync → `RUNNING`
- fim com sucesso → `SUCCESS`
- fim com falha → `FAILED`

Integrações conectadas:

- sync legado de `pessoas`
- sync legado de `produtos`
- exportação/importação de `nfe`
- exportação/importação de `financeiro`

`SankhyaSyncLog` continua existindo e continua sendo escrito.

## 7. IntegrationHealth

O adapter passou a manter snapshot oficial em `IntegrationHealth`.

Atualizações cobertas:

- teste de conexão;
- sucesso recente de sync;
- falha recente de sync;
- falhas consecutivas;
- último job associado.

Estados utilizados nesta etapa:

- `CONNECTED`
- `DISCONNECTED`
- `DEGRADED`
- `AUTH_ERROR`
- `CONFIG_ERROR`
- `PARTIAL_FAILURE`
- `RATE_LIMITED`

## 8. Eventos oficiais

Eventos emitidos pelo adapter:

- `IntegrationConfigured`
- `IntegrationCredentialRotated`
- `IntegrationSyncStarted`
- `IntegrationSyncCompleted`
- `IntegrationSyncFailed`
- `IntegrationHealthChanged`

Implementação:

- reuso de `publish_domain_event_safe(...)`
- nenhuma fila paralela criada
- nenhum Alert Engine paralelo criado
- nenhuma infraestrutura paralela de notificação criada

## 9. Compatibilidade preservada

Compatibilidades preservadas explicitamente:

- `SankhyaConfig` continua fonte provider-specific;
- `SankhyaSyncLog` continua existindo;
- rotas FastAPI do Sankhya não foram quebradas;
- payloads públicos não foram alterados de forma incompatível;
- escopo continua `TENANT`;
- não foi introduzido escopo `UnidadeProdutiva`;
- nenhum provider novo foi criado.

## 10. Testes executados

Executado:

- `services/api/.venv/bin/pytest services/api/tests/unit/integracoes -q`
- `services/api/.venv/bin/ruff check services/api/integracoes/models.py services/api/integracoes/events.py services/api/integracoes/sankhya/services/canonical_adapter.py services/api/integracoes/sankhya/services/sync_service.py services/api/integracoes/sankhya/services/nfe_financeiro_service.py services/api/integracoes/sankhya/services/__init__.py services/api/tests/unit/integracoes/test_sankhya_canonical_adapter.py services/api/tests/unit/integracoes/test_sankhya_governed_integration.py`
- `./.venv/bin/alembic upgrade head`
- `git diff --check`

Resultado:

- `50 passed`
- `ruff` sem violações no escopo alterado
- Alembic íntegro em `head`

## 11. Limitações

Ainda não foi feito:

- migração de dados de `SankhyaConfig` para `TenantIntegracao`;
- substituição de `SankhyaSyncLog` por `IntegrationJob`;
- uso real de `outbox_event_id` nos jobs Sankhya;
- automação explícita de Alert Engine para Integrações;
- dashboards específicos do health oficial;
- convergência do frontend para exibir `IntegrationHealth` e `IntegrationJob`.

## 12. Próxima execução recomendada

Próxima execução recomendada:

**`SANKHYA-DOMAIN-02`**

Escopo recomendado:

- adaptar rotas e consultas para ler status oficial sem remover status legado;
- começar a expor health e jobs oficiais na API Sankhya;
- mapear logs legados e jobs oficiais na mesma experiência operacional;
- preparar migração progressiva de leitura do frontend para o domínio oficial.
