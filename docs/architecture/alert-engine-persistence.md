# Alert Engine Persistence

Status: Canonical
Parent architecture: [alert-engine-architecture.md](./alert-engine-architecture.md)
Parent contracts: [alert-engine-contracts.md](./alert-engine-contracts.md)
Scope: Physical persistence model for the AgroSaaS Alert Engine

## 1. Purpose

This document defines the recommended physical persistence design for the Alert Engine.

It does not create tables, migrations, code, or endpoints. It specifies the storage model that future implementation work must follow.

## 2. MVP Physical Scope

### 2.1 Tables included in the MVP

The MVP should persist the core lifecycle and auditable state:

- `alert_events`
- `alert_indicators`
- `operational_alerts`
- `alert_insights`
- `alert_lifecycle_events`

### 2.2 Tables postponed

Deferred for a later phase:

- `alert_deliveries`

Reason:

- delivery is channel-specific infrastructure
- it is useful, but not required to validate the core Alert Engine loop
- it can be derived from alert status and delivery adapters in early stages

### 2.3 Virtual or on-demand in the beginning

May start as virtual or computed-on-read:

- some low-value indicators
- some transient insights
- delivery tracking per channel

Canonical rule:

- Events, alerts, and lifecycle actions are core persisted state.
- Indicators and insights should be persisted when they are reused, audited, or expensive to compute.
- Deliveries can be introduced after the core lifecycle is stable.

## 3. Physical Design Principles

- All core tables must be tenant-scoped.
- All tables that represent alert-owned operational memory must include `tenant_id`.
- Every persisted object must be traceable back to its source.
- Auditability is mandatory.
- Append-only patterns are preferred for immutable facts and lifecycle history.
- Update-in-place is allowed only for lifecycle state tables where the model explicitly represents current state.

## 4. Event Table

### 4.1 Table name

`alert_events`

### 4.2 Purpose

Append-only ledger of domain facts consumed by the Alert Engine.

### 4.3 Recommended columns

- `id UUID PK`
- `tenant_id UUID NOT NULL`
- `domain VARCHAR(20) NOT NULL`
- `category VARCHAR(20) NOT NULL`
- `source VARCHAR(120) NOT NULL`
- `source_id UUID NULL`
- `occurred_at TIMESTAMPTZ NOT NULL`
- `ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `actor_id UUID NULL`
- `entity_type VARCHAR(80) NULL`
- `entity_id UUID NULL`
- `payload JSONB NOT NULL`
- `correlation_id UUID NULL`
- `causation_id UUID NULL`
- `metadata JSONB NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

### 4.4 Primary key and foreign keys

- Primary key: `id`
- Suggested foreign keys:
  - `tenant_id` to tenant root table
  - `actor_id` to user/person table when available
  - `causation_id` self-reference to `alert_events.id`

### 4.5 Recommended indexes

- `(tenant_id, occurred_at DESC)`
- `(tenant_id, ingested_at DESC)`
- `(tenant_id, domain, occurred_at DESC)`
- `(tenant_id, category, occurred_at DESC)`
- `(tenant_id, source, source_id)`
- `(tenant_id, correlation_id)`
- `(tenant_id, causation_id)`

### 4.6 Constraints

- `domain` must match canonical enum values.
- `category` must match canonical enum values.
- `payload` must be a valid JSON object.
- `occurred_at` must be less than or equal to `ingested_at` unless a delayed import policy explicitly allows backfill.
- `source` cannot be empty.

### 4.7 Immutability

`alert_events` is append-only.

No `UPDATE` should be used for business correction.

Corrections are modeled by compensating events.

### 4.8 Retention

Events should have the longest retention of all Alert Engine records because they are the raw operational memory.

Recommended strategy:

- keep hot recent data indexed for fast query
- archive older partitions when needed
- never delete without a retention policy approved by governance

### 4.9 Partitioning future

Partitioning may be introduced later by:

- tenant-aware hash partitioning or
- time-based partitioning by `occurred_at`

Canonical recommendation:

- prefer time-based partitioning only after real volume justifies it
- keep the MVP unpartitioned unless the ingestion rate demands otherwise

## 5. Indicator Table

### 5.1 Table name

`alert_indicators`

### 5.2 Purpose

Stores materialized or reusable derived metrics.

### 5.3 Recommended columns

- `id UUID PK`
- `tenant_id UUID NOT NULL`
- `domain VARCHAR(20) NOT NULL`
- `category VARCHAR(20) NOT NULL`
- `key VARCHAR(120) NOT NULL`
- `label VARCHAR(160) NOT NULL`
- `value_numeric NUMERIC(18,6) NULL`
- `value_text TEXT NULL`
- `value_bool BOOLEAN NULL`
- `unit VARCHAR(40) NULL`
- `period_start TIMESTAMPTZ NULL`
- `period_end TIMESTAMPTZ NULL`
- `computed_at TIMESTAMPTZ NOT NULL`
- `inputs JSONB NOT NULL`
- `confidence NUMERIC(4,3) NULL`
- `metadata JSONB NULL`
- `calculation_version VARCHAR(40) NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

### 5.4 Polymorphic value model

Use one of the following value columns at a time:

- `value_numeric`
- `value_text`
- `value_bool`

Canonical rule:

- exactly one value column should be populated for a typed indicator
- null is acceptable only when the indicator is intentionally a marker without value

### 5.5 Provenance

`inputs` must preserve the source material used to compute the metric.

Recommended structure:

```json
[
  {
    "type": "EVENT",
    "id": "uuid",
    "weight": 1.0
  }
]
```

The exact JSON shape may evolve, but provenance is mandatory.

### 5.6 Versioning

`calculation_version` is required and must change whenever the formula, window, or normalization logic changes.

Versioning policy:

- semantic or controlled internal versioning is acceptable
- every stored indicator must be reproducible against the same version

### 5.7 Materialization policy

Persist indicators when:

- they feed alert rules
- they are used repeatedly in dashboards
- they are computationally expensive
- they must be historically comparable

Indicators may remain virtual when:

- they are trivial
- they are only needed for a single response
- they are cheap to derive and not reused

### 5.8 Recommended indexes

- `(tenant_id, key, computed_at DESC)`
- `(tenant_id, domain, computed_at DESC)`
- `(tenant_id, category, computed_at DESC)`
- `(tenant_id, period_start, period_end)`
- `(tenant_id, calculation_version)`

## 6. OperationalAlert Table

### 6.1 Table name

`operational_alerts`

### 6.2 Purpose

Stores the current alert state and lifecycle fields.

### 6.3 Recommended columns

- `id UUID PK`
- `tenant_id UUID NOT NULL`
- `unidade_produtiva_id UUID NULL`
- `domain VARCHAR(20) NOT NULL`
- `category VARCHAR(20) NOT NULL`
- `title VARCHAR(180) NOT NULL`
- `message TEXT NOT NULL`
- `severity VARCHAR(20) NOT NULL`
- `priority VARCHAR(20) NOT NULL`
- `status VARCHAR(20) NOT NULL`
- `confidence NUMERIC(4,3) NULL`
- `trigger_type VARCHAR(20) NOT NULL`
- `source_type VARCHAR(120) NOT NULL`
- `source_id VARCHAR(120) NOT NULL`
- `source_event_ids JSONB NOT NULL`
- `source_indicator_ids JSONB NOT NULL`
- `dedupe_key VARCHAR(160) NOT NULL`
- `action_label VARCHAR(120) NULL`
- `action_url TEXT NULL`
- `context JSONB NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- `expires_at TIMESTAMPTZ NULL`
- `acknowledged_at TIMESTAMPTZ NULL`
- `resolved_at TIMESTAMPTZ NULL`
- `acknowledged_by UUID NULL`
- `resolved_by UUID NULL`

### 6.4 Primary key and foreign keys

- Primary key: `id`
- Suggested foreign keys:
  - `tenant_id` to tenant root table
  - `unidade_produtiva_id` to production unit table
  - `acknowledged_by` to user/person table
  - `resolved_by` to user/person table

### 6.5 Recommended indexes

- `(tenant_id, status, updated_at DESC)`
- `(tenant_id, severity, priority, updated_at DESC)`
- `(tenant_id, domain, category, updated_at DESC)`
- `(tenant_id, source_type, source_id)`
- `(tenant_id, dedupe_key)`
- `(tenant_id, unidade_produtiva_id, status)`
- `(tenant_id, expires_at)`

### 6.6 Deduplication policy

Recommended canonical dedupe rule:

- unique active alert by `tenant_id + dedupe_key` for open-state alerts

Preferred implementation:

- partial unique index over active statuses

Conceptually:

- one active alert per dedupe key per tenant
- when the alert is resolved, expired, or cancelled, a new alert may be created again if the condition reappears

### 6.7 Status lifecycle

- `OPEN`
- `ACKNOWLEDGED`
- `SNOOZED`
- `RESOLVED`
- `EXPIRED`
- `CANCELLED`

State policy:

- open and acknowledged alerts remain active unless resolved, expired, or cancelled
- snoozed alerts remain active but hidden or deferred by consumer policy
- resolved alerts are historical and may reappear later as a new alert if the condition returns
- expired alerts may reappear as a new alert when the source condition is valid again
- cancelled alerts may reappear if they were cancelled as duplicates or invalidated by correction

### 6.8 Expiration policy

An alert may expire by:

- explicit `expires_at`
- rule policy window
- source condition invalidation

Expired alerts must remain auditable.

### 6.9 Action fields

`action_label` and `action_url` are optional but highly recommended for UI and Copilot surfaces.

### 6.10 Operational scope

`unidade_produtiva_id` is optional because:

- some alerts are tenant-wide
- some alerts are tied to a specific farm/unit
- some alerts only make sense at tenant or group scope

## 7. Insight Table

### 7.1 Table name

`alert_insights`

### 7.2 Purpose

Stores narrative interpretations that are reusable or auditable.

### 7.3 Recommended columns

- `id UUID PK`
- `tenant_id UUID NOT NULL`
- `domain VARCHAR(20) NOT NULL`
- `category VARCHAR(20) NOT NULL`
- `title VARCHAR(180) NOT NULL`
- `summary TEXT NOT NULL`
- `narrative TEXT NOT NULL`
- `severity VARCHAR(20) NULL`
- `priority VARCHAR(20) NULL`
- `confidence NUMERIC(4,3) NULL`
- `evidence_event_ids JSONB NOT NULL`
- `evidence_indicator_ids JSONB NOT NULL`
- `evidence_alert_ids JSONB NOT NULL`
- `generated_by VARCHAR(40) NOT NULL`
- `generated_at TIMESTAMPTZ NOT NULL`
- `expires_at TIMESTAMPTZ NULL`
- `metadata JSONB NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

### 7.4 Persistence policy

Persist insights when they are:

- reused across screens
- shown in Copilot memory
- used in notifications
- needed for audits or explanations
- expected to remain useful beyond a single request

Generate on-demand when they are:

- ephemeral
- highly contextual
- only needed for an interactive response

### 7.5 Narrative versioning

The narrative can evolve independently of the underlying facts.

Recommended strategy:

- preserve narrative text as stored history
- add `metadata.narrativeVersion`
- create a new insight when the interpretation materially changes

### 7.6 Copilot association future

For future Copilot conversation linking, the recommended approach is:

- `conversation_id` should be added only if a persistent conversation store is formalized
- until then, use `metadata` or a join table in a later phase

Canonical rule:

- do not force a premature coupling between insights and conversation state

## 8. Lifecycle Events Table

### 8.1 Table name

`alert_lifecycle_events`

### 8.2 Purpose

Immutable audit trail for alert state changes.

### 8.3 Recommended columns

- `id UUID PK`
- `tenant_id UUID NOT NULL`
- `alert_id UUID NOT NULL`
- `actor_id UUID NULL`
- `action_type VARCHAR(20) NOT NULL`
- `previous_status VARCHAR(20) NOT NULL`
- `new_status VARCHAR(20) NOT NULL`
- `payload JSONB NULL`
- `source_channel VARCHAR(40) NOT NULL`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`

### 8.4 Primary key and foreign keys

- Primary key: `id`
- Foreign key: `alert_id -> operational_alerts.id`
- Suggested foreign key: `tenant_id -> tenant root table`
- Suggested foreign key: `actor_id -> user/person table`

### 8.5 Recommended indexes

- `(tenant_id, alert_id, created_at DESC)`
- `(tenant_id, action_type, created_at DESC)`
- `(tenant_id, actor_id, created_at DESC)`

### 8.6 Audit rules

Every lifecycle action must create a lifecycle event record.

No lifecycle mutation is considered complete without an audit entry.

### 8.7 Permission policy future

The table does not enforce permissions itself, but it assumes:

- tenant isolation
- role-based authorization
- optional unit scope authorization

## 9. Alert Deliveries Table

### 9.1 Table name

`alert_deliveries`

### 9.2 MVP decision

Postponed for later phases.

### 9.3 Reason

Delivery is channel infrastructure, not core persistence for alert decisioning.

The MVP can rely on:

- current alert state
- lifecycle events
- channel adapters that log delivery externally

### 9.4 Future recommended columns

- `id UUID PK`
- `tenant_id UUID NOT NULL`
- `alert_id UUID NOT NULL`
- `channel VARCHAR(40) NOT NULL`
- `status VARCHAR(20) NOT NULL`
- `delivered_at TIMESTAMPTZ NULL`
- `read_at TIMESTAMPTZ NULL`
- `failed_at TIMESTAMPTZ NULL`
- `error_message TEXT NULL`
- `metadata JSONB NULL`

### 9.5 Future indexes

- `(tenant_id, alert_id, channel)`
- `(tenant_id, channel, status)`
- `(tenant_id, delivered_at DESC)`

## 10. RLS and Multi-Tenant Model

### 10.1 Tenant policy

Every table in this model must include `tenant_id`.

RLS should enforce:

- tenant-scoped reads
- tenant-scoped writes
- tenant-scoped updates
- tenant-scoped deletes where allowed

### 10.2 Unit scope policy

`unidade_produtiva_id` applies only to operationally scoped alerts.

Alerts without a unit scope are still tenant-scoped.

### 10.3 Cross-unit visibility within tenant

The engine must support cross-unit views inside the same tenant when the consumer has permission.

Implementation guidance:

- the physical model should support filtering by `tenant_id` alone
- optional filtering by `unidade_produtiva_id` narrows to a specific unit
- dashboards and Copilot can aggregate across units only inside the same tenant

### 10.4 Index compatibility

Every index must start with `tenant_id` or otherwise remain compatible with tenant-first filtering.

## 11. Dedupe Rules

### 11.1 Canonical dedupe key

`dedupe_key` is the canonical physical dedupe token.

Recommended generation factors:

- tenant
- domain
- category
- source_type
- source_id
- unit scope
- stable condition signature

### 11.2 Active-state dedupe

Recommended rule:

- only one active alert per `tenant_id + dedupe_key`

### 11.3 Reappearance rules

Resolved alerts can reappear:

- yes, as a new alert if the condition happens again

Expired alerts can reappear:

- yes, as a new alert if a new valid condition occurs

Snoozed alerts can be updated:

- yes, the same alert may change status or snooze window until it resolves or expires

Acknowledge keeps the alert active:

- yes, acknowledged alerts remain active and queryable

### 11.4 Partial uniqueness recommendation

Preferred physical enforcement:

- unique partial index over active statuses only

This prevents duplicate active alerts while allowing historical repetitions after closure.

## 12. Retention and Performance

### 12.1 Event retention

Longest retention.

Recommended:

- hot recent storage
- archive older partitions later
- governed deletion only if required by policy

### 12.2 Indicator retention

Medium retention.

Recommended:

- keep enough history for trend analysis
- prune if the indicator is superseded or too granular to preserve forever

### 12.3 Alert retention

Long retention for audit and operational history.

Recommended:

- retain full lifecycle state for alert history
- keep resolved and expired alerts queryable with pagination

### 12.4 Insight retention

Medium to long retention depending on whether the insight is reused by Copilot.

### 12.5 Lifecycle event retention

Long retention because it is the audit trail for status changes.

### 12.6 Partitioning future

Introduce partitioning only if real volume requires it.

Most likely first candidate:

- `alert_events`

Possible future partition axes:

- by time
- by tenant

### 12.7 Query limits

Canonical safeguards:

- default limit must be small and safe
- pagination must be required for broad list endpoints
- alert summaries should not scan unbounded historical sets in the online path

Suggested default list limit:

- 20 for standard views
- 5 for compact dashboard widgets

### 12.8 Pagination strategy

Use offset pagination for simple MVP query surfaces and cursor pagination later if scale requires it.

Canonical recommendation:

- start with offset pagination for implementation simplicity
- move to cursor pagination if alert volume or retention makes offset expensive

## 13. Compatibility With Dashboard and Copilot

### 13.1 `GET /api/v1/alerts`

Reads from:

- `operational_alerts`

May enrich with:

- lifecycle context
- latest insight references

### 13.2 `GET /api/v1/alerts/summary`

Reads from:

- `operational_alerts`

Potentially joins or aggregates:

- `alert_events` for provenance
- `alert_indicators` for metric context

### 13.3 Dashboard Geral

Dashboard Geral should primarily consume:

- active alerts
- summary by domain
- top alerts ordered by severity and priority

### 13.4 Copilot IA

Copilot should primarily consume:

- operational alerts
- indicators
- selected events for explanation
- insights for narrative memory

### 13.5 Campo/PWA

Campo should consume:

- alerts relevant to the unit or task scope
- lifecycle actions for acknowledgment or resolution when offline sync allows

The PWA must remain offline-first and should queue actions rather than bypassing the core engine.

## 14. Roadmap to Implementation

### EXECUTION-33C.1 - Migration MVP

Define and implement the core tables:

- `alert_events`
- `alert_indicators`
- `operational_alerts`
- `alert_insights`
- `alert_lifecycle_events`

### EXECUTION-33C.2 - Models and backend schemas

Define ORM models and API schemas aligned to this persistence model.

### EXECUTION-33C.3 - Lifecycle service

Implement the alert lifecycle state machine and dedupe policies.

### EXECUTION-33C.4 - Read and summary endpoints

Implement query, summary, and aggregation services.

### EXECUTION-33C.5 - First alert generators

Connect the first domain emitters to the engine:

- agriculture
- livestock
- finance
- operations

### EXECUTION-33C.6 - Delivery table and adapters

Introduce `alert_deliveries` when channel delivery tracking becomes necessary.

## 15. Canonical Summary

The physical model is intentionally layered:

- `alert_events` stores immutable facts
- `alert_indicators` stores reusable derived metrics
- `operational_alerts` stores current decision state
- `alert_insights` stores reusable narratives
- `alert_lifecycle_events` stores immutable alert audit history
- `alert_deliveries` is deferred until channel tracking is required

This gives AgroSaaS a persistence model that is auditable, tenant-safe, scalable, and compatible with dashboards, Copilot, and future channels.
