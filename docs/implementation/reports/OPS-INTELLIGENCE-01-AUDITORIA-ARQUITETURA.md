# OPS-INTELLIGENCE-01 — Auditoria de Arquitetura

## 1. Resumo Executivo

A auditoria do código confirma que o AgroSaaS já possui uma fundação transversal madura para inteligência operacional, mas apenas na camada de alertas e eventos.

Conclusão central:

- existe um `Alert Engine` global oficial
- existe uma esteira de `Domain Events` + `Outbox`
- existe um `Notification Dispatcher` preparado
- não existe ainda um `Recommendation Engine` global oficial
- as recomendações atuais estão distribuídas e heterogêneas

Veredicto:

- o Recommendation Engine climático **não** deve ser promovido diretamente a motor global
- a arquitetura correta é um **Recommendation Engine global com providers por domínio**

## 2. Auditoria

### 2.1 Infraestrutura transversal já existente

Evidências principais:

- `services/api/alert_engine/service.py`
  - lifecycle oficial de alertas
  - create/update com `dedupe_key`
  - acknowledge, snooze e resolução

- `services/api/alert_engine/dispatcher.py`
  - despacho event-driven de alertas a partir de `DomainEvent`

- `services/api/alert_engine/scheduler.py`
  - execução agendada global de generators

- `services/api/events/helpers.py`
  - `publish_domain_event_safe`
  - publicação direta ou via outbox

- `services/api/events/outbox_relay.py`
  - relay oficial da `domain_event_outbox`

- `services/api/notifications/dispatcher.py`
  - dispatcher oficial de notificações com policy

### 2.2 Recommendation Engine climático

Evidências:

- `services/api/agricola/climatico/recommendation_service.py`
- `services/api/agricola/climatico/router.py`
- `services/api/campo/service.py`

Achados:

- existe um serviço explícito de recomendação climática
- ele usa `RegistroClima` e `OperationalAlert`
- ele é consumido pelo backend do Campo no `pull`
- ele não possui lifecycle próprio
- ele não possui persistência própria
- ele não possui contrato reutilizável para outros domínios

Achado crítico:

- o generator climático persiste alertas com `source_id=str(reg.id)` em `services/api/alert_engine/generators/clima_generator.py`
- o `ClimaRecommendationService` consulta alertas por `source_id == unidade_produtiva_id`

Isso indica desacoplamento incompleto entre alerta climático e recomendação climática.

### 2.3 Cadeia climática consolidada

Evidências:

- provider OpenWeather em `services/api/integracoes/openweather/services.py`
- evento `ClimaSyncRealizado` em `services/api/agricola/climatico/events.py`
- subscriber `ClimaEventSubscriber` em `services/api/agricola/climatico/subscribers.py`
- `RegistroClima` consumido por:
  - `ClimaAlertGenerator`
  - `ClimaRecommendationService`
  - PWA Campo via `SyncService.pull`

Conclusão:

- a cadeia climática está funcional e reutilizável
- ela valida a estratégia event-driven
- ela não resolve por si só o problema de recomendação global

## 3. Componentes Existentes

### 3.1 Alert Engine oficial

Arquivos:

- `services/api/alert_engine/models.py`
- `services/api/alert_engine/schemas.py`
- `services/api/alert_engine/service.py`
- `services/api/alert_engine/dispatcher.py`
- `services/api/alert_engine/scheduler.py`
- `services/api/alert_engine/generators/*`

Capacidades confirmadas:

- domínios oficiais: `AGRICULTURE`, `LIVESTOCK`, `FINANCE`, `OPERATIONS`, `FIELD`, `INTEGRATIONS`, `SYSTEM`
- categorias, severidade, prioridade, dedupe e status
- execução agendada
- execução dirigida por evento
- lifecycle e auditoria

Generators encontrados:

- `agricultura`
- `clima`
- `financeiro`
- `pecuaria`
- `campo`
- `esg_certificacoes`

### 3.2 Domain Events e Outbox

Arquivos:

- `services/api/events/publisher.py`
- `services/api/events/helpers.py`
- `services/api/events/outbox_model.py`
- `services/api/events/outbox_relay.py`
- `services/api/events/outbox_worker.py`

Capacidades confirmadas:

- publicação segura
- persistência em outbox
- retry e dead-letter
- fan-out por subscriber

### 3.3 Notifications

Arquivos:

- `services/api/notifications/dispatcher.py`
- `services/api/notifications/subscribers.py`

Capacidades confirmadas:

- dispatcher oficial
- política de entrega
- bridge futura para eventos

Limitação atual:

- `NotificationEventSubscriber` está preparado, mas não está conectado ao fluxo produtivo principal

### 3.4 Motores e serviços locais de recomendação ou decisão

Encontrados:

- clima:
  - `services/api/agricola/climatico/recommendation_service.py`

- agrícola assistido:
  - `services/api/agricola/recomendacoes/service.py`
  - `services/api/agricola/inteligencia_operacional/service.py`
  - `services/api/agricola/prioridades/service.py`

- financeiro:
  - `services/api/financeiro/services/lancamento_service.py`
  - `services/api/financeiro/services/alerta_inteligente_service.py`
  - `services/api/ia/dre_intelligence_service.py`

- hedge:
  - `services/api/financeiro/hedge/service.py`

- frota:
  - `services/api/operacional/services/frota_inteligencia_service.py`
  - `services/api/operacional/services/frota_dashboard_detail_service.py`

- compras/estoque:
  - `services/api/operacional/services/estoque_service.py`
  - `services/api/operacional/services/compras_service.py`
  - `services/api/ia/compras_estrategia_service.py`

- wizard:
  - `services/api/wizard/checklist_engine.py`
  - `services/api/wizard/router.py`
  - `apps/web/src/hooks/use-wizard.ts`

## 4. Componentes Reutilizáveis

### Reutilização direta

- `AlertLifecycleService`
- `AlertGeneratorRunner`
- `AlertSchedulerService`
- `publish_domain_event_safe`
- `DomainEventOutboxRelay`
- `NotificationDispatcher`
- RLS / `tenant_id`
- RBAC existente

### Reutilização parcial

- `ClimaRecommendationService`
  - reutilizar regras
  - descartar papel de núcleo global

- `RecomendacoesOperacionaisEconomicasAgricolaV1Service`
  - reutilizar como provider agrícola

- `FrotaInteligenciaService`
  - reutilizar heurísticas

- `LancamentoService.gerar_recomendacoes`
  - reutilizar regras determinísticas

- `ChecklistEngine`
  - reutilizar sinais e pendências do wizard

## 5. Componentes Duplicados

### 5.1 Recomendações distribuídas sem contrato comum

Há duplicação conceitual de recomendação em:

- clima
- agrícola
- financeiro
- hedge
- frota
- compras
- growth/upgrade IA

Problemas observados:

- formatos diferentes
- severidades diferentes
- sem lifecycle comum
- sem dedupe comum
- sem política comum de expiração
- sem trilha comum de aceite/execução

### 5.2 Alertas fora do Alert Engine oficial

Ainda existem mecanismos legados ou paralelos:

- `services/api/notificacoes/alertas_engine.py`
- `services/api/agricola/alertas/service.py`
- alertas e recomendações montados diretamente em dashboards/serviços locais

Conclusão:

- o `Alert Engine` oficial existe
- mas a consolidação dos produtores ainda não terminou

### 5.3 Drift documental

`docs/architecture/domain-events-inventory.md` não lista o evento climático `agricola.climatico.sync_realizado`, embora ele exista em produção no código.

Isso indica:

- documentação parcialmente defasada
- necessidade de governança documental do pipeline event-driven

## 6. Arquitetura Recomendada

### Decisão

Adotar:

- `Recommendation Engine` global oficial
- `providers` por domínio
- lifecycle próprio de recomendação

### Não recomendado

- promover `ClimaRecommendationService` a núcleo global
- manter motores completamente independentes por domínio

### Padrão recomendado

```text
OperationalContext
  -> RecommendationProvider
  -> RecommendationEngine
  -> RecommendationResult
  -> RecommendationLifecycle
  -> Dashboard / Campo / Notification
```

### Papel de cada camada

- `OperationalContext`
  - encapsula o recorte operacional oficial

- `RecommendationProvider`
  - aplica regras de domínio

- `RecommendationEngine`
  - orquestra providers, dedupe, persistência e exposição

- `RecommendationResult`
  - materializa a sugestão com fonte rastreável

- `RecommendationLifecycle`
  - controla criação, visualização, aceite, descarte, execução e expiração

## 7. Fluxo Operacional

### Fluxo por scheduler

```text
Scheduler
  -> providers elegíveis
  -> RecommendationEngine
  -> persist RecommendationResult
  -> optional notifications
```

### Fluxo por evento

```text
DomainEvent
  -> Outbox
  -> EventPublisher
  -> Recommendation subscriber/dispatcher
  -> RecommendationEngine
  -> persist RecommendationResult
```

### Fluxo de consumo

```text
Web / Campo
  -> leitura de RecommendationResult
  -> ação humana
  -> update lifecycle
```

## 8. Governança

### Regras

- recomendação não executa operação sozinha
- recomendação precisa apontar origem oficial
- recomendação precisa respeitar domínio assistido
- recomendação precisa usar `tenant_id`
- recomendação precisa suportar `dedupe_key`
- recomendação precisa auditar aceite, descarte e execução

### Fronteiras sensíveis

- financeiro:
  - não recalcular fonte econômica oficial

- territorial/fundiário:
  - não criar fonte paralela

- campo:
  - manter offline-first

- wizard:
  - manter pendência e bloqueio como fonte oficial

## 9. Riscos

### Risco 1

Transformar o motor climático em motor global.

Impacto:

- alto acoplamento com `RegistroClima`
- sem generalização real

### Risco 2

Criar um motor por domínio sem contrato oficial.

Impacto:

- explosão de formatos
- drift de severidade e prioridade
- auditoria impossível

### Risco 3

Misturar recomendação com alerta.

Impacto:

- lifecycle confuso
- UI confusa
- sem separação entre detecção e ação sugerida

### Risco 4

Ignorar o pipeline já existente de eventos/outbox.

Impacto:

- arquitetura paralela
- perda de observabilidade
- duplicação operacional

## 10. Roadmap

### Próximo épico sugerido 1

`OPS-INTELLIGENCE-02`

Escopo:

- contratos oficiais de recomendação
- entities/modelos
- lifecycle
- dispatcher/subscriber

### Próximo épico sugerido 2

`OPS-INTELLIGENCE-03`

Escopo:

- provider climático
- provider agrícola
- provider financeiro

### Próximo épico sugerido 3

`OPS-INTELLIGENCE-04`

Escopo:

- provider pecuária
- provider estoque
- provider frota

### Próximo épico sugerido 4

`OPS-INTELLIGENCE-05`

Escopo:

- provider ESG
- provider wizard
- provider campo

### Próximo épico sugerido 5

`OPS-INTELLIGENCE-06`

Escopo:

- dashboard unificado
- consumo no Campo
- telemetria de aceite e execução

## 11. Veredicto Final

- documentos de auditoria e arquitetura: definidos
- veredicto arquitetural: **motor global oficial com providers por domínio**
- `Recommendation Engine` climático: **reaproveitado apenas como provider/regra de clima, não como núcleo global**
- arquitetura recomendada: **OperationalContext -> RecommendationProvider -> RecommendationEngine -> RecommendationResult -> RecommendationLifecycle**
- próximos épicos sugeridos:
  - `OPS-INTELLIGENCE-02`
  - `OPS-INTELLIGENCE-03`
  - `OPS-INTELLIGENCE-04`
  - `OPS-INTELLIGENCE-05`
  - `OPS-INTELLIGENCE-06`
