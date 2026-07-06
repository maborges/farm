# INTEGRATIONS-DOMAIN-01 — Auditoria de Materialização do Domínio Oficial de Integrações

## 1. Resumo Executivo

O AgroSaaS já possui uma base técnica relevante para sustentar o domínio oficial de Integrações, mas essa base ainda está fragmentada entre módulos específicos, principalmente `integracoes.sankhya`, `iot_integracao`, `events`, `alert_engine`, `notificacoes` e `core`.

A conclusão da auditoria é:

- a infraestrutura transversal já existe e é forte;
- a modelagem oficial do domínio de Integrações ainda não existe como domínio unificado;
- parte importante do que foi arquitetado já existe de forma parcial e reutilizável;
- o maior risco futuro é criar novos modelos paralelos para config, credencial, jobs, logs, health, alertas e auditoria, duplicando capacidades já existentes.

Em termos práticos:

- `IntegrationProvider` e `IntegrationConfig` já possuem equivalentes parciais;
- `IntegrationCredential`, `IntegrationLog` e `IntegrationJob` também possuem base parcial;
- `IntegrationProviderDefinition`, `IntegrationFeature`, `IntegrationSyncPolicy`, `IntegrationVersion`, `IntegrationScope` e `IntegrationStatus` ainda não estão materializados como contratos oficiais;
- Outbox, Alert Engine, Notification Engine, auditoria, RLS e segurança de segredos devem ser reaproveitados, não recriados.

## 2. Estado Atual

O estado atual tem dois blocos bem diferentes:

- infraestrutura transversal madura;
- modelagem de integração ainda provider-centric.

Infraestrutura madura já existente:

- eventos transacionais com Outbox, retry, backlog, health e observabilidade;
- Alert Engine desacoplado, multi-tenant e orientado a scheduler;
- Notification Engine já separado do domínio original;
- logs de auditoria de tenant e de backoffice;
- sessão com RLS por tenant;
- utilitário de criptografia/masking de segredos de integração;
- RBAC de tenant e backoffice já em uso na integração Sankhya.

Materialização de domínio ainda incompleta:

- Sankhya tem modelagem própria e funcional;
- IoT possui catálogos e vínculos genéricos parcialmente reutilizáveis;
- não existe um namespace oficial único para providers, configs, credentials, features, lifecycle, health e jobs;
- ainda não existe um contrato genérico persistente que governe todos os providers.

## 3. Evidências

### 3.1 Arquitetura e governança

- [docs/architecture/INTEGRATIONS-ARCH-01.md](/opt/lampp/htdocs/farm/docs/architecture/INTEGRATIONS-ARCH-01.md)
- [docs/architecture/INTEGRATIONS-ARCH-02.md](/opt/lampp/htdocs/farm/docs/architecture/INTEGRATIONS-ARCH-02.md)
- [docs/architecture/INTEGRATIONS-LIFECYCLE-01.md](/opt/lampp/htdocs/farm/docs/architecture/INTEGRATIONS-LIFECYCLE-01.md)
- [docs/implementation/reports/SANKHYA-GOV-02-CORRECAO-GOVERNADA-INTEGRACAO-SANKHYA.md](/opt/lampp/htdocs/farm/docs/implementation/reports/SANKHYA-GOV-02-CORRECAO-GOVERNADA-INTEGRACAO-SANKHYA.md)

### 3.2 Modelos e tabelas já existentes

- [services/api/integracoes/sankhya/models/__init__.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/models/__init__.py)
  - `SankhyaConfig`
  - `SankhyaSyncLog`
  - `SankhyaPessoa`
  - `SankhyaProduto`
  - `SankhyaNFe`
  - `SankhyaLancamentoFinanceiro`
- [services/api/iot_integracao/new_holland/models/__init__.py](/opt/lampp/htdocs/farm/services/api/iot_integracao/new_holland/models/__init__.py)
  - `MarketplaceIntegracao`
  - `TenantIntegracao`
  - `IntegracaoNewHolland`
- [services/api/migrations/versions/fase3_sankhya.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/fase3_sankhya.py)
  - cria `sankhya_config`, `sankhya_sync_logs` e tabelas provider-specific
- [services/api/migrations/versions/fase3_sprints26_34.py](/opt/lampp/htdocs/farm/services/api/migrations/versions/fase3_sprints26_34.py)
  - cria `marketplace_integracoes`, `tenant_integracoes` e `integracao_new_holland`

### 3.3 Infraestrutura reutilizável

- [services/api/events/outbox_model.py](/opt/lampp/htdocs/farm/services/api/events/outbox_model.py)
  - `DomainEventOutbox`, `DomainEventOutboxStatus`
- [services/api/events/outbox_service.py](/opt/lampp/htdocs/farm/services/api/events/outbox_service.py)
  - `DomainEventOutboxService`
  - idempotência por `tenant_id + idempotency_key`
  - `SET LOCAL app.current_tenant_id`
- [services/api/events/outbox_worker.py](/opt/lampp/htdocs/farm/services/api/events/outbox_worker.py)
  - worker CLI, loops, métricas, health, backlog
- [services/api/events/outbox_observability.py](/opt/lampp/htdocs/farm/services/api/events/outbox_observability.py)
  - snapshot, métricas e health do pipeline
- [services/api/alert_engine/models.py](/opt/lampp/htdocs/farm/services/api/alert_engine/models.py)
  - `OperationalAlert`, `AlertLifecycleEvent`, `AlertInsight`
- [services/api/alert_engine/scheduler.py](/opt/lampp/htdocs/farm/services/api/alert_engine/scheduler.py)
  - scheduler multi-tenant por tenant/unidade
- [services/api/notificacoes/models.py](/opt/lampp/htdocs/farm/services/api/notificacoes/models.py)
  - `Notificacao`, `NotificacaoPreferencia`
- [services/api/core/models/tenant_audit_log.py](/opt/lampp/htdocs/farm/services/api/core/models/tenant_audit_log.py)
  - `TenantAuditLog`
- [services/api/core/models/admin_audit_log.py](/opt/lampp/htdocs/farm/services/api/core/models/admin_audit_log.py)
  - `AdminAuditLog`
- [services/api/core/services/audit_service.py](/opt/lampp/htdocs/farm/services/api/core/services/audit_service.py)
  - `write_audit_log(...)`
- [services/api/core/dependencies.py](/opt/lampp/htdocs/farm/services/api/core/dependencies.py)
  - `get_session(...)`
  - `get_tenant_id(...)`
  - `SET LOCAL app.current_tenant_id`

### 3.4 Segurança de credenciais

- [services/api/integracoes/security.py](/opt/lampp/htdocs/farm/services/api/integracoes/security.py)
  - `encrypt_integration_secret(...)`
  - `decrypt_integration_secret(...)`
  - `mask_integration_secret(...)`
- [services/api/integracoes/sankhya/services/sync_service.py](/opt/lampp/htdocs/farm/services/api/integracoes/sankhya/services/sync_service.py)
  - criptografia ao persistir
  - masking na resposta

## 4. Componentes Reutilizáveis

### 4.1 Reutilizáveis imediatamente

| Componente | Situação | Evidências | Observação |
| --- | --- | --- | --- |
| Outbox transacional | Reutilizar | `events/outbox_model.py`, `events/outbox_service.py`, `events/outbox_worker.py` | Não criar mecanismo paralelo de eventos/sync |
| Observabilidade de pipeline | Reutilizar | `events/outbox_observability.py` | Serve como base para sync assíncrono |
| Alert Engine | Reutilizar | `alert_engine/models.py`, `alert_engine/scheduler.py` | Não criar `IntegrationAlert` paralelo se alertas puderem ser gerados no motor atual |
| Notification Engine | Reutilizar | `notificacoes/models.py` | Entrega de alertas/notificações já existe |
| Auditoria tenant/backoffice | Reutilizar | `core/models/tenant_audit_log.py`, `core/models/admin_audit_log.py`, `core/services/audit_service.py` | Não criar histórico administrativo paralelo |
| RLS / tenant session | Reutilizar | `core/dependencies.py`, `events/outbox_service.py` | Base para isolamento multi-tenant |
| Segurança de segredos | Reutilizar | `integracoes/security.py` | Base para `IntegrationCredential` |

### 4.2 Reutilizáveis com promoção de conceito

| Componente atual | Pode virar | Evidências | Observação |
| --- | --- | --- | --- |
| `MarketplaceIntegracao` | `IntegrationProvider` parcial | `iot_integracao/new_holland/models/__init__.py` | Já é catálogo, mas está acoplado a marketplace/comercial |
| `TenantIntegracao` | `IntegrationConfig` parcial | `iot_integracao/new_holland/models/__init__.py` | Já possui `tenant_id`, `configuracoes`, `credenciais`, `status` |
| `SankhyaConfig` | `IntegrationConfig` provider-specific | `integracoes/sankhya/models/__init__.py` | Funcional, mas não genérico |
| `SankhyaSyncLog` | `IntegrationLog` ou `IntegrationJob` parcial | `integracoes/sankhya/models/__init__.py` | Mais log de execução do que job oficial |

## 5. Componentes Parciais

### 5.1 Conceitos que já existem, mas não atendem integralmente

| Conceito | Classificação | Evidências | Lacuna principal |
| --- | --- | --- | --- |
| `IntegrationProvider` | EXISTE PARCIALMENTE | `MarketplaceIntegracao` em `iot_integracao/new_holland/models/__init__.py` | Mistura catálogo com marketplace e metadados comerciais |
| `IntegrationConfig` | EXISTE PARCIALMENTE | `TenantIntegracao`, `SankhyaConfig` | Implementações paralelas e provider-specific |
| `IntegrationConnection` | EXISTE PARCIALMENTE | `SankhyaConfig.ws_url`, `TenantIntegracao.configuracoes` | Não há contrato oficial separado |
| `IntegrationCredential` | EXISTE PARCIALMENTE | `SankhyaConfig.password`, `TenantIntegracao.credenciais`, `IntegracaoNewHolland.client_secret` | Persistência separada ainda não é padrão |
| `IntegrationHealth` | EXISTE PARCIALMENTE | campos `teste_status`, `ultimo_teste`, `ultimo_sync` em `SankhyaConfig`; métricas no outbox | Não existe entidade/contrato genérico |
| `IntegrationJob` | EXISTE PARCIALMENTE | `SankhyaSyncLog`, worker/outbox | Falta job oficial por feature/provider |
| `IntegrationLog` | EXISTE PARCIALMENTE | `SankhyaSyncLog`, audit logs | Falta unificação entre log operacional, auditoria e sync |
| `IntegrationEvent` | EXISTE PARCIALMENTE | `DomainEventOutbox` | Existe transporte, não contrato específico do domínio Integrações |
| `IntegrationStatus` | EXISTE PARCIALMENTE | `TenantIntegracao.status`, `IntegracaoNewHolland.status`, `SankhyaConfig.ativo/teste_status` | Falta enum/lifecycle oficial materializado |

## 6. Componentes Ausentes

| Conceito | Classificação | Evidências | Observação |
| --- | --- | --- | --- |
| `IntegrationProviderDefinition` | NÃO EXISTE | sem classe/model equivalente encontrada | Não há schema declarativo por provider |
| `IntegrationFeature` | NÃO EXISTE | sem model/enum oficial encontrado | Features hoje ficam implícitas ou ad hoc |
| `IntegrationSyncPolicy` | NÃO EXISTE | sem model/contract encontrado | Não há política genérica por feature |
| `IntegrationVersion` | NÃO EXISTE | apenas audit logs genéricos | Não há versionamento comparável de config |
| `IntegrationScope` | NÃO EXISTE | só existe na arquitetura documental | Não há enum/model persistente oficial |
| `IntegrationAlert` | NÃO APLICÁVEL como tabela própria | Alert Engine já existe | Deve reutilizar `OperationalAlert` |

## 7. Infraestrutura Reutilizável

### 7.1 Outbox, retry e idempotência

O domínio Integrações não precisa criar seu próprio mecanismo de fila transacional.

Evidências:

- `DomainEventOutbox` já possui `tenant_id`, `event_type`, `payload`, `attempts`, `status`, `idempotency_key`;
- `DomainEventOutboxService.enqueue(...)` já persiste com idempotência estável;
- `outbox_worker.py` já fornece operação contínua, status, stats, health e métricas;
- `outbox_observability.py` já entrega backlog, retries, throughput e health.

Decisão prática da auditoria:

- `IntegrationEvent` não deve nascer como nova infraestrutura de transporte;
- ele deve reutilizar o ecossistema de `events`.

### 7.2 Alertas e notificações

O domínio Integrações também não precisa de novo motor de alertas.

Evidências:

- `OperationalAlert` já modela alertas operacionais multi-tenant;
- `AlertSchedulerService` já roda geradores por tenant;
- `Notificacao` e `NotificacaoPreferencia` já permitem entrega desacoplada.

Decisão prática da auditoria:

- alertas de credencial expirada, sync parado, auth error e degradação devem entrar no Alert Engine;
- não criar `integration_alerts` paralela.

### 7.3 Auditoria

Alterações administrativas de integrações já possuem base para auditoria.

Evidências:

- `TenantAuditLog` cobre operações do tenant;
- `AdminAuditLog` cobre suporte/backoffice;
- `write_audit_log(...)` já serializa before/after.

Decisão prática da auditoria:

- não criar histórico administrativo duplicado;
- `IntegrationVersion` futura deve complementar, não substituir, a trilha de auditoria atual.

## 8. Gap Analysis

| Conceito | Existe | Reutilizar | Evoluir | Criar | Evidências |
| --- | --- | --- | --- | --- | --- |
| IntegrationProvider | Parcial | Sim | Sim | Não imediato | `MarketplaceIntegracao` |
| IntegrationProviderDefinition | Não | Não | Não | Sim | não encontrado |
| IntegrationConfig | Parcial | Sim | Sim | Sim, se unificar contratos | `TenantIntegracao`, `SankhyaConfig` |
| IntegrationConnection | Parcial | Sim | Sim | Sim, como contrato | `SankhyaConfig.ws_url`, `configuracoes` |
| IntegrationCredential | Parcial | Sim | Sim | Sim, como contrato | `password`, `credenciais`, `client_secret` |
| IntegrationFeature | Não | Não | Não | Sim | não encontrado |
| IntegrationSyncPolicy | Não | Não | Não | Sim | não encontrado |
| IntegrationHealth | Parcial | Sim | Sim | Sim, como visão oficial | `teste_status`, `ultimo_teste`, observability |
| IntegrationJob | Parcial | Sim | Sim | Sim, se precisar job de negócio | `SankhyaSyncLog`, outbox worker |
| IntegrationAlert | Parcial | Sim | Sim | Não como domínio paralelo | `OperationalAlert` |
| IntegrationVersion | Não | Parcial | Sim | Sim | `TenantAuditLog` apenas audit |
| IntegrationEvent | Parcial | Sim | Sim | Não como infra paralela | `DomainEventOutbox` |
| IntegrationLog | Parcial | Sim | Sim | Sim, se unificar visões | `SankhyaSyncLog`, audit logs |
| IntegrationScope | Não | Não | Não | Sim | só em docs |
| IntegrationStatus | Parcial | Sim | Sim | Sim | `status`, `ativo`, `teste_status` |

## 9. Plano de Materialização

### Fase 1 — Promoção de conceitos reutilizáveis

- promover `MarketplaceIntegracao` como ponto de partida para catálogo de providers;
- promover `TenantIntegracao` como ponto de partida para configuração genérica tenant-scoped;
- manter `SankhyaConfig` como adapter/provider-specific temporário;
- formalizar reaproveitamento obrigatório de `integracoes/security.py`, `TenantAuditLog`, `AdminAuditLog`, Outbox, Alert Engine e Notification Engine.

### Fase 2 — Contratos oficiais do domínio

- materializar `IntegrationProviderDefinition`;
- materializar `IntegrationScope`;
- materializar contratos de `Connection`, `Credential`, `Feature`, `SyncPolicy`, `Health`, `Status`;
- definir fronteira entre dados comuns do domínio e dados específicos do provider.

### Fase 3 — Encaixe governado do Sankhya

- adaptar Sankhya ao domínio oficial como provider ERP;
- separar mais claramente config genérica vs dados específicos do provider;
- preservar compatibilidade de rotas e serviço existentes.

### Fase 4 — Novos providers

- incorporar ERP adicionais, bancos, clima, satélite, comunicação e storage sem nova arquitetura;
- usar `ProviderDefinition` para evitar novos modelos fixos por provider sempre que possível.

## 10. Riscos

### 10.1 Riscos de duplicação

- criar nova tabela de alertas de integração;
- criar novo mecanismo de jobs/fila para sync;
- criar novo audit log específico de integração;
- criar novo secret manager paralelo;
- criar novo catálogo de providers sem aproveitar `MarketplaceIntegracao`;
- criar nova config oficial ignorando `TenantIntegracao` e `SankhyaConfig`.

### 10.2 Riscos de acoplamento errado

- promover Sankhya diretamente a modelo universal;
- acoplar o domínio oficial a ERP antes de suportar clima, satélite, IoT, comunicação e storage;
- confundir provider catalog com config do cliente;
- confundir log operacional com job de negócio;
- confundir audit trail com versionamento de configuração.

## 11. Recomendações

### 11.1 O que já existe e deve ser reutilizado

- infraestrutura de eventos, retry, backlog e health;
- Alert Engine e Notification Engine;
- auditoria de tenant e backoffice;
- mecanismo de sessão multi-tenant com RLS;
- utilitário de criptografia/masking;
- `MarketplaceIntegracao` e `TenantIntegracao` como sementes do domínio;
- `SankhyaConfig` e `SankhyaSyncLog` como adapters temporários do provider ERP.

### 11.2 O que deve apenas mudar de namespace ou ser promovido conceitualmente

- `MarketplaceIntegracao` para papel de provider catalog;
- `TenantIntegracao` para papel de configuração oficial tenant-scoped;
- `SankhyaSyncLog` para papel de evidência provider-specific conectada ao log/job oficial futuro.

### 11.3 O que precisa ser criado

- `IntegrationProviderDefinition`;
- `IntegrationScope`;
- contratos oficiais de `Feature`, `SyncPolicy`, `Health`, `Status`, `Version`;
- camada oficial de composição entre provider, config, connection e credential.

### 11.4 O que não deve ser criado

- novo outbox de integrações;
- novo scheduler genérico paralelo;
- novo sistema de alertas;
- novo sistema de notificações;
- novo mecanismo de auditoria;
- nova solução de segredos fora do utilitário já existente, salvo evolução compatível.

## 12. Próxima Execução

A próxima execução recomendada é:

`INTEGRATIONS-DOMAIN-02 — Especificação de Materialização do Domínio Oficial`

Ela deve:

- definir exatamente quais modelos atuais serão promovidos;
- definir quais tabelas novas são realmente necessárias;
- definir o encaixe de `MarketplaceIntegracao`, `TenantIntegracao`, `SankhyaConfig` e `SankhyaSyncLog`;
- impedir duplicação de infraestrutura já existente;
- preparar a implementação incremental do domínio sem quebrar Sankhya.

## Veredicto Final da Auditoria

A aderência entre arquitetura e implementação é parcial.

- a infraestrutura de suporte do domínio já existe em nível alto de maturidade;
- a modelagem oficial do domínio de Integrações ainda não foi materializada;
- o projeto está pronto para implementar o domínio oficial;
- essa implementação deve começar por promoção e unificação de conceitos já existentes, não por criação do zero.
