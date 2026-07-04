# OPS-INTELLIGENCE-05 - Telemetria e Governança Operacional

## Objetivo
Implementar telemetria, métricas e governança operacional do Recommendation Engine global sem alterar frontend, Campo PWA, NotificationDispatcher, Alert Engine ou o lifecycle canônico.

## Auditoria Inicial

### EXISTE E ATENDE
- `services/api/recommendations/models.py` já possui `recommendation_results` e `recommendation_lifecycle_events`.
- `services/api/recommendations/lifecycle_service.py` já grava o lifecycle explícito e mantém trilha imutável dos eventos.
- `services/api/core/services/audit_service.py` já fornece auditoria tenant-aware reutilizável.
- `services/api/core/models/tenant_audit_log.py` já materializa o audit log por tenant.

### EXISTE PARCIALMENTE
- `services/api/core/observability.py` já oferece observability transversal, mas focada em request logging e performance.
- `services/api/events/outbox_metrics.py` e `services/api/events/outbox_observability.py` já fornecem padrão operacional read-only para outro domínio.

### NÃO EXISTE
- Camada específica de métricas de recommendations por tenant, domínio, status, prioridade, lifecycle e leaderboard por regra.
- Endpoints read-only de governança para Recommendation Engine.

## Implementação
- Adicionado `services/api/recommendations/metrics_service.py` com agregações read-only sobre `recommendation_results` e `recommendation_lifecycle_events`.
- Expandido `services/api/recommendations/schemas.py` com contratos de summary, domínio, regra e lifecycle.
- Expandidos os endpoints em `services/api/recommendations/router.py`:
  - `GET /api/v1/recommendations/metrics/summary`
  - `GET /api/v1/recommendations/metrics/by-domain`
  - `GET /api/v1/recommendations/metrics/by-rule`
  - `GET /api/v1/recommendations/metrics/lifecycle`
- Reexportado o novo contrato em `services/api/recommendations/__init__.py`.

## Garantias
- Read-only.
- Tenant-safe.
- Não chama providers.
- Não integra Alert Engine.
- Não integra NotificationDispatcher.
- Não recalcula recomendações.
- Não altera frontend nem Campo PWA.

## Testes
- Criado `services/api/tests/unit/recommendations/test_recommendations_metrics.py`.
- Reforçado anti-acoplamento em `services/api/tests/unit/recommendations/test_recommendations_anti_coupling.py`.
- Coberturas validadas:
  - métricas por tenant
  - proteção cross-tenant
  - agregação por domínio
  - agregação por status
  - agregação por prioridade
  - taxa de aceite
  - taxa de descarte
  - taxa de execução
  - tempo médio até view/accept/execute
  - leaderboard por regra
  - lifecycle operacional
  - anti-acoplamento com providers/alertas/notificações

## Validação
- `services/api/.venv/bin/pytest services/api/tests/unit/recommendations/test_recommendations_metrics.py -q`
  - Resultado: `5 passed in 69.66s`

