# Alert Engine Contracts

Status: Oficial
Parent architecture: [alert-engine-architecture.md](./alert-engine-architecture.md)
Scope: Contract layer for the AgroSaaS Alert Engine

## 1. Purpose

This document defines the oficial contracts of the Alert Engine before any implementation.

It does not define storage details, endpoints, or code. It defines the semantic API surface that future implementations must follow.

The Alert Engine contract layer covers:

- Event
- Indicator
- OperationalAlert
- Insight
- Alert Summary
- Alert Query
- Alert Lifecycle Actions

## 2. Oficial Enum Set

### 2.1 Domain

Oficial values:

```ts
type Domain = "AGRICULTURE" | "LIVESTOCK" | "FINANCE" | "OPERATIONS" | "FIELD" | "SYSTEM";
```

Decision:

- Use English tokens in contracts.
- Keep the user-facing labels localized in product UI.

Rationale:

- The backend already uses English technical identifiers extensively.
- English enum tokens reduce friction across APIs, services, logs, and future integrations.
- Portuguese is appropriate for labels and descriptions, not for transport-level identifiers.

### 2.2 Category

Oficial values:

```ts
type Category =
  | "SANITARIO"
  | "OPERACIONAL"
  | "ECONOMICO"
  | "FINANCEIRO"
  | "CLIMATICO"
  | "MANUTENCAO"
  | "GOVERNANCA"
  | "QUALIDADE"
  | "COMPLIANCE"
  | "PRODUCAO";
```

Decision:

- Keep Category in Portuguese.

Rationale:

- Category expresses product and business semantics, not transport semantics.
- These labels are already aligned with the business language used in AgroSaaS.

### 2.3 Severity

Oficial values:

```ts
type Severity = "INFO" | "WARNING" | "CRITICAL" | "EMERGENCY";
```

Meaning:

- INFO: informational condition
- WARNING: attention required
- CRITICAL: high-impact condition
- EMERGENCY: immediate critical response

### 2.4 Priority

Oficial values:

```ts
type Priority = "LOW" | "NORMAL" | "HIGH" | "URGENT";
```

Meaning:

- LOW: can wait
- NORMAL: standard follow-up
- HIGH: should be handled soon
- URGENT: immediate handling required

### 2.5 AlertStatus

Oficial values:

```ts
type AlertStatus = "OPEN" | "ACKNOWLEDGED" | "SNOOZED" | "RESOLVED" | "EXPIRED" | "CANCELLED";
```

### 2.6 TriggerType

Oficial values:

```ts
type TriggerType = "RULE" | "THRESHOLD" | "MODEL" | "MANUAL" | "SCHEDULE";
```

### 2.7 InsightGeneratedBy

Oficial values:

```ts
type InsightGeneratedBy = "RULE_ENGINE" | "ANALYTICS" | "COPILOT" | "HUMAN";
```

## 3. Oficial Event Contract

### 3.1 Contract

```ts
type Event = {
  id: string;
  tenantId: string;
  domain: Domain;
  category: Category;
  source: string;
  sourceId?: string;
  occurredAt: string;
  ingestedAt: string;
  actorId?: string;
  entityType?: string;
  entityId?: string;
  payload: Record<string, unknown>;
  correlationId?: string;
  causationId?: string;
  metadata?: Record<string, unknown>;
};
```

### 3.2 Required fields

- `id`
- `tenantId`
- `domain`
- `category`
- `source`
- `occurredAt`
- `ingestedAt`
- `payload`

### 3.3 Optional fields

- `sourceId`
- `actorId`
- `entityType`
- `entityId`
- `correlationId`
- `causationId`
- `metadata`

### 3.4 Validation rules

- `id` must be globally unique within the tenant namespace.
- `tenantId` must match the authenticated tenant context.
- `domain` must be one of the oficial enum values.
- `category` must be one of the oficial enum values.
- `source` must be a stable technical identifier of the origin.
- `occurredAt` must represent the moment the business fact happened.
- `ingestedAt` must represent the moment the Alert Engine received it.
- `payload` must never be empty when the event is intended for intelligence processing.
- `correlationId` groups related facts across domains.
- `causationId` links a derived event to the event that caused it.

### 3.5 Immutability rules

- An event is immutable after persistence.
- No field is edited in place.
- Corrections are modeled by new events.
- A correction event must reference the original event via `causationId` or `metadata.originalEventId`.

### 3.6 Compensating event rule

If a business fact must be corrected, the system emits a compensating event instead of mutating the original fact.

Examples:

- Pesagem lançada com peso incorreto -> emitir evento de correção de pesagem
- Vacinação registrada em lote errado -> emitir evento de estorno/correção e novo evento válido
- Lançamento financeiro duplicado -> emitir evento de estorno financeiro

### 3.7 Domain examples

Agriculture:

- operação agrícola executada
- safra alterada de fase
- talhão vinculado a safra

Livestock:

- pesagem realizada
- vacinação concluída
- movimentação de lote

Finance:

- lançamento financeiro registrado
- receita confirmada
- despesa aprovada

Operations:

- tarefa concluída
- manutenção executada
- equipamento sincronizado

Field:

- evento offline capturado
- fila de sincronização processada
- confirmação de visita em área

System:

- recalculo concluído
- ingestão falhou
- regra atualizada

## 4. Oficial Indicator Contract

### 4.1 Contract

```ts
type Indicator = {
  id: string;
  tenantId: string;
  domain: Domain;
  category: Category;
  key: string;
  label: string;
  value: number | string | boolean | null;
  unit?: string;
  periodStart?: string;
  periodEnd?: string;
  computedAt: string;
  inputs: string[];
  confidence?: number;
  metadata?: Record<string, unknown>;
};
```

### 4.2 Required fields

- `id`
- `tenantId`
- `domain`
- `category`
- `key`
- `label`
- `value`
- `computedAt`
- `inputs`

### 4.3 Optional fields

- `unit`
- `periodStart`
- `periodEnd`
- `confidence`
- `metadata`

### 4.4 Validation rules

- `key` must be stable and machine-friendly.
- `label` must be human-readable.
- `value` may be numeric, textual, boolean, or null.
- `inputs` must contain the source event IDs or source materialization IDs used to compute the indicator.
- `computedAt` must be the exact timestamp of the computation or materialization.
- `periodStart` and `periodEnd` define the analytical window when the indicator is temporal.
- `confidence`, when present, must be between `0.0` and `1.0`.

### 4.5 Periodicity

Indicators may be:

- event-driven
- periodic
- on-demand
- hybrid

Oficial rule:

- If the metric is cheap and only needed inside a single request, it can be computed on demand.
- If the metric is reused, audited, or compared over time, it should be materialized.

### 4.6 Provenance rule

Every materialized indicator must preserve provenance through `inputs`.

This allows replay, audit, and explainability.

### 4.7 Versioning of calculation

Indicator computation must be versioned through `metadata`, for example:

```ts
metadata: {
  calculationVersion: "1.0.0",
  algorithm: "gmd_window_30d",
}
```

Versioning is mandatory when the formula may change over time.

### 4.8 Materialization guidance

Persist indicators when they are:

- used by alert rules
- shown in dashboards frequently
- needed for trend analysis
- expensive to compute
- necessary for historical reproducibility

Examples:

- GMD médio
- custo sanitário
- tarefas atrasadas
- saldo financeiro

## 5. Oficial OperationalAlert Contract

### 5.1 Contract

```ts
type OperationalAlert = {
  id: string;
  tenantId: string;
  domain: Domain;
  category: Category;
  title: string;
  message: string;
  severity: Severity;
  priority: Priority;
  status: AlertStatus;
  confidence?: number;
  triggerType: TriggerType;
  sourceType: string;
  sourceId: string;
  sourceEventIds: string[];
  sourceIndicatorIds: string[];
  dedupeKey: string;
  actionLabel?: string;
  actionUrl?: string;
  unidadeProdutivaId?: string;
  context?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
  expiresAt?: string;
  acknowledgedAt?: string;
  resolvedAt?: string;
  acknowledgedBy?: string;
  resolvedBy?: string;
};
```

### 5.2 Required fields

- `id`
- `tenantId`
- `domain`
- `category`
- `title`
- `message`
- `severity`
- `priority`
- `status`
- `triggerType`
- `sourceType`
- `sourceId`
- `sourceEventIds`
- `sourceIndicatorIds`
- `dedupeKey`
- `createdAt`
- `updatedAt`

### 5.3 Optional fields

- `confidence`
- `actionLabel`
- `actionUrl`
- `unidadeProdutivaId`
- `context`
- `expiresAt`
- `acknowledgedAt`
- `resolvedAt`
- `acknowledgedBy`
- `resolvedBy`

### 5.4 Validation rules

- `title` must be short and operationally clear.
- `message` must explain the condition and the reason for the alert.
- `sourceType` identifies the origin class, such as a domain service, model, or rule pack.
- `sourceId` identifies the exact origin instance.
- `sourceEventIds` must list every event that contributed to the alert.
- `sourceIndicatorIds` must list every indicator that contributed to the alert.
- `dedupeKey` must be stable across repeated evaluations of the same condition.
- `confidence`, when present, must be between `0.0` and `1.0`.

### 5.5 Dedupe rule

Alerts must not be duplicated when the same condition is re-evaluated and still valid.

The engine should reuse the same alert when:

- `dedupeKey` matches
- tenant matches
- source scope matches
- the alert is still open or snoozed

The engine should create a new alert when:

- the condition materially changes
- the original alert expired or resolved
- the scope changed

### 5.6 Expiration rule

An alert expires when:

- the business condition is no longer valid
- the policy window ends
- the rule policy marks it as stale
- the source evidence is superseded

Expired alerts remain in history and do not disappear from audit trails.

### 5.7 Status rule

- `OPEN`: created and awaiting action
- `ACKNOWLEDGED`: seen or triaged by a user or automation
- `SNOOZED`: temporarily deferred
- `RESOLVED`: condition resolved
- `EXPIRED`: no longer active by policy
- `CANCELLED`: invalidated by correction or supersession

### 5.8 Source examples

Lote sem pesagem:

- domain: `LIVESTOCK`
- category: `PRODUCAO`
- severity: `WARNING`
- priority: `HIGH`

Vacinação atrasada:

- domain: `LIVESTOCK`
- category: `SANITARIO`
- severity: `CRITICAL`
- priority: `URGENT`

Tarefa atrasada:

- domain: `OPERATIONS`
- category: `OPERACIONAL`
- severity: `WARNING`
- priority: `HIGH`

Caixa negativo:

- domain: `FINANCE`
- category: `FINANCEIRO`
- severity: `CRITICAL`
- priority: `URGENT`

### 5.9 Action fields

`actionLabel` and `actionUrl` provide the oficial next step exposed to UI and Copilot.

Examples:

- `actionLabel: "Registrar pesagem"`
- `actionUrl: "/dashboard/pecuaria/lotes/{id}/pesagens"`

These fields are hints for consumers. They do not replace access control.

## 6. Oficial Insight Contract

### 6.1 Contract

```ts
type Insight = {
  id: string;
  tenantId: string;
  domain: Domain;
  category: Category;
  title: string;
  summary: string;
  narrative: string;
  severity?: Severity;
  priority?: Priority;
  confidence?: number;
  evidence: {
    eventIds: string[];
    indicatorIds: string[];
    alertIds: string[];
  };
  generatedBy: InsightGeneratedBy;
  generatedAt: string;
  expiresAt?: string;
  metadata?: Record<string, unknown>;
};
```

### 6.2 Required fields

- `id`
- `tenantId`
- `domain`
- `category`
- `title`
- `summary`
- `narrative`
- `evidence`
- `generatedBy`
- `generatedAt`

### 6.3 Optional fields

- `severity`
- `priority`
- `confidence`
- `expiresAt`
- `metadata`

### 6.4 Validation rules

- `summary` must be concise and user-facing.
- `narrative` must explain the interpretation in plain language.
- `evidence.eventIds` may be empty only for purely synthetic insights.
- `evidence.indicatorIds` should exist when the insight derives from metric analysis.
- `evidence.alertIds` should exist when the insight is reacting to an alert.
- `generatedBy` must identify the producer class.
- `confidence`, when present, must be between `0.0` and `1.0`.

### 6.5 Persisted vs on-demand

Persist the insight when it will be:

- reused by Copilot
- shown on dashboards
- stored in history
- audited later
- delivered through notifications

Generate on-demand when the insight is:

- highly contextual
- ephemeral
- only needed for a single interaction

### 6.6 Copilot association

The Copilot can consume insights as:

- explanation cache
- narrative summary
- conversation context
- recommendation memory

But the Copilot must never treat an insight as the source of truth if the underlying events or indicators are available.

### 6.7 Examples

- Custo sanitário subiu
- Lote perdeu desempenho
- Fluxo de caixa crítico

## 7. Alert Summary Contract

### 7.1 Contract

```ts
type AlertSummary = {
  totalOpen: number;
  maxSeverity: Severity | null;
  maxPriority: Priority | null;
  mostCriticalDomain?: Domain;
  byDomain: Record<Domain, {
    open: number;
    critical: number;
    urgent: number;
  }>;
  topAlerts: OperationalAlert[];
};
```

### 7.2 Summary rules

- `totalOpen` counts only alerts whose status is `OPEN`, `ACKNOWLEDGED`, or `SNOOZED` depending on consumer policy.
- `maxSeverity` reflects the highest severity among open alerts.
- `maxPriority` reflects the highest priority among open alerts.
- `mostCriticalDomain` identifies the domain with the highest weighted open risk.
- `byDomain` must always include all oficial domains.
- `topAlerts` must be ordered by severity, then priority, then recency.

### 7.3 Ordering rule for `topAlerts`

Default ordering:

1. severity descending
2. priority descending
3. createdAt descending

The result must be stable and deterministic.

### 7.4 Default limit

Default `topAlerts` limit:

- 5 for dashboard summary cards
- 10 for expandable views

The exact limit is a consumer choice, but the oficial default for compact surfaces is 5.

### 7.5 Filters

Summary may accept the same scope filters as the query API, but only to constrain the aggregate.

### 7.6 No-alert behavior

When no alerts exist:

- `totalOpen = 0`
- `maxSeverity = null`
- `maxPriority = null`
- `mostCriticalDomain = undefined`
- `byDomain` must still return every domain with zero counts
- `topAlerts = []`

## 8. Alert Query API

### 8.1 Oficial query surface

```http
GET /api/v1/alerts
```

### 8.2 Supported filters

- `domain`
- `category`
- `severity`
- `priority`
- `status`
- `sourceType`
- `sourceId`
- `dateFrom`
- `dateTo`
- `limit`
- `offset`

### 8.3 Query rules

- Filters are combinable.
- Unspecified filters must not narrow the result.
- Date filters operate on `createdAt` unless the consumer explicitly requests another temporal field.
- `limit` must have a safe default.
- `offset` must be non-negative.
- Query results must respect tenant isolation.

### 8.4 Oficial response shape

The oficial list response is a paginated envelope:

```ts
type AlertQueryResponse = {
  items: OperationalAlert[];
  total: number;
  limit: number;
  offset: number;
};
```

### 8.5 Sorting

Default ordering for the list endpoint:

1. severity descending
2. priority descending
3. createdAt descending

Consumers may request alternative sorts later, but the oficial default must remain action-first.

### 8.6 Summary endpoint

```http
GET /api/v1/alerts/summary
```

The summary endpoint returns `AlertSummary` and may reuse the same filtering contract as the list endpoint.

## 9. Alert Lifecycle Actions

### 9.1 Oficial actions

```http
POST /api/v1/alerts/{id}/acknowledge
POST /api/v1/alerts/{id}/snooze
POST /api/v1/alerts/{id}/resolve
POST /api/v1/alerts/{id}/dismiss
```

### 9.2 Acknowledge

Purpose:
Mark the alert as seen or triaged.

Payload:

```ts
type AcknowledgeAlertPayload = {
  comment?: string;
};
```

Status change:

- `OPEN` -> `ACKNOWLEDGED`
- `SNOOZED` -> `ACKNOWLEDGED` if policy allows

Who can execute:

- authorized user
- automation with triage permission

Auditing:

- actor
- timestamp
- comment
- previous status

### 9.3 Snooze

Purpose:
Temporarily defer the alert.

Payload:

```ts
type SnoozeAlertPayload = {
  until: string;
  reason?: string;
};
```

Status change:

- `OPEN` -> `SNOOZED`
- `ACKNOWLEDGED` -> `SNOOZED`

Rules:

- `until` must be in the future
- snooze must be bounded in time

### 9.4 Resolve

Purpose:
Close the alert because the underlying condition was addressed.

Payload:

```ts
type ResolveAlertPayload = {
  resolutionNote?: string;
};
```

Status change:

- `OPEN` -> `RESOLVED`
- `ACKNOWLEDGED` -> `RESOLVED`
- `SNOOZED` -> `RESOLVED`

Rules:

- resolution should reference the action or event that fixed the condition when available

### 9.5 Dismiss

Purpose:
Remove the alert from active consideration because it was invalid, duplicated, or superseded.

Payload:

```ts
type DismissAlertPayload = {
  reason?: string;
};
```

Status change:

- `OPEN` -> `CANCELLED`
- `ACKNOWLEDGED` -> `CANCELLED`
- `SNOOZED` -> `CANCELLED`

Rules:

- dismiss is not the same as resolve
- dismiss should be reserved for invalid, duplicated, or superseded alerts

### 9.6 Permission model

The action executor must be checked against:

- tenant access
- domain access
- unit access when `unidadeProdutivaId` is present
- role or permission policy

### 9.7 Audit requirements

Every lifecycle action must record:

- tenantId
- alertId
- actorId
- action type
- payload
- previous status
- new status
- timestamp
- source channel

## 10. Security and Multi-Tenant Rules

### 10.1 Tenant isolation

All Alert Engine contracts are tenant-scoped.

No query, summary, or lifecycle action may cross tenant boundaries.

### 10.2 Unit of production scope

`unidadeProdutivaId`, when present, scopes the alert to the operational entity within the tenant.

It is optional because some alerts are tenant-wide or domain-wide.

### 10.3 Visibility

Visibility depends on:

- tenant
- unit of production
- role
- explicit permission
- channel policy

### 10.4 RLS future policy

The implementation should use RLS-aligned persistence where applicable.

The contract layer does not define database mechanics, but it assumes:

- tenant-scoped reads
- tenant-scoped writes
- no bypass of tenant context

### 10.5 Audit

The contract layer assumes all operations are auditable and traceable.

Audit data is part of the lifecycle, not optional metadata.

## 11. Versioning

### 11.1 Contract version

Oficial contract version:

```text
v1
```

### 11.2 Compatibility policy

- Additive changes are allowed when they do not break current consumers.
- Removing or renaming required fields is a breaking change.
- Enum expansion is allowed only if consumers can tolerate unknown values.

### 11.3 Extension policy

- Use `metadata` for non-breaking extensions.
- Do not overload required fields with mixed semantics.
- If a field becomes core to the contract, promote it from `metadata` to first-class schema in a future version.

### 11.4 Breaking change policy

Breaking changes require:

- new version
- migration plan for consumers
- explicit deprecation timeline
- documentation update

## 12. Oficial Summary

The contract layer is intentionally strict:

- Event records facts
- Indicator materializes derived metrics
- OperationalAlert manages lifecycle and actionability
- Insight explains meaning
- AlertSummary compresses the current state
- Alert Query exposes scoped retrieval
- Lifecycle actions change alert status with auditability

The Copilot consumes these contracts. It does not own them.
