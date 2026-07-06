# EXECUTION-33A - Alert Engine Architecture

## Summary

This execution established the oficial architecture for the AgroSaaS Alert Engine.

No code, migrations, endpoints, or frontend/backend contracts were changed.

## Decisions

### Official intelligence chain

The oficial lifecycle is:

```text
Evento -> Indicador -> Alerta -> Insight -> Copiloto IA -> Usuário -> Ação -> Evento
```

This keeps the loop closed and makes the Alert Engine transversal across Agriculture, Livestock, Finance, Operations, and Field.

### Core concept definitions

- Event: immutable fact
- Indicator: derived metric
- Alert: actionable condition with lifecycle
- Insight: interpretive narrative

### Cross-cutting attributes

- Priority: action urgency
- Severity: condition seriousness
- Confidence: certainty score from 0.0 to 1.0
- Category: domain-independent condition taxonomy

### Copilot role

Copilot is only an interpreter and consumer.
It does not create events, indicators, or alerts.

### Persistence policy

- Events: always persist
- Indicators: persist when analytically valuable
- Alerts: always persist
- Insights: persist when useful for memory, audit, or reuse

### Integration policy

Copilot should prioritize alerts, then indicators, then events, then insights depending on the question.

## Roadmap

Recommended follow-up sequence:

1. EXECUTION-33B - Oficial Contracts
2. EXECUTION-33C - Persistence Model
3. EXECUTION-33D - Dashboard Consumption
4. EXECUTION-33E - Copilot Consumption
5. EXECUTION-33F - Field/PWA Consumption
6. EXECUTION-33G - Notifications
7. EXECUTION-33H - WhatsApp Adapter
8. EXECUTION-33I - Automation Adapters

## Validation

- Documentation only
- No implementation artifacts created
- No database schema changes
- No API contract changes
- No frontend changes
- No backend changes

