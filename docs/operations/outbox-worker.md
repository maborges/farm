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
python -m events.outbox_worker status
python -m events.outbox_worker stats
```

Sem subcomando explícito, o worker assume `run`.

## Comandos

### `run`

Executa o relay em lotes controlados.

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

No modo `--verbose`, cada lote registra a sua própria duração e contagem.

## Troubleshooting

- Se o comando sair com `2`, revise os parâmetros e os valores numéricos.
- Se sair com `3`, o backlog existe, mas o lock não foi obtido.
- Se sair com `1`, verifique o erro operacional nos logs estruturados.
- Se sair com `130`, o processo recebeu `Ctrl+C` e encerrou de forma graciosa.

## Limitações Atuais

- Não há daemon persistente.
- Não há scheduler externo.
- Não há processamento distribuído.
- Não há dashboard de observabilidade.
- Retry e dead letter continuam delegados ao relay/outbox service.
