# EXECUTION-34N - Domain Event Outbox MVP

## Resumo

O Outbox MVP foi implementado para persistir Domain Events reliable e reduzir o risco de perda entre o commit do domínio e o fan-out para subscribers.
A entrega agora deixa de depender exclusivamente de publicação em memória para os eventos auditados como confiáveis, mantendo `EventPublisher` como ponto comum de fan-out.

## Arquivos criados

- `services/api/events/outbox_model.py`
- `services/api/events/outbox_service.py`
- `services/api/events/outbox_relay.py`
- `services/api/migrations/versions/20260626_domain_event_outbox.py`
- `services/api/tests/unit/events/test_domain_event_outbox.py`
- `services/api/tests/unit/test_domain_event_outbox_migration_static.py`

## Arquivos alterados

- `services/api/events/helpers.py`
- `services/api/events/base.py`
- `services/api/events/__init__.py`
- `services/api/alert_engine/dispatcher.py`
- `services/api/alert_engine/__init__.py`
- `services/api/tests/unit/events/test_outbox_readiness_anti_acoplamento.py`

## Estrutura implementada

- `DomainEventOutbox`
  - modelo canônico para persistência de Domain Events reliable.
  - inclui `tenant_id`, `unidade_produtiva_id`, `event_type`, `source_type`, `source_id`, `payload`, `metadata`, `correlation_id`, `causation_id`, `status`, `attempts`, `next_attempt_at`, `locked_at`, `locked_by`, `created_at`, `processed_at`, `failed_at`, `last_error` e `idempotency_key`.
- `DomainEventOutboxService`
  - persiste eventos na outbox com idempotência;
  - lista eventos pendentes;
  - faz claim por lote;
  - marca como `processed`, `failed` ou `dead_letter`;
  - reconstrói `DomainEvent` a partir da linha persistida.
- `DomainEventOutboxRelay`
  - relay programático interno para processar lotes pendentes;
  - reconstrói `DomainEvent`;
  - chama `EventPublisher`;
  - consolida resultado e status de execução.
- `enqueue_domain_event(...)`
  - helper canônico para gravação na outbox.
- `publish_domain_event_safe(...)`
  - mantém fallback explícito para publicação in-memory quando não houver `session` ou quando o uso do Outbox for desabilitado.
- Migration Alembic
  - tabela criada no schema `farms`;
  - índices adicionados;
  - RLS habilitado conforme padrão do projeto.

## Política de idempotência

- Constraint única por `tenant_id + idempotency_key`.
- Padrão adotado:
  - `campo:<suffix>:<source_id>`
  - `pecuaria:<suffix>:<source_id>`
  - fallback por domínio do evento quando necessário

## Política de retry

- `max_attempts = 5`
- backoff exponencial simples em minutos
- status suportados:
  - `pending`
  - `processing`
  - `failed`
  - `processed`
  - `dead_letter`

## Relay

- O relay é programático.
- Ainda não existe worker externo.
- O relay reconstrói `DomainEvent` antes do fan-out.
- O relay chama `EventPublisher` como ponto comum de entrega para subscribers.
- O relay marca cada item como `processed`, `failed` ou `dead_letter`.
- O relay não chama `Alert Engine` nem `Notification Dispatcher` diretamente.

## Reuso arquitetural

Reutilização confirmada de:

- `DomainEvent`
- `EventPublisher`
- `EventSubscriberRegistry`
- `EventSubscriberResult`
- `AlertEngineEventSubscriber`
- `NotificationEventSubscriber`

## Ajustes arquiteturais

- Remoção da dependência direta de `alert_engine.models.Domain` em `events.base` para quebrar o ciclo de import entre `events` e `alert_engine`.
- Normalização de `domain` no `AlertDispatcherService` quando recebe enum ou string.
- Compatibilidade com Python 3.10 via fallback para `timezone.utc`.

## Validações executadas

- `ruff check` nos arquivos novos e alterados: OK
- `mypy` nos arquivos novos e alterados: OK
- `pytest tests/unit/events/test_domain_event_outbox.py -q`: OK
- `pytest tests/unit/test_domain_event_outbox_migration_static.py -q`: OK
- `pytest tests/unit/events/test_outbox_readiness_anti_acoplamento.py -q`: OK
- `pytest tests/unit/events -q`: OK
- `pytest tests/unit/notifications -q`: OK
- `alembic heads`: OK
- `alembic current`: OK
- `alembic upgrade head`: OK
- `alembic downgrade -1`: OK
- `alembic upgrade head` novamente: OK
- `git diff --check`: OK

## Falha ambiental conhecida

- `pytest tests/unit/alert_engine -q` falhou por `PermissionError [Errno 1] Operation not permitted` ao tentar abrir socket/conexão com banco no sandbox.
- Resultado observado: `70 passed, 36 failed`.
- As falhas ficaram concentradas em fixtures e testes que dependem de banco real.
- Isso não caracteriza regressão do Outbox.

## Confirmações

- Nenhum endpoint público foi alterado.
- Nenhuma migration além da necessária para o Outbox foi criada.
- O Alert Engine continua desacoplado dos canais de entrega.
- O Notification Dispatcher continua desacoplado do Outbox.
- `EventPublisher` continua sendo o fan-out comum.
- O Outbox não chama Alert Engine nem Notification Dispatcher diretamente.

## Próximos passos recomendados

1. `EXECUTION-34O` - migrar/controlar pontos de emissão para uso transacional pleno do Outbox, se ainda houver fallback pós-commit.
2. `EXECUTION-34P` - worker real para relay.
3. `EXECUTION-34Q` - Notification Policies.
4. `EXECUTION-34R` - canais reais de notificação.
5. `EXECUTION-34S` - observabilidade de Outbox e eventos.
