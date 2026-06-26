# Domain Events Criticality Matrix

## Objetivo

Classificar os eventos de domínio atuais para orientar o futuro Outbox MVP.
O critério aqui é o impacto operacional da perda do evento, não a severidade visual do alerta.

## Matriz

| event_type | produtor | criticidade | justificativa | prioridade de migração para Outbox |
|---|---|---|---|---|
| `campo.tarefa.invalidada` | `services/api/campo/router.py` | reliable | Reflete uma mudança operacional já persistida; pode ser reprocessado sem bloquear o fluxo principal. | alta |
| `campo.sync.falha` | `services/api/campo/router.py` | reliable | Sinaliza erro operacional pós-commit; não altera consistência do domínio, mas não deve ser perdido. | alta |
| `campo.sync.falha` | `services/api/pecuaria/services/manejo_sync_service.py` | reliable | Mesmo padrão de falha operacional pós-commit, com necessidade de reprocessamento confiável. | alta |
| `pecuaria.planejamento.sanitario.atualizado` | `services/api/pecuaria/routers/manejos.py` | reliable | Marca atualização de planejamento com impacto de observabilidade e alertamento. | alta |
| `pecuaria.vacinacao.registrada` | `services/api/pecuaria/services/manejo_sync_service.py` | reliable | Evento operacional pós-commit que alimenta o Alert Engine e deve ser reprocessável. | alta |

## Classes de criticidade

### best_effort

Nenhum evento de produção atual foi classificado como best_effort. O fluxo de notificação continua best_effort por natureza,
mas ele não é um `DomainEvent` de produção nesta auditoria.

### reliable

Todos os eventos de produção atuais entram aqui. Eles não devem bloquear a transação principal, mas devem ser persistíveis e reprocessáveis.

### critical

Nenhum evento crítico foi encontrado nesta base para os fluxos auditados.

## Recomendação de priorização

1. `campo.tarefa.invalidada`
2. `campo.sync.falha`
3. `pecuaria.sync.falha`
4. `pecuaria.planejamento.sanitario.atualizado`
5. `pecuaria.vacinacao.registrada`

Todos os cinco pontos devem migrar para Outbox antes de qualquer novo fluxo crítico de estoque, fiscal ou financeiro.
