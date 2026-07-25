---
adr: ADR-125
title: "LocPath Drift Taxonomy Extension — Location-Assignment, Location-Policy, and Location-Boundary Drift Classes"
status: Proposed
date: "2026-06-25"
author: WhalerMike
supersedes: []
superseded_by: null
related:
  - ADR-102   # LocPath location addressing — root authority
  - ADR-108   # Addressing-plane drift gate — routes all DRIFT-LOCPATH-* events
  - ADR-124   # HR duty-station adapter — primary producer of DRIFT-LOCPATH-UNMAPPED and DRIFT-LOCPATH-DIVERGENCE
  - ADR-104   # E911 location services — DRIFT-LOCPATH-E911 event class
  - UIAO_194  # LocPath Codebook
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-125-locpath-drift-taxonomy.html
---

# ADR-125: LocPath Drift Taxonomy Extension

## Context

ADR-102 D6 item 4 reserves a LocPath-specific drift taxonomy:

> Drift taxonomy classes for DRIFT-IDENTITY::location-assignment,
> DRIFT-AUTHZ::location-policy, and DRIFT-BOUNDARY::location-boundary.

The UIAO drift engine (ADR-108) routes addressing-plane drift events as a
distinct category. The OrgPath drift taxonomy (ADR-035 et al.) provides the
structural template: each drift class has an identifier, a severity, a
namespace, a posture label, and a default actuation level. This ADR defines
the six LocPath drift classes, specifies which adapter or process emits each
one, and assigns their default actuation levels within the ADR-108 framework.

All DRIFT-LOCPATH-* classes route to the addressing-plane drift gate and
inherit the `never-autofix` posture established in ADR-108 D3 for phase 1.

## Decision

### D1. Namespace allocation

LocPath drift classes are allocated within the `DRIFT-LOCPATH-*` namespace,
parallel to existing namespaces like `DRIFT-PRIV-*` (PAM, ADR-124),
`DRIFT-IDENTITY-*`, and `DRIFT-AUTHZ-*`. All six classes in this ADR use the
`DRIFT-LOCPATH-` prefix.

Within ADR-108's addressing-plane routing, LocPath events carry the dimension
label `locpath` and flow through the addressing-plane drift gate before being
published to AGD.

### D2. Class definitions

#### DRIFT-LOCPATH-UNMAPPED

| Field | Value |
|---|---|
| Class ID | `DRIFT-LOCPATH-UNMAPPED` |
| Namespace | `DRIFT-LOCPATH-*` |
| Severity | HIGH |
| ADR-108 plane | addressing |
| Default actuation | L2 (advise) |
| Autofix posture | never-autofix |
| Producer | `locpath-hr-duty-station` adapter (ADR-124 D2) |

**Meaning.** The HR duty-station field for this identity carries a code that
has no entry in the duty-station mapping table (ADR-124 D2). The identity has
no governed Primary LocPath. This is a gap in the mapping table, not a gap in
the HR record itself.

**Resolution.** Add a mapping entry for the HR code in
`src/uiao/canon/data/locpath/duty-station-map.yaml` and rerun the adapter.

**Evidence fields.** `subject`, `hr_code`, `hr_source_system`, `detected_at`.

---

#### DRIFT-LOCPATH-NODENOTFOUND

| Field | Value |
|---|---|
| Class ID | `DRIFT-LOCPATH-NODENOTFOUND` |
| Namespace | `DRIFT-LOCPATH-*` |
| Severity | HIGH |
| ADR-108 plane | addressing |
| Default actuation | L2 (advise) |
| Autofix posture | never-autofix |
| Producer | `locpath-hr-duty-station` adapter (ADR-124 D3) |

**Meaning.** The mapping table resolves the HR code to a LocPath node path,
but that node path does not exist in the LocPath node registry
(`src/uiao/canon/data/locpath/location-registry.yaml`). The mapping table has an entry but
it points to a non-existent node — typically a stale mapping after a site is
renamed or decommissioned.

**Resolution.** Either add the missing node to the node registry (if it is a
new or renamed site) or update the mapping table to point to the correct
existing node.

**Evidence fields.** `subject`, `hr_code`, `mapped_locpath`, `detected_at`.

---

#### DRIFT-LOCPATH-INCOMPLETE

| Field | Value |
|---|---|
| Class ID | `DRIFT-LOCPATH-INCOMPLETE` |
| Namespace | `DRIFT-LOCPATH-*` |
| Severity | MEDIUM |
| ADR-108 plane | addressing |
| Default actuation | L2 (advise) |
| Autofix posture | never-autofix |
| Producer | `locpath-hr-duty-station` adapter (ADR-124 D3) |

**Meaning.** The LocPath node resolves in the registry, but the node is missing
one or more required minimum attributes: E911 civic address, `diaApproved`
status, or `telemetryBoundary` classification (per UIAO_194). The assignment
is structurally valid but the node is under-specified for policy enforcement.

**Resolution.** Update the node registry entry to supply the missing required
attribute(s).

**Evidence fields.** `subject`, `locpath`, `missing_attributes[]`, `detected_at`.

---

#### DRIFT-LOCPATH-DIVERGENCE

| Field | Value |
|---|---|
| Class ID | `DRIFT-LOCPATH-DIVERGENCE` |
| Namespace | `DRIFT-LOCPATH-*` |
| Severity | MEDIUM |
| ADR-108 plane | addressing |
| Default actuation | L2 (advise) |
| Autofix posture | never-autofix |
| Producer | `locpath-hr-duty-station` adapter (ADR-124 D5) |

**Meaning.** Dynamic Location Context signals (ADR-102 D2) persistently
indicate a different physical site than the governed Primary LocPath derived
from the HR duty-station record. The assignment may need updating (e.g., the
employee's actual workspace has changed but HR record has not been updated), or
there may be an anomaly in the observational signal.

Emitted only after the stability threshold: 3 or more consecutive collection
cycles showing the same divergence, and the observed site is a different
LocPath node than the assigned node (not just a different floor or room).

**Resolution.** Review whether the HR record needs updating. If the employee
has legitimately moved, update the HR duty-station record (which the adapter
will then reflect). If the observational signal is spurious, suppress for this
subject.

**Evidence fields.** `subject`, `assigned_locpath`, `observed_locpath`,
`observation_source`, `consecutive_cycles`, `detected_at`.

---

#### DRIFT-LOCPATH-E911

| Field | Value |
|---|---|
| Class ID | `DRIFT-LOCPATH-E911` |
| Namespace | `DRIFT-LOCPATH-*` |
| Severity | CRITICAL |
| ADR-108 plane | addressing |
| Default actuation | L3 (gated action) |
| Autofix posture | never-autofix |
| Producer | E911 location services adapter (ADR-104) |

**Meaning.** The LocPath node for this identity's Primary LocPath is either
missing a valid E911 civic address record or the E911 configuration in the
UCaaS platform does not match the LocPath node's civic address. E911 compliance
is a legal obligation under Ray Baum's Act; a mis-routed emergency call is a
life-safety event.

This class is defined in concert with ADR-104 (E911 PROPOSED). ADR-104 D2
specifies the E911 location record format; `DRIFT-LOCPATH-E911` is the drift
event that surfaces when an identity's LocPath-to-E911 mapping is missing or
mis-configured.

At L3, the drift event opens a ServiceNow ticket in the E911 compliance queue
rather than executing any automated remediation. No auto-remediation for E911
misconfigurations; every resolution requires human verification.

**Evidence fields.** `subject`, `locpath`, `e911_error_type`
(`missing-civic-address` | `ucaas-address-mismatch` | `node-missing-e911`),
`ucaas_platform`, `detected_at`.

---

#### DRIFT-LOCPATH-POLICY

| Field | Value |
|---|---|
| Class ID | `DRIFT-LOCPATH-POLICY` |
| Namespace | `DRIFT-LOCPATH-*` |
| Severity | HIGH |
| ADR-108 plane | addressing |
| Default actuation | L2 (advise) |
| Autofix posture | never-autofix |
| Producer | Location-policy authz adapter (future phase; reserved) |

**Meaning.** The identity's governed Primary LocPath does not satisfy a
location-based authorization policy that governs a resource the identity is
currently authorized to access. For example: an authorization policy requires
that access to a classified system only be exercised from a DIA-approved
location (`diaApproved: true` on the LocPath node), but the identity's
Primary LocPath node carries `diaApproved: false`.

This class is reserved for the authorization-policy integration phase of the
LocPath program (ADR-102 D6 item 5: Entra ID exposure for location-derived
dynamic groups and AU scoping). In phase 1 it is defined but not yet emitted.

**Evidence fields.** `subject`, `locpath`, `policy_id`, `policy_requirement`,
`locpath_attribute_actual`, `resource_id`, `detected_at`.

---

### D3. Severity and actuation summary

| Class | Severity | Default actuation | Phase |
|---|---|---|---|
| DRIFT-LOCPATH-UNMAPPED | HIGH | L2 — advise | 1 (active) |
| DRIFT-LOCPATH-NODENOTFOUND | HIGH | L2 — advise | 1 (active) |
| DRIFT-LOCPATH-INCOMPLETE | MEDIUM | L2 — advise | 1 (active) |
| DRIFT-LOCPATH-DIVERGENCE | MEDIUM | L2 — advise | 1 (active) |
| DRIFT-LOCPATH-E911 | CRITICAL | L3 — gated action | per ADR-104 |
| DRIFT-LOCPATH-POLICY | HIGH | L2 — advise | reserved (phase 2) |

All classes may be escalated by deployment-specific override configuration
per ADR-108 D4. No class may be set to L4 (autonomous autofix) for
addressing-plane events without an explicit ADR amendment.

### D4. Drift class registration

All six classes ship as executable canon in
`src/uiao/modernization/locpath/drift.py` (the planned standalone YAML
registry was folded into the module at implementation). Each class
definition carries the fields defined in D2 plus an `introduced_by`
reference to this ADR.

## Consequences

**Positive.** Location-assignment, location-policy, and location-boundary
failures now have named, routable drift classes rather than silently not
appearing in the governance posture. The E911 class (DRIFT-LOCPATH-E911)
connects a life-safety compliance gap directly to the drift engine, ensuring
E911 mis-configurations surface at CRITICAL severity with a L3 ticket response.

**Negative.** The DRIFT-LOCPATH-POLICY class is defined but not yet emitted in
phase 1. Its presence in the taxonomy may be confusing until the authorization-
policy integration phase ships. Documentation must clearly mark it as reserved.

**Neutral.** The six classes extend the existing drift taxonomy without modifying
any existing class. DRIFT-LOCPATH-* occupies a distinct namespace; there are no
collisions with OrgPath, PAM, or KYC drift classes.

## Related

- [ADR-102 — LocPath Location Addressing](./adr-102-locpath-location-addressing.md)
- [ADR-108 — Addressing-Plane Drift Gate](./adr-108-addressing-plane-drift-gate.md)
- [ADR-124 — LocPath HR Duty-Station Adapter](./adr-124-locpath-hr-duty-station-adapter.md)
- [ADR-104 — E911 Location Services](./adr-104-e911-location-services.md)
- [UIAO_194 — LocPath Codebook](../UIAO_194_LocPath_Codebook.md)
