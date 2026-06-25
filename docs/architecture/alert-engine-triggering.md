# Alert Engine Triggering

Status: Canonical
Scope: Arquitetura oficial de disparo do Alert Engine
Applies to: Agriculture, Livestock, Finance, Operations, Field/PWA, Copilot IA, Notifications, External APIs

## 1. Purpose

This document defines when and by whom the Alert Engine generators must run in AgroSaaS.

It complements:

- `docs/architecture/alert-engine-architecture.md`
- `docs/architecture/alert-engine-contracts.md`
- `docs/architecture/alert-engine-persistence.md`

The Alert Engine is not a dashboard concern. It is the shared intelligence infrastructure that consumes facts, computes indicators, evaluates conditions, and materializes alerts and insights.

## 2. Canonical Trigger Taxonomy

Alert generation is divided into three official trigger classes.

### 2.1 Event-driven alerts

These run immediately or near-immediately after a domain fact is committed.

Typical examples:

- Campo sync failed
- task invalidated
- financial due date crossed by a domain event
- vaccination recorded with an inconsistency
- agricultural operation completed with divergence

Best use:

- irreversible facts
- failures
- status transitions
- corrections
- explicit domain events

### 2.2 Scheduled / periodic alerts

These run on a cadence and reevaluate time-dependent or threshold-based conditions.

Typical examples:

- lot without weighing for 45 days
- high sanitary cost per head
- GMD below target
- crop without movement
- cash flow critical
- certification expiring soon

Best use:

- conditions that depend on time passing
- thresholds that must be recomputed
- indicators that are cheaper to batch
- rules that should not block the source transaction

### 2.3 On-demand alerts

These run only when a user or Copilot explicitly requests fresh analysis for a bounded scope.

Typical examples:

- lot analysis
- crop analysis
- financial diagnosis
- Copilot refresh after a follow-up question

Best use:

- exploratory analysis
- interactive diagnostics
- expensive computations that should not run continuously

## 3. Source Producers Map

The sources below already exist or are natural producers of signals.

### 3.1 Campo

Primary signal sources:

- `TarefaCampo`
- sync push/pull flow
- task status changes
- processing errors

Canonical existing services:

- `services/api/campo/service.py`
- `services/api/campo/router.py`
- `services/api/pecuaria/routers/campo_sync.py`

Signal type:

- `TarefaCampo` is both an event source and a trigger source
- sync errors are immediate event sources

### 3.2 Pecuaria

Primary signal sources:

- `EventoAnimal`
- pesagens
- vaccination planning and execution
- sanitary cost accumulation
- handling planning
- lots and animals

Canonical existing services:

- `services/api/pecuaria/services/lote_indicadores_service.py`
- `services/api/pecuaria/services/lote_resumo_sanitario_service.py`
- `services/api/pecuaria/services/manejo_planejamento_service.py`
- `services/api/pecuaria/services/manejo_sync_service.py`

Signal type:

- some facts are event sources
- some are indicator sources
- some are both, depending on the rule

### 3.3 Agricultura

Primary signal sources:

- operations
- safra
- talhoes
- application events
- harvest events
- input usage
- recommendations

Signal type:

- mostly event sources today
- indicators may be derived through adapter services

### 3.4 Financeiro

Primary signal sources:

- lancamentos
- vencimentos
- fluxo de caixa
- plano de acao
- existing intelligent financial alerts

Signal type:

- strong event source
- strong periodic indicator source

### 3.5 ESG / Certifications

Primary signal sources:

- evidences
- nonconformities
- action plans
- expiring certificates

Signal type:

- event source
- periodic deadline source

## 4. Trigger Strategy Comparison

### 4.1 Option A - Disparo dentro do sync Campo

Pattern:

```text
Campo Sync -> Generator -> Alert Engine
```

Advantages:

- low latency for sync failures
- easy to attach to Campo flows

Disadvantages:

- strong coupling to sync internals
- rollback risk if alert logic fails
- harder to preserve offline-first guarantees
- encourages domain-specific alert logic in transport code

Decision:

- acceptable only for local, immediate post-sync signals
- not the canonical architecture for the whole platform

### 4.2 Option B - Disparo dentro dos services de dominio

Pattern:

```text
Domain Service -> Generator -> Alert Engine
```

Advantages:

- simple to understand
- easy to start
- keeps logic close to the source

Disadvantages:

- spreads alert logic across modules
- harder to standardize
- risks domain-service bloat
- duplicates timing and retry concerns

Decision:

- acceptable for small, explicit, high-signal events
- not the preferred long-term coordination model

### 4.3 Option C - Dispatcher de eventos de dominio

Pattern:

```text
Domain Service -> Domain Event -> Alert Dispatcher -> Generators -> Alert Engine
```

Advantages:

- best long-term decoupling
- supports multiple consumers
- reusable for Copilot and notifications later
- centralizes routing and observability

Disadvantages:

- more moving parts
- requires event envelope discipline
- usually benefits from outbox or post-commit dispatch

Decision:

- canonical direction for event-driven alerts
- recommended backbone for future growth

### 4.4 Option D - Scheduler periodico

Pattern:

```text
Cron / Job -> Generators -> Alert Engine
```

Advantages:

- ideal for time-based rules
- easy to batch by tenant or unit
- naturally idempotent

Disadvantages:

- latency between condition and alert
- requires job orchestration
- may scan many tenants if poorly chunked

Decision:

- canonical for periodic and threshold checks

### 4.5 Option E - Hybrid

Pattern:

```text
Event-driven + Scheduled + On-demand
```

Decision:

- this is the official architecture
- event-driven for immediate facts
- scheduled for time and threshold reevaluation
- on-demand for consultative analysis

## 5. Official Architecture Recommendation

### 5.1 Canonical trigger model

- Event-driven for explicit domain facts and failures
- Scheduled for time-based and threshold-based conditions
- On-demand for analysis and Copilot refresh

### 5.2 What each domain should do

#### Campo

- emit facts and sync results
- do not own alert policy
- do not run heavy global scans inside user request flow

#### Pecuaria

- publish relevant facts and indicators
- can trigger narrow post-commit evaluations for immediate facts
- scheduled sweeps should cover time-based conditions

#### Agricultura

- emit operational facts and derived metrics
- use the dispatcher for event-driven signals when available
- use scheduled scans for agronomic thresholds and deadlines

#### Financeiro

- emit financial events and due-date changes
- scheduled evaluations should cover critical balances and overdue items

#### ESG / Certifications

- emit compliance facts
- scheduled checks should govern expiration and deadline conditions

### 5.3 How to avoid coupling with Campo

- Campo must not know alert internals beyond a narrow integration point
- Campo sync should never own alert policy
- alert generation should happen post-commit or through a dispatcher
- failures in alert generation must not break offline-first sync unless explicitly required

### 5.4 How to avoid coupling with IA

- Copilot must not create events
- Copilot must not recompute core indicators by default
- Copilot may request on-demand refreshes through a bounded generator contract
- Copilot is a consumer and interpreter, not a producer of truth

### 5.5 How to avoid duplicate alerts

- every generator must use stable `dedupe_key`
- Alert Engine must reuse active alerts when the condition is still valid
- resolved, expired, or cancelled alerts may reappear as new alerts
- scheduled jobs must be idempotent by design

## 6. Canonical Generator Contract

Generators are domain signal executors. They do not own persistence rules; they call the Alert Engine service.

### 6.1 Conceptual interface

```python
class AlertGenerator:
    async def run(self, tenant_id, unidade_produtiva_id=None, context=None):
        ...
```

### 6.2 Required parameters

- `tenant_id`
- optional `unidade_produtiva_id`

### 6.3 Optional context

`context` may carry:

- `event_id`
- `batch_id`
- `source_type`
- `dry_run`
- `scope`
- `reason`

### 6.4 Expected return

Generators should return a structured result with:

- created count
- updated count
- ignored count
- skipped count
- warnings or non-fatal issues

### 6.5 Expected errors

Generators may raise:

- tenant violation
- business rule violation
- validation error
- infrastructure error

Generators should isolate per-item failures when running batches.

## 7. Canonical Dispatcher Contract

The dispatcher is the routing and execution coordinator for event-driven generators.

### 7.1 Conceptual interface

```python
class AlertDispatcher:
    async def dispatch(self, event, tenant_id, context=None):
        ...
```

### 7.2 Responsibilities

- receive a domain event envelope
- resolve eligible generators
- execute generators
- isolate failures per generator
- log structured execution metadata
- avoid breaking the source flow unless the event is explicitly critical

### 7.3 Dispatcher rules

- dispatcher routing must be deterministic
- one event may fan out to multiple generators
- a generator failure should be contained unless the source transaction requires strict coupling
- dispatcher should favor post-commit execution or outbox consumption

## 8. Canonical Scheduler Architecture

### 8.1 Where it should run

Recommended runtime:

- Celery Beat
- cron-like admin jobs
- background worker tasks

### 8.2 Cadence policy

Recommended cadences:

- near-real-time jobs: every 5 to 15 minutes
- operational sweeps: hourly
- broad tenant sweeps: daily
- expensive cross-domain analyses: nightly or on-demand

### 8.3 Execution scope

Schedulers should support:

- by tenant
- by unit
- by domain
- by generator family
- by time window

### 8.4 Cost controls

Schedulers must:

- page tenants and units
- enforce per-run limits
- checkpoint progress
- remain idempotent
- avoid full-table scans when indexes are available

## 9. Transactional Policy

### 9.1 Same transaction

Use only when alert generation is a strict invariant of the source write.

Pros:

- strong consistency

Cons:

- alert failure can break the main domain operation
- risky for high-volume or cross-module logic

### 9.2 Post-commit

This is the recommended default.

Pros:

- does not block the source domain
- safer for cross-module execution
- easier to retry and observe

Cons:

- eventual consistency

### 9.3 Official decision

- default to post-commit execution
- reserve same-transaction execution for rare, explicitly critical cases
- prefer outbox or queued dispatch where consistency matters

## 10. Rule Classification for Existing Generators

### 10.1 Campo rules

#### Task overdue

- classification: hybrid
- reason: it is time-driven, but can also be reevaluated after task creation/update

#### Task invalidated

- classification: event-driven
- reason: the state transition itself is the signal

#### Sync failure

- classification: event-driven
- reason: it originates from an immediate processing error

### 10.2 Pecuaria rules

#### Lot without weighing

- classification: scheduled
- reason: depends on elapsed time and periodic reevaluation

#### Vaccination overdue

- classification: hybrid
- reason: it can react to schedule changes and time passing

#### High sanitary cost

- classification: scheduled
- reason: it depends on aggregated indicators and threshold checks

### 10.3 Why this classification is official

- immediate failures should not wait for a nightly sweep
- time-based thresholds should not depend only on writes
- consultative analysis should remain optional and bounded

## 11. Copilot Integration Policy

Copilot must consume alerts and insights, not generate truth by default.

### 11.1 Default behavior

- read alert summaries first
- read alert lists when detailed context is necessary
- read indicators or events only when the summary is insufficient

### 11.2 On-demand refresh

Copilot may request a refresh when:

- the user explicitly asks for fresh diagnostics
- the current alert cache is stale
- the target analysis is bounded to a tenant and optional unit scope

### 11.3 Prohibited behavior

- Copilot must not run heavy global scans implicitly
- Copilot must not auto-execute operational actions
- Copilot must not create events, indicators, or alerts directly

### 11.4 Interpreter rule

Copilot interprets:

- Event -> context
- Indicator -> measurement
- Alert -> actionability
- Insight -> narrative

It does not author operational truth.

## 12. Roadmap

Recommended roadmap:

### EXECUTION-34B

Standardize generator interface and registry.

### EXECUTION-34C

Scheduler MVP for Campo and Pecuaria periodic checks.

### EXECUTION-34D

Post-commit dispatcher for critical domain events.

### EXECUTION-34E

Agriculture generators.

### EXECUTION-34F

Finance generators.

### EXECUTION-34G

Copilot consuming enriched alerts and on-demand refresh hooks.

### Future extensions

- notification adapters
- WhatsApp adapters
- external API adapters
- delivery tracking

## 13. Canonical Conclusion

The official Alert Engine triggering architecture is hybrid:

- event-driven for immediate domain facts and failures
- scheduled for time-based and threshold-based reevaluation
- on-demand for consultative analysis and Copilot refresh

The long-term backbone should be a dispatcher plus scheduled execution, with post-commit execution as the default transaction policy.

