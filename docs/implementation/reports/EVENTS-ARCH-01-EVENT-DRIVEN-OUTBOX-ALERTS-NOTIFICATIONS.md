# EVENTS-ARCH-01 — Relatório curto

## Resultado

A auditoria confirmou uma arquitetura event-driven canônica já existente e suficientemente clara para normatização.

## Decisões centrais

- O fluxo canônico oficial foi definido como `Domain Service -> Outbox -> Relay -> EventPublisher -> Subscribers`.
- `DomainEventOutbox` foi definido como padrão transacional oficial.
- `EventPublisher` foi definido como único fan-out oficial.
- `Alert Engine` foi definido como consumidor desacoplado via subscriber.
- `Notification Dispatcher` foi definido como consumidor desacoplado para entrega de notificações.
- `Notification Policies` foram definidas como camada decisória.
- `Adapters` foram definidos como camada de entrega.
- Worker, métricas e health foram documentados como operação oficial local da v1.0.

## Compatibilidades registradas

- `publish_domain_event_safe(...)` pode operar em modo in-memory como fallback controlado.
- `NotificationEventSubscriber` existe, mas permanece como bridge opcional/não ligada por padrão ao registry global.
- `LOG` e `NOOP` continuam válidos como canais de compatibilidade operacional.

## Limitações registradas

- métricas in-memory;
- ausência de broker externo;
- ausência de Prometheus/OpenTelemetry;
- deduplicação e silence window de notificações sem persistência;
- retry por canal ainda ausente.

## v1.0 x v1.1

### v1.0

- Outbox transacional como padrão.
- Relay e worker oficializados.
- EventPublisher como fan-out único.
- Alert Engine e Notification Dispatcher formalizados como consumidores desacoplados.

### v1.1

- ampliar wiring de notificações orientadas a eventos;
- persistir preferências e deduplicação;
- evoluir observabilidade externa;
- avaliar operação distribuída.

## Arquivos auditados

- `services/api/events/`
- `services/api/alert_engine/`
- `services/api/notifications/`
- testes unitários de `events`, `alert_engine` e `notifications`
- relatórios `EXECUTION-34Q`, `34R`, `34S`, `34T` e `34U`

## Validação

- `git diff --check`
  - resultado: sem erros

## Confirmações

- Nenhum código operacional foi alterado.
- Nenhuma migration foi criada.
- Nenhum endpoint foi criado.
- Apenas documentação foi criada nesta execução.
