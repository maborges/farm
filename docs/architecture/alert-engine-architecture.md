# Alert Engine Architecture

Status: Canonical
Scope: AgroSaaS multi-domain intelligence infrastructure
Applies to: Agriculture, Livestock, Finance, Operational, Field/PWA, Notifications, Copilot IA, External APIs

## 1. Purpose

The Alert Engine is the transversal intelligence infrastructure of AgroSaaS.

It is responsible for converting raw domain facts into actionable decision layers:

```text
Evento
  -> Indicador
  -> Alerta
  -> Insight
  -> Copiloto IA
  -> Usuário
  -> Ação
  -> Evento
```

This is the official closed-loop lifecycle.

The sequence covers all domains because every domain can emit events, produce indicators, generate alerts, create insights, and expose them to the Copilot and to the user. The resulting action can create new events, closing the loop.

## 2. Architectural Boundary

The Central de Alertas does not belong to any dashboard.

It is a shared domain service consumed by:

- Dashboard Geral
- Dashboards Especializados
- Copiloto IA
- Campo (PWA)
- Notificações
- WhatsApp adapters in the future
- Automation engines in the future
- External APIs in the future

Dashboards only present or filter the intelligence. They do not own the intelligence lifecycle.

## 3. Official Chain of Intelligence

### 3.1 Canonical chain

```text
Evento -> Indicador -> Alerta -> Insight -> Copiloto IA -> Usuário
```

### 3.2 Canonical feedback loop

```text
Usuário -> Ação -> Evento
```

### 3.3 Coverage assessment

The chain covers:

- Agriculture: pesagens, vacinação, operações, safra, talhão, produção
- Livestock: lotes, ganho de peso, sanidade, manejo, mortalidade
- Finance: lançamentos, caixa, margem, orçamento, inadimplência, DRE
- Operational: tarefas, manutenção, execução, atrasos, sincronização
- Field/PWA: offline actions, sync queue, confirmations, capture events

No additional intelligence layer is required between Indicador and Alerta, because the Alert Engine itself already performs rule evaluation and threshold interpretation.

However, two non-intelligence transport layers must be recognized:

- Ingestion layer: receives events from domains and external integrations
- Delivery layer: distributes alerts and insights to channels

These are infrastructure layers, not conceptual intelligence layers.

## 4. Canonical Concepts

### 4.1 Evento

Definition:
An immutable fact captured from a domain or integration.

Responsibility:
Record that something happened, when it happened, where it happened, and under which context.

Producer:

- Domain services
- User actions
- Sync workers
- Integrations
- Automation jobs
- Device/field submissions

Consumer:

- Indicator engine
- Alert engine
- Insight engine
- Audit and traceability
- Copilot context resolution

Persistence:

- Persisted as append-only ledger
- Never edited in place
- Corrections are represented by new events

AgroSaaS examples:

- pesagem realizada
- vacinação concluída
- operação agrícola executada
- lançamento financeiro registrado
- sincronização Campo recebida

Can it be altered?
No. An event must not be altered after persistence.

Can it be recalculated?
No. The event is not recalculated. Only derived layers are recalculated.

Is it immutable?
Yes. Immutability is mandatory.

Recommended rule:
If something was wrong, emit a compensating event or correction event rather than mutating the original fact.

### 4.2 Indicador

Definition:
A derived metric computed from one or more events, snapshots, or business states.

Responsibility:
Summarize operational reality into measurable values.

Producer:

- Indicator engine
- Domain services when a metric is cheap and deterministic
- Scheduled recomputation jobs

Consumer:

- Alert engine
- Insight engine
- Copilot IA
- Dashboards

Persistence:

- Persist when the metric is used repeatedly, needs historical trend, or is expensive to compute
- Do not persist if it is trivial, ephemeral, or purely local to a single request

AgroSaaS examples:

- peso medio
- GMD
- custo sanitario
- saldo financeiro
- tarefas atrasadas

Should indicators be persisted?
Yes, when they have analytical, historical, or cross-channel value.

Should indicators always be calculated on demand?
No. On-demand calculation is allowed for low-cost, transient views, but the canonical behavior is to persist important indicators as snapshots with provenance.

Canonical rule:
Indicators are derived data and may be materialized.

### 4.3 Alerta

Definition:
A decision object produced when an indicator, event, or rule evaluation indicates a condition that deserves attention, action, or escalation.

Responsibility:
Convert measurement and context into an actionable operational concern.

Producer:

- Deterministic rules
- Threshold engines
- Scheduling engines
- Domain services
- Risk models

Consumer:

- Dashboard
- Copilot IA
- Field/PWA
- Notification channels
- Automation engines

Persistence:

- Persist as a lifecycle object
- Keep creation, status changes, acknowledgement, closure, expiry, and delivery metadata

AgroSaaS examples:

- vacinação atrasada
- lote sem pesagem
- caixa negativo
- tarefa vencida

When is it born?
When a rule, threshold, or model first classifies a condition as relevant.

When does it expire?
When the condition is no longer valid, the period ends, or the alert becomes stale by policy.

Who acknowledges it?
Any authorized user, automation, or consuming workflow that marks it as seen or triaged.

Who closes it?
The user, a rule-based resolution flow, an automation, or the system when the underlying condition resolves.

Canonical rule:
An alert is not the same as an event. The event says what happened. The alert says what demands attention.

### 4.4 Insight

Definition:
An interpretive statement that explains what the data means, why it matters, or what should be considered next.

Responsibility:
Translate alerts, indicators, and events into contextual reasoning.

Producer:

- Copilot IA
- Rule-based narrative engine
- Analytics layer
- Human-authored logic

Consumer:

- Users
- Dashboard summaries
- Copilot conversation state
- Notifications with explanation

Persistence:

- Persist when the insight will be reused, audited, tracked over time, or shown in a timeline
- It may also be generated on demand without persistence

AgroSaaS examples:

- "Os custos sanitarios cresceram 18%."
- "O lote perdeu desempenho."
- "A fazenda esta aumentando despesas."

Is insight AI?
Not necessarily.

Can insight exist without AI?
Yes. A deterministic rules engine or analytics engine can generate insights.

Should insight be persisted?
Sometimes. Persist if the insight is part of operational memory, audit, explainability, or a user-facing timeline.

Canonical rule:
Insight is interpretation. It is not the raw fact and not the operational alert itself.

## 5. Conceptual Contracts

These are canonical conceptual interfaces. They are not implementation code.

### 5.1 Event

```ts
type Event = {
  id: string;
  tenantId: string;
  domain: "AGRICULTURE" | "LIVESTOCK" | "FINANCE" | "OPERATIONS" | "FIELD" | "SYSTEM";
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

### 5.2 Indicator

```ts
type Indicator = {
  id: string;
  tenantId: string;
  domain: "AGRICULTURE" | "LIVESTOCK" | "FINANCE" | "OPERATIONS" | "FIELD" | "SYSTEM";
  category: Category;
  key: string;
  label: string;
  value: number | string | boolean | null;
  unit?: string;
  periodStart?: string;
  periodEnd?: string;
  computedAt: string;
  inputs: string[];
  confidence?: Confidence;
  metadata?: Record<string, unknown>;
};
```

### 5.3 OperationalAlert

```ts
type OperationalAlert = {
  id: string;
  tenantId: string;
  domain: "AGRICULTURE" | "LIVESTOCK" | "FINANCE" | "OPERATIONS" | "FIELD" | "SYSTEM";
  category: Category;
  title: string;
  message: string;
  severity: Severity;
  priority: Priority;
  status: "OPEN" | "ACKNOWLEDGED" | "SNOOZED" | "RESOLVED" | "EXPIRED" | "CANCELLED";
  confidence?: Confidence;
  triggerType: "RULE" | "THRESHOLD" | "MODEL" | "MANUAL" | "SCHEDULE";
  sourceEventIds: string[];
  sourceIndicatorIds: string[];
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

### 5.4 Insight

```ts
type Insight = {
  id: string;
  tenantId: string;
  domain: "AGRICULTURE" | "LIVESTOCK" | "FINANCE" | "OPERATIONS" | "FIELD" | "SYSTEM";
  category: Category;
  title: string;
  summary: string;
  narrative: string;
  severity?: Severity;
  priority?: Priority;
  confidence?: Confidence;
  evidence: {
    eventIds: string[];
    indicatorIds: string[];
    alertIds: string[];
  };
  generatedBy: "RULE_ENGINE" | "ANALYTICS" | "COPILOT" | "HUMAN";
  generatedAt: string;
  expiresAt?: string;
  metadata?: Record<string, unknown>;
};
```

## 6. Cross-Cutting Attributes

### 6.1 Priority

Definition:
Represents urgency of action.

Proposed values:

- LOW
- NORMAL
- HIGH
- URGENT

Meaning:

- LOW: can wait
- NORMAL: expected follow-up
- HIGH: should be addressed soon
- URGENT: requires immediate attention

Priority differs from severity:

- Severity measures impact or seriousness of the condition
- Priority measures ordering of attention and response

Example:
A low-severity alert may be urgent if it blocks an operational deadline.

### 6.2 Severity

Definition:
Represents the intrinsic seriousness of the condition.

Canonical use:

- INFO
- WARNING
- CRITICAL
- EMERGENCY

Severity should answer:
How bad is the condition?

Priority should answer:
How fast must we act?

### 6.3 Confidence

Definition:
Numeric estimate between 0.0 and 1.0 that indicates how reliable a derived decision is.

When it should exist:

- AI-generated insights
- Predictive alerts
- Probabilistic models
- Hybrid engines with model scoring

Should it exist only for AI?
No. It may also exist for non-ML rule systems when the evaluation has uncertainty, incomplete evidence, or heuristic scoring.

Should deterministic rules always have confidence?
Not mandatory. Deterministic rules may omit it or set it to 1.0 only if the product wants explicit certainty semantics.

Canonical rule:
If the engine cannot justify uncertainty, do not invent confidence. Leave it absent or set it explicitly according to engine policy.

### 6.4 Category

Definition:
Domain-independent classification of the condition type.

Recommended canonical categories:

- SANITARIO
- OPERACIONAL
- ECONOMICO
- FINANCEIRO
- CLIMATICO
- MANUTENCAO
- GOVERNANCA
- QUALIDADE
- COMPLIANCE
- PRODUCAO

Assessment:
The proposed list is correct as a canonical base. It should remain independent from the business domain.

Domain is not category.

Example:

- Domain: LIVESTOCK
- Category: SANITARIO

## 7. Alert Engine Logical Flow

### 7.1 High-level architecture

```text
Dominios de origem
  Agriculture
  Livestock
  Finance
  Operations
  Field/PWA
  Integrations

        |
        v

Alert Engine
  - Ingestion
  - Normalization
  - Indicator computation
  - Rule evaluation
  - Alert lifecycle
  - Insight synthesis
  - Routing and delivery planning

        |
        v

Alert Store
  - Event ledger
  - Indicator snapshots
  - Alert lifecycle records
  - Insight timeline
  - Delivery state

        |
        v

Consumption channels
  Dashboard Geral
  Dashboards Especializados
  Copiloto IA
  Campo (PWA)
  Notificações
  WhatsApp adapter
  External API
  Automation engines
```

### 7.2 Responsibilities by layer

Ingestion:
Accepts facts from domains and integrations. It does not decide business meaning.

Normalization:
Converts domain-specific payloads into canonical structures.

Indicator computation:
Aggregates facts into measurable metrics.

Rule evaluation:
Determines whether an alert should exist or change state.

Insight synthesis:
Explains what the alert or indicator means in context.

Routing and delivery:
Chooses which channel receives the alert or insight.

Alert Store:
Keeps the full operational memory and lifecycle history.

## 8. Responsibilities by Actor

### Who creates Event?

- Domain services
- Sync workers
- Human actions
- Integrations
- Device captures

### Who calculates Indicator?

- Indicator engine
- Deterministic domain services when explicitly designed to materialize a metric

### Who generates Alert?

- Alert Engine rules
- Threshold policies
- Risk models
- Scheduled evaluators

### Who generates Insight?

- Copilot IA
- Analytics engine
- Narrative rules

### Who answers questions?

- Copilot IA

### Who executes actions?

- User
- Automation
- Field workflows
- External integrations

Canonical prohibition:
Copilot never creates Event.
Copilot never creates Indicator.
Copilot never creates Alert.
Copilot only interprets and recommends.

## 9. Persistence Strategy

### 9.1 Event

Persist?
Yes, always.

Why:

- auditability
- traceability
- replay
- provenance
- legal and operational history

Disadvantages:

- storage growth
- need for indexing and retention policy

### 9.2 Indicator

Persist?
Yes for meaningful metrics, no for trivial transient computations.

Why:

- trend analysis
- historical comparisons
- cheap repeated reads
- cross-channel consistency

Disadvantages:

- recomputation complexity
- versioning and staleness management

### 9.3 Alert

Persist?
Yes, always.

Why:

- lifecycle management
- acknowledgement and closure
- escalation tracking
- notifications and delivery history

Disadvantages:

- state management complexity
- deduplication and expiry policies

### 9.4 Insight

Persist?
Conditional.

Why persist:

- explainability
- memory for Copilot
- audit of recommendations
- user timelines

Why not always persist:

- some insights are ephemeral
- some are generated on demand

Disadvantages:

- narrative versioning
- semantic drift over time

## 10. Copilot IA Integration Policy

The Copilot should consume the following layers in this order of preference:

1. Alerts
2. Indicators
3. Events
4. Insights

### Why Alerts first?

Alerts already contain interpreted significance. They are the highest-value input for action-oriented dialogue.

### Why Indicators second?

Indicators provide quantitative context for comparison, trend, and prioritization.

### Why Events third?

Events are the source of truth, useful when the Copilot needs deeper explanation, traceability, or to reconstruct causality.

### Why Insights fourth?

Insights are narrative outputs. The Copilot can reuse them, but they are not the primary source of truth.

### When should the IA query Events directly?

- when the user asks "what happened?"
- when an alert is insufficient to explain the root cause
- when the Copilot needs traceability or chronology
- when it must reconstruct a timeline across domains

### When is it enough to use Alerts?

- when the question is action-oriented
- when prioritization is the main objective
- when the Copilot is proposing the next step

### When should it use Insights?

- when the response must be human-readable and explanatory
- when summarizing patterns, trends, or recommendations
- when presenting a narrative in dashboard cards or chat summaries

Canonical rule:
The Copilot interprets. It does not originate business truth.

## 11. Recommended Roadmap

The ideal sequence for implementation is:

```text
EXECUTION-33A
Alert Engine Architecture

EXECUTION-33B
Canonical Contracts

EXECUTION-33C
Persistence Model

EXECUTION-33D
Dashboard Consumption

EXECUTION-33E
Copilot Consumption

EXECUTION-33F
Field/PWA Consumption

EXECUTION-33G
Notifications

EXECUTION-33H
WhatsApp Adapter

EXECUTION-33I
Automation Adapters
```

Reasoning:

- Architecture first: define boundaries and semantics
- Contracts second: stabilize interfaces before persistence
- Persistence third: model lifecycle and storage
- Dashboards and Copilot next: consume the canonical store
- Field and notifications after the core is stable
- WhatsApp and automation adapters last, because they are channel integrations

## 12. Non-Negotiable Rules

- Events are immutable
- Indicators are derived, not raw facts
- Alerts are lifecycle objects
- Insights are interpretations, not source facts
- Copilot is a consumer and interpreter only
- Dashboards are consumers, not owners
- The Alert Engine is transversal and domain-agnostic
- Domain classification and condition classification must remain separate

## 13. Canonical Summary

The AgroSaaS intelligence stack is not a dashboard feature.

It is a shared operational memory and decision infrastructure:

```text
Evento -> Indicador -> Alerta -> Insight -> Copiloto IA -> Usuário -> Ação -> Evento
```

This document is the canonical architectural reference for all Alert Engine work.
