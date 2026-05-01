---
deliverable_id: Spec2-D2.6
title: "Error Handling and Quarantine Specification"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 2
status: Draft
version: 0.2
owner: Identity Architecture
created: 2026-04-30
updated: 2026-05-01
verification_history:
  - date: 2026-05-01
    pass: "v0.1 → v0.2 (synchronization-only)"
    note: "D2.6 is a policy / taxonomy specification; it does NOT make Microsoft-side architectural claims that require Microsoft Learn verification. The version bump to 0.2 keeps D2.6 in lockstep with sister D2.x specs whose substantive verification this pass landed (D2.3 corrections; D2.8 corrections; D2.1/D2.2/D2.4/D2.5/D2.7 confirmations)."
    no_corrections: true
    confirmed:
      - "D2.6 §2.5 'partial-disable' / 'session-revoke-failed' failure_reasons remain wire-compatible with D2.3 §10 — verified by reviewing the renamed D2.3 step-3 provenance event 'leaver.session-revoke-verified' and confirming D2.6 escalation tier 2 + 15-min SLA continue to apply to that class of failure"
canonical_adrs:
  - ADR-003
  - ADR-035
  - ADR-049
  - ADR-050
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
  - Spec2-D1.5
  - Spec2-D1.8
  - Spec2-D3.1
sibling_deliverables:
  - Spec2-D2.1
  - Spec2-D2.2
  - Spec2-D2.3
  - Spec2-D2.4
  - Spec2-D2.5
  - Spec2-D2.7
  - Spec2-D2.8
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D2.6: Error Handling and Quarantine Specification

> **Status (v0.2, 2026-05-01):** Synchronization-only version bump.
> D2.6 is a policy / taxonomy spec and makes no Microsoft-side
> architectural claims that need Microsoft Learn verification.
> The bump keeps D2.6 in lockstep with sister D2.x specs whose
> substantive v0.2 verification this pass landed. Wire-compatibility
> with D2.3 §10 confirmed after the D2.3 step-3 rename
> (`leaver.refresh-token-revoke` → `leaver.session-revoke-verified`):
> the `partial-disable` / `session-revoke-failed` failure_reasons +
> tier-2 + 15-min SLA continue to apply unchanged.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Error Handling & Quarantine
specification called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 2 → D2.6:

> *Error scenarios: missing required attributes, UPN conflict,
> manager not found, invalid department code, HR data integrity
> failure. Quarantine queue design. Manual remediation workflow.
> Escalation paths. SLA for quarantine resolution.*

D2.6 is the canonical failure-handling sister of D2.1–D2.5 + D2.7 +
D2.8. Every workflow in Track C delegates failure routing here.
D3.1 §6 establishes the retry / quarantine manager component;
D2.6 specifies the queue contract, the SLA framework, and the
remediation workflow.

### 1.1 Scope

In scope:

- The canonical failure taxonomy (the `failure_reason` enumeration
  used across D2.x).
- Quarantine queue shape and lifecycle.
- Per-failure-class SLA defaults.
- Manual remediation workflow (operator-facing).
- Escalation paths.
- Re-injection mechanics (a quarantined record returning to the
  middleware after operator remediation).
- Provenance emission for quarantine events.
- Auditor-visible quarantine artefacts.

Out of scope:

- The retry mechanism itself (D3.1 §6.1–§6.2) — D2.6 starts where
  retries are exhausted.
- Microsoft Graph error codes per se (D3.1 §6.1 enumerates).
- HR-system internal data-quality remediation (HR's responsibility).

## 2. Failure Taxonomy

D2.6 is the authoritative source of the `failure_reason` enumeration
used in D2.x quarantine routing. The taxonomy:

### 2.1 HR-data-quality class

| `failure_reason` | Origin workflow(s) | Description |
|---|---|---|
| `schema-validation` | All | A required field per D1.1 is missing, malformed, or fails its validation rule |
| `worker-type-unknown` | D2.1 / D2.5 | The HR `workerType` value is not in the D1.6 taxonomy |
| `usage-location-missing` | D2.1 / D2.2 | HR record missing country code; license assignment cannot proceed |
| `start-date-invalid` | D2.1 | `startDate` unparseable or in implausible range |
| `manager-stale` | D2.1 / D2.2 | `managerEmployeeId` references a record `active: false` for >90 days |

### 2.2 Codebook / mapping class

| `failure_reason` | Origin workflow(s) | Description |
|---|---|---|
| `orgpath-codebook-miss` | D2.1 / D2.2 / D2.5 | Department / division / location / cost-center value not in the OrgPath codebook (ADR-035) |
| `upn-collision` | D2.1 / D2.5 | UPN generation produced a collision unresolvable by D1.5 rules |
| `prehire-window-config` | D2.1 | Pre-hire window misconfigured (D2.7); not record-specific |
| `conversion-path-unsupported` | D2.5 | Worker-type transition path not in D2.5 §2.1 matrix without policy override |
| `prior-link-policy` | D2.4 | Rehire prior-record-link policy violation |
| `rehire-window-expired` | D2.4 | Match window §2.2 exceeded but record still soft-present (re-routed, not blocked) |

### 2.3 Operation-collision class

| `failure_reason` | Origin workflow(s) | Description |
|---|---|---|
| `event-collision` | All | Two D2.x events arrived for the same `externalId` in the same cycle; precedence rule resolved one and dropped the other |
| `rehire-active-collision` | D2.4 | Reactivation against a record already `active: true` |
| `late-edit-dropped` | D2.3 | HR edit during retention window for a terminated record |
| `upn-flip-unauthorized` | D2.5 | UPN flip requested without explicit operator approval |

### 2.4 Microsoft Graph / network class

| `failure_reason` | Origin workflow(s) | Description |
|---|---|---|
| `graph-auth-failure` | All | Token acquisition or scope rejection (D3.1 §6.1) |
| `graph-permission-denied` | All | Required Graph permission absent on service principal |
| `graph-schema-rejection` | All | SCIM payload rejected by `bulkUpload` schema validator |
| `graph-rate-limit` | All | 429 / 503 — handled by retry first; quarantines only on retry exhaustion |
| `graph-server-error` | All | 5xx after retry exhaustion |

### 2.5 Leaver-specific class

| `failure_reason` | Origin workflow(s) | Description |
|---|---|---|
| `partial-disable` | D2.3 | Step 1 of Leaver succeeded but a later step failed; record is in a partial-leaver security gap |
| `session-revoke-failed` | D2.3 | `revokeSignInSessions` failed |
| `group-removal-failed` | D2.3 / D2.5 | Removal of a single group failed during step 4 (D2.3) or §6.1 (D2.5) |
| `mailbox-convert-failed` | D2.3 | Shared-mailbox conversion failed |
| `reassign-sla-breach` | D2.3 | Direct-report reassignment SLA exceeded |

### 2.6 Cross-cutting class

| `failure_reason` | Origin workflow(s) | Description |
|---|---|---|
| `provenance-emission-failed` | All | Provenance record could not be persisted (D3.1 §8.3 contract) |
| `scope-filter` | All | Record excluded by D2.8 — not a failure per se, but routed to quarantine for audit |

The taxonomy is stable. New `failure_reason` values require an
update to this document and the canon registry, not just an
in-code addition.

## 3. Quarantine Queue Shape

### 3.1 Record contract

Each quarantined record is a structured JSON document with the
following schema:

```yaml
quarantine_id: <UUIDv4>
quarantined_at: <ISO-8601 UTC>
external_id: <employeeId>
upn: <middleware-computed UPN, if available>
workflow: <joiner|mover|leaver|rehire|conversion|scope-filter>
failure_reason: <enum from §2>
failure_detail: <free-form string from middleware>
sla_resolution_target_at: <ISO-8601 UTC>   # quarantined_at + per-class SLA from §4
hr_record_snapshot:
  # full HR record at the time of quarantine; the middleware MUST
  # NOT mutate this after the quarantine record is written
  ...
canonical_payload_attempted:
  # the SCIM payload the middleware tried to emit, if any
  ...
graph_response:
  # if the failure was a Graph error
  status: <int>
  request_id: <string>
  error_body: <string>
remediation_state:
  status: <open|in-progress|resolved|wont-fix>
  assigned_to: <operator id or null>
  notes: []
escalation_state:
  level: <0|1|2|3>
  escalated_at: <timestamp or null>
provenance_id: <UUIDv4 of the related provenance record>
```

### 3.2 Lifecycle

A quarantine record progresses through:

1. **Created** (`status: open`) on initial quarantine emission.
2. **Triaged** (`status: in-progress`) when an operator acknowledges
   it.
3. **Resolved** (`status: resolved`) when the underlying issue is
   fixed and the record is re-injected to the middleware.
4. **Won't-fix** (`status: wont-fix`) when the operator determines
   the record is intentionally excluded (e.g., a contractor record
   that should be in the scope filter exclusion list).

The middleware MUST NOT auto-resolve quarantine records. Operator
acknowledgment is a control point; quarantine is the canonical
human-in-the-loop boundary.

### 3.3 Sink

The quarantine queue persists in a tenant-scoped store separate
from the provenance store (per D3.1 §6.3 reference). Implementation
choice (Azure Cosmos DB, Azure Table Storage, etc.) is a tenant
concern; the contract is the §3.1 record shape and the §3.2
lifecycle.

The quarantine store MUST be:

- **Replayable.** Operators can re-inject a record into the next
  middleware sync cycle.
- **Auditable.** Every state transition emits a provenance record.
- **Searchable.** Queries by `external_id`, `failure_reason`, or
  age are first-class.
- **Retention-bounded.** Resolved records are retained per the
  tenant's audit-retention schedule (typically 7 years for
  federal civilian; tenant-policy override).

## 4. SLA Framework

The middleware MUST stamp each quarantine record with an SLA target.
The defaults below are calibrated for federal civilian operations;
agencies may tighten via policy.

### 4.1 Per-failure-reason SLA defaults

| `failure_reason` | SLA (business days) | Escalation tier |
|---|---|---|
| `schema-validation` | 1 | HR-data-quality |
| `worker-type-unknown` | 1 | Canon governance (D1.6 update) |
| `usage-location-missing` | 1 | HR-data-quality |
| `start-date-invalid` | 1 | HR-data-quality |
| `manager-stale` | 2 | HR-data-quality |
| `orgpath-codebook-miss` | 1 | Canon governance (codebook update) |
| `upn-collision` | 1 | Identity engineering |
| `prehire-window-config` | same-day | Operator-only (configuration) |
| `conversion-path-unsupported` | 3 | Canon governance + tenant-policy |
| `event-collision` | same-day | Routing logged; usually no remediation needed |
| `partial-disable` | **15 minutes** | **Security incident** |
| `session-revoke-failed` | **15 minutes** | **Security incident** |
| `group-removal-failed` | 1 hour (during retention) | Identity engineering |
| `mailbox-convert-failed` | 1 | Messaging operations |
| `reassign-sla-breach` | tenant-policy | HR escalation |
| `graph-auth-failure` | same-day | Identity engineering |
| `graph-permission-denied` | same-day | Identity engineering |
| `graph-schema-rejection` | 1 | Middleware engineering |
| `graph-server-error` | same-day (after retries) | Microsoft support escalation if persistent |
| `provenance-emission-failed` | **15 minutes** | **Audit integrity incident** |
| `scope-filter` | n/a | Logged for audit; not actionable |

### 4.2 SLA breach behavior

When `now >= sla_resolution_target_at`:

1. The record's `escalation_state.level` increments by one.
2. A `quarantine.sla-breach` provenance event is emitted.
3. Notification fires per the escalation tier (§5).
4. The new SLA target is set per the next escalation tier's
   default. Recursive breaches escalate again.

## 5. Escalation Paths

The escalation tiers:

| Tier | Recipient (default) | Action |
|---|---|---|
| 0 | Quarantine queue (passive) | Initial create; awaiting triage |
| 1 | Operator queue + on-call rotation page | Triage required within SLA |
| 2 | Identity engineering lead + HR liaison | SLA-breached once |
| 3 | Identity governance lead + agency CISO (security incidents) | SLA-breached twice OR a `security incident` failure_reason |

Security-incident failure reasons (`partial-disable`,
`session-revoke-failed`, `provenance-emission-failed`) start at
**tier 2** and escalate to **tier 3 after the 15-minute SLA**.
They never sit at tier 0.

The recipient lists are tenant-configurable; the tier structure is
canonical.

## 6. Manual Remediation Workflow

The remediation workflow is operator-facing. The canonical steps:

### Step 1: Triage

- Operator picks a record from the queue.
- `remediation_state.status` flips to `in-progress`; `assigned_to`
  is set.
- A `quarantine.triaged` provenance event is emitted.

### Step 2: Diagnose

The operator inspects:

- `failure_reason` and `failure_detail`.
- `hr_record_snapshot` for HR-data-quality issues.
- `canonical_payload_attempted` for what the middleware tried to
  emit.
- `graph_response` for Graph-side errors.
- The most recent provenance records for the same `external_id`.

### Step 3: Remediate

Per the failure class:

| Failure class | Remediation action |
|---|---|
| HR-data-quality | Submit HR-side correction; record waits for next HR feed cycle |
| Codebook / mapping | Update OrgPath codebook (ADR-035) or D1.6 taxonomy or D1.5 UPN rules; canon-governance change |
| Operation-collision | Usually no remediation — records auto-resolve on next cycle |
| Graph / network | Engineering investigation; may require Microsoft support |
| Leaver-specific | Resume the disable sequence from the failed step (§2.5); D2.3 §11 idempotency makes this safe |

### Step 4: Re-inject

- The operator sets `remediation_state.status: resolved`.
- The middleware's next sync cycle picks up the record from the
  queue (the re-injection queue) and re-processes it as if it
  arrived fresh from HR.
- A `quarantine.resolved` provenance event is emitted.

If re-injection fails, the record is re-quarantined with a new
`quarantine_id` and a `prior_quarantine_id` reference. The
original record's `remediation_state.status` becomes `resolved`
(closed) but the new record continues the lifecycle.

### Step 5: Won't-fix

Some records are intentionally excluded:

- Contractors who should be in the scope-filter exclusion list.
- Test records that should never have entered the HR feed.

The operator marks `remediation_state.status: wont-fix`; a
`quarantine.wont-fix` provenance event is emitted. The decision is
auditable.

## 7. Provenance Emission

D2.6 emits its own provenance event family:

| `event_type` | Trigger |
|---|---|
| `quarantine.created` | Initial quarantine emission |
| `quarantine.triaged` | Operator picks up the record |
| `quarantine.resolved` | Re-injection successful or `wont-fix` decision |
| `quarantine.sla-breach` | SLA target exceeded; escalation tier increments |
| `quarantine.re-injected` | Record sent back to the middleware sync queue |
| `quarantine.escalated` | Escalation tier transition |

Each emission carries the `quarantine_id` plus the standard D3.1
§8.2 correlation block.

Control evidence: AC-2, AU-2, AU-6 (audit review), and IR-4
(incident response — for security-incident escalations).

## 8. Operator Surface

D2.6 names the contract; the operator UI / CLI is implementation.
The minimum surface MUST support:

| Capability | Minimum implementation |
|---|---|
| List open quarantine records | Table with `external_id`, `failure_reason`, `quarantined_at`, SLA status |
| Filter by failure class, SLA tier, age | Standard query controls |
| View record detail | Full §3.1 record + linked provenance |
| Triage / resolve / won't-fix actions | State transitions emit provenance |
| Re-inject command | Sends record to middleware sync queue |
| SLA dashboard | Per-tier counts; escalation queue |

The `uiao` CLI integration target: `uiao quarantine list / show /
triage / resolve / re-inject` subcommands.

## 9. Auditor-Visible Artefacts

For audit purposes, the following are first-class:

1. The full quarantine record at every state transition (preserved
   in the provenance store).
2. A daily quarantine-state digest (count by `failure_reason`,
   tier breakdown, SLA-breach count).
3. A per-`external_id` lifecycle reconstruction (queries on
   provenance store + quarantine store joined on `external_id`).
4. An aggregate compliance report mapping `failure_reason` →
   NIST control evidence, demonstrating that the substrate
   enforces AC-2 / AU-2 / AU-6 / IR-4 by construction.

## 10. Failure-Reason Stability Contract

This taxonomy is canonical. Adding, renaming, or removing a
`failure_reason` requires:

1. An update to this document (D2.6).
2. An update to the canon registry.
3. A search-and-update across D2.1–D2.5, D2.7, D2.8, and D3.1 to
   ensure all references are aligned.
4. A note in the next version's `verification_history` block in
   the affected specs.

## 11. References

### 11.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-035](../adr/adr-035-orgpath-codebook-binding.md)
- [ADR-049](../adr/adr-049-microsoft-adapter-coverage-expansion.md)
- [ADR-050](../adr/adr-050-reference-middleware-implementation-choices.md)

### 11.2 UIAO docs

- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 2 → D2.6.

### 11.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — §6.3 establishes the retry / quarantine manager.
- All Phase 2 specs delegate failure routing here:
  [Spec2-D2.1](./Spec2-D2.1-JoinerWorkflowSpecification.md),
  [Spec2-D2.2](./Spec2-D2.2-MoverWorkflowSpecification.md),
  [Spec2-D2.3](./Spec2-D2.3-LeaverWorkflowSpecification.md),
  [Spec2-D2.4](./Spec2-D2.4-RehireWorkflowSpecification.md),
  [Spec2-D2.5](./Spec2-D2.5-ConversionWorkflowSpecification.md),
  [Spec2-D2.7](./Spec2-D2.7-PreHireProvisioningWindowSpecification.md),
  [Spec2-D2.8](./Spec2-D2.8-ProvisioningScopeFilterRules.md).

### 11.4 Compliance

- NIST SP 800-53 Rev 5: AC-2, AU-2, AU-6, IR-4.
