# EXECUTION-34M - Outbox Readiness Audit

## Resumo

A auditoria confirmou que os fluxos atuais de Domain Events, Alert Dispatcher e Notification Dispatcher
estão corretamente desacoplados em termos de contrato, mas ainda operam em memória e sem persistência de entrega.
Isso mantém o sistema funcional, porém com risco de perda entre o commit do domínio e a fan-out real.

## Eventos encontrados

Eventos de produção auditados:

- `campo.tarefa.invalidada`
- `campo.sync.falha`
- `pecuaria.planejamento.sanitario.atualizado`
- `pecuaria.vacinacao.registrada`

Não foram encontrados outros `event_type` publicados em produção nos fluxos escaneados.
O `campo.sync.falha` possui dois emissores concretos: `services/api/campo/router.py` e `services/api/pecuaria/services/manejo_sync_service.py`.

## Produtores

- `services/api/campo/router.py`
- `services/api/pecuaria/routers/manejos.py`
- `services/api/pecuaria/services/manejo_sync_service.py`

## Consumidores

- `AlertEngineEventSubscriber`
- `AlertDispatcherService`
- `AlertGeneratorRegistry`
- `AlertGeneratorRunner`
- `AlertLifecycleService`

O `NotificationEventSubscriber` está preparado e testado, mas não consome eventos de produção nesta auditoria.

## Gaps encontrados

- Ausência de Outbox persistente.
- Ausência de replay confiável.
- Ausência de retry persistido.
- Ausência de DLQ.
- Ausência de worker externo de relay.
- Dependência do ciclo de vida atual do processo da API para entrega efetiva.

## Riscos atuais do modelo in-memory

- perda de evento logo após o commit;
- falta de rastreabilidade de entrega/reentrega;
- dificuldade de replay manual;
- visibilidade limitada sobre falhas transitórias;
- maior acoplamento operacional ao runtime da API.

## Recomendação para o Outbox MVP

1. Inserir tabela de outbox com campos mínimos de tenant, origem, payload, status, tentativas e lock.
2. Migrar primeiro os eventos reliable de Campo e Pecuária.
3. Introduzir relay com leitura concorrente via `SKIP LOCKED`.
4. Reutilizar `EventPublisher` como ponto comum de fan-out.
5. Manter `AlertDispatcherService` e `NotificationDispatcher` como consumidores downstream.

## Validações executadas

- auditoria via `rg` dos pontos de publicação e subscribers;
- leitura dos contratos `events`, `alert_engine` e `notifications`;
- verificação dos testes existentes de anti-acoplamento.

## Confirmações

- Nenhuma migration foi criada.
- Nenhum endpoint público foi alterado.
- Nenhum fluxo funcional foi alterado.
- O Alert Engine permanece desacoplado dos canais de entrega.
