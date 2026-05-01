---
deliverable_id: Spec2-D2.7
title: "Pre-Hire Provisioning Window Specification"
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
  - Spec2-D1.5
  - Spec2-D3.1
sibling_deliverables:
  - Spec2-D2.1
  - Spec2-D2.6
  - Spec2-D2.8
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D2.7: Pre-Hire Provisioning Window Specification

> **Status (v0.1, 2026-04-30):** Initial draft. Awaiting verification
> against agency hiring SLAs and Microsoft Learn `accountEnabled`
> timing semantics.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Pre-Hire Window specification called
for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 2 → D2.7:

> *Define timing: how many days before start date should account be
> created? Which attributes are populated at pre-hire vs. day-of-hire?
> When does the account become enabled? When does license assignment
> occur?*

D2.7 is the timing companion to D2.1 (Joiner). D2.1 §2 names three
temporal modes; D2.7 specifies the windows, the attribute splits, and
the operator-tunable knobs.

### 1.1 Scope

In scope:

- The pre-hire window length (default + bounds + tenant-policy
  overrides).
- Which attributes are populated during pre-hire vs. day-of-hire.
- The `accountEnabled` (`active`) state machine across the window.
- License assignment timing.
- Welcome-notification timing relative to the window.
- Edge cases: pre-hire date in the past, pre-hire date never
  reaching day-of-hire (rescinded offer), variable-length windows
  by worker type.

Out of scope:

- The Joiner workflow itself (D2.1 is the substrate; D2.7 specifies
  its temporal parameters).
- Day-zero provisioning when the worker arrives without HR-side
  pre-hire processing — that's a Joiner edge case handled by D2.1
  §2 (mode = day-of-hire, no prior pre-hire pass).
- Onboarding-program logistics (training schedules, equipment
  shipping, etc.) — those are HR/IT-ops concerns.

## 2. The Pre-Hire Window

### 2.1 Default

The canonical default pre-hire window for UIAO is **14 calendar
days**:

- An HR record with `startDate` ≤ `today + 14 days` is in scope
  for pre-hire processing.
- Records with `startDate > today + 14 days` are deferred (per
  D2.8 §3, scope filter); they will enter scope on a future sync
  cycle as the start date approaches.

### 2.2 Bounds

The window is bounded by:

| Bound | Value | Reason |
|---|---|---|
| Minimum | 1 calendar day | Same-day pre-hire is degenerate; forces day-of-hire mode |
| Maximum | 60 calendar days | Beyond 60 days, license-allocation churn and stale-record exposure outweigh the early-onboarding benefit |
| Per-worker-type override | tenant policy | Some agencies pre-hire FTEs at 30 days but contractors at 7 days |

Tenants may set per-worker-type windows. The middleware reads them
from the worker-type taxonomy (D1.6) joined with the deployment's
configuration.

### 2.3 Disabled state during the window

Throughout the pre-hire window, the account MUST be `active: false`.
This is the load-bearing security posture:

- The account exists in Entra ID (license-bound where applicable;
  group memberships established).
- The account cannot acquire tokens (interactive sign-in fails).
- License assignment may still occur if the tenant chose an
  early-license posture (see §4); it is decoupled from
  sign-in capability.

The transition to `active: true` occurs on day-of-hire per D2.1 §2.

## 3. Attribute Population Split

D2.7 specifies which attributes are populated when. The default
posture is "everything on pre-hire", with a small set of
exceptions:

### 3.1 Populated at pre-hire creation (POST `/Users`)

The full canonical SCIM payload from D3.1 §5.2:

- `externalId` (HR `employeeId`)
- `userName` (UPN)
- `name.givenName` / `name.familyName`
- `displayName`
- `active: false`
- `emails`
- `phoneNumbers` (if present)
- `addresses` (if present)
- `enterprise:User.employeeNumber`
- `enterprise:User.department`
- `enterprise:User.manager`
- `extensionAttribute1` (OrgPath)
- `usageLocation`
- Worker-type-bound license-affinity attribute

Rationale: pre-hire creation should be **payload-complete**. Late
attribute fills cause additional sync churn and a broader audit
surface (more provenance records to reason about per `externalId`).

### 3.2 Populated only at day-of-hire (PATCH transition)

The single mandatory exception is `active`:

- `active: false` at pre-hire creation.
- `active: true` at day-of-hire transition.

Tenants MAY add additional attributes to the day-of-hire-only set,
but the canonical UIAO posture keeps the set minimal. Examples of
attributes some tenants defer to day-of-hire:

- Group memberships of statically-assigned groups (kept null
  during pre-hire to avoid legacy-document share-permission
  pre-grant — explicit operator preference).
- Mailbox creation (some tenants defer mailbox provisioning to
  day-of-hire to reduce Exchange license window).

### 3.3 Updateable during the window

If HR-side data changes during the pre-hire window (e.g., department
finalized later than initial offer), the middleware MUST PATCH
the existing pre-hire record. This is a Mover-class event during
the pre-hire window; attribute updates use the D2.2 update
sequence (D2.2 §4) but the `active` flag remains `false`.

The middleware MUST emit a provenance event of type
`provisioning.user.joiner` (NOT `provisioning.user.mover`) for
attribute changes during pre-hire — this is still part of the
joiner lifecycle, not a mover event. The first mover event for an
`externalId` is the first attribute change AFTER day-of-hire.

## 4. License Assignment Timing

License assignment timing has two viable postures, both supported:

### 4.1 Posture A: Pre-hire license (default)

License is assigned at pre-hire creation via group-based licensing.
The license is consumed during the pre-hire window even though the
account is disabled.

| Pro | Con |
|---|---|
| Day-of-hire is friction-free; mailbox / Teams / OneDrive provisioning has time to settle | License window is wider; cost overrun if pre-hire never reaches day-of-hire |
| Welcome email can be drafted into the new mailbox in advance | Licensed-but-disabled accounts have a slight audit-surface overhead |

### 4.2 Posture B: Day-of-hire license

License is held back; the user is in the relevant dynamic groups
but a `accountEnabled eq true` filter on the licensing rule blocks
assignment.

| Pro | Con |
|---|---|
| No license consumption during pre-hire | Day-of-hire has provisioning latency for license-bound services |

### 4.3 Choice

The default UIAO posture is **Posture A (pre-hire license)**.
Rationale: federal civilian operations cannot tolerate a
day-of-hire mailbox-provisioning lag of 30+ minutes for new
employees. License cost overrun on rescinded offers is
quantifiable and small relative to onboarding-friction cost.

Tenants may override to Posture B via configuration. The decision
is logged in the deployment's substrate-manifest.yaml.

## 5. Day-of-Hire Transition Trigger

The middleware's day-of-hire transition trigger:

- On every sync cycle, scan all pre-hire (`active: false`) records.
- For records where `startDate <= today (UTC)` AND the record has
  not yet had a `joiner.day-of-hire` provenance event, emit the
  PATCH `active: true` operation.

The "today" comparison MUST use the tenant's configured time zone
when evaluating the date boundary, NOT the middleware's local
time. Federal agencies often span US time zones; a record whose
`startDate` is in Pacific Time should not transition at 8 PM Pacific
because the middleware ran in UTC.

The middleware MUST NOT transition a record whose `startDate` is
in the past relative to the tenant time zone but the record was
never pre-hired. That case is the "no pre-hire pass" branch of
D2.1 §2 (mode = day-of-hire) — it is handled by Joiner directly,
not by D2.7.

## 6. Edge Cases

### 6.1 Rescinded offer (pre-hire never reaches day-of-hire)

When HR rescinds an offer before `startDate`:

- The HR feed flags the record (e.g., `employmentStatus: rescinded`
  or simply removes the record).
- The middleware MUST detect this and emit a Leaver-equivalent
  cleanup against the pre-hire record:
  - Disable confirmation (already `active: false`).
  - Group-membership removal (if any statically-assigned groups
    were applied; dynamic groups self-correct).
  - Mailbox archival (if Posture A and mailbox was created).
  - Provenance event: `provisioning.user.joiner.rescinded`.
- The retention window for rescinded pre-hires is shorter than
  the canonical Leaver retention — default 30 days.

This is handled in the joiner family, not the leaver family,
because the worker never reached `active: true`. The audit trail
distinguishes a never-active rescission from a normal leaver
event.

### 6.2 `startDate` in the past at first observation

If the middleware observes an HR record where `startDate` is
already past — meaning the worker has effectively passed both
pre-hire and day-of-hire windows in a single observation:

- The middleware processes it as a direct day-of-hire event (D2.1
  §2 mode = day-of-hire, no prior pre-hire pass).
- It emits a single POST `/Users` with `active: true`.
- It emits a `provisioning.user.joiner` provenance record with
  `correlation.start_date_observed_late: true` flag.

This is the "HR feed catching up" case (e.g., manual-entry agencies
with delayed system-of-record feeds).

### 6.3 Variable-length windows by worker type

When per-worker-type windows differ:

- The middleware reads the window from the worker-type taxonomy
  (D1.6) on every record.
- A worker-type CHANGE during pre-hire (which would be a Conversion
  per D2.5) MUST trigger a window recomputation. If the new
  worker type's window is shorter and `startDate` is now outside
  that shorter window, the record is moved to the day-of-hire
  branch.

### 6.4 Window misconfiguration

If the deployment's window configuration is missing or invalid
(e.g., `pre_hire_window_days: -1`):

- The middleware MUST surface a startup-time error before
  processing any HR records.
- It MUST NOT fall back to a hardcoded default — that risks a
  silent posture change on configuration error.

This is enforced by the configuration schema in
`substrate-manifest.yaml`.

## 7. Welcome Notification Timing

Per D2.1 §9: the welcome notification fires on day-of-hire, NOT
during pre-hire.

D2.7 binds the rule explicitly:

- Pre-hire creation: NO notification (account exists, but the
  worker is not "live" yet).
- Day-of-hire transition: SINGLE notification (idempotent on
  `(externalId, joiner.day-of-hire)`).
- Pre-hire attribute update during the window: NO notification.
- Rescission during the window: NO notification (the worker never
  arrived).

## 8. Provenance Emission

D2.7 itself does not introduce new provenance event types. The
events emitted across the window:

| Time | Event | Source |
|---|---|---|
| Pre-hire creation | `provisioning.user.joiner` (active=false) | D2.1 |
| Pre-hire attribute update | `provisioning.user.joiner` (active=false; delta block) | D2.1 + D2.7 |
| Day-of-hire transition | `provisioning.user.joiner` (active=true; transition flag) | D2.1 |
| Rescission | `provisioning.user.joiner.rescinded` | D2.7 §6.1 |

The middleware MUST stamp a `pre_hire_window_observed: <integer>`
field in the provenance correlation block on the day-of-hire
event, recording how many days before `startDate` the pre-hire
record was first created. This is operationally useful — agencies
tune the window based on observed mean pre-hire-creation lead
time.

## 9. Operator Knobs

The operator-tunable configuration surface for D2.7:

```yaml
pre_hire_window:
  default_days: 14
  per_worker_type:
    Full-Time Employee: 14
    Part-Time Employee: 7
    Contractor: 7
    Intern: 30          # interns often start later than they're hired
    Vendor: 0           # vendors are day-of-hire only
    Volunteer: 0
  license_posture: "pre-hire"   # or "day-of-hire"
  rescission_retention_days: 30
  time_zone: "America/New_York"  # tenant time zone for startDate comparison
```

The configuration lives in the deployment's
`substrate-manifest.yaml` per the canonical config-binding pattern.

## 10. Failure Modes

D2.7-specific failure modes (delegated to D2.6):

| Failure | `failure_reason` | Routing |
|---|---|---|
| Window misconfigured | `prehire-window-config` | Operator alert; not record-specific |
| `startDate` unparseable | `start-date-invalid` | Quarantine |
| Time-zone configuration missing | `prehire-timezone-config` | Operator alert |

## 11. References

### 11.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 11.2 UIAO docs

- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 2 → D2.7.

### 11.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — substrate; §5.5 establishes pre-hire as `active: false`.
- [Spec2-D2.1 — Joiner](./Spec2-D2.1-JoinerWorkflowSpecification.md) — workflow this spec parameterizes.
- [Spec2-D2.6 — Error Handling & Quarantine](./Spec2-D2.6-ErrorHandlingQuarantineSpecification.md).
- [Spec2-D2.8 — Provisioning Scope Filter Rules](./Spec2-D2.8-ProvisioningScopeFilterRules.md) — far-future records are filtered there.
- Spec2-D1.6 — worker-type classification taxonomy (per-worker-type window source).

### 11.4 Microsoft documentation (verification pending in v0.2)

- Microsoft Graph — `accountEnabled` write semantics.
- Microsoft Learn — Group-based licensing `accountEnabled` filter behavior.

### 11.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, IA-4.
