# EXECUTION-34A - Alert Engine Triggering Architecture

## Summary

This execution defined the canonical triggering architecture for the AgroSaaS Alert Engine.

The work was documentation-only. No code, migrations, endpoints, or frontend/backend contracts were changed.

## Decisions

### Trigger taxonomy

- Event-driven: immediate reaction to domain facts and failures
- Scheduled/periodic: time-based and threshold-based reevaluation
- On-demand: user or Copilot-requested analysis

### Source map

- Campo: task state, sync flow, and processing errors
- Pecuaria: lots, weighing, vaccination, sanitary cost, and planning
- Agricultura: operations, safra, talhoes, and execution traces
- Financeiro: launches, due dates, cash flow, and action plans
- ESG/Certificacoes: evidence, nonconformities, and expiring certificates

### Official strategy

- Hybrid architecture is the canonical model
- Event-driven for immediate facts
- Scheduled for time and threshold rules
- On-demand for consultative analysis

### Generator contract

- generators receive `tenant_id`
- optional `unidade_produtiva_id`
- optional `context`
- return counts for created, updated, ignored, and skipped alerts

### Dispatcher contract

- receives a domain event envelope
- resolves and executes eligible generators
- isolates failures per generator
- prefers post-commit or outbox-style execution

### Scheduler policy

- run by tenant and optionally by unit
- use paging and checkpointing
- remain idempotent
- keep heavy reevaluations outside user-facing request paths

### Transaction policy

- post-commit is the default
- same transaction is reserved for rare, explicitly critical invariants

### Rule classification

- Campo task overdue: hybrid
- Campo task invalidated: event-driven
- Campo sync failure: event-driven
- Pecuaria lot without weighing: scheduled
- Pecuaria vaccination overdue: hybrid
- Pecuaria high sanitary cost: scheduled

### Copilot role

- Copilot consumes alerts and insights
- Copilot does not author truth
- Copilot may request bounded on-demand refreshes
- Copilot does not execute automatic operational actions

## Roadmap

Recommended follow-up sequence:

1. EXECUTION-34B - Standardize generator interface
2. EXECUTION-34C - Scheduler MVP for Campo/Pecuaria
3. EXECUTION-34D - Post-commit dispatcher for critical events
4. EXECUTION-34E - Agriculture generators
5. EXECUTION-34F - Finance generators
6. EXECUTION-34G - Copilot alert consumption

## Validation

- Documentation only
- No migrations created
- No endpoints created
- No frontend code changed
- No backend code changed
- No implementation artifacts added
