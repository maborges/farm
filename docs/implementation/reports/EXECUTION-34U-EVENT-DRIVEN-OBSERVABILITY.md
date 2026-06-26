# EXECUTION-34U - Event-Driven Observability MVP

## Objetivo

Adicionar uma camada leve de observabilidade para o Outbox Worker e a cadeia
event-driven, sem dependências externas e sem alterar os contratos centrais do
relay/publisher.

## Arquivos Criados

- `services/api/events/outbox_metrics.py`
- `services/api/events/outbox_observability.py`
- `services/api/tests/unit/events/test_outbox_observability.py`
- `docs/implementation/reports/EXECUTION-34U-EVENT-DRIVEN-OBSERVABILITY.md`

## Arquivos Alterados

- `services/api/events/outbox_worker.py`
- `services/api/events/__init__.py`
- `services/api/tests/unit/events/test_outbox_worker.py`
- `docs/operations/outbox-worker.md`

## Arquitetura

- `OutboxMetrics` mantém estado operacional em memória.
- `OutboxHealthStatus` classifica o estado do pipeline.
- `OutboxBacklogSnapshot` consulta o Outbox sem expor payload.
- O worker reutiliza a camada nova para heartbeat, `health` e `metrics`.
- O comando `stats` permanece compatível.

## Comandos Adicionados

- `python -m events.outbox_worker health`
- `python -m events.outbox_worker metrics`
- `python -m events.outbox_worker metrics --format json`

## Métricas Disponíveis

- `uptime_seconds`
- `cycles`
- `batches_processed`
- `events_processed`
- `events_failed`
- `errors`
- `current_backlog`
- `retries_seen`
- `last_batch_size`
- `max_batch_size`
- `average_batch_size`
- `throughput_per_minute`
- `last_success_at`
- `last_error_at`
- `last_error`

## Critérios de Health

- `OK`: backlog baixo, sem erro recente e com processamento normal.
- `DEGRADED`: erro recente, backlog acima do limite saudável, retries
  relevantes ou sucesso recente ausente.
- `CRITICAL`: backlog muito alto, retries excessivos ou erros recorrentes com
  ausência de sucesso recente.
- `UNKNOWN`: ausência de dados operacionais suficientes.

## Limitações

- Não há persistência de métricas.
- Não há endpoint HTTP de health/metrics.
- Não há Prometheus, OpenTelemetry, Grafana, CloudWatch ou Datadog.
- O estado é in-memory e por processo.

## Validações Executadas

- `services/api/.venv/bin/ruff check services/api/events services/api/tests/unit/events`
- `timeout 240s services/api/.venv/bin/pytest services/api/tests/unit/events -q`
- `git diff --check`

## Resultado

- O worker ganhou `health` e `metrics` sem alterar o `EventPublisher`, o
  Alert Engine, o Notification Dispatcher ou o Outbox Relay.
- O heartbeat do loop contínuo passou a carregar backlog, throughput e últimas
  ocorrências relevantes.
- O pipeline event-driven preservou o desenho original.
