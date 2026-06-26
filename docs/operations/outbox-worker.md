# Outbox Worker

## Visão Geral

O Outbox Worker processa eventos persistidos na `domain_event_outbox` fora do fluxo das requisições.
Ele usa o `DomainEventOutboxRelay` e mantém `EventPublisher` como ponto comum de fan-out.

## Arquitetura

```text
DomainEventOutbox
  -> DomainEventOutboxRelay
  -> EventPublisher
  -> Subscribers
```

O worker é apenas a camada operacional.
Ele não conhece Alert Engine, Notification Dispatcher, generators ou adapters.

## Como Executar

```bash
python -m events.outbox_worker --help
python -m events.outbox_worker run --batch-size 50 --max-batches 1
python -m events.outbox_worker run --loop
python -m events.outbox_worker run --loop --interval 5
python -m events.outbox_worker run --loop --heartbeat 60
python -m events.outbox_worker run --loop --max-runtime 300
python -m events.outbox_worker health
python -m events.outbox_worker metrics
python -m events.outbox_worker metrics --format json
python -m events.outbox_worker status
python -m events.outbox_worker stats
```

Sem subcomando explícito, o worker assume `run`.

## Comandos

### `run`

Executa o relay em lotes controlados.

Com `--loop`, o worker permanece executando indefinidamente e reutiliza
`run_outbox_relay_once(...)` em ciclos sucessivos.

### `status`

Mostra um snapshot rápido do backlog:

- `pending`
- `processing`
- `failed`
- `dead_letter`
- `processed`

### `stats`

Mostra agregados do backlog:

- total por status
- total por `event_type`
- total por `tenant`
- backlog estimado

### `health`

Mostra um resumo operacional amigável:

- status geral
- backlog
- retries
- última execução bem-sucedida
- último erro
- recomendação operacional

### `metrics`

Mostra métricas operacionais da cadeia event-driven.

Por padrão a saída é em texto. Use `--format json` para integração com scripts.

## Parâmetros

### Comuns

- `--tenant-id`
- `--event-type`
- `--verbose`

### `run`

- `--batch-size`
- `--max-batches`
- `--locked-by`
- `--stop-on-error`
- `--dry-run`
- `--loop`
- `--interval`
- `--backoff`
- `--max-backoff`
- `--heartbeat`
- `--max-runtime`

### `metrics`

- `--format`

## Exit Codes

- `0`: execução bem-sucedida
- `1`: erro operacional
- `2`: erro de configuração ou argumentos inválidos
- `3`: lock não obtido
- `4`: erro inesperado
- `130`: interrupção por `KeyboardInterrupt`

## Dry Run

Use `--dry-run` para listar eventos candidatos sem:

- chamar `EventPublisher`
- alterar status
- persistir mudanças

Exemplo:

```bash
python -m events.outbox_worker run --dry-run --batch-size 20
```

## Logs

Os logs estruturados incluem:

- `worker_run_id`
- `start_time`
- `finish_time`
- `duration_ms`
- `batch_size`
- `max_batches`
- `tenant_id`
- `event_type`
- `processed`
- `failed`
- `dead_letter`
- `skipped`
- `warnings`

No modo contínuo, também são emitidos:

- `worker starting`
- `batch processed`
- `worker alive`
- `processing failed`
- `worker stopped gracefully`

No modo `--verbose`, cada lote registra a sua própria duração e contagem.

### Heartbeat

O heartbeat é configurável via `--heartbeat` e registra um snapshot em memória:

- `uptime`
- `cycles`
- `batches_processed`
- `events_processed`
- `errors`
- `last_success`
- `last_error`
- `last_error_at`
- `current_backlog`
- `retries_seen`
- `throughput_per_minute`
- `average_batch_size`

## Observabilidade Operacional

Os comandos `health` e `metrics` reutilizam a camada de observabilidade em
memória e o snapshot do Outbox.

Exemplos:

```bash
python -m events.outbox_worker health
python -m events.outbox_worker metrics
python -m events.outbox_worker metrics --format json
python -m events.outbox_worker run --loop --heartbeat 60
```

Saída esperada do `health`:

```text
Outbox Worker Health

Status: OK
Backlog: 4
Retries: 0
Pending: 4
Last success: 2026-06-26T10:12:00
Last error: none

Recommendation:
No action required.
```

Métricas mínimas expostas:

- uptime
- cycles
- batches processed
- events processed
- events failed
- errors
- backlog
- retries
- throughput per minute
- average batch size

### Backoff

Em caso de erro no loop contínuo, o worker aplica backoff exponencial:

- primeiro erro: `5s`
- segundo: `10s`
- terceiro: `20s`
- quarto: `40s`
- máximo: `60s`

## Troubleshooting

- Se o comando sair com `2`, revise os parâmetros e os valores numéricos.
- Se sair com `3`, o backlog existe, mas o lock não foi obtido.
- Se sair com `1`, verifique o erro operacional nos logs estruturados.
- Se sair com `130`, o processo recebeu `Ctrl+C` e encerrou de forma graciosa.
- Se usar `--max-runtime`, o processo encerra sozinho ao atingir o limite.

## Limitações Atuais

- O modo contínuo ainda é in-memory e por processo.
- Não há scheduler externo.
- Não há processamento distribuído.
- Não há dashboard de observabilidade.
- Não há persistência de métricas nem endpoint HTTP de health/metrics.
- Retry e dead letter continuam delegados ao relay/outbox service.
