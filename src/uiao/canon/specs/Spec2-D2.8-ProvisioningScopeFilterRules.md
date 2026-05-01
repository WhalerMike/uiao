---
deliverable_id: Spec2-D2.8
title: "Provisioning Scope Filter Rules"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 2
status: Draft
version: 0.2
owner: Identity Architecture
created: 2026-04-30
updated: 2026-05-01
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
verification_history:
  - date: 2026-05-01
    pass: "v0.1 → v0.2 (initial verification)"
    source: "Microsoft Learn — Scoping users or groups to be provisioned with scoping filters in Microsoft Entra ID"
    url: "https://learn.microsoft.com/en-us/entra/identity/app-provisioning/define-conditional-rules-for-provisioning-user-accounts"
    confirmed:
      - "Synchronization-job scoping filters consist of one or more clauses; clauses are nested inside Groups"
      - "All clauses inside a Group must be satisfied (logical AND); when multiple Groups are defined, at least one Group must be satisfied (logical OR)"
      - "A clause is defined by selecting a source Attribute Name, an Operator, and an Attribute Value"
      - "Supported operators include: EQUALS (case-sensitive exact match), ENDS_WITH, & (substring contains), !& (substring does NOT contain) among others"
    corrected:
      - field: "Illustrative Entra-side filter expression in §5"
        from: |
          employmentStatus IN ("Active", "On Leave")
            AND country IN ("US")
            AND workerType IN ("Full-Time Employee", "Part-Time Employee", "Contractor", "Intern")
        to:   "Microsoft does not use SQL-style IN(...) in scoping filter expressions. The canonical authoring surface is the Clauses-within-Groups builder using EQUALS / ENDS_WITH / & / !& operators. v0.2 reframes §5 to describe the Group/Clause structure rather than emit a literal expression string."
        impact: "Prose-only correction; no implementation impact since §5's prior syntax was illustrative and explicitly flagged as 'final syntax pending v0.2 verification'."
  - remaining_unverified:
      - "bulkUpload payload-rejection semantics (specifically: schema-validator-side 4xx codes for fields outside the synchronization job's scope) — search results identify the troubleshooting page exists but did not enumerate response codes per rejection class"
---

# Spec 2 — D2.8: Provisioning Scope Filter Rules

> **Status (v0.2, 2026-05-01):** Initial verification pass against
> Microsoft Learn scoping-filters reference complete. Confirmed
> the Clause/Group structure (clauses within groups; AND inside,
> OR across) and the supported operator set (`EQUALS`,
> `ENDS_WITH`, `&`, `!&`). **Material correction:** v0.1's §5
> illustrative expression used SQL-style `IN(...) AND ...`
> syntax which is not Microsoft's authoring surface. v0.2
> reframes §5 around the canonical Clause-builder operators.
> See frontmatter `verification_history`.

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

### 5.1 Microsoft Entra scoping-filter authoring surface

Per Microsoft Learn (verified 2026-05-01), Entra ID provisioning
scoping filters are authored as **Clauses nested inside Groups**:

- Each **Clause** has three fields: source attribute name, operator,
  attribute value.
- All clauses inside a **Group** are joined by logical **AND** —
  every clause in the group MUST be satisfied for the group to
  match.
- When **multiple Groups** are defined, they are joined by logical
  **OR** — at least ONE group MUST be satisfied for the rule to
  apply.

Supported operators include:

| Operator | Semantics |
|---|---|
| `EQUALS` | Attribute matches the input value exactly (case-sensitive) |
| `ENDS_WITH` | Attribute ends with the input value |
| `&` (contains) | Attribute exists/contains the input value |
| `!&` (not-contains) | Attribute does NOT contain the input value |

Additional operators exist for present/not-present, regex, and
greater-than/less-than comparisons; the authoritative list is on
the Microsoft Learn scoping-filters page (linked in §12.4).

### 5.2 The canonical UIAO scoping rule

Expressed in the Microsoft Clause/Group authoring shape:

**Group 1 — Active employees / on-leave employees, US, eligible
worker types** (all clauses must match):

| Source attribute | Operator | Value |
|---|---|---|
| `employmentStatus` | `EQUALS` | `Active` |
| `country` | `EQUALS` | `US` |
| `workerType` | `EQUALS` | `Full-Time Employee` |

**Group 2** — same except `workerType EQUALS Part-Time Employee`.
**Group 3** — `workerType EQUALS Contractor`.
**Group 4** — `workerType EQUALS Intern`.
**Group 5** — `employmentStatus EQUALS On Leave` + remaining
matching predicates.

(The group-multiplication is required because `EQUALS` is
single-valued; SQL-style multi-value `IN (...)` is not part of
Microsoft's authoring surface.)

The middleware MUST emit ONLY records that pass this rule. If
the middleware emits a record that the Entra filter would reject,
the deployment is misconfigured — both filters MUST be treated as
the same scope rule.

The deployment's substrate-manifest binds the canonical UIAO
scope-filter shape (the per-deployment value lists from §3.1) to
the Entra-side group expansion above. The middleware's startup
phase MUST validate that the per-deployment Entra synchronization
job's scoping filter is the expansion of the middleware-side
configuration; mismatches surface as `filter-version-skew`
(§10).

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

### 12.4 Microsoft documentation

**Verified at v0.2 (2026-05-01):**

- Microsoft Learn — Scoping users or groups to be provisioned with scoping filters in Microsoft Entra ID:
  `https://learn.microsoft.com/en-us/entra/identity/app-provisioning/define-conditional-rules-for-provisioning-user-accounts`
  Confirmed: Clause/Group structure; `EQUALS`, `ENDS_WITH`, `&`, `!&` operators; per-clause source attribute + operator + value triple. §5 reframed accordingly.

**Remaining unverified at v0.2:**

- Microsoft Learn — `bulkUpload` payload-rejection semantics (per-rejection-class HTTP response codes). The troubleshooting page exists; this verification pass did not enumerate response-code/error-class mapping.

### 12.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, AC-3 (access enforcement — the scope is an access-enforcement decision).
