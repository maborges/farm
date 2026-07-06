# OPS-INTELLIGENCE-07 - Scheduler/Runner do Recommendation Engine

## Objetivo

Implementar a orquestração backend para execução controlada do `RecommendationEngine` global, com suporte a `tenant_id`, `unidade_produtiva_id`, filtro por domínio, `dry_run` e batch controlado, sem UI, sem notificações e sem Alert Engine.

## Auditoria Inicial

### `services/api/recommendations/`

- Classificação: `EXISTE PARCIALMENTE`
- Achado: já existiam `RecommendationEngine`, `registry`, `lifecycle_service`, `metrics_service`, `query_service` e providers registrados.
- Lacuna: não havia scheduler/runner/controlador dedicado para executar providers em modo operacional controlado.

### `services/api/alert_engine/scheduler.py`

- Classificação: `EXISTE PARCIALMENTE`
- Achado: existe um scheduler maduro para generators do Alert Engine, com batch, isolamento de erro e resumo agregado.
- Reuso: o padrão de resumo por execução e batch controlado foi usado como referência estrutural.

### `services/api/events/outbox_worker.py`

- Classificação: `EXISTE PARCIALMENTE`
- Achado: existe worker com CLI, dry run, logging operacional e agregação de resultado.
- Reuso: o padrão de controle de lote e isolamento de falhas foi reaproveitado conceitualmente.

### `services/api/events/outbox_observability.py`

- Classificação: `EXISTE PARCIALMENTE`
- Achado: existe camada de observabilidade agregada para backlog/health/metrics.
- Reuso: serviu como referência para manter contratos read-only e agregados estáveis.

### `services/api/core/`

- Classificação: `EXISTE PARCIALMENTE`
- Achado: existe contexto operacional e infra de jobs/background, mas nada específico para Recommendation Engine.

### Scheduler/runner específico de recommendations

- Classificação: `NÃO EXISTE`
- Conclusão: a orquestração estava ausente e precisou ser criada dentro de `services/api/recommendations/`.

## Implementação

### Arquivos criados

- [`services/api/recommendations/runner.py`](/opt/lampp/htdocs/farm/services/api/recommendations/runner.py)
- [`services/api/recommendations/scheduler.py`](/opt/lampp/htdocs/farm/services/api/recommendations/scheduler.py)
- [`services/api/tests/unit/recommendations/test_recommendations_scheduler_runner.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_scheduler_runner.py)
- [`docs/implementation/reports/OPS-INTELLIGENCE-07-SCHEDULER-RUNNER.md`](/opt/lampp/htdocs/farm/docs/implementation/reports/OPS-INTELLIGENCE-07-SCHEDULER-RUNNER.md)

### Arquivos alterados

- [`services/api/recommendations/engine.py`](/opt/lampp/htdocs/farm/services/api/recommendations/engine.py)
- [`services/api/recommendations/schemas.py`](/opt/lampp/htdocs/farm/services/api/recommendations/schemas.py)
- [`services/api/recommendations/__init__.py`](/opt/lampp/htdocs/farm/services/api/recommendations/__init__.py)
- [`services/api/tests/unit/recommendations/test_recommendations_anti_coupling.py`](/opt/lampp/htdocs/farm/services/api/tests/unit/recommendations/test_recommendations_anti_coupling.py)

## Contrato Implementado

- Execução controlada por `tenant_id`.
- Filtro opcional por `unidade_produtiva_id`.
- Filtro opcional por `domain`.
- `dry_run` sem persistência.
- Batch controlado por `batch_size` e `max_batches`.
- Execução por provider com isolamento de erro.
- Contadores agregados:
  - `candidates_total`
  - `recommendations_created`
  - `recommendations_updated`
  - `errors`
- Preservação de dedupe via `RecommendationEngine` e `RecommendationLifecycleService`.

## Garantias Técnicas

- Não cria provider novo.
- Não integra NotificationDispatcher.
- Não integra Alert Engine.
- Não altera frontend.
- Não altera Campo PWA.
- Não executa mutação operacional fora do engine já oficial.
- Não cria pipeline paralelo.

## Validação

### Executado com sucesso

- `cd services/api && .venv/bin/python -m py_compile recommendations/engine.py recommendations/runner.py recommendations/scheduler.py recommendations/schemas.py tests/unit/recommendations/test_recommendations_scheduler_runner.py tests/unit/recommendations/test_recommendations_anti_coupling.py`
- `cd services/api && .venv/bin/alembic heads`
- `git diff --check`

### Executado com falha no ambiente

- `cd services/api && .venv/bin/python -m pytest tests/unit/recommendations -q`

Observação: a suíte encontrou timeout de conexão com o banco no ambiente disponível durante a execução dos testes existentes do pacote, antes de concluir a bateria nova de scheduler/runner. A implementação nova compila e o diff está limpo, mas a execução completa do pytest depende da disponibilidade do banco do ambiente de teste.

