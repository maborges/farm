# Domain Events

## Propósito

A fundação de Domain Events do AgroSaaS existe para desacoplar fatos de domínio do Alert Engine.
Domain Services publicam um evento canônico em memória e a cadeia de publicação faz o roteamento
para subscribers e, quando aplicável, para o Alert Engine.

## Fluxo Atual

```text
Domain Service
  -> publish_domain_event_safe(...)
  -> EventPublisher
  -> EventSubscriberRegistry
  -> AlertEngineEventSubscriber
  -> AlertDispatcherService
  -> AlertGeneratorRegistry
  -> AlertGeneratorRunner
  -> Generators
  -> AlertLifecycleService
```

## Conceitos

- `DomainEvent`: envelope canônico do fato de domínio. Carrega identidade do evento, tenant,
  unidade produtiva, tipo, origem, entidade, correlação, causalidade e metadata segura.
- `EventPublisher`: resolve subscribers registrados para o `event_type` e executa a fan-out.
- `EventSubscriber`: contrato de consumo de eventos em memória.
- `AlertEngineEventSubscriber`: subscriber de ponte que converte `DomainEvent` em `AlertDomainEvent`
  e delega ao `AlertDispatcherService`.
- `AlertDispatcherService`: coordena o Alert Engine. Resolve generators e agrega resultados.

## Por que Domain Services não chamam o Dispatcher

Domain Services devem conhecer apenas o evento canônico e o helper de publicação segura.
Chamar `AlertDispatcherService` diretamente introduz acoplamento com a implementação do Alert Engine,
confunde fronteiras arquiteturais e dificulta evoluir para Outbox ou filas sem reescrever domínio.

## Eventos Publicados Hoje

- `campo.tarefa.invalidada`
- `campo.sync.falha`
- `pecuaria.vacinacao.registrada`
- `pecuaria.planejamento.sanitario.atualizado`

## Eventos Consumidos Hoje pelo Alert Engine

O Alert Engine consome os quatro eventos acima por meio do `AlertEngineEventSubscriber`.

## Política Post-Commit

- Se o fluxo já faz `commit` explícito, o evento é publicado somente depois do commit bem-sucedido.
- Se o fluxo está em transação gerenciada externamente, a publicação ocorre após a confirmação
  do estado persistido, sem forçar commit adicional.
- A falha na publicação não deve quebrar o fluxo principal do domínio.

## Política de Isolamento de Falhas

`publish_domain_event_safe(...)` captura exceções do publisher/subscribers, registra log estruturado e
retorna `None` em caso de erro não fatal.
Isso preserva o fluxo principal e evita que o Alert Engine interrompa operações de negócio.

## Logs Estruturados

Os logs principais carregam, quando disponíveis:

- `event_id`
- `event_type`
- `tenant_id`
- `unidade_produtiva_id`
- `correlation_id`
- `causation_id`
- `subscriber_name`
- `dispatch_id`
- `status`
- `duration_ms`
- `errors`
- `warnings`

Os logs não devem incluir payloads grandes, snapshots completos ou dados sensíveis desnecessários.

## Limitações Atuais

- Não existe Outbox.
- Os eventos são in-memory.
- Não há retry automático.
- Não há DLQ.
- Não há worker externo dedicado.
- A publicação depende do processo atual da API.

## Preparação para Outbox Futura

O desenho atual já separa:

- produção do fato de domínio;
- publicação canônica;
- fan-out para subscribers;
- ponte para o Alert Engine.

Isso facilita introduzir Outbox depois sem alterar os Domain Services, apenas trocando o mecanismo
de entrega do evento.
