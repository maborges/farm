# EXECUTION-34O - Transactional Outbox Adoption

## Resumo

Esta execução consolidou os pontos reais de emissão de Domain Events auditados para usar o Outbox como caminho principal sempre que a sessão transacional está disponível.
O objetivo foi reduzir a dependência de fallback pós-commit e aproximar a gravação do evento da mutação principal do domínio.

## Pontos auditados

- `campo.tarefa.invalidada`
- `campo.sync.falha` emitido pelo Campo
- `campo.sync.falha` emitido pela Pecuária
- `pecuaria.planejamento.sanitario.atualizado`
- `pecuaria.vacinacao.registrada`

## Classificação por ponto

| Ponto | Classificação | Observação |
|---|---|---|
| `campo.tarefa.invalidada` | grava Outbox na mesma transação | O evento agora é enfileirado antes do commit final da invalidação. |
| `campo.sync.falha` emitido pelo Campo | grava Outbox na mesma transação | O evento é enfileirado antes do commit final do fluxo de sync. |
| `campo.sync.falha` emitido pela Pecuária | grava Outbox na mesma transação | O resultado da sincronização é persistido e o evento é enfileirado antes do commit final do processamento. |
| `pecuaria.planejamento.sanitario.atualizado` | grava Outbox na mesma transação | O evento é enfileirado antes do commit final do planejamento. |
| `pecuaria.vacinacao.registrada` | grava Outbox na mesma transação | O evento é enfileirado antes do commit final da vacinação. |

## Pontos convertidos para Outbox transacional

- `campo.tarefa.invalidada`
- `campo.sync.falha` no fluxo Campo
- `campo.sync.falha` no fluxo Pecuária
- `pecuaria.planejamento.sanitario.atualizado`
- `pecuaria.vacinacao.registrada`

Os cinco pontos agora usam `publish_domain_event_safe(..., commit=False)` nas rotas/serviços onde a sessão já está ativa, permitindo que a gravação do evento e a mutação de negócio sejam consolidadas antes do commit final.

## Pontos mantidos pós-commit e motivo

- Nenhum dos cinco pontos reliable permaneceu como emissor pós-commit.
- O único caminho de fallback pós-commit que continua existe no helper oficial quando a sessão não está disponível ou quando o caller opta explicitamente por não usar o Outbox.

## Pontos com fallback in-memory e motivo

- O fallback in-memory continua disponível apenas em `publish_domain_event_safe(...)` quando não há `session` ou quando `use_outbox=False`.
- Isso é intencional para cenários sem contexto transacional e para testes/fallback explícito.

## Idempotency keys confirmadas

- `campo:tarefa.invalidada:{tarefa_id}`
- `campo:sync.falha:{tarefa_id}`
- `pecuaria:sync.falha:{tarefa_campo_id}`
- `pecuaria:planejamento.sanitario.atualizado:{tarefa_campo_id}`
- `pecuaria:vacinacao.registrada:{tarefa_campo_id}`

## Riscos remanescentes

- O helper oficial ainda mantém fallback in-memory em cenários sem sessão.
- O fluxo de sync da Pecuária ainda possui commits internos em etapas intermediárias, então a transacionalidade plena depende de refatoração futura mais ampla.
- O relay ainda é programático e não opera como worker externo.

## Arquivos alterados

- `services/api/events/helpers.py`
- `services/api/campo/router.py`
- `services/api/pecuaria/routers/manejos.py`
- `services/api/pecuaria/services/manejo_sync_service.py`
- `services/api/tests/unit/events/test_events_fundation.py`
- `services/api/tests/unit/events/test_outbox_readiness_anti_acoplamento.py`
- `services/api/tests/unit/campo/test_campo_domain_events.py`
- `services/api/tests/unit/pecuaria/test_pecuaria_domain_events.py`

## Arquivos criados

- `docs/implementation/reports/EXECUTION-34O-TRANSACTIONAL-OUTBOX-ADOPTION.md`

## Validações executadas

- `ruff check` nos arquivos focados neste ajuste: OK
- `ruff check` nos routers/serviços legados alterados (`campo/router.py`, `pecuaria/routers/manejos.py`, `pecuaria/services/manejo_sync_service.py`): a execução ampla ainda reporta violações históricas pré-existentes do arquivo inteiro
- `mypy` nos arquivos focados neste ajuste: OK
- `pytest services/api/tests/unit/notifications -q`: OK
- `pytest services/api/tests/unit/events/test_events_fundation.py -q`: OK
- `pytest services/api/tests/unit/campo/test_campo_domain_events.py -q`: OK
- `pytest services/api/tests/unit/pecuaria/test_pecuaria_domain_events.py -q`: OK
- `alembic heads`: OK
- `git diff --check`: OK
- `pytest services/api/tests/unit/events -q`: execução iniciada e interrompida no sandbox após 16 testes passados; a suíte completa ficou lenta demais para conclusão dentro da sessão

## Confirmações

- Nenhum endpoint público foi alterado.
- Nenhuma migration nova foi criada.
- O Alert Engine continua desacoplado dos canais de entrega.
- O Notification Dispatcher continua desacoplado do Outbox.
- `EventPublisher` continua sendo o fan-out comum.
- O Outbox não chama Alert Engine nem Notification Dispatcher diretamente.
