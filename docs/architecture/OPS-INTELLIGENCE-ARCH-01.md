# OPS-INTELLIGENCE-ARCH-01

## Arquitetura Recomendada do Motor de Inteligência Operacional

## Status

- Tipo: arquitetura alvo
- Escopo: auditoria e definição oficial
- Implementação: não iniciada neste documento

## Resumo Executivo

O AgroSaaS já possui infraestrutura transversal suficiente para suportar um motor global de inteligência operacional, mas essa infraestrutura está incompleta na camada de recomendações.

Hoje o projeto já tem:

- `Alert Engine` oficial com domínios, categorias, severidades, prioridade, deduplicação e lifecycle em `services/api/alert_engine/*`
- `Domain Events` com publicação segura e `Outbox` em `services/api/events/*`
- `Notification Dispatcher` oficial em `services/api/notifications/*`
- scheduler interno do `Alert Engine` em `services/api/alert_engine/scheduler.py`
- consumo de recomendações no `apps/web` e no `apps/campo`

Hoje o projeto ainda não tem:

- contrato global de `Recommendation`
- persistência oficial de recomendações
- lifecycle oficial de recomendação
- deduplicação transversal de recomendação
- auditoria transversal do que foi sugerido, aceito, executado, descartado ou expirado

## Veredicto Arquitetural

O `Recommendation Engine` climático não deve evoluir sozinho como motor global.

Também não é recomendado manter motores completamente independentes por domínio.

A recomendação é:

- criar um **Recommendation Engine global oficial**
- com **rule providers por domínio**
- reutilizando a infraestrutura transversal já pronta
- sem fundir recomendação com alerta

Em termos práticos:

```text
OperationalContext
  -> RecommendationRuleProvider (por domínio)
  -> RecommendationEngine
  -> RecommendationResult
  -> RecommendationLifecycle
  -> Notification / Dashboard / Campo
```

## Por que o motor climático não deve virar o motor global diretamente

O serviço climático atual em `services/api/agricola/climatico/recommendation_service.py` é útil como prova de conceito, mas é acoplado demais ao domínio climático:

- depende diretamente de `RegistroClima`
- usa tipos fixos de operação (`PULVERIZACAO`, `COLHEITA`, `ADUBACAO`, `GERAL`)
- usa thresholds específicos de clima
- constrói respostas diretamente no formato do domínio climático
- não possui lifecycle próprio
- não persiste recomendação
- não possui contrato de governança cross-domain

Além disso, ele já mostra sinais de acoplamento frágil:

- consulta `OperationalAlert` para enriquecer a recomendação
- porém os alertas climáticos são persistidos com `source_id=str(reg.id)` no generator de clima
- enquanto o serviço climático consulta alertas por `source_id == unidade_produtiva_id`

Isso indica que o motor climático atual deve ser tratado como **provider/regra legada de clima**, e não como núcleo oficial global.

## Diretriz Oficial

### 1. Separar `Alert Engine` de `Recommendation Engine`

O `Alert Engine` já é oficial e deve continuar responsável por:

- detectar risco
- materializar alerta
- manter lifecycle de alerta
- consolidar severidade, prioridade e dedupe

O `Recommendation Engine` proposto deve ser responsável por:

- transformar sinais oficiais em ação sugerida
- organizar prioridade operacional
- explicar contexto e justificativa
- expor próximos passos
- registrar decisão humana

### 2. Recommendation Engine global com providers por domínio

O núcleo deve ser único.

As regras devem ser especializadas por domínio.

Modelo recomendado:

```text
RecommendationEngine
  -> AgricultureRecommendationProvider
  -> LivestockRecommendationProvider
  -> InventoryRecommendationProvider
  -> FleetRecommendationProvider
  -> FinanceRecommendationProvider
  -> ESGRecommendationProvider
  -> FieldRecommendationProvider
  -> WizardRecommendationProvider
```

Isso preserva:

- governança única
- contratos homogêneos
- UI consistente
- auditoria única

Sem forçar:

- uma regra climática a conhecer hedge
- uma regra de frota a conhecer vacinação
- uma regra de estoque a conhecer checklist do wizard

### 3. Recomendação é domínio assistido

Pelo `agrosaas-domain-map`, recomendação pertence ao domínio assistido.

Portanto:

- recomendação não executa operação
- recomendação não recalcula DRE oficial
- recomendação não substitui workflow operacional
- recomendação não substitui aprovação humana

## Domínio Oficial Recomendado

### Entidades conceituais

```text
OperationalContext
  - tenant_id
  - unidade_produtiva_id
  - domain
  - scope_type
  - scope_id
  - source_alert_ids[]
  - source_event_ids[]
  - source_indicator_ids[]
  - payload

RecommendationRule
  - code
  - domain
  - version
  - execution_mode
  - severity_mapping
  - eligibility_rules

RecommendationResult
  - recommendation_id
  - tenant_id
  - unidade_produtiva_id
  - domain
  - category
  - rule_code
  - status
  - priority
  - confidence
  - title
  - summary
  - rationale
  - action_label
  - action_url
  - scope_type
  - scope_id
  - source_alert_ids[]
  - source_event_ids[]
  - source_indicator_ids[]
  - context
  - dedupe_key
  - expires_at

RecommendationLifecycle
  - CREATED
  - VIEWED
  - ACCEPTED
  - DISMISSED
  - EXECUTED
  - EXPIRED
  - REOPENED
```

### Responsabilidades

Quem produz recomendações:

- providers de domínio
- regras determinísticas
- eventualmente LLMs assistivos como enriquecimento, nunca como fonte única

Quem consome:

- `apps/web`
- `apps/campo`
- rotas analíticas e dashboards executivos
- mecanismos de notificação quando permitido por política

Quem persiste:

- o domínio oficial de recomendações

Quem executa:

- usuário humano
- ou fluxo assistido explícito já governado por outro módulo

Quem fecha:

- usuário
- ou policy/lifecycle automática

Quem audita:

- trilha de lifecycle
- `TenantAuditLog`
- eventos estruturados

## Reaproveitamento Recomendado

### Reaproveitar sem mudanças conceituais

- `DomainEvent` e `publish_domain_event_safe` em `services/api/events/helpers.py`
- `Outbox` e `DomainEventOutboxRelay` em `services/api/events/*`
- `AlertSchedulerService` e `AlertGeneratorRunner` como referência de execução
- `NotificationDispatcher` em `services/api/notifications/dispatcher.py`
- RLS e `tenant_id`
- RBAC atual

### Reaproveitar com adaptação

- `ClimaRecommendationService`
  - reaproveitar apenas a lógica de regra
  - não reaproveitar como núcleo arquitetural

- `RecomendacoesOperacionaisEconomicasAgricolaV1Service`
  - reaproveitar como provider agrícola assistido
  - manter como upstream governado do domínio agrícola

- `FrotaInteligenciaService`
  - reaproveitar heurísticas e fatores de risco
  - converter para provider de recomendação

- `LancamentoService.gerar_recomendacoes`
  - reaproveitar regras financeiras determinísticas
  - mover para provider financeiro quando o épico de implementação começar

### Não reaproveitar como fonte oficial

- strings soltas de `recomendacao_operacional`
- recomendações derivadas diretamente em responses de dashboard
- sugestões locais sem persistência

## Padrão de Execução Recomendado

### Scheduled path

```text
Scheduler
  -> RecommendationEngine
  -> Domain Providers
  -> persist RecommendationResult
  -> optional notifications
```

### Event-driven path

```text
Domain Event
  -> Outbox
  -> EventPublisher
  -> Recommendation subscriber/dispatcher
  -> RecommendationEngine
  -> persist RecommendationResult
```

### Read-model path

```text
Dashboard / Campo
  -> query RecommendationResult
  -> hydrate UI
  -> user action updates lifecycle
```

## Governança

### Regras mandatórias

- nenhuma recomendação executa mutação por conta própria
- recomendação precisa apontar a fonte oficial
- recomendação precisa referenciar `source_alert_ids`, `source_event_ids` ou `source_indicator_ids`
- toda recomendação precisa ter `dedupe_key`
- toda recomendação precisa respeitar `tenant_id`
- toda recomendação precisa suportar expiração e reabertura

### Fronteiras

- Econômico continua upstream da recomendação financeira
- Territorial/Fundiário não pode ser duplicado por recomendações
- Campo continua offline-first; o cliente apenas consome snapshot e registra decisões locais
- Wizard continua governando pendências e bloqueios; o engine apenas sugere

## Roadmap Arquitetural

### Épico 1

- modelagem oficial de recommendation
- contratos e lifecycle
- subscriber/dispatcher de recommendation

### Épico 2

- provider climático
- provider agrícola
- provider financeiro

### Épico 3

- provider pecuária
- provider estoque
- provider frota

### Épico 4

- provider ESG
- provider wizard
- provider campo

### Épico 5

- UI unificada
- analytics de aceitação/execução
- telemetria de qualidade das recomendações

## Decisão Final

Arquitetura recomendada:

- **motor global oficial de recomendações**
- **providers por domínio**
- **reuso da infraestrutura de eventos, outbox, alertas, notificações, RLS e RBAC**
- **ClimaRecommendationService reaproveitado apenas como provider/rule set legado**

