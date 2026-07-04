# OPS-INTELLIGENCE-05B - Contratos de Métricas para Dashboard

## Objetivo
Revisar e consolidar os contratos de retorno das métricas do Recommendation Engine para suportar um dashboard futuro, sem UI, sem frontend e sem Campo PWA.

## Auditoria Inicial

### EXISTE E ATENDE
- Os endpoints read-only já existiam em `services/api/recommendations/router.py`.
- Os contratos básicos de summary, distribuição por domínio, regras e lifecycle já estavam em `services/api/recommendations/schemas.py`.
- A base tenant-safe e read-only já estava implementada em `services/api/recommendations/metrics_service.py`.

### EXISTE PARCIALMENTE
- Os contratos ainda não expunham metadados explícitos de filtro.
- Não havia série temporal simples para consumo de dashboard.
- Os endpoints ainda não aceitavam filtros uniformes por período, domínio e unidade produtiva.

### NÃO EXISTE
- Dashboard/UI.
- Endpoints novos.
- Tabelas novas.
- Integração com providers, notificações ou alertas.

## Consolidação Feita
- Mantidos os endpoints existentes, sem quebra:
  - `GET /api/v1/recommendations/metrics/summary`
  - `GET /api/v1/recommendations/metrics/by-domain`
  - `GET /api/v1/recommendations/metrics/by-rule`
  - `GET /api/v1/recommendations/metrics/lifecycle`
- Adicionados filtros read-only e tenant-safe:
  - `start_date`
  - `end_date`
  - `domain`
  - `unidade_produtiva_id`
- Adicionados metadados de contrato:
  - `filters`
  - `generated_at`
- Adicionada timeline simples para dashboard futuro:
  - `summary.timeline`
  - `lifecycle.timeline`
- Mantida compatibilidade com os campos já consumidos:
  - `by_domain`
  - `by_status`
  - `by_priority`
  - `view_rate`
  - `accept_rate`
  - `dismiss_rate`
  - `execute_rate`
  - rankings por regra

## Arquivos Ajustados
- `services/api/recommendations/metrics_service.py`
- `services/api/recommendations/schemas.py`
- `services/api/recommendations/router.py`
- `services/api/recommendations/__init__.py`
- `services/api/tests/unit/recommendations/test_recommendations_metrics.py`

## Testes
- Validação específica:
  - `services/api/.venv/bin/python -m pytest services/api/tests/unit/recommendations/test_recommendations_metrics.py -q`
  - Resultado: `6 passed`
- Validação total do domínio:
  - `services/api/.venv/bin/python -m pytest services/api/tests/unit/recommendations -q`
  - Resultado: `41 passed`

## Garantias
- Read-only.
- Tenant-safe.
- Sem mutations operacionais.
- Sem providers.
- Sem notificações.
- Sem Alert Engine.
- Sem frontend.
- Sem Campo PWA.
- Sem endpoint novo.

