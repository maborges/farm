# EXECUTION-34Q - Operational CLI para Outbox Worker

## Melhorias implementadas

- CLI oficial para o worker do Outbox.
- Subcomandos `run`, `status` e `stats`.
- `--dry-run` para inspeção sem efeitos colaterais.
- `--verbose` para detalhamento por lote.
- exit codes padronizados.
- logging operacional com contexto estruturado.
- documentação operacional para operadores.

## Comandos suportados

- `python -m events.outbox_worker --help`
- `python -m events.outbox_worker run`
- `python -m events.outbox_worker status`
- `python -m events.outbox_worker stats`

## Parâmetros

- `--batch-size`
- `--max-batches`
- `--locked-by`
- `--tenant-id`
- `--event-type`
- `--stop-on-error`
- `--dry-run`
- `--verbose`

## Exit Codes

- `0`: sucesso
- `1`: erro operacional
- `2`: erro de configuração ou argumentos inválidos
- `3`: lock não obtido
- `4`: erro inesperado
- `130`: interrupção graciosa por `KeyboardInterrupt`

## Exemplos

```bash
python -m events.outbox_worker run --batch-size 20 --max-batches 5 --locked-by outbox-worker-1
python -m events.outbox_worker run --dry-run --tenant-id 00000000-0000-0000-0000-000000000000
python -m events.outbox_worker status
python -m events.outbox_worker stats --event-type campo.sync.falha
```

## Limitações

- O worker continua processando de forma local e programática.
- Não há daemon externo.
- Não há fila externa.
- Não há dashboard.
- Não há alteração do núcleo do Outbox, Relay, EventPublisher ou Subscribers.

## Validações

- `ruff check` nos arquivos tocados: OK.
- `mypy` nos arquivos tocados: OK.
- `pytest services/api/tests/unit/events/test_outbox_worker.py -q`: OK.
- `pytest services/api/tests/unit/events -q`: OK.
- `git diff --check`: OK.

## Observação

Essa execução melhora exclusivamente a camada operacional.
O comportamento do Relay e da persistência transacional permanece inalterado.
