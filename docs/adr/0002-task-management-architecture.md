# ADR-0002: Task Management — Event-Sourced Activity as Single Source of Truth

**Date:** 2026-05-25
**Status:** Accepted

---

## Context

RetailFlux v3 required a persistent workflow layer so executives could act on insights surfaced by the dashboards. The core design question was: **how should task history be modeled?**

Three competing needs drove the decision:
1. **Audit trail** — every status change, assignment, comment, and KPI link must be attributable to a user with a timestamp. Compliance in retail contexts (procurement approvals, financial tasks) requires this.
2. **Analytics source** — productivity reports, bottleneck detection, and team scorecards all require querying the history of what happened to tasks over time.
3. **Real-time propagation** — state transitions must publish to the Redis pub/sub channel (`retailflux:tasks:{company_id}`) so the Kanban board and task detail views update instantly without polling.

The naive design (a `tasks` table with mutable `status` + `updated_at` columns, and a separate `audit_log` table written by the API) creates **drift**: the audit log captures what the API *intended* to do, but if a background job or direct DB query mutates state outside the API, audit and reality diverge.

---

## Decision

Use **event-sourced `task_activity`** as the single canonical record for all task mutations. Every state change writes one immutable row to `task_activity` with `kind` (e.g. `status_changed`, `assigned`, `commented`) and a `payload` JSONB capturing `{from, to, meta}`. The `tasks` table holds the *current materialized state* (denormalized for fast reads), but `task_activity` is the authoritative truth.

```sql
task_activity (
  id UUID PK,
  task_id UUID FK,
  actor_id UUID FK,
  kind activity_kind,
  payload JSONB,
  created_at TIMESTAMPTZ
)
```

Consequences of this design:
- The audit trail **is** the activity log — no separate audit table for tasks.
- Analytics queries (`GET /tasks/analytics/department`) aggregate `task_activity`, not `tasks`, ensuring no drift between "what happened" and "what we report."
- State replay is possible: given a task's activity stream, the current state can be reconstructed deterministically.

The workflow state machine (`app/domains/tasks/workflow.py`) enforces allowed transitions before writing to `task_activity`, preventing invalid state sequences at the application layer.

---

## Alternatives Considered

### Mutable `tasks` table with a separate audit log
The most common pattern: `tasks.status` is updated in place; a separate `task_audit` table records changes via a trigger or middleware call.

**Rejected** because:
- Trigger-based audit fires even on direct DB mutations (migrations, scripts), creating noise.
- Analytics on "how long did tasks stay in `blocked` status?" requires either a separate snapshot table or post-hoc reconstruction — both are fragile.
- Two sources of truth (current state + audit) will drift under partial failure conditions.

### Full event sourcing with CQRS (no mutable state in `tasks`)
Pure CQRS: the `tasks` table is a read-model rebuilt from the event stream; all writes go to an event store. This is the theoretically correct approach.

**Rejected** because:
- Rebuilding the read-model on every query is expensive at free-tier database scale.
- CQRS adds significant complexity (projectors, eventually-consistent reads, snapshot intervals) that is not justified for a task system of this scale.
- The hybrid approach (mutable `tasks` + authoritative `task_activity`) gives 80% of the event-sourcing benefits at 20% of the complexity.

### Storing activity in MongoDB
MongoDB's flexible schema is appealing for activity payloads. Task search is already handled by a denormalized `task_search_index` MongoDB collection.

**Rejected** because keeping the authoritative state in Postgres (alongside `tasks`) enables foreign-key integrity and transactional consistency. The activity append and the state update can be committed atomically in a single Postgres transaction.

---

## Consequences

**Positive:**
- Analytics, audit, and real-time propagation all share a single write path — no possibility of divergence.
- `task_activity` can be replayed to reconstruct any historical state (useful for debugging approval disputes or SLA violations).
- Future event sourcing migration path is clear: add a projector that consumes `task_activity` and rebuilds arbitrary read-models.
- `kind` enum makes queries for specific event types (e.g., "all escalations this month") trivially fast with a partial index.

**Negative / Trade-offs:**
- Insert-heavy workload: a typical task lifecycle (create → assign → 3 transitions → 5 comments → close) writes ~10 `task_activity` rows. At high volume, the table grows quickly.
- Analytics queries over `task_activity` scan more rows than a pre-aggregated snapshot table would. Mitigated by the `productivity_daily` MongoDB collection (nightly Celery rollup).
- Application code must be disciplined: all mutations must go through `app/domains/tasks/service.py`; bypass paths must be audited.

**Follow-ons:**
- Index `task_activity(task_id, created_at DESC)` and `(company_id, kind, created_at DESC)` — both are in migration `0014_perf_indexes.py`.
- Nightly Celery job `task_productivity_rollup` aggregates `task_activity` into `productivity_daily` so analytics queries never hit the raw activity table at scale.
- v3.x: consider a snapshot mechanism (every N events, write a state snapshot) to cap replay cost.
