# Domain Events Inventory

## Escopo da auditoria

Este inventário cobre os `DomainEvent` publicados atualmente no código de produção em `services/api`.
A busca encontrou quatro tipos de evento de domínio em produção, com cinco pontos de emissão concretos.
Não foram encontrados outros `event_type` publicados fora dos fluxos abaixo.

## Inventário

| event_type | domínio | produtor | arquivo / linha aproximada | consumidor atual | subscriber | criticidade | modelo atual | payload mínimo | idempotency key sugerida | observações |
|---|---|---|---|---|---|---|---|---|---|---|
| `campo.tarefa.invalidada` | Campo | `services/api/campo/router.py` | `campo/router.py:74-92` | `AlertDispatcherService` via `AlertEngineEventSubscriber` | `AlertEngineEventSubscriber` | operacional | reliable | `status_anterior`, `status_novo`, `motivo`, `tarefa_id`, `module`, `type` | `campo:tarefa.invalidada:{tarefa_id}` | Publicado após `commit`, sem bloquear o fluxo principal. |
| `campo.sync.falha` | Campo | `services/api/campo/router.py` | `campo/router.py:95-117` | `AlertDispatcherService` via `AlertEngineEventSubscriber` | `AlertEngineEventSubscriber` | operacional | reliable | `sync_status`, `error_type`, `error_message`, `origin`, `tarefa_id`, `module`, `type` | `campo:sync.falha:{tarefa_id}` | Falha do sync pós-commit. |
| `campo.sync.falha` | Pecuária | `services/api/pecuaria/services/manejo_sync_service.py` | `manejo_sync_service.py:532-561` | `AlertDispatcherService` via `AlertEngineEventSubscriber` | `AlertEngineEventSubscriber` | operacional | reliable | `error_type`, `error_message`, `origin`, `local_id`, `status` | `pecuaria:sync.falha:{tarefa_campo_id}` | Segundo ponto de emissão para o mesmo `event_type`, com payload diferente. |
| `pecuaria.planejamento.sanitario.atualizado` | Pecuária | `services/api/pecuaria/routers/manejos.py` | `manejos.py:29-56` | `AlertDispatcherService` via `AlertEngineEventSubscriber` | `AlertEngineEventSubscriber` | operacional | reliable | `tipo`, `lote_id`, `lote_identificacao`, `operador_id`, `produto_id`, `dose`, `unidade_medida`, `data_programada`, `quantidade_animais`, `observacoes` | `pecuaria:planejamento.sanitario.atualizado:{tarefa_campo_id}` | Publicado somente para planejamento de vacinação. |
| `pecuaria.vacinacao.registrada` | Pecuária | `services/api/pecuaria/services/manejo_sync_service.py` | `manejo_sync_service.py:563-598` | `AlertDispatcherService` via `AlertEngineEventSubscriber` | `AlertEngineEventSubscriber` | operacional | reliable | `tarefa_campo_id`, `lote_id`, `animal_id`, `animal_count`, `produto_id`, `produto_nome`, `dose`, `unidade_medida`, `via_aplicacao`, `data_aplicacao` | `pecuaria:vacinacao.registrada:{tarefa_campo_id}` | Evento emitido após vacinação concluída e persistida. |

## Adjacências não produtivas

- `notifications.dispatch` aparece apenas como contrato de integração e em testes do `NotificationEventSubscriber`.
- Não há publicação produtiva desse `event_type` nos fluxos auditados.

## Conclusão do inventário

- Eventos únicos de produção encontrados: `campo.tarefa.invalidada`, `campo.sync.falha`, `pecuaria.planejamento.sanitario.atualizado`, `pecuaria.vacinacao.registrada`.
- Pontos concretos de emissão: cinco.
- Consumidor atual de produção: `AlertEngineEventSubscriber`.
- Canal de notificação atual: ainda não recebe eventos de produção; permanece preparado para integração futura.
