# EXECUTION-34F - Domain Events Integration

## Resumo

A EXECUTION-34F integrou os fluxos reais de Campo e Pecuária à fundação canônica de Domain Events.
Os Domain Services continuam sem depender diretamente do Alert Engine, e a publicação agora ocorre
de forma post-commit, com isolamento de falhas via `publish_domain_event_safe(...)`.

## Arquivos Criados

- `services/api/events/helpers.py`
- `services/api/tests/unit/campo/test_campo_domain_events.py`
- `services/api/tests/unit/pecuaria/test_pecuaria_domain_events.py`

## Arquivos Alterados

- `services/api/events/__init__.py`
- `services/api/campo/router.py`
- `services/api/pecuaria/routers/manejos.py`
- `services/api/pecuaria/services/manejo_sync_service.py`
- `services/api/tests/unit/events/test_events_fundation.py`

## Pontos de Publicação

- `campo.tarefa.invalidada` em `services/api/campo/router.py`, após `commit` e `refresh` da tarefa invalidada.
- `campo.sync.falha` em `services/api/campo/router.py`, após persistência do estado de falha no sync.
- `campo.sync.falha` em `services/api/pecuaria/services/manejo_sync_service.py`, quando o resultado do sync é `ERROR`.
- `pecuaria.planejamento.sanitario.atualizado` em `services/api/pecuaria/routers/manejos.py`, após `commit`.
- `pecuaria.vacinacao.registrada` em `services/api/pecuaria/services/manejo_sync_service.py`, após `commit`.

## Garantias de Post-Commit

- Os eventos são publicados somente após a confirmação da mutação principal.
- A publicação não força commit adicional em fluxos já transacionais.
- Falhas na publicação são isoladas por `publish_domain_event_safe(...)`.

## Testes Executados

- `pytest services/api/tests/unit/events -q`
- `pytest services/api/tests/unit/campo/test_campo_domain_events.py -q`
- `pytest services/api/tests/unit/pecuaria/test_pecuaria_domain_events.py -q`
- `pytest services/api/tests/unit/alert_engine -q`
- `pytest services/api/tests/integration/alert_engine -q`

## Validações Executadas

- `git diff --check`
- `ruff check` nos arquivos novos e alterados relevantes
- `mypy` restrito aos módulos de produção tocados nesta execução
- `pytest services/api/tests/unit/events -q` -> passou
- `pytest services/api/tests/unit/campo/test_campo_domain_events.py -q` -> passou
- `pytest services/api/tests/unit/pecuaria/test_pecuaria_domain_events.py -q` -> passou
- `pytest services/api/tests/unit/events/test_events_anti_acoplamento.py -q` -> passou
- `pytest services/api/tests/unit/alert_engine/test_alert_engine_dispatcher.py -q` -> 1 falha ambiental em teste que exige acesso a banco/socket no sandbox
- `pytest services/api/tests/unit/alert_engine -q` e `pytest services/api/tests/integration/alert_engine -q` permanecem sujeitos ao mesmo limite ambiental

## Limitações Conhecidas

- A fundação continua in-memory.
- Não existe Outbox, fila, worker externo ou retry automático.
- Alguns testes amplos do Alert Engine e de integração podem falhar em sandbox por acesso a banco/socket.
- O baseline de `ruff` e `mypy` do repositório possui ruído legado fora do escopo desta execução.

## Confirmações

- Nenhuma regra de negócio foi alterada.
- Nenhum endpoint público foi alterado.
- Nenhuma migration foi criada.
- Os Domain Services continuam sem depender diretamente de `AlertDispatcherService`.
