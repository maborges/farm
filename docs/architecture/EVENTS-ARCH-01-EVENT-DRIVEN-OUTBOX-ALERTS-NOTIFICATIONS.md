# EVENTS-ARCH-01 — Event-Driven, Outbox, Alertas e Notificações

## 1. Resumo executivo

O AgroSaaS já possui uma arquitetura event-driven oficial suficientemente clara para orientar novos desenvolvimentos.

O fluxo oficial encontrado na codebase é:

```text
Domain Service
  ↓
enqueue_domain_event(...) / publish_domain_event_safe(..., use_outbox=True)
  ↓
DomainEventOutbox
  ↓
Commit
  ↓
DomainEventOutboxRelay
  ↓
publish_domain_event(...)
  ↓
EventPublisher
  ↓
EventSubscriberRegistry
  ├── AlertEngineEventSubscriber
  └── outros subscribers registrados
```

Para notificações, a arquitetura oficial é desacoplada e separada do domínio original:

```text
NotificationEvent
  ↓
NotificationDispatcher
  ↓
NotificationPolicyService
  ↓
NotificationPolicy
  ↓
NotificationAdapterRegistry
  ↓
Adapters (LOG / NOOP / EMAIL)
```

Conclusão objetiva:

- `DomainEventOutbox` é o padrão transacional oficial para eventos persistentes.
- `EventPublisher` é o único fan-out oficial.
- `Alert Engine` é consumidor desacoplado por subscriber.
- `Notification Dispatcher` é a porta oficial de entrega de notificações.
- Publicação direta sem Outbox existe apenas como fallback controlado.
- Ainda há limitações operacionais de v1.0, especialmente métricas in-memory, subscriber de notificação não ligado por padrão ao registry global e ausência de infraestrutura externa de fila/telemetria.

## 2. Fluxo oficial

Fluxo oficial confirmado pela codebase:

```text
Domain Service
  ↓
enqueue_domain_event(...)
  ↓
domain_event_outbox
  ↓
commit da transação principal
  ↓
DomainEventOutboxRelay.run_once(...)
  ↓
publish_domain_event(...)
  ↓
EventPublisher.publish(...)
  ↓
EventSubscriberRegistry.find_by_event_type(...)
  ↓
Subscribers registrados
```

Fluxo oficial de alertas:

```text
DomainEvent
  ↓
AlertEngineEventSubscriber
  ↓
AlertDispatcherService
  ↓
AlertGeneratorRegistry
  ↓
AlertGeneratorRunner
  ↓
AlertLifecycleService
```

Fluxo oficial de notificações:

```text
NotificationEvent
  ↓
NotificationDispatcher
  ↓
NotificationPolicyService
  ↓
NotificationPolicyResult
  ↓
NotificationAdapterRegistry
  ↓
Adapter por canal
```

## 3. Domain Events

`DomainEvent` é o envelope oficial do fato de domínio. O contrato atual carrega:

- `event_id`
- `tenant_id`
- `unidade_produtiva_id`
- `domain`
- `event_type`
- `source_type`
- `entity_type`
- `entity_id`
- `occurred_at`
- `correlation_id`
- `causation_id`
- `metadata`

Norma oficial:

- Todo novo evento deve usar `DomainEvent`.
- Todo novo evento deve ter `tenant_id`.
- `event_type` é obrigatório e deve seguir nomenclatura estável por domínio.
- `metadata` deve ser pequeno, idempotente e sem dados sensíveis desnecessários.
- `correlation_id` e `causation_id` devem ser preenchidos sempre que houver encadeamento relevante.

## 4. Outbox

`DomainEventOutbox` é a persistência transacional oficial da cadeia event-driven.

Responsabilidades confirmadas:

- persistir o evento antes da entrega;
- proteger a publicação com idempotência;
- separar `PENDING`, `PROCESSING`, `PROCESSED`, `FAILED` e `DEAD_LETTER`;
- suportar retries por `attempts` e `next_attempt_at`;
- registrar `locked_at` e `locked_by` para coordenação de relay;
- permitir filtros por `tenant_id` e `event_type`.

Norma oficial:

- Todo Domain Service com `AsyncSession` e transação de negócio deve usar Outbox.
- A persistência deve acontecer antes do commit final do fluxo de negócio.
- `idempotency_key` estável por tenant é obrigatória para evitar duplicidade.
- `DEAD_LETTER` é estado terminal operacional, não mecanismo de correção de domínio.

## 5. Relay

`DomainEventOutboxRelay` é a ponte oficial entre persistência e fan-out.

Funções confirmadas:

- claim de lotes elegíveis;
- rebuild do `DomainEvent` a partir do Outbox;
- chamada de `publish_domain_event(...)`;
- marcação de sucesso com `mark_processed(...)`;
- marcação de falha com `mark_failed(...)`;
- isolamento por lote e por evento.

Norma oficial:

- Nenhum novo fluxo deve pular do Outbox diretamente para Alert Engine ou Notification Dispatcher.
- O Relay é a única etapa autorizada a retirar eventos persistidos do Outbox para entrega.

## 6. Worker

O worker oficial do Outbox é `python -m events.outbox_worker`.

Capacidades auditadas:

- `run`
- `status`
- `stats`
- `health`
- `metrics`
- `run --loop`
- `--dry-run`
- filtros por `tenant_id` e `event_type`
- `heartbeat`
- `backoff`
- `max-runtime`

Norma oficial:

- Operação contínua deve reutilizar `run_outbox_relay_once(...)`.
- O worker não deve embutir lógica de domínio.
- O worker não substitui EventPublisher, Alert Engine ou Notification Dispatcher.

## 7. EventPublisher

`EventPublisher` é o único fan-out oficial do AgroSaaS.

Responsabilidades confirmadas:

- resolver subscribers por `event_type`;
- executar cada subscriber com isolamento de falhas;
- consolidar resultado com sucessos, falhas, warnings e duração;
- impedir que a falha de um subscriber derrube o fan-out inteiro.

Norma oficial:

- Domain Services não devem chamar `AlertDispatcherService` diretamente.
- Domain Services não devem chamar `NotificationDispatcher` diretamente.
- Novos consumidores devem entrar via subscriber registrado.

## 8. Subscribers

O registry oficial é `EventSubscriberRegistry`.

Situação encontrada:

- `AlertEngineEventSubscriber` está registrado no registry global.
- `NotificationEventSubscriber` existe como bridge opcional/futura, mas não está ligado por padrão ao registry global de subscribers.

Norma oficial:

- Todo novo subscriber deve ser registrado no registry.
- Subscriber deve ser idempotente.
- Subscriber não deve assumir exclusividade de consumo.
- Subscriber não deve acoplar o domínio emissor à implementação interna do consumidor.
- Falha em subscriber deve ser isolada e retornar resultado estruturado.

## 9. Alert Engine

O Alert Engine foi confirmado como consumidor desacoplado da cadeia de eventos.

Camadas identificadas:

- `AlertDispatcherService`
- `AlertGeneratorRegistry`
- `AlertGeneratorRunner`
- generators por domínio
- `AlertLifecycleService`
- camadas de query e summary
- `AlertSchedulerService` para execução agendada

Norma oficial:

- Novo alerta deve nascer como generator.
- Generator deve ser idempotente.
- `dedupe_key` deve ser estável.
- Persistência de alerta deve passar pelo lifecycle.
- Execução agendada deve usar a infraestrutura de scheduler do próprio Alert Engine, não atalhos no domínio original.

## 10. Notification Dispatcher

`NotificationDispatcher` é a porta oficial de entrega de notificações.

Fluxo confirmado:

```text
NotificationEvent
  ↓
NotificationPolicyService
  ↓
NotificationPolicyResult
  ↓
AdapterRegistry.resolve(...)
  ↓
adapter.send(...)
```

Capacidades identificadas:

- prioridade;
- múltiplos canais;
- supressão por policy;
- deduplicação;
- janela de silêncio;
- isolamento de falhas por canal;
- continuação mesmo quando um canal falha.

Norma oficial:

- Domain Service não envia notificação diretamente.
- Domínio publica evento; a camada de notificação decide elegibilidade e canal.
- Adapter entrega; policy decide.

## 11. Notification Policies

`NotificationPolicyService` é a camada decisória oficial antes da entrega.

Funções confirmadas:

- resolver policy por `event_type`;
- determinar `priority`;
- determinar `channels`;
- determinar `recipients`;
- aplicar `dedupe_key`;
- aplicar `silence_window`.

Norma oficial:

- Toda decisão de canal, prioridade e supressão deve viver em policy.
- `DefaultNotificationPolicy` é fallback, não justificativa para bypass arquitetural.
- Deduplicação deve ser tenant-scoped.
- Janela de silêncio não deve ser implementada dentro de adapters.

## 12. Adapters

Adapters confirmados:

- `LOG`
- `NOOP`
- `EMAIL`

Papel oficial dos adapters:

- traduzir o `NotificationEvent` para o mecanismo de entrega;
- devolver resultado estruturado;
- não decidir regra de negócio;
- não conhecer Alert Engine;
- não conhecer domínio emissor além do envelope oficial.

Norma oficial:

- Novos canais devem entrar via `NotificationAdapterRegistry`.
- Retry por canal não deve ser improvisado em Domain Services.
- Adapter é camada de entrega, não de orquestração.

## 13. Observabilidade

Observabilidade atual confirmada:

- `OutboxMetrics` em memória;
- `OutboxBacklogSnapshot`;
- `OutboxHealthStatus`;
- comandos `health` e `metrics`;
- heartbeat do worker;
- backlog, retries, throughput, last success, last error.

Métricas disponíveis:

- `cycles`
- `batches_processed`
- `events_processed`
- `events_failed`
- `errors`
- `current_backlog`
- `retries_seen`
- `last_success_at`
- `last_error_at`
- `last_error`
- `throughput_per_minute`
- `average_batch_size`

Estados de health:

- `OK`
- `DEGRADED`
- `CRITICAL`
- `UNKNOWN`

## 14. Normas para novos eventos

- Todo novo evento deve carregar `tenant_id`.
- Todo novo evento deve declarar `event_type` estável.
- `event_type` deve seguir padrão semântico por domínio, por exemplo `campo.sync.falha`.
- Todo novo evento deve ser publicável de forma idempotente.
- Payload não deve carregar objetos ORM, classes internas ou snapshots excessivos.
- Dados sensíveis só podem entrar em metadata quando forem indispensáveis.
- Serviços transacionais devem persistir no Outbox.
- Publicação direta in-memory só é aceitável em exceção controlada, sem sessão transacional, e deve ser tratada como compatibilidade e não como direção futura.

## 15. Normas para novos subscribers

- Registrar o subscriber no `EventSubscriberRegistry`.
- Declarar `event_types` explícitos.
- Não quebrar o fan-out caso falhe.
- Retornar resultado estruturado.
- Ser seguro para reprocessamento.
- Não chamar de volta o serviço de domínio original.
- Não introduzir acoplamento com detalhes internos do módulo emissor.

## 16. Normas para novos alerts

- Criar generator, não chamada direta do dispatcher a partir do domínio.
- Usar `AlertGeneratorRegistry`.
- Aplicar `dedupe_key` estável.
- Persistir via `AlertLifecycleService`.
- Respeitar multi-tenant.
- Manter severidade e prioridade alinhadas ao contrato de alertas.
- Se o caso for agendado, usar `AlertSchedulerService`.

## 17. Normas para novas notificações

- Não enviar e-mail, push ou WhatsApp diretamente de Domain Service.
- Criar ou reutilizar `NotificationEvent`.
- Passar obrigatoriamente por `NotificationDispatcher`.
- Deixar `NotificationPolicyService` decidir prioridade, canal, dedupe e silêncio.
- Usar adapter somente para entrega.
- Tratar canais ainda não implementados como `NOOP` ou `NOT_IMPLEMENTED`, sem criar bypass.

## 18. Compatibilidades

Compatibilidades que permanecem válidas por enquanto:

- `publish_domain_event_safe(...)` com fallback in-memory;
- operação local do worker por processo;
- policies, dedupe e silence window em memória;
- bridge de notificação existente, porém opcional/não ligada por padrão ao registry global;
- adapters `LOG` e `NOOP` como fallback operacional legítimo.

## 19. Limitações

Limitações atuais confirmadas:

- não há fila externa;
- não há broker;
- não há scheduler/orquestrador externo do worker;
- não há Prometheus, OpenTelemetry ou dashboard nativo;
- métricas são in-memory e por processo;
- deduplicação de notificação é in-memory;
- silence window não é persistida por tenant;
- não há retry por canal de notificação;
- subscriber de notificação ainda não é fan-out padrão global para todos os eventos.

## 20. v1.0 x v1.1

### v1.0

- Fixar Outbox como padrão transacional.
- Fixar `EventPublisher` como único fan-out.
- Fixar `AlertEngineEventSubscriber` como bridge oficial de alertas.
- Fixar `NotificationDispatcher -> Policy -> Adapter` como arquitetura oficial de notificação.
- Fixar worker CLI, loop contínuo, métricas e health como operação padrão local.

### v1.1

- Ligar notificação orientada a eventos ao registry global de forma mais ampla, quando houver cobertura e governança suficientes.
- Persistir preferências, deduplicação e silence window por tenant.
- Evoluir retry e histórico por canal.
- Adicionar telemetria externa e observabilidade persistente.
- Introduzir operação distribuída, se a escala exigir.

## 21. Pergunta final obrigatória

Resposta objetiva: **sim**.

Após esta execução, qualquer novo desenvolvimento event-driven no AgroSaaS passa a ter uma referência arquitetural clara sobre como publicar eventos, persistir no Outbox, fazer relay, acionar alertas, aplicar políticas de notificação e entregar mensagens sem acoplar Domain Services diretamente ao Alert Engine ou ao Notification Dispatcher.
