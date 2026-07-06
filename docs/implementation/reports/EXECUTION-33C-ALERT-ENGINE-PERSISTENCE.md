# EXECUTION-33C - Alert Engine Persistence

## Summary

This execution defined the oficial physical persistence model for the AgroSaaS Alert Engine.

The work was documentation-only. No code, endpoints, tables, or migrations were created or modified.

## Decisions

### MVP scope

Included in MVP:

- `alert_events`
- `alert_indicators`
- `operational_alerts`
- `alert_insights`
- `alert_lifecycle_events`

Deferred:

- `alert_deliveries`

### Physical model

- `alert_events` is append-only and immutable
- `alert_indicators` stores materialized reusable metrics with provenance and calculation versioning
- `operational_alerts` stores current alert state and dedupe key
- `alert_insights` stores reusable narrative interpretations
- `alert_lifecycle_events` stores immutable audit history of state changes

### Dedupe

The recommended physical dedupe rule is:

- one active alert per `tenant_id + dedupe_key`

Best-enforced by a partial unique index over active statuses.

### Retention

- Events: longest retention
- Indicators: medium retention
- Alerts: long retention
- Insights: medium to long retention
- Lifecycle events: long retention
- Deliveries: future phase

### Multi-tenant and RLS

All tables must include `tenant_id`.
All access is tenant-scoped.
`unidade_produtiva_id` is optional and used only when the alert is unit-scoped.

### Compatibility

The physical model is designed to feed:

- `GET /api/v1/alerts`
- `GET /api/v1/alerts/summary`
- Dashboard Geral
- Copiloto IA
- Campo/PWA

## Roadmap

Recommended next steps:

1. EXECUTION-33C.1 - Migration MVP
2. EXECUTION-33C.2 - Models and backend schemas
3. EXECUTION-33C.3 - Lifecycle service
4. EXECUTION-33C.4 - Read and summary endpoints
5. EXECUTION-33C.5 - First alert generators
6. EXECUTION-33C.6 - Delivery table and adapters

## Validation

- Documentation only
- No migrations created
- No endpoints created
- No frontend code changed
- No backend code changed
- No contract implementation added

