---
deliverable_id: Spec2-D2.4
title: "Rehire Workflow Specification"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 2
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-04-30
updated: 2026-04-30
canonical_adrs:
  - ADR-003
  - ADR-035
  - ADR-048
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
  - Spec2-D1.5
  - Spec2-D3.1
sibling_deliverables:
  - Spec2-D2.1
  - Spec2-D2.3
  - Spec2-D2.6
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D2.4: Rehire Workflow Specification

> **Status (v0.1, 2026-04-30):** Initial draft. Awaiting verification
> against Microsoft Graph user-restoration semantics for soft-deleted
> users and Lifecycle Workflows reactivation reference.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Rehire workflow specification called
for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 2 → D2.4:

> *Rehire handling: match on Employee ID, reactivate vs. create new,
> attribute refresh, OrgPath reassignment, license reassignment,
> access review, manager notification.*

Rehire is the inverse of Leaver during the retention window. It is
also a Joiner variant when the prior `externalId` has aged out of
retention. The decision boundary — reactivate vs. create new — is
the load-bearing rule of D2.4.

### 1.1 Scope

In scope:

- The match-and-decide rule (`externalId` correlation; HR
  `employeeId` immutability assumption).
- The reactivation path (`active: false` → `active: true` on the
  same record, with attribute refresh).
- The new-record path (when retention has expired or HR issued a
  new `employeeId`).
- Attribute-refresh semantics on rehire.
- Access review trigger on rehire.
- Manager notification.
- Provenance event vocabulary (`provisioning.user.rehire`).

Out of scope:

- HR-side rehire-decision logic (whether the person is re-hired at
  all is HR's call).
- Knowledge-of-prior-employment policy (whether HR informs the
  new manager of the rehire — a tenant policy concern).
- Soft-deleted-user restoration when retention has not just
  expired but the record has been hard-deleted by Lifecycle
  Workflows — that's a Joiner case.

## 2. Match Rule

The middleware MUST attempt to match incoming HR records against
existing Entra ID records using `externalId` (the HR `employeeId`,
preserved across the leaver retention window per D2.3 §6).

### 2.1 Match outcomes

| HR record state | Entra ID state | Rehire decision |
|---|---|---|
| Same `employeeId` as a record currently `active: false` within retention | Record present, `accountEnabled: false` | **Reactivate** (path A) |
| Same `employeeId`, retention window expired, record hard-deleted | No record | **Create new** as a Joiner (path B) |
| Different `employeeId`, same person (per HR's identity match) | Possibly present under prior ID | **Create new** (path B); flag for HR data-quality review |
| Same `employeeId`, record still `active: true` | Present and active | **Not a rehire** — this is a Mover or no-op |

The key invariant: UIAO trusts HR's `employeeId` as the durable
identity correlation. If HR re-uses the same `employeeId` for the
rehired person, UIAO reactivates. If HR issues a new `employeeId`
(e.g., agency policy mandates), UIAO treats the rehire as a new
joiner and the prior record's audit trail is preserved separately.

### 2.2 Match window

The reactivation match is bounded by the leaver retention window
(D2.3 §6) plus a tenant-configurable rehire grace window. After
`leaver_termination_date + retention_window + rehire_grace_window`,
the record is no longer reactivatable — it is treated as new.

Default values:

- Retention window: 90 days (federal civilian default per D2.3).
- Rehire grace window: 30 days.
- Aggregate rehire-eligible window: 120 days from termination.

Tenants may extend per agency-specific NARA schedule.

## 3. Path A: Reactivation

### 3.1 Trigger

HR record arrives with:

- `employeeId` matches an Entra ID record where `active: false`
  AND that record's prior leaver record is within the rehire-
  eligible window per §2.2.
- `terminationDate` is no longer set OR is a future date (i.e., HR
  is re-engaging the worker, not extending the prior termination).

### 3.2 Sequence

1. **Match resolution.** Confirm `externalId` correlation; load
   prior canonical payload from the provenance store.
2. **Attribute refresh.** Apply the new HR record's attributes via
   PATCH. This is the standard Joiner attribute population sequence
   (D2.1 §4) but against an existing record:
   - OrgPath recalculation (NEW org placement on rehire).
   - UPN reconsideration (typically preserved if same person — the
     UPN is durable identity for legacy artifacts).
   - Manager link refresh.
   - Display name composition.
   - `usageLocation` refresh.
   - All other D1.1 fields refreshed from the current HR feed.
3. **Reactivation.** SCIM PATCH `active: true`.
4. **License reassignment.** Group-based licensing recomputes
   automatically as `accountEnabled` flips and OrgPath / worker-
   type attributes settle.
5. **Access review trigger.** Mandatory on rehire — see §5.
6. **Manager notification.** See §6.
7. **Provenance emission.** `provisioning.user.rehire.reactivate`
   per §7.

### 3.3 Reactivation SCIM payload

The PATCH MUST set `active: true` and replace any attributes whose
canonical hash differs from the prior canonical payload. The
middleware MUST NOT issue separate PATCH operations for
reactivation and attribute refresh — they are atomic in a single
PATCH per record:

```json
{
  "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
  "Operations": [
    { "op": "replace", "path": "active", "value": true },
    { "op": "replace", "path": "displayName", "value": "..." },
    { "op": "replace",
      "path": "urn:scim:schemas:extension:Microsoft:2.0:User:extensionAttribute1",
      "value": "..." }
    // ...remaining changed fields
  ]
}
```

### 3.4 Group memberships on reactivation

Statically-assigned groups removed during D2.3 step 4 are NOT
re-added by reactivation. The user begins with **only** the
group memberships that the dynamic-group engine reconstructs from
the refreshed attributes (per D2.2 §6). Static group membership
restoration is an HR-operations decision and is out of scope for
the middleware.

This is intentional: a rehired worker should not silently inherit
the access surface of their prior employment unless explicitly
re-granted. The access review (§5) is the canonical mechanism for
this re-grant.

## 4. Path B: Create New

When the match fails (retention expired, or HR issued a new
`employeeId`), the rehire is processed as a Joiner per D2.1. The
only differences from a typical Joiner are:

- The provenance event is emitted as `provisioning.user.rehire.new`
  instead of `provisioning.user.joiner` so the audit trail
  distinguishes the rehire from a true new hire.
- The new-record creation MAY emit a `rehire.prior-record-link`
  provenance event with a reference to the prior `externalId`,
  IF HR provides that linkage. This is explicitly tenant-policy
  controlled — some agencies require the link, others prohibit
  it (privacy / fresh-start posture).

## 5. Access Review Trigger

The Rehire workflow MUST emit an access-review trigger event on
both Path A (reactivation) and Path B (new-record) regardless of
the org placement. The shape mirrors D2.2 §8 with the trigger
reason set to `rehire`:

```yaml
event_type: rehire.access-review-trigger
external_id: <employeeId>
upn: <UPN>
trigger_reasons:
  - rehire
prior_state:
  termination_date: <date from leaver record>
  prior_orgpath: <OrgPath at termination>
new_state:
  hire_date: <date>
  orgpath: <new OrgPath>
suggested_review_scope:
  - all-current-group-memberships
  - manager-attestation-required
```

The access review is mandatory because the rehired worker may have
substantially different access needs than at termination, and the
manager attestation is an audit-grade control under AC-2.

## 6. Manager Notification

The Rehire workflow MUST emit a manager-notification event on
reactivation:

| Field | Value |
|---|---|
| `event_type` | `rehire.manager-notify` |
| `external_id` | `employeeId` |
| `upn` | UPN |
| `manager_upn` | New manager UPN |
| `prior_termination_date` | from leaver record |
| `rehire_path` | `reactivate` or `new` |

Idempotency: keyed on `(externalId, event_type, hire_date)`.

## 7. Provenance Emission

The Rehire workflow emits one of:

| Path | `event_type` | Notes |
|---|---|---|
| A — Reactivation | `provisioning.user.rehire.reactivate` | Includes `delta` block with prior vs. new orgpath / manager / department |
| B — New | `provisioning.user.rehire.new` | Joiner-equivalent shape |

Control evidence: AC-2, IA-4, AC-6 (the access review).

The Path-A delta block MUST capture:

```yaml
delta:
  active:
    before: false
    after: true
  orgpath:
    before: "GOV/EXEC/OPM/HRIT"
    after:  "GOV/EXEC/OPM/SECURITY"
  manager:
    before: "EMP-00789"
    after:  "EMP-04412"
  termination_window:
    leaver_date: <prior termination date>
    rehire_date: <current hire date>
    days_inactive: <integer>
```

This is the audit anchor for the rehire — a future auditor can
reconstruct the full lifecycle by joining `provisioning.user.leaver.*`
and `provisioning.user.rehire.reactivate` records on `externalId`.

## 8. Failure Modes

Delegated to D2.6. Rehire-specific failure surface:

| Failure | `failure_reason` | Routing |
|---|---|---|
| Match window exceeded but record still soft-present | `rehire-window-expired` | Treat as Path B (new); do NOT reactivate |
| Reactivate-active-record collision (duplicate processing) | `rehire-active-collision` | No-op; provenance emitted as `outcome: already-active` |
| Refreshed attributes fail D1.1 schema validation | `schema-validation` | Quarantine (D2.6) |
| New `employeeId` for known-rehire person, prior-record-link policy violation | `prior-link-policy` | Tenant-specific resolution |

## 9. Idempotency

1. The same Rehire event processed twice in the same cycle MUST
   produce one PATCH operation.
2. A reactivation against an already-`active: true` record is a
   no-op with `outcome: already-active`.
3. The access-review trigger and manager-notification events are
   idempotent on `(externalId, event_type, hire_date)`.

## 10. References

### 10.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-035](../adr/adr-035-orgpath-codebook-binding.md)
- [ADR-048](../adr/adr-048-orgpath-attribute-storage-decision.md)

### 10.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_135](../UIAO_135_identity-directory-transformation-inventory.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 2 → D2.4.

### 10.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — substrate.
- [Spec2-D2.1 — Joiner](./Spec2-D2.1-JoinerWorkflowSpecification.md) — Path B target.
- [Spec2-D2.3 — Leaver](./Spec2-D2.3-LeaverWorkflowSpecification.md) — symmetric inverse; defines retention.
- [Spec2-D2.6 — Error Handling & Quarantine](./Spec2-D2.6-ErrorHandlingQuarantineSpecification.md).

### 10.4 Microsoft documentation (verification pending in v0.2)

- Microsoft Graph — soft-deleted-user restoration.
- Microsoft Learn — Lifecycle Workflows reactivation tasks.
- Microsoft Graph — Access Reviews trigger semantics.

### 10.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, AC-6, IA-4.
