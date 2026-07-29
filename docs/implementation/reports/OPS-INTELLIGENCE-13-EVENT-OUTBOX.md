# OPS-INTELLIGENCE-13 — Ativação Reativa por Domain Events e Outbox

Data: 2026-07-29  
Status: concluído — GO

## Auditoria da infraestrutura

O caminho oficial reutilizado é `publish_domain_event_safe` → `DomainEventOutboxService` → `DomainEventOutboxRelay` → `EventPublisher` → `EventSubscriberRegistry`. O relay reconstrói o `DomainEvent`, isola subscribers e delega retry/backoff/dead-letter ao Outbox. O motor reutilizado é `RecommendationEngine`, registry, `RecommendationLifecycleService`, dedupe ativo por `tenant_id + dedupe_key` e bridge de notificação do próprio engine.

## Eventos inventariados e seleção

| Evento | Domínio | Provider acionado | Escopo | Dados suficientes? | Risco | Selecionado? |
| --- | --- | --- | --- | --- | --- | --- |
| `campo.sync.falha` | Campo | `campo` | `sync_campo`/tarefa e unidade | Sim | Baixo: fato concluído e contrato estável | Sim |
| `campo.tarefa.invalidada` | Campo | — | tarefa | Parcial | Provider não possui regra reativa específica | Não |
| `pecuaria.reproducao.registrada` | Pecuária | — | evento animal | Parcial | Falta mapeamento aderente ao provider | Não |
| `pecuaria.vacinacao.registrada` | Pecuária | — | tarefa/unidade | Parcial | Exige critério reativo próprio | Não |
| `pecuaria.planejamento.sanitario.atualizado` | Pecuária | — | planejamento | Parcial | Sem regra reativa específica | Não |
| `integrations.sync_completed` | Integrações | — | configuração/job | Não | Sem escopo operacional de provider | Não |
| `agricola.climatico.sync_realizado` | Clima | — | variável | Não comprovado | Sem publicação Outbox ativa verificada | Não |

Foi ativado somente o menor conjunto seguro: um evento publicado, com tenant, escopo e regra de provider já existente; nenhum payload ou regra foi inventado.

## Arquitetura implementada

- `RecommendationEventMapper` reconhece eventos elegíveis, valida tenant e escopo e cria `RecommendationSignal` e `OperationalContext`.
- `RecommendationEventSubscriber` é registrado no `EventSubscriberRegistry` existente e aciona o engine com o provider focado.
- `events.subscribers` apenas importa o subscriber no caminho de registro padrão; não foi criado registry, worker, fila ou Outbox adicional.
- O subscriber não contém regra de provider, persistência direta, mutação operacional ou dispatch direto de notificação.

## Idempotência, RLS e falhas

O Outbox preserva idempotência por evento; em redelivery, o lifecycle deduplica por `tenant_id + dedupe_key` e atualiza o resultado ativo. O `event_id` é preservado em `signal_id`, `source_signal_ids`, payload e contexto. Antes da primeira query do provider, o subscriber executa `set_config('app.current_tenant_id', ..., true)` a partir do tenant validado no evento; o escopo expira no commit do relay, sem `SET` global ou bypass de RLS.

Eventos desconhecidos retornam `ignored`; contratos incompletos retornam `rejected`, ambos sem retry. Falhas de engine/provider retornam `errors`, permitindo ao relay aplicar retry/backoff oficial. O publisher mantém isolamento entre subscribers.

## Telemetria

O subscriber registra `event_id`, `event_type`, `tenant_id`, escopo, providers, criações, atualizações, falhas, duração, tentativa quando disponível e outcome (`processed`, `ignored`, `rejected` ou `failed`), sem payload completo. O relay preserva attempts e erro por linha de Outbox.

## Arquivos alterados

- `services/api/recommendations/event_mapper.py`
- `services/api/recommendations/event_subscriber.py`
- `services/api/events/subscribers.py`
- `services/api/tests/unit/recommendations/test_recommendations_event_outbox.py`
- `docs/architecture/OPS-INTELLIGENCE-ARCH-01.md`
- `docs/implementation/reports/OPS-INTELLIGENCE-13-EVENT-OUTBOX.md`

Não foram alterados scheduler, worker periódico de recomendações, advisory lock, lifecycle funcional, providers, tabelas, migrations, API, Web, Campo ou a infraestrutura existente de Event/Outbox.

## Testes e evidências

```text
pytest tests/unit/recommendations/test_recommendations_event_outbox.py -q
6 passed, 1 deselected

pytest tests/unit/events/test_events_fundation.py tests/unit/events/test_domain_event_outbox.py -q
27 passed

pytest tests/unit/recommendations -q
50 passed, 31 deselected

pytest tests/unit/recommendations -m integration -q
31 passed, 50 deselected
```

O teste PostgreSQL cobre `DomainEvent -> Outbox -> Relay -> RecommendationEventSubscriber -> CampoRecommendationProvider -> RecommendationResult`, com tenant, RLS, lifecycle inicial `CREATED`, preservação do event id e redelivery sem duplicação. `py_compile` e `ruff check` dos arquivos Python alterados passaram.

## Limitações e próximos eventos

A ativação é deliberadamente focada em `campo.sync.falha`. Próximos candidatos são `pecuaria.vacinacao.registrada` e `campo.tarefa.invalidada`, após regras reativas explícitas; depois `agricola.climatico.sync_realizado`, quando publicação Outbox e escopo de unidade forem comprovados.

## Veredicto

**GO.** O caminho reativo complementa a reconciliação periódica sem infraestrutura paralela nem alteração do scheduler aprovado.
