# EXECUTION-34P - Outbox Relay Worker MVP

## Resumo

Esta execução adicionou a primeira forma operacional controlada para executar o `DomainEventOutboxRelay` fora do fluxo principal das requisições.
O processamento continua baseado no Outbox transacional já consolidado e o `EventPublisher` permanece como ponto comum de fan-out.

## Arquivos criados

- `services/api/events/outbox_worker.py`
- `services/api/tests/unit/events/test_outbox_worker.py`
- `docs/implementation/reports/EXECUTION-34P-OUTBOX-RELAY-WORKER-MVP.md`

## Arquivos alterados

- `services/api/events/outbox_service.py`
- `services/api/events/outbox_relay.py`
- `services/api/events/__init__.py`
- `services/api/tests/unit/events/test_domain_event_outbox.py`
- `services/api/tests/unit/events/test_outbox_readiness_anti_acoplamento.py`

## Forma de execução operacional

- Função canônica: `run_outbox_relay_once(...)`
- Entrada interna simples: `python -m events.outbox_worker`
- O worker usa sessão assíncrona canônica do projeto e instancia `DomainEventOutboxRelay` por dentro.

## Parâmetros suportados

- `--batch-size`
- `--max-batches`
- `--locked-by`
- `--tenant-id`
- `--event-type`
- `--stop-on-error`

## Estratégia implementada

- O worker executa o relay em lotes pequenos.
- `locked_by` é propagado para o relay como identificador de lock.
- `tenant_id` e `event_type` são repassados ao relay e ao serviço de Outbox.
- O resultado é consolidado em `OutboxWorkerRunResult`, com totais de batches, claimed, processed, failed, dead_letter, erros e warnings.
- O worker não conhece Alert Engine nem Notification Dispatcher.

## Limitações

- Não há loop infinito nesta execução.
- Não há framework externo.
- Não há endpoint HTTP.
- Não há worker distribuído.
- O comportamento de retry e dead letter continua delegado ao relay/outbox service.

## Validações executadas

- `ruff check` nos arquivos novos e alterados: OK
- `mypy` nos arquivos novos e alterados: OK
- `pytest services/api/tests/unit/events/test_outbox_worker.py -q`: OK
- `pytest services/api/tests/unit/events/test_domain_event_outbox.py -q`: OK
- `pytest services/api/tests/unit/events/test_outbox_readiness_anti_acoplamento.py -q`: OK
- `pytest services/api/tests/unit/events -q`: iniciado com sucesso; interrompido manualmente após 17 testes passados por lentidão do sandbox
- `pytest services/api/tests/unit/notifications -q`: OK
- `alembic heads`: OK
- `git diff --check`: OK

## Próximos passos

- EXECUTION-34Q: policy layer para priorização/filtragem de notificações.
- EXECUTION-34R: canais reais de notificação.
- EXECUTION-34S: observabilidade do Outbox e do relay.
- EXECUTION-34T: externalização do worker em scheduler/cron de produção, se necessário.

## Confirmações

- Nenhum endpoint público foi criado.
- Nenhuma migration nova foi criada.
- O worker não acopla o Outbox ao Alert Engine.
- O worker não acopla o Outbox ao Notification Dispatcher.
- `EventPublisher` continua sendo o fan-out comum.
