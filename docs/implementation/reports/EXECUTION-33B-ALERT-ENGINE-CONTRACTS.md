# EXECUTION-33B - Alert Engine Contracts

## Summary

This execution defined the canonical contract layer for the AgroSaaS Alert Engine.

The work was documentation-only. No code, endpoints, tables, or migrations were created or modified.

## Decisions

### Enums

- `Domain`: canonical in English for transport and interoperability
- `Category`: canonical in Portuguese for business semantics
- `Severity`: `INFO | WARNING | CRITICAL | EMERGENCY`
- `Priority`: `LOW | NORMAL | HIGH | URGENT`
- `AlertStatus`: `OPEN | ACKNOWLEDGED | SNOOZED | RESOLVED | EXPIRED | CANCELLED`
- `TriggerType`: `RULE | THRESHOLD | MODEL | MANUAL | SCHEDULE`
- `InsightGeneratedBy`: `RULE_ENGINE | ANALYTICS | COPILOT | HUMAN`

### Core contracts

- Event: immutable business fact
- Indicator: derived and optionally materialized metric
- OperationalAlert: lifecycle-managed decision object
- Insight: narrative interpretation with evidence

### Summary and query contracts

- `AlertSummary` defines dashboard aggregation
- `GET /api/v1/alerts` is the canonical list/query surface
- `GET /api/v1/alerts/summary` is the canonical summary surface

### Lifecycle actions

- acknowledge
- snooze
- resolve
- dismiss

All lifecycle operations require auditability and tenant isolation.

### Versioning

The canonical version is `v1`.
Extensions should use `metadata`.
Breaking changes require a new version and deprecation plan.

## Validation

- Documentation only
- No migrations created
- No endpoints created
- No frontend code changed
- No backend code changed
- No contract implementation added

