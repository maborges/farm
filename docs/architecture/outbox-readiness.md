# Outbox Readiness

## Por que o Outbox será necessário

O modelo atual é in-memory e best-effort na camada de transporte. Isso cria janelas de perda entre o commit do domínio
e a publicação efetiva para subscribers. O Outbox elimina esse risco ao persistir o fato a ser propagado dentro da mesma
fronteira transacional do domínio ou, no mínimo, em uma etapa idempotente imediatamente associada ao commit.

## Onde o Outbox deve entrar

O ponto de inserção recomendado é entre a mutação do domínio e o `EventPublisher`.

Fluxo futuro recomendado:

```text
Domain Service
  -> grava estado de negócio
  -> grava outbox na mesma transação
  -> commit
  -> relay/worker lê outbox pendente
  -> EventPublisher
  -> EventSubscriberRegistry
  -> AlertEngineEventSubscriber / NotificationEventSubscriber
```

O `EventPublisher` continua sendo o ponto comum de fan-out. O Outbox apenas substitui a origem in-memory do evento.

## Fluxos que devem migrar primeiro

1. `campo.tarefa.invalidada`
2. `campo.sync.falha`
3. `pecuaria.sync.falha`
4. `pecuaria.planejamento.sanitario.atualizado`
5. `pecuaria.vacinacao.registrada`

Esses fluxos já são pós-commit, têm consumidores definidos e representam alertas operacionais confiáveis.

## Proposta de tabela futura

Tabela sugerida: `domain_event_outbox`

Campos mínimos:

- `id`
- `tenant_id`
- `unidade_produtiva_id`
- `event_type`
- `source_type`
- `source_id`
- `payload`
- `metadata`
- `correlation_id`
- `causation_id`
- `status`
- `attempts`
- `next_attempt_at`
- `locked_at`
- `locked_by`
- `created_at`
- `processed_at`
- `failed_at`
- `last_error`

## Política de retry

- Retry com backoff exponencial e jitter.
- Incremento de `attempts` a cada falha transitória.
- Atualização de `next_attempt_at` para evitar hot loop.
- Lock otimista/pessimista com `SKIP LOCKED` no relay futuro.

## Política de idempotência

- Chave idempotente derivada de `tenant_id + event_type + source_id + causation_id` quando existir.
- Persistir a chave em índice único ou coluna dedicada.
- O relay deve ser idempotente ao reenviar para `EventPublisher`.

## Política de erro

- Erros transitórios permanecem reprocessáveis.
- Erros permanentes devem registrar `last_error` e mover o registro para estado terminal após o limite de tentativas.
- O domínio não deve ser revertido por falha do relay.

## DLQ futura

- Pode existir como status terminal na mesma tabela ou em uma tabela separada.
- Deve conter o payload original, o erro final e metadados de replay manual.

## Worker futuro

- Um worker único ou serviço agendado deve varrer registros pendentes.
- Deve adquirir lotes pequenos, respeitar `tenant_id` e processar com isolamento por lock.
- O worker não deve conhecer regras de negócio.

## Relação com `EventPublisher`

O `EventPublisher` permanece a camada comum de fan-out e execução de subscribers.
No MVP de Outbox, o relay lerá a tabela e chamará o publisher com o `DomainEvent` reconstruído.

## Relação com `NotificationDispatcher`

O `NotificationDispatcher` continua downstream do `NotificationEventSubscriber`.
Ele não deve ser chamado diretamente pelo Outbox nem pelos Domain Services.

## Relação com `AlertDispatcher`

O `AlertDispatcherService` continua sendo acionado pelo `AlertEngineEventSubscriber`.
O Outbox não deve conhecer generators, lifecycle ou regras do Alert Engine.

## Risco atual do modelo em memória

- perda de evento após commit e antes da publicação;
- impossibilidade de replay confiável;
- observabilidade limitada de falhas transitórias;
- ausência de estado persistido para reprocessamento manual.

## Recomendação para o MVP

1. Implementar a tabela de outbox.
2. Introduzir relay/worker simples com `SKIP LOCKED`.
3. Migrar primeiro os eventos operacionais reliable.
4. Manter `EventPublisher` e subscribers existentes intactos.
5. Adiar qualquer integração automática com canais externos até o relay estar estável.
