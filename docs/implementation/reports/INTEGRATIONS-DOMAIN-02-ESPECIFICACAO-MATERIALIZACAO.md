# INTEGRATIONS-DOMAIN-02 — Especificação de Materialização do Domínio Oficial de Integrações

## 1. Resumo Executivo

O domínio oficial de Integrações não deve ser implementado do zero.

A auditoria anterior mostrou que o AgroSaaS já possui:

- infraestrutura transversal madura;
- componentes parciais reutilizáveis;
- um provider real em produção arquitetural, o Sankhya;
- base suficiente para materialização incremental sem big bang.

Esta especificação define que a materialização deve seguir quatro princípios:

- promover sementes já existentes antes de criar novas tabelas;
- separar claramente oficial de provider-specific;
- reutilizar integralmente Outbox, Alert Engine, Notification Engine, auditoria, RLS e segurança de segredos;
- preservar compatibilidade com Sankhya durante toda a transição.

O domínio futuro será composto por:

- catálogo de providers;
- definição declarativa por provider;
- configuração oficial por escopo;
- envelopes de connection e credential;
- feature enablement;
- sync policy;
- health;
- job/log/version;
- adapters provider-specific.

## 2. Decisão de Reaproveitamento

| Item | Decisão | Justificativa |
| --- | --- | --- |
| `MarketplaceIntegracao` | PROMOVER | Já atua como catálogo de integrações e é a melhor semente para `IntegrationProvider`, apesar do acoplamento comercial atual. |
| `TenantIntegracao` | PROMOVER | Já é a melhor semente de `IntegrationConfig` tenant-scoped, com `configuracoes`, `credenciais` e `status`. |
| `SankhyaConfig` | MANTER PROVIDER-SPECIFIC | Deve continuar existindo temporariamente como adapter/provider config até o oficial absorver a configuração comum. |
| `SankhyaSyncLog` | MANTER PROVIDER-SPECIFIC | Continua como log operacional específico do provider enquanto `IntegrationLog` e `IntegrationJob` não estiverem materializados. |
| `DomainEventOutbox` | REUTILIZAR | É a infraestrutura oficial de eventos e execução assíncrona. Não deve ser duplicada. |
| `OperationalAlert` | REUTILIZAR | É o mecanismo oficial de alertas operacionais. |
| `Notificacao` | REUTILIZAR | É a camada oficial de entrega/notificação. |
| `TenantAuditLog` | REUTILIZAR | Continua sendo a trilha de auditoria administrativa do tenant. |
| `AdminAuditLog` | REUTILIZAR | Continua sendo a trilha de suporte/backoffice. |
| `integracoes/security.py` | NÃO ALTERAR | Já resolve criptografia, masking e compatibilidade legada de segredos. Deve ser o utilitário oficial do domínio. |

## 3. Modelos Oficiais Propostos

### 3.1 `IntegrationProvider`

- criar tabela nova: não inicialmente;
- reaproveitar tabela existente: sim, promover `marketplace_integracoes`;
- destino: adapter evolutivo;
- observação: a tabela atual deve perder protagonismo de marketplace e virar catálogo oficial ao longo da implementação.

### 3.2 `IntegrationProviderDefinition`

- criar tabela nova: não obrigatoriamente na fase inicial;
- destino recomendado: JSON schema versionado associado ao provider;
- materialização sugerida inicial: coluna/estrutura declarativa no provider promovido;
- observação: não precisa nascer em tabela isolada se o schema puder viver no provider.

### 3.3 `IntegrationConfig`

- criar tabela nova: sim;
- reaproveitar tabela existente: parcialmente, via evolução de `tenant_integracoes`;
- observação: a recomendação é evoluir `tenant_integracoes` para o papel de configuração oficial, em vez de criar tabela totalmente paralela.

### 3.4 `IntegrationConnection`

- criar tabela nova: não na primeira fase;
- destino recomendado: envelope estruturado dentro de `IntegrationConfig`;
- forma: JSON validado por provider definition;
- observação: parâmetros não secretos devem sair do provider-specific e convergir para esse envelope.

### 3.5 `IntegrationCredential`

- criar tabela nova: sim;
- motivo: separar segredo de config comum;
- observação: segredos não devem continuar misturados com configuração comum no modelo oficial.

### 3.6 `IntegrationFeature`

- criar tabela nova: opcional;
- destino recomendado: tabela filha por config ou JSON estruturado;
- recomendação: iniciar como tabela filha, para permitir enablement granular por feature sem ambiguidade.

### 3.7 `IntegrationSyncPolicy`

- criar tabela nova: sim;
- motivo: política operacional por feature não deve ficar implícita;
- observação: manual, agendado, webhook, evento/outbox, pull, push devem ser materializados explicitamente.

### 3.8 `IntegrationHealth`

- criar tabela nova: sim, preferencialmente como snapshot operacional;
- alternativa: view/materialização derivada na fase inicial;
- recomendação: começar com tabela simples de snapshot para não depender apenas de cálculo em tempo real.

### 3.9 `IntegrationJob`

- criar tabela nova: sim, mas sem duplicar Outbox;
- observação: o job é o registro operacional da sincronização; o Outbox continua sendo o transporte/evento.

### 3.10 `IntegrationLog`

- criar tabela nova: não imediatamente;
- materialização recomendada: adapter/view unificada sobre `IntegrationJob`, `SankhyaSyncLog`, audit logs e eventos operacionais;
- observação: não criar nova tabela de log genérico antes de entender o formato mínimo comum.

### 3.11 `IntegrationVersion`

- criar tabela nova: sim;
- motivo: auditoria e versionamento não são a mesma coisa;
- observação: precisa guardar snapshots versionados, não apenas before/after administrativo.

### 3.12 `IntegrationScope`

- criar tabela nova: não;
- destino recomendado: enum oficial persistido nos modelos oficiais;
- valores oficiais: `PLATFORM`, `TENANT`, `ESTABELECIMENTO`, `USUARIO`.

### 3.13 `IntegrationStatus`

- criar tabela nova: não;
- destino recomendado: enum oficial persistido em `IntegrationConfig`, `IntegrationJob` e `IntegrationHealth`;
- observação: status e lifecycle devem ser contratos explícitos.

## 4. Fronteira Oficial × Provider-Specific

### 4.1 Fica no domínio oficial

- provider;
- provider definition;
- scope;
- lifecycle;
- status;
- connection envelope;
- credential envelope;
- feature enablement;
- sync policy;
- health snapshot;
- job operacional;
- versionamento;
- auditoria administrativa;
- integração com Outbox, Alert Engine e Notification Engine.

### 4.2 Fica no provider Sankhya

- `gateway_url`;
- `service_urls`;
- `company_code`;
- autenticação e handshake específicos do WS Sankhya;
- mapeamentos de pessoas, produtos, NFe e financeiro;
- formato de payload do Sankhya;
- detalhes de erro do WebService;
- tabelas espelho provider-specific já existentes;
- logs específicos do conector enquanto a unificação não for concluída.

### 4.3 Fica em futuros providers

- contratos técnicos específicos de autenticação;
- mapeamento de payloads próprios;
- webhooks/adapters específicos;
- traduções de feature para o protocolo do fornecedor;
- detalhes específicos de rate limit, retry e health.

## 5. Persistência Proposta

### 5.1 Estrutura sugerida

#### `integration_providers`

- origem inicial: evolução de `marketplace_integracoes`;
- campos principais:
  - `id`
  - `slug`
  - `nome`
  - `categoria`
  - `provider_type`
  - `ativo`
  - `oficial`
  - `versao`
  - `definition_schema`
  - `created_at`
  - `updated_at`

#### `integration_configs`

- origem inicial: evolução de `tenant_integracoes`;
- campos principais:
  - `id`
  - `tenant_id`
  - `scope_type`
  - `scope_id`
  - `provider_id`
  - `status`
  - `lifecycle_state`
  - `connection_payload`
  - `credential_ref_id`
  - `health_status`
  - `enabled_at`
  - `disabled_at`
  - `last_validated_at`
  - `created_at`
  - `updated_at`
  - `deleted_at`

#### `integration_credentials`

- tabela nova;
- campos principais:
  - `id`
  - `tenant_id`
  - `provider_id`
  - `scope_type`
  - `scope_id`
  - `credential_payload_encrypted`
  - `mask_metadata`
  - `version_number`
  - `active`
  - `created_by`
  - `rotated_at`
  - `created_at`
  - `updated_at`

#### `integration_features`

- tabela nova;
- campos principais:
  - `id`
  - `config_id`
  - `feature_code`
  - `enabled`
  - `settings_payload`
  - `created_at`
  - `updated_at`

#### `integration_sync_policies`

- tabela nova;
- campos principais:
  - `id`
  - `config_id`
  - `feature_code`
  - `mode`
  - `schedule_expression`
  - `batch_size`
  - `retry_policy`
  - `backoff_policy`
  - `priority`
  - `idempotency_strategy`
  - `created_at`
  - `updated_at`

#### `integration_health_snapshots`

- tabela nova;
- campos principais:
  - `id`
  - `tenant_id`
  - `config_id`
  - `provider_id`
  - `status`
  - `details_payload`
  - `last_success_at`
  - `last_failure_at`
  - `generated_at`

#### `integration_jobs`

- tabela nova;
- campos principais:
  - `id`
  - `tenant_id`
  - `config_id`
  - `provider_id`
  - `feature_code`
  - `job_type`
  - `status`
  - `trigger_type`
  - `outbox_event_id` opcional
  - `started_at`
  - `finished_at`
  - `retry_count`
  - `result_payload`
  - `error_payload`
  - `created_at`
  - `updated_at`

#### `integration_versions`

- tabela nova;
- campos principais:
  - `id`
  - `tenant_id`
  - `config_id`
  - `version_number`
  - `snapshot_payload`
  - `change_reason`
  - `created_by`
  - `created_at`

### 5.2 Regras obrigatórias de persistência

- toda tabela tenant-scoped deve ter `tenant_id`;
- `scope_type` e `scope_id` devem existir onde o escopo variar;
- ERP continua proibido em `UnidadeProdutiva`;
- `deleted_at` só onde fizer sentido operacional;
- `provider_id` deve existir em todo agregado operacional relevante;
- segredos não ficam em `integration_configs`.

## 6. Credenciais

### 6.1 Materialização

Segredos devem ficar exclusivamente em `IntegrationCredential`.

`IntegrationConfig` deve referenciar credencial ativa por `credential_ref_id`.

### 6.2 Requisitos obrigatórios

- reutilizar `services/api/integracoes/security.py`;
- criptografar antes de persistir;
- nunca retornar segredo bruto ao frontend;
- sempre expor apenas masking;
- registrar rotação sem expor valor;
- versionar credenciais;
- permitir manter credencial anterior até rotação concluída, se necessário;
- separar alteração de config comum de alteração de credencial.

### 6.3 Auditoria

- alteração administrativa continua em `TenantAuditLog` ou `AdminAuditLog`;
- versionamento de segredo usa `IntegrationVersion` para metadados seguros, nunca para snapshot com segredo em texto puro.

## 7. Jobs e Sync

### 7.1 Decisão oficial

`IntegrationJob` deve ser uma tabela própria.

`DomainEventOutbox` continua sendo apenas a infraestrutura de evento/transporte assíncrono.

### 7.2 Relação entre os dois

- sync manual pode criar `IntegrationJob` sem Outbox;
- sync agendado pode criar `IntegrationJob` e, quando necessário, enfileirar evento no Outbox;
- sync por evento deve usar Outbox para disparo;
- `IntegrationJob` guarda o ciclo operacional do trabalho;
- Outbox guarda a publicação/entrega do evento.

### 7.3 Regras para evitar duplicação

- não usar `IntegrationJob` como substituto de Outbox;
- não usar Outbox como histórico operacional completo do sync;
- `SankhyaSyncLog` permanece temporariamente como provider log até o adapter oficial existir.

## 8. Alertas e Notificações

### 8.1 Alertas

O domínio deve usar `OperationalAlert` e o Alert Engine existentes.

Casos esperados:

- credencial inválida;
- expiração próxima;
- falhas consecutivas;
- degradação;
- sync parado;
- backlog anormal;
- erro de autenticação;
- erro de configuração.

### 8.2 Notificações

Entrega deve continuar usando:

- `Notificacao`;
- `NotificacaoPreferencia`;
- Notification Engine já existente.

### 8.3 Regra

Não criar:

- `integration_alerts`;
- `integration_notifications`;
- dispatcher paralelo.

## 9. Auditoria e Versionamento

### 9.1 Auditoria

Continuar usando:

- `TenantAuditLog` para ações do cliente;
- `AdminAuditLog` para suporte/backoffice;
- `write_audit_log(...)` como helper transacional.

### 9.2 Versionamento

`IntegrationVersion` deve ser tabela própria.

Motivo:

- auditoria registra ação;
- versionamento registra snapshot comparável.

### 9.3 Modelo recomendado

- `TenantAuditLog` e `AdminAuditLog` continuam obrigatórios;
- `IntegrationVersion` guarda snapshots estruturados de config, features, policies e referências de credencial;
- segredos nunca entram em snapshot em texto puro.

## 10. RLS e Multi-Tenant

Regras obrigatórias:

- toda tabela tenant-scoped possui `tenant_id`;
- uso de `get_session()` com RLS;
- filtros por `tenant_id` permanecem como defesa complementar;
- escopos válidos continuam sendo `PLATFORM`, `TENANT`, `ESTABELECIMENTO`, `USUARIO`;
- ERP nunca por `UnidadeProdutiva`;
- `scope_type = ESTABELECIMENTO` só será ativado quando esse domínio administrativo existir formalmente;
- até lá, ERP permanece em `TENANT`.

## 11. Compatibilidade com Sankhya

### 11.1 Decisões

- `SankhyaConfig` será mantido temporariamente;
- `SankhyaConfig` passa a ser tratado como adapter/provider config legado;
- `SankhyaSyncLog` permanece provider-specific;
- rotas atuais continuam;
- frontend atual continua;
- não haverá migração big bang.

### 11.2 Estratégia

1. materializar primeiro o oficial.
2. criar adapters para leitura/escrita compatível.
3. somente depois mover Sankhya para consumir o oficial progressivamente.

### 11.3 Efeito prático

- dados antigos podem continuar onde estão inicialmente;
- Sankhya pode escrever temporariamente nos modelos legados e refletir no oficial por adapter;
- o frontend não precisa quebrar na fase inicial;
- a convergência será incremental, não disruptiva.

## 12. Plano Incremental

### Fase 1 — Enums e contratos

- materializar `IntegrationScope`;
- materializar `IntegrationStatus`;
- materializar lifecycle oficial;
- definir contratos de payload para connection, credential, feature e sync policy.

### Fase 2 — Provider e config genéricos

- promover `marketplace_integracoes` para catálogo oficial;
- evoluir `tenant_integracoes` para `IntegrationConfig`;
- introduzir `scope_type` e `scope_id`;
- manter compatibilidade com o que já existe.

### Fase 3 — Credential, version e health

- criar `integration_credentials`;
- criar `integration_versions`;
- criar `integration_health_snapshots`;
- conectar tudo a `integracoes/security.py`.

### Fase 4 — Jobs e policies

- criar `integration_sync_policies`;
- criar `integration_jobs`;
- integrar com Outbox sem duplicação.

### Fase 5 — Adapters Sankhya

- manter rotas e contratos atuais;
- criar adapter oficial para Sankhya;
- reduzir dependência direta de `SankhyaConfig`.

### Fase 6 — Observabilidade e provider adicional

- conectar jobs/health/alerts ao Alert Engine e observabilidade existente;
- validar a arquitetura com um segundo provider não-ERP.

## 13. Riscos

Principais riscos:

- duplicar infraestrutura já existente;
- acoplar o domínio oficial ao Sankhya;
- criar tabelas demais cedo demais;
- quebrar RLS ao introduzir novas tabelas;
- expor segredo em snapshot/versionamento;
- confundir audit trail com versionamento;
- migrar Sankhya cedo demais;
- transformar `IntegrationLog` em tabela redundante;
- usar `UnidadeProdutiva` como escopo indevido de ERP.

## 14. Critérios para Implementação

`INTEGRATIONS-DOMAIN-03` só deve começar quando estes critérios estiverem explícitos e aceitos:

- promoção de `MarketplaceIntegracao` e `TenantIntegracao` aprovada;
- decisão sobre criação de `integration_credentials` aprovada;
- fronteira oficial × provider-specific congelada;
- estratégia de compatibilidade com Sankhya aprovada;
- regra de uso obrigatório de `get_session()` e RLS confirmada;
- regra de reaproveitamento de Outbox, Alert Engine, Notification Engine e audit logs confirmada;
- nomenclatura final das tabelas oficiais aprovada;
- lifecycle e enums considerados estáveis.

## 15. Próxima Execução

Próxima execução recomendada:

`INTEGRATIONS-DOMAIN-03 — Foundation Persistente do Domínio Oficial de Integrações`

Essa execução deve se limitar a:

- enums oficiais;
- evolução controlada de provider/config;
- tabela de credenciais;
- tabela de versionamento;
- constraints multi-tenant e RLS;
- sem migração disruptiva do Sankhya na primeira etapa.
