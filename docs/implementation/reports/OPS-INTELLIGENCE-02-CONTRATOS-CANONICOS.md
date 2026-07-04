# OPS-INTELLIGENCE-02 — Contratos Canônicos

## Escopo

Implementada a fundação canônica do `Recommendation Engine` global em `services/api/recommendations/`, sem providers reais de domínio e sem integração com frontend, Campo, notificações ou `Alert Engine`.

## Auditoria prévia

Antes da implementação, foi confirmado no código:

- não existia módulo global em `services/api/recommendations/`
- existiam apenas serviços locais de recomendação, especialmente:
  - `services/api/agricola/climatico/recommendation_service.py`
  - `services/api/agricola/recomendacoes/service.py`
  - `services/api/financeiro/services/lancamento_service.py`
  - `services/api/operacional/services/frota_inteligencia_service.py`
- a infraestrutura transversal já existente e reutilizada como referência foi:
  - `services/api/alert_engine/*`
  - `services/api/events/*`
  - `services/api/notifications/*`

## O que foi criado

### Módulo canônico

- `services/api/recommendations/enums.py`
- `services/api/recommendations/schemas.py`
- `services/api/recommendations/models.py`
- `services/api/recommendations/provider.py`
- `services/api/recommendations/registry.py`
- `services/api/recommendations/engine.py`
- `services/api/recommendations/lifecycle_service.py`
- `services/api/recommendations/__init__.py`

### Persistência

- migration:
  - `services/api/migrations/versions/20260703_ops_intelligence_02_recommendations_foundation.py`

### Testes

- `services/api/tests/unit/recommendations/test_recommendations_models_schemas.py`
- `services/api/tests/unit/recommendations/test_recommendations_registry_engine.py`
- `services/api/tests/unit/recommendations/test_recommendations_lifecycle_service.py`
- `services/api/tests/unit/recommendations/test_recommendations_anti_coupling.py`

## Contratos implementados

### Enums

- `RecommendationDomain`
- `RecommendationStatus`
- `RecommendationPriority`
- `RecommendationSourceType`
- `RecommendationActionType`
- `RecommendationLifecycleActionType`

### Schemas conceituais

- `RecommendationSignal`
- `OperationalContext`
- `RecommendationCandidate`
- `RecommendationResultCreate`
- `RecommendationResultResponse`
- `RecommendationLifecycleEventCreate`
- `RecommendationLifecycleEventResponse`

### Persistência ORM

- `RecommendationResult`
- `RecommendationLifecycleEvent`

## Comportamento implementado

### Engine

`RecommendationEngine`:

- resolve providers pelo registry
- executa providers por domínio
- recebe apenas `RecommendationCandidate`
- persiste via `RecommendationLifecycleService`
- contabiliza `created`, `updated` e `errors`

### Lifecycle

`RecommendationLifecycleService` implementa:

- `create_or_update_recommendation`
- `mark_viewed`
- `accept`
- `dismiss`
- `postpone`
- `execute`
- `expire`
- `supersede`
- `reopen`

### Dedupe

- ativo por `tenant_id + dedupe_key`
- recomendações ativas não duplicam
- resultados encerrados permitem nova recomendação futura

## Persistência e RLS

Tabelas criadas:

- `recommendation_results`
- `recommendation_lifecycle_events`

Características:

- `tenant_id` obrigatório
- políticas RLS por tabela
- `FORCE ROW LEVEL SECURITY`
- índices por tenant, domínio, escopo e dedupe
- índice parcial único para `dedupe_key` ativo

## Restrições preservadas

- sem alteração em frontend
- sem alteração em Campo PWA
- sem provider climático
- sem provider agrícola
- sem provider financeiro
- sem provider pecuária
- sem provider frota
- sem provider estoque
- sem provider ESG
- sem provider wizard
- sem integração com `NotificationDispatcher`
- sem integração com `Alert Engine`
- sem promoção de `ClimaRecommendationService` a núcleo global

## Observações

- a contagem `created` vs `updated` no engine é derivada do estado persistido retornado pelo lifecycle service
- nesta etapa, `RecommendationSignal` e `OperationalContext` são contratos de entrada, não tabelas
- a integração com sinais reais de domínio fica para os próximos épicos

## Próximos passos sugeridos

1. `OPS-INTELLIGENCE-03`
   - introduzir providers reais começando por clima, agrícola e financeiro
2. `OPS-INTELLIGENCE-04`
   - integrar leitura de recomendações por query service ou router
3. `OPS-INTELLIGENCE-05`
   - ligar telemetria e métricas de aceite/execução
