---
deliverable_id: Spec2-D2.5
title: "Conversion Workflow Specification"
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
  - ADR-049
canonical_docs:
  - UIAO_007
  - UIAO_135
  - UIAO_136
upstream_deliverables:
  - Spec2-D1.1
  - Spec2-D1.5
  - Spec2-D1.6
  - Spec2-D3.1
sibling_deliverables:
  - Spec2-D2.2
  - Spec2-D2.3
  - Spec2-D2.6
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D2.5: Conversion Workflow Specification

> **Status (v0.1, 2026-04-30):** Initial draft. Awaiting verification
> against Microsoft Learn group-based licensing tier-change semantics
> and Lifecycle Workflows worker-type-change tasks if such exist.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Conversion workflow specification
called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 2 → D2.5:

> *Contractor-to-employee conversion (and reverse): worker type
> change trigger, attribute remapping, license tier change, group
> membership overhaul, access scope change, OrgPath recalculation.*

Conversion is distinguished from Mover (D2.2) by **what changes**:
the worker type itself. A worker-type change has cascading effects
that ordinary attribute deltas do not — license tier, group set,
retention policy, and audit posture all shift. D2.5 codifies the
discipline required.

### 1.1 Scope

In scope:

- The Conversion trigger surface (worker-type deltas only).
- The bidirectional conversion paths (contractor ↔ employee, and
  the longer matrix of worker-type-to-worker-type transitions per
  D1.6).
- UPN preservation rule under conversion.
- License tier change semantics.
- Group-membership overhaul vs. preservation rules.
- Access review trigger (mandatory).
- OrgPath recalculation.
- Provenance event vocabulary (`provisioning.user.conversion`).

Out of scope:

- Termination — that's Leaver (D2.3); a contractor's contract-end
  date is a Leaver event when the worker is **leaving**, not when
  they are **converting**.
- Joiner / Mover / Rehire mechanics — those have their own specs.
- HR-side decision logic (whether a contractor is eligible for
  conversion is HR / hiring-manager territory).

## 2. Conversion Trigger Surface

A Conversion event is defined as a non-empty delta on the HR
`workerType` attribute for a record that is currently `active:
true`. The middleware MUST detect worker-type deltas BEFORE
evaluating Mover triggers (per D2.2 §2 explicit precedence).

### 2.1 The conversion matrix

Per the D1.6 worker-type taxonomy (when published), the canonical
conversion paths are:

| From | To | Common case | Notes |
|---|---|---|---|
| Contractor | Full-Time Employee | Contractor-to-FTE conversion | The classic path; license tier upgrades, retention extends |
| Part-Time Employee | Full-Time Employee | Promotion-class conversion | Often paired with title / department change |
| Full-Time Employee | Part-Time Employee | Reverse promotion / lifestyle change | License tier may downgrade |
| Full-Time Employee | Contractor | Reverse conversion | Access scope shrinks; retention shortens |
| Intern | Full-Time Employee | Intern-to-FTE | Common at end of internship |
| Intern | Contractor | Internship → contracted continuation | Less common |
| Vendor | Contractor | Vendor → embedded contractor | Tenant-policy-specific |
| Volunteer | (any paid type) | Volunteer → paid worker | Atypical; tenant-policy review |
| External Collaborator | (any internal type) | B2B → internal hire | Cross-tenant case; outside scope of D2.5 v0.1 |

Each transition has its own license / group / retention profile.
D1.6 enumerates them; D2.5 binds the workflow timing.

### 2.2 The contract-end edge case

A contractor whose contract ends without conversion is a **Leaver**
(D2.3), not a Conversion. The trigger discriminator is:

- `workerType` change with `active: true` preserved → Conversion.
- `terminationDate <= today` with no new `workerType` → Leaver.
- Same record receiving both signals in the same cycle → **Leaver
  wins** (per D2.3 §3 precedence).

## 3. Pre-Conditions

Before a record is eligible for Conversion processing:

1. The record is currently `active: true` in Entra ID.
2. The HR `workerType` value is in the D1.6 canonical taxonomy.
3. The new `workerType` is in the D1.6 canonical taxonomy.
4. The transition path is in the §2.1 matrix (or has explicit
   tenant-policy support).
5. The HR record passes scope filter rules (D2.8) for the new
   worker type.

Records failing pre-conditions route to D2.6 quarantine with the
appropriate `failure_reason`.

## 4. Attribute Remapping

Conversion MUST execute the full Joiner-style attribute population
sequence (D2.1 §4) against the existing record. The reasoning: a
worker-type change is large enough that EVERY attribute should be
re-derived from the post-conversion HR record, not just the
delta-detected fields. This is the most conservative posture and
the canonical UIAO choice.

### 4.1 UPN preservation rule

Conversion MUST **preserve the UPN** unless tenant policy
explicitly requires otherwise. UPN preservation under conversion is
load-bearing for:

- Legacy email continuity.
- Document and SharePoint share permissions tied to UPN.
- M365 Graph correlation in audit logs.

If the HR feed presents a different UPN derivation rule for the
new worker type (e.g., contractor `firstname.lastname.contractor@`
vs. employee `firstname.lastname@`), the middleware MUST flag this
to operations and **NOT** auto-flip the UPN. UPN flips are an
operator decision logged in a dedicated provenance event
(`conversion.upn-flip`).

### 4.2 OrgPath recalculation

OrgPath MUST be recalculated. A worker-type change frequently
correlates with a department / role / cost-center change; even
when departmental fields are nominally unchanged, the worker type
may be a codebook component (per ADR-035 codebook design). The
recalculation handles either case.

### 4.3 `extensionAttribute2` (worker-type / license-affinity)

Per D2.1 §7, the worker-type-derived license-affinity attribute
(typically `extensionAttribute2` in tenant-specific configurations)
MUST be re-stamped to reflect the new worker type. This is the
trigger that drives group-based licensing recompute.

## 5. License Tier Change

License tier changes are an automatic consequence of worker-type
attribute change feeding into group-based-licensing dynamic group
rules. The middleware does not directly assign licenses.

### 5.1 The transition window

A license tier change can produce a brief window where:

- The user is removed from the prior worker-type-bound group
  (license released).
- The user is added to the new worker-type-bound group (license
  granted).

The two events are NOT atomic — Entra ID processes them in
sequence. For a fraction of a sync interval the user may have
**neither** license (interim sign-in failures) or **both**
licenses (transient over-allocation). The middleware MUST emit a
`conversion.license-transition` provenance event so the audit
trail captures the window.

Mitigation: the middleware SHOULD pre-stamp both old and new
worker-type-bound group memberships on the same SCIM PATCH that
flips `workerType`. This biases toward the both-licenses-briefly
case rather than the neither-license case. For tenants where
license-cost overrun is unacceptable, a tenant-configurable
inverse posture is supported. Default: prefer both-briefly.

### 5.2 Region-restricted SKU edge case

If conversion involves a country-code change (e.g., contractor
abroad → US-based employee), the `usageLocation` shift may
disqualify the user from a region-restricted SKU on one side of
the transition. The middleware MUST emit a
`conversion.region-restriction` warning in the provenance record;
the operator is responsible for license-portfolio adjustment.

## 6. Group Membership Overhaul

Conversion has the **most aggressive group-membership semantics** of
any D2.x workflow:

| Group class | Behavior on conversion |
|---|---|
| Worker-type-bound dynamic groups | Auto-recompute on attribute write (membership cascade) |
| Department / OrgPath dynamic groups | Auto-recompute on OrgPath write |
| Statically-assigned groups (general) | **Preserved** — operator may override |
| Statically-assigned groups marked `worker-type-restricted` (tenant tag) | **Removed** — see §6.1 |
| Privileged-role-assignable groups | **Reviewed** — see §6.2 |

### 6.1 Worker-type-restricted statically-assigned groups

Some statically-assigned groups (typically administrative or
sensitive-access groups) are tenant-tagged as restricted to
specific worker types. The middleware MUST enumerate and remove
the user from any such group whose tag does not match the new
worker type.

The tag convention (one of several supported tenant-policy
shapes):

- Group description prefix: `[worker-type:fte,contractor]` →
  group is restricted to FTE and Contractor worker types.
- Or: a custom security attribute on the group (`workerTypeAllowed`).

### 6.2 Privileged-role review

If the user holds any role-assignable-group memberships, the
Conversion workflow MUST emit an immediate access-review trigger
specifically for the role assignments. Privileged access does not
auto-cascade through worker-type changes; manual attestation is
required (control AC-6).

## 7. Access Review Trigger

The Conversion workflow MUST emit a mandatory access-review
trigger:

```yaml
event_type: conversion.access-review-trigger
external_id: <employeeId>
upn: <UPN>
trigger_reasons:
  - conversion
old_state:
  worker_type: "Contractor"
  orgpath: "GOV/EXEC/OPM/HRIT/External"
  department: "HRIT"
new_state:
  worker_type: "Full-Time Employee"
  orgpath: "GOV/EXEC/OPM/HRIT"
  department: "HRIT"
suggested_review_scope:
  - all-current-group-memberships
  - role-assignable-groups        # mandatory per §6.2
  - manager-attestation-required
  - re-baseline-access-by-new-worker-type
```

The access review is mandatory on every conversion regardless of
direction. Even a tier-up (contractor → FTE) changes the access
posture and warrants attestation.

## 8. Provenance Emission

The Conversion workflow emits a primary provenance record plus
supplementary records for each material side-effect:

| Sub-event | `event_type` | Trigger |
|---|---|---|
| Primary | `provisioning.user.conversion` | Always — on the SCIM PATCH that flips `workerType` |
| UPN flip | `provisioning.user.conversion.upn-flip` | If UPN was changed (operator-approved override of §4.1) |
| License transition window | `provisioning.user.conversion.license-transition` | Always — captures the §5.1 window |
| Region restriction warning | `provisioning.user.conversion.region-restriction` | If `usageLocation` change crosses a region-restricted SKU boundary |
| Restricted group removal | `provisioning.user.conversion.group-removal` | One per removed group (§6.1) |
| Access review trigger | `provisioning.user.conversion.access-review` | Always — §7 |

All records share the same `correlation` block; the audit trail
joins on `external_id` + the conversion timestamp.

The primary record's `delta` block MUST capture:

```yaml
delta:
  worker_type:
    before: "Contractor"
    after:  "Full-Time Employee"
  orgpath:
    before: "GOV/EXEC/OPM/HRIT/External"
    after:  "GOV/EXEC/OPM/HRIT"
  manager:
    before: "EMP-00789"
    after:  "EMP-00789"
  upn:
    before: "jane.doe.contractor@agency.gov"
    after:  "jane.doe.contractor@agency.gov"   # preserved per §4.1
  license_affinity_attribute:
    before: "CONTRACTOR-A1"
    after:  "FTE-E5"
```

Control evidence: AC-2, AC-6 (mandatory access review), AU-2.

## 9. SCIM Operation

| Sub-event | SCIM method | Path | Notes |
|---|---|---|---|
| Primary attribute flip | PATCH | `/Users/{externalId}` | Single atomic PATCH per conversion; carries `workerType`, OrgPath, license-affinity attribute, and any other deltas |
| Restricted group removal | Graph DELETE batch | `/groups/{groupId}/members/{userId}/$ref` | Out of band relative to SCIM bulkUpload |

Conversion does NOT issue a separate `active`-flip operation —
the user remains `active: true` throughout the conversion. This
distinguishes it from Leaver (which flips to `false`) and Rehire
(which flips to `true`).

## 10. Failure Modes

Delegated to D2.6. Conversion-specific failure surface:

| Failure | `failure_reason` | Routing |
|---|---|---|
| New `workerType` not in D1.6 taxonomy | `worker-type-unknown` | Quarantine; canonical taxonomy update |
| Transition path not in §2.1 matrix without policy override | `conversion-path-unsupported` | Quarantine; tenant-policy resolution |
| Concurrent Conversion + Leaver | `event-collision` | Leaver wins |
| Restricted group removal fails | `group-removal-failed` | Per-group retry; access review surfaces residual exposure |
| License tier transition leaves user license-less | `license-transition-gap` | Operator alert; review tier-bound groups |
| UPN flip attempted without explicit operator approval | `upn-flip-unauthorized` | Conversion blocked; operator must approve |

## 11. Idempotency

1. Replaying the same Conversion event MUST emit a single PATCH and
   a single primary provenance record per sync cycle.
2. The license-transition and region-restriction provenance events
   are idempotent on `(externalId, conversion_timestamp)`.
3. A Conversion against a record whose `workerType` already matches
   the target is a no-op (`outcome: already-converted`).

## 12. References

### 12.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-035](../adr/adr-035-orgpath-codebook-binding.md)
- [ADR-048](../adr/adr-048-orgpath-attribute-storage-decision.md)
- [ADR-049](../adr/adr-049-microsoft-adapter-coverage-expansion.md)

### 12.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_135](../UIAO_135_identity-directory-transformation-inventory.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 2 → D2.5.

### 12.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md) — substrate.
- [Spec2-D2.2 — Mover](./Spec2-D2.2-MoverWorkflowSpecification.md) — explicit precedence boundary.
- [Spec2-D2.3 — Leaver](./Spec2-D2.3-LeaverWorkflowSpecification.md) — contract-end edge case.
- [Spec2-D2.6 — Error Handling & Quarantine](./Spec2-D2.6-ErrorHandlingQuarantineSpecification.md).
- Spec2-D1.6 — worker-type classification taxonomy.

### 12.4 Microsoft documentation (verification pending in v0.2)

- Microsoft Learn — group-based licensing tier-change semantics.
- Microsoft Learn — Access Reviews for role-assignable groups.

### 12.5 Compliance

- NIST SP 800-53 Rev 5: AC-2, AC-6 (privileged-role review), AU-2.
