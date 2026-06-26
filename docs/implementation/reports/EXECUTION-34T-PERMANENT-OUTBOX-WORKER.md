# EXECUTION-34T - Permanent Outbox Worker

## Objetivo

Adicionar modo de execução contínua ao Outbox Worker sem alterar a arquitetura
central de eventos, o `DomainEventOutboxRelay` ou os contratos públicos
existentes.

## Arquitetura

- O comando `run` continua sendo o ponto de entrada do worker.
- O novo modo `run --loop` reutiliza exclusivamente `run_outbox_relay_once(...)`.
- O loop contínuo controla intervalo, backoff, heartbeat e runtime máximo.
- Estatísticas operacionais permanecem em memória por processo.

Fluxo:

```text
CLI -> run_outbox_relay_once(...)
CLI -> loop contínuo -> run_outbox_relay_once(...) em ciclos
```

## Arquivos Criados

- Nenhum arquivo novo de código.

## Arquivos Alterados

- `services/api/events/outbox_worker.py`
- `services/api/events/__init__.py`
- `services/api/tests/unit/events/test_outbox_worker.py`
- `docs/operations/outbox-worker.md`

## Fluxo Operacional

- `run` sem `--loop` mantém o comportamento anterior.
- `run --loop` executa ciclos sucessivos com pausa configurável por `--interval`.
- Em erro, o worker aplica backoff exponencial entre ciclos.
- O heartbeat registra o estado operacional do processo em intervalos
  configuráveis.
- `--max-runtime` encerra automaticamente a execução contínua.
- `SIGINT` e `SIGTERM` disparam desligamento gracioso sem interromper lote em
  andamento.

## Novos Parâmetros

- `--loop`
- `--interval`
- `--backoff`
- `--max-backoff`
- `--heartbeat`
- `--max-runtime`

## Decisões Técnicas

- Reuso integral de `run_outbox_relay_once(...)` para evitar duplicação de
  lógica.
- `WorkerStats` em memória para acompanhar ciclos, batches, eventos, erros e
  timestamps de última atividade.
- Handlers de sinal instalados no event loop para preservar encerramento
  gracioso.
- Backoff exponencial limitado por teto configurável.
- Nenhuma persistência adicional foi introduzida.

## Limitações

- O modo contínuo é por processo e não persiste estatísticas.
- Não há fila de trabalho distribuída nem scheduler externo.
- Não há métricas Prometheus, OpenTelemetry ou dead letter nova.

## Validações Executadas

- `services/api/.venv/bin/ruff check services/api/events services/api/tests/unit/events`
- `services/api/.venv/bin/pytest services/api/tests/unit/events -q`
- `timeout 240s services/api/.venv/bin/pytest services/api/tests/unit/events -q`
- `git diff --check`

## Resultado

- O worker ganhou modo permanente sem alterar `run_outbox_relay_once(...)`.
- A compatibilidade com `run`, `status`, `stats`, `--dry-run` e `--verbose`
  foi preservada.
- O comportamento orientado a eventos permaneceu intacto.
