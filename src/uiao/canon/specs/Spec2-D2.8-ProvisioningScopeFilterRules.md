---
deliverable_id: Spec2-D2.8
title: "Provisioning Scope Filter Rules"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 2
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-04-30
updated: 2026-04-30
canonical_adrs:
  - ADR-003
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
  - Spec2-D1.6
  - Spec2-D3.1
sibling_deliverables:
  - Spec2-D2.1
  - Spec2-D2.6
  - Spec2-D2.7
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D2.8: Provisioning Scope Filter Rules

> **Status (v0.1, 2026-04-30):** Initial draft. Awaiting verification
> against Microsoft Learn synchronization-job scoping filter syntax
> for §5 (Entra-side filter expression).

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Provisioning Scope Filter
specification called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 2 → D2.8:

> *Define which HR records are in scope for provisioning:
> include/exclude by worker type, location, department, employment
> status. Handle edge cases: LOA (leave of absence), sabbatical,
> secondment, internship end dates.*

D2.8 defines the **gate** at the boundary between the HR feed and
the middleware. Records that don't pass the filter are not
provisioned. The gate has three layers (middleware-side, Entra-
side, audit-side) and a small set of edge cases that are the
operationally-tricky cases.

### 1.1 Scope

In scope:

- The middleware-side filter (the canonical UIAO scope rules).
- The Entra-side filter (the synchronization job's scoping
  filter, when leveraging the Entra ID provisioning service).
- The audit posture for filtered records.
- The standard include / exclude predicates.
- Edge cases: LOA, sabbatical, secondment, internship end dates.
- The interaction with D2.1 (joiner pre-conditions),
  D2.7 (pre-hire window), and D2.6 (failed-filter quarantine
  routing).

Out of scope:

- HR-side data quality (D1.8 covers the inbound contract).
- Worker-type taxonomy itself (D1.6 enumerates).
- Decisions about whether a worker SHOULD have an account
  (an HR / staffing decision; D2.8 just enforces the rules
  configured for the deployment).

## 2. Filter Layering

The scope filter operates at three layers:

| Layer | Where | Purpose |
|---|---|---|
| **Middleware-side filter** | UIAO middleware (D3.1 §3.2) | Authoritative include/exclude evaluation; the canonical UIAO filter |
| **Entra-side filter** | Entra ID synchronization job scoping | Defense-in-depth; explicitly drops records the middleware should never have emitted |
| **Audit posture** | Provenance store + quarantine | Filtered records are visible to auditors as `outcome: scope-filter` events |

The middleware-side filter is load-bearing. The Entra-side filter
is a belt-and-suspenders defense. Audit posture is what makes the
filter auditable (silent drops are forbidden).

## 3. Standard Include / Exclude Predicates

The canonical predicates:

### 3.1 Include predicates

A record passes the include filter if **all** of the following
are true:

| Predicate | Default value | Tenant override |
|---|---|---|
| `workerType` is in the deployment's `workerTypeAllowed` list | All values from D1.6 except `External Collaborator` | tenant policy |
| `employmentStatus` is in `{active, on-leave, pre-hire}` | yes | tenant policy |
| `country` (`usageLocation`) is in `countryAllowed` list | `[US]` for federal civilian default | tenant policy |
| `department` is in `departmentAllowed` list (or list is empty meaning "all") | empty (allow all) | tenant policy |
| `location` is in `locationAllowed` list (or empty) | empty | tenant policy |
| `startDate` is within `today + maxLookaheadDays` (deferral bound) | 90 days | tenant policy |

The `maxLookaheadDays` predicate is the boundary at which a
far-future hire is deferred. Records beyond it are NOT
quarantined — they're simply not yet in scope. The middleware
re-evaluates on every sync cycle.

### 3.2 Exclude predicates

A record fails the filter if **any** of the following are true,
regardless of include matches:

| Predicate | Default behavior |
|---|---|
| `employmentStatus = rescinded` | Always exclude (route to D2.7 §6.1 cleanup) |
| `employmentStatus = test` (HR test record) | Always exclude; logged to audit |
| `employeeId` is on the deployment's `employeeIdExcludeList` | Manual override list for individuals (sensitive cases) |
| `workerType` is in `workerTypeExcluded` list | Manual override list for worker classes |
| `terminationDate < today - retentionWindowDays` | Past-retention; not provisionable (covered by D2.4 rehire window expiry) |

The `employeeIdExcludeList` is a tenant-managed list. Adding to or
removing from it is a governance-level change that emits a
provenance event of type `scope.exclusion-list-update`.

## 4. The Edge Cases

### 4.1 LOA (Leave of Absence)

LOA is **NOT a Leaver event**. UIAO's posture:

- Account remains `active: true`.
- Group memberships preserved.
- License preserved.
- An LOA-flag attribute (tenant-policy-named, typically
  `extensionAttribute3`) is stamped.
- Conditional Access policies that filter on the LOA flag may
  restrict access (e.g., block VPN access during LOA).

The HR `employmentStatus = on-leave` value passes the include
filter. The flag is what changes; the account stays in scope.

### 4.2 Sabbatical

Sabbaticals are operationally similar to LOA but typically longer
(6–12 months). UIAO treats them identically to LOA from the
middleware's perspective:

- Account active.
- Sabbatical flag stamped (`extensionAttribute3` = `sabbatical`).
- CA policies apply per tenant policy.

The differentiation between LOA and sabbatical lives in the flag
value, not in the scope filter.

### 4.3 Secondment

Secondment (temporary assignment to another agency / department /
program) is a **Mover** event, NOT a special scope-filter case:

- The HR record presents new department / location / manager.
- The middleware processes it via D2.2 (Mover).
- OrgPath recalculates to reflect the secondment placement.
- A secondment flag may be stamped, but the scope filter is
  unaffected.

### 4.4 Internship end dates

Interns differ from FTEs in two scope-relevant ways:

| Attribute | Intern-specific behavior |
|---|---|
| `terminationDate` | Set at the internship end date — drives a Leaver event on that date |
| Pre-hire window | Often longer (D2.7 default 30 days for `Intern`) — interns are hired well in advance of academic-calendar starts |
| Conversion path | Common case: Intern → FTE conversion (D2.5) |

Internship end dates do NOT require special filtering. The
standard Leaver workflow (D2.3) handles them. The scope filter
includes interns whose `terminationDate` is in the future and
excludes them after termination per the standard rules.

The edge case worth calling out: an intern's `terminationDate` is
known at hire (academic-calendar bound). The middleware MUST NOT
quarantine a record where `startDate < today < terminationDate`
even if the difference is short — short-term contracts are
legitimate.

### 4.5 Other temporary engagements

| HR scenario | Filter posture |
|---|---|
| Detail (temporary assignment within the agency) | Mover (D2.2) — not a scope concern |
| Reservist activation | LOA-equivalent; account stays active with flag |
| Furlough | LOA-equivalent (special operational class) |
| Suspension | Tenant-policy decision; default: account remains active but CA policies may restrict |

## 5. Entra-Side Synchronization Job Filter

The Entra ID provisioning service supports scoping filters on
synchronization jobs. UIAO's posture: the Entra-side filter MUST
be a **superset** of the middleware-side filter — it should not
let through any record that the middleware would have filtered, but
it MAY filter additional records (defense in depth).

The canonical Entra-side filter expression (illustrative; final
syntax pending v0.2 verification):

```
employmentStatus IN ("Active", "On Leave")
  AND country IN ("US")
  AND workerType IN ("Full-Time Employee", "Part-Time Employee", "Contractor", "Intern")
```

The middleware MUST emit ONLY records that pass this expression.
If the middleware emits a record that the Entra filter would
reject, the deployment is misconfigured — both filters MUST be
treated as the same scope rule.

## 6. Audit Posture

Filtered records are NOT silently dropped. The middleware MUST
emit one of two provenance events for every record evaluated by
the filter:

| Outcome | Event |
|---|---|
| In scope | (no scope-specific event; the workflow's own provenance is sufficient) |
| Out of scope | `provisioning.scope.excluded` |

The `provisioning.scope.excluded` event carries:

```yaml
event_type: provisioning.scope.excluded
external_id: <employeeId>
hr_record_extracted_at: <timestamp>
exclusion_reasons:
  - "workerType=External Collaborator not in allowed list"
  - "country=CA not in [US]"
filter_layer: middleware
```

This is the audit anchor for "we saw this record and chose not to
provision it." Auditors verifying coverage can query the
provenance store for `provisioning.scope.excluded` events and
correlate against HR's expected scope.

The `filter_layer` field distinguishes middleware-side filtering
from Entra-side filtering when a record was filtered at both.

### 6.1 Filter-rule version stamping

Every `provisioning.scope.excluded` event MUST stamp the version
of the scope-filter configuration in effect:

```yaml
filter_config:
  version: <semver>
  hash: <SHA-256 of the filter config YAML>
```

Filter rule changes (additions to allowed lists, exclusions, etc.)
are governance-level events. The version stamp ensures that an
audit reconstruction of "why was this person excluded on
2026-03-15?" resolves to the precise filter config in force then.

## 7. Configuration Surface

D2.8's operator-tunable configuration:

```yaml
provisioning_scope_filter:
  version: "1.0"
  workerTypeAllowed:
    - Full-Time Employee
    - Part-Time Employee
    - Contractor
    - Intern
    - Vendor
    - Volunteer
  workerTypeExcluded:
    - External Collaborator   # B2B handled separately
  countryAllowed:
    - US
  departmentAllowed: []   # empty = allow all
  locationAllowed: []
  employmentStatusAllowed:
    - Active
    - On Leave
    - Pre-Hire
  employeeIdExcludeList: []   # individual overrides
  maxLookaheadDays: 90
  retentionWindowDays: 90
```

The configuration lives in the deployment's
`substrate-manifest.yaml` joined with deployment-specific overrides.
The version field is incremented on every change; the hash is
computed by the middleware at startup.

## 8. Filter Evaluation Order

The middleware evaluates predicates in the following order. The
order matters because some predicates are cheaper than others, and
exclusion is short-circuit:

1. **Exclusion predicates** (§3.2). Short-circuit on first match.
2. **Worker-type include**. Cheap; fail fast.
3. **Country / location include**. Cheap.
4. **Department include**. Mid-cost (often a list of dozens).
5. **`employeeIdExcludeList`**. Hash lookup; cheap but listed
   later because it's typically empty.
6. **`maxLookaheadDays` deferral check**. Date math.
7. **Past-retention exclusion**. Date math.

A record passes the filter only if it survives all seven steps.
A record is quarantined as `scope-filter` only if the
`employeeIdExcludeList` matches — the other exclusions emit a
`provisioning.scope.excluded` provenance event but do NOT
quarantine. (Exclusion-list matches are quarantined for explicit
audit attention; far-more-common worker-type and country
mismatches are not.)

## 9. Interaction with Sibling Workflows

| Sibling | Interaction |
|---|---|
| D2.1 Joiner | Pre-condition #2 (D2.1 §3) calls into D2.8 |
| D2.7 Pre-hire window | The `maxLookaheadDays` predicate (§3.1) defines the deferral horizon |
| D2.4 Rehire | The retention-window exclusion (§3.2) defines the rehire-window expiry boundary |
| D2.6 Error handling | `scope-filter` failure_reason routes here; the small set of exclusion-list cases land in quarantine |

## 10. Failure Modes

D2.8-specific failure modes (delegated to D2.6):

| Failure | `failure_reason` | Routing |
|---|---|---|
| Filter configuration missing or schema-invalid | `prehire-window-config` (reused config-error class) | Operator alert; processing blocks until resolved |
| `employeeIdExcludeList` match | `scope-filter` | Quarantine for audit attention (not error per se) |
| Filter rule version mismatch between middleware and Entra job | `filter-version-skew` | Operator alert |

## 11. Lifecycle of a Filter Rule Change

Adding or removing entries in `workerTypeAllowed`,
`countryAllowed`, `employeeIdExcludeList`, etc., is a governance
event. The canonical lifecycle:

1. Operator proposes change in deployment configuration repo.
2. Change is reviewed (per agency governance — dual-control
   typical).
3. Configuration version increments.
4. Change is committed and applied at next middleware sync cycle.
5. Middleware emits `scope.config-update` provenance event with
   diff and new version.
6. The next batch of `provisioning.scope.excluded` events stamps
   the new filter version.

This is the audit primitive for "when did the scope change and
who approved it?"

## 12. References

### 12.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 12.2 UIAO docs

- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 2 → D2.8.

### 12.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — substrate; §3.4 names synchronization-job scoping.
- [Spec2-D2.1 — Joiner](./Spec2-D2.1-JoinerWorkflowSpecification.md) — pre-condition #2 calls in here.
- [Spec2-D2.4 — Rehire](./Spec2-D2.4-RehireWorkflowSpecification.md) — rehire window expiry boundary.
- [Spec2-D2.6 — Error Handling & Quarantine](./Spec2-D2.6-ErrorHandlingQuarantineSpecification.md).
- [Spec2-D2.7 — Pre-Hire Provisioning Window](./Spec2-D2.7-PreHireProvisioningWindowSpecification.md) — the lookahead boundary.
- Spec2-D1.6 — worker-type taxonomy.
- Spec2-D1.8 — HR data-quality requirements (forthcoming).

### 12.4 Microsoft documentation (verification pending in v0.2)

- Microsoft Learn — Entra ID provisioning synchronization-job scoping filter syntax.
- Microsoft Learn — `bulkUpload` payload-rejection semantics.

### 12.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, AC-3 (access enforcement — the scope is an access-enforcement decision).
