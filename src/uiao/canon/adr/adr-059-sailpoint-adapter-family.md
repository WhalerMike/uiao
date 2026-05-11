---
id: ADR-059
title: "SailPoint NERM Adapter — Boundary-Exception Carve-Out and Slot Allocation"
status: accepted
date: 2026-05-07
accepted: 2026-05-07
deciders:
  - governance-steward
  - identity-engineer
  - security-steward
  - privacy-officer
supersedes: []
related_adrs:
  - ADR-027  # Adapter retirement — symmetric three-stage lifecycle for activation
  - ADR-035  # Per-adapter activation template
  - ADR-049  # Microsoft adapter coverage expansion — multi-slot allocation precedent
  - ADR-052  # PIV / USAccess — recent identity-class adapter precedent
  - ADR-054  # Single-ATO Reciprocity — authorization-level reciprocity (informs Option B)
  - ADR-055  # Customer Identity Canon Block — non-employee CIR scope for NERM
canon_refs:
  - UIAO_003  # Adapter Segmentation Overview — class × mission-class
  - UIAO_129  # Application Identity Model — workforce-identity surface
  - UIAO_139  # Spec3-D1.1 Service Account Discovery Scan — current service-account surface
  - UIAO_141  # Customer Identity Model — non-employee CIR target
  - UIAO_142  # Customer KYC Onboarding & Reciprocity Runbook
mandate_traceability:
  - "OMB M-22-09 — Federal Zero Trust Strategy (machine-identity governance)"
  - "FICAM (Federal Identity, Credential, and Access Management) — service alignment"
  - "OMB M-19-17 — Enabling Mission Delivery through Improved ICAM"
---

# ADR-059: SailPoint NERM Adapter — Boundary-Exception Carve-Out and Slot Allocation

## Status

ACCEPTED — 2026-05-07

## Context

UIAO has substantial canon for Microsoft-native identity governance: the
Entra ID / M365 modernization adapters (ADR-035..040, ADR-049), the
Customer Identity Canon Block (ADR-055, UIAO_141 / UIAO_142), the
Service Account Discovery Scan (UIAO_139), and the Application Identity
Model (UIAO_129). One structural gap is salient enough to warrant its
own carve-out:

**Non-employee identity lifecycle.** UIAO_141 / UIAO_142 declare the
Customer Identity primitive but provide no operational substrate for the
non-employee branch (contractors, vendors, business partners, sponsored
external identities) at scale. The Microsoft ecosystem does not provide
a FedRAMP-Moderate, FICAM-aligned non-employee lifecycle product;
Entra ID Governance covers the workforce branch only.

SailPoint Non-Employee Risk Management (NERM) is the leading
FedRAMP-Moderate-authorized commercial substrate for this gap:

* FedRAMP Moderate authorization 2025-03-04 (add-on to SailPoint
  Identity Security Cloud, parent ATO 2024-06-05, package
  `FR2001938710A`, hosted on AWS GovCloud).
* FICAM-aligned per SailPoint's own attestation; sponsorship,
  proofing, risk-scoring, and lifecycle-state model maps directly to
  the UIAO_141 Customer Identity Record (CIR) bindings.
* API surface: SailPoint Identity Security Cloud V3 REST + SCIM 2.0.

Two adjacent SailPoint surfaces — Identity Security Cloud (ISC) and
Machine Identity Security — would address other UIAO gaps (cross-
platform IGA and cross-source machine-identity governance respectively)
but are deferred from this ADR. They are recorded in §Notes as
deliberate alternatives for a future ADR after NERM proves out the
integration pattern.

### The boundary problem

UIAO's published cloud boundary
([AGENTS.md](../../../../AGENTS.md)): *"Cloud boundary: GCC-Moderate
(Microsoft 365 SaaS only). Amazon Connect Contact Center is the sole
Commercial exception."* SailPoint NERM runs on AWS GovCloud, which is
FedRAMP Moderate but is not the M365 GCC-Moderate substrate. A
narrowly-scoped Commercial-exception carve-out is required.

The schema enum `gcc-boundary` in
`src/uiao/schemas/adapter-registry/adapter-registry.schema.json`
currently accepts two values: `gcc-moderate` and
`commercial-exception-amazon-connect`. The Amazon Connect carve-out
established the canon convention: each Commercial exception is
named after the specific product, not after the underlying cloud.

## Decision

1. **Boundary carve-out (Option A, NERM-only).** A second
   Commercial-exception is added to UIAO's cloud boundary statement,
   scoped to SailPoint NERM only and justified by:

   * NERM's FedRAMP Moderate authorization (2025-03-04).
   * The direct functional fit with UIAO_141 (Customer Identity
     Model) non-employee branch.
   * The smallest possible cloud-boundary-expansion blast radius.

   Two alternative paths — Option B (full SailPoint ISC family with a
   broader boundary expansion) and Option C (IdentityIQ on-prem only)
   — are documented in §Notes as deliberate alternatives. Adoption of
   Option B is left to a future ADR after NERM proves out the
   integration pattern.

2. **Allocate one new conformance adapter slot** in
   `src/uiao/canon/adapter-registry.yaml`:

   | Adapter id | Registry | class | mission-class | Initial status |
   |---|---|---|---|---|
   | `sailpoint-nerm` | conformance | conformance | identity | reserved |

   `sailpoint-nerm` is allocated as conformance-only in this ADR.
   A `sailpoint-nerm-actions` modernization slot may be allocated in a
   follow-on ADR if non-employee-lifecycle *writes* prove operationally
   distinct from general-population writes; the conformance side is the
   right starting point because UIAO_141 entitlement-model evidence is
   read-shaped, not write-shaped.

3. **Extend the `gcc-boundary` schema enum.** Add
   `commercial-exception-sailpoint-nerm` to the `gcc-boundary` enum in
   `src/uiao/schemas/adapter-registry/adapter-registry.schema.json`,
   matching the named-product-exception convention established by
   `commercial-exception-amazon-connect`. The enum description is
   updated to record that Commercial exceptions are added in lockstep
   with their authorizing ADR, never as a generic cloud descriptor.

4. **Reciprocal-consumption entitlements.** Because NERM holds
   non-employee Customer Identity Records per UIAO_141, every NERM-
   served attribute disclosure must be tied to a reciprocal-consumption
   entitlement in
   `src/uiao/canon/reciprocal-consumption-registry.yaml` per the
   ADR-055 doctrine. The activation ADR for `sailpoint-nerm` documents
   the sponsoring-agency entitlement model and the audit-event format.

5. **SSOT-conflict resolution.** SailPoint ships native Entra ID and
   Active Directory connectors that overlap with the existing
   `entra-id`, `entra-id-governance`, and `active-directory`
   modernization adapters. Per the SSOT invariant
   ([AGENTS.md](../../../../AGENTS.md) §Operating principles 1), UIAO
   holds SSOT for all Entra/AD writes. The activation ADR for
   `sailpoint-nerm` must declare:
   * which sources NERM reads (UIAO-mediated or non-overlapping);
   * the failure mode if NERM attempts a write to an Entra/AD object
     under UIAO SSOT (must fail closed — NERM is allocated as
     `ssot-mutation: never` and conformance-only in this ADR, so the
     concern is bounded but the activation contract must record it).

6. **No registry edits at activation level.** Per ADR-049 precedent,
   this ADR is registry-shaped, not implementation-shaped.
   `sailpoint-nerm` lands as `status: reserved`; activation requires a
   per-adapter ADR modeled on ADR-035.

7. **AGENTS.md amendment.** A separate small PR amends the cloud-
   boundary statement in `AGENTS.md` to list NERM as the second
   Commercial exception. The amendment is editorial in this ADR's
   scope; the substantive decision is encoded in the schema enum and
   the registry slot.

## Consequences

### Positive

* Provides a FedRAMP-Moderate, FICAM-aligned substrate for the
  non-employee branch of UIAO_141 — operational depth the canon
  block currently lacks.
* Preserves the conservative cloud-boundary posture: only one new
  Commercial-exception carve-out is made; the broader ISC family is
  documented as future work but not committed to.
* The `mission-class: identity` value on the conformance side is now
  exercised by three blocks (`piv-usaccess`, the UIAO_141 / UIAO_142
  KYC block, and `sailpoint-nerm`); the doctrinal axis is consistently
  used.
* Establishes the schema convention for future Commercial exceptions:
  one named enum value per carve-out, added in lockstep with its ADR.

### Negative / costs

* The cloud boundary now has two Commercial exceptions instead of
  one. Future vendor requests will cite this precedent — the next
  carve-out ADR has to argue against the slippery-slope explicitly.
  The named-enum convention (Decision 3) makes the precedent
  inspectable: each new carve-out adds exactly one auditable schema
  value.
* Schema and AGENTS.md edits create a coordinated multi-file change
  set. Mitigated by the small total surface (one ADR file, one
  schema enum value, one registry entry, one AGENTS.md sentence,
  one index.md row).

### Risks

* If SailPoint's product reorganization merges NERM into core ISC
  (the add-on architecture is recent and could continue to evolve),
  the `sailpoint-nerm` slot may need to migrate to a broader ISC slot
  via the ADR-027 retirement path. Acceptable risk; ADR-027 exists
  precisely for this case.
* If FedRAMP redefines AWS GovCloud authorization scope under the
  20x evolution (per ADR-043 / UIAO_132), the boundary carve-out
  justification may need to be re-anchored.

## Follow-on work

1. PR #1 (this ADR) — land `adr-059-sailpoint-adapter-family.md` plus
   the schema enum extension, the `sailpoint-nerm` registry entry, and
   the `adr/index.md` row.
2. PR #2 — amend `AGENTS.md` cloud-boundary statement to list NERM as
   second Commercial exception.
3. Per-adapter activation ADR (modeled on ADR-035) when
   `sailpoint-nerm` promotes to `active`. Activation requires:
   * A documented sponsoring-agency entitlement model.
   * A reciprocal-consumption-registry entry per ADR-055.
   * The SSOT-conflict resolution declaration per Decision 5.
   * The audit-event format specification.
4. Future ADR — Option B (full ISC family) carve-out if NERM
   integration proves the pattern. Drafted scope is recorded in
   `inbox/drafts/sailpoint-adapter-plan.md` (4 additional slots:
   `sailpoint-isc-governance`, `sailpoint-machine-identity`,
   `sailpoint-isc-actions`, `sailpoint-machine-identity-actions`).
5. Update `src/uiao/canon/adr/index.md` to list ADR-059 under the
   Adapter Model theme. (Note: index has not been updated since
   ADR-031; full backfill is out of this ADR's scope.)

## Notes

### Alternatives considered (recorded for traceability)

* **Option B — Full SailPoint Identity Security Cloud family.**
  Allocate four additional reserved slots (`sailpoint-isc-governance`,
  `sailpoint-machine-identity`, `sailpoint-isc-actions`,
  `sailpoint-machine-identity-actions`) to cover cross-platform IGA and
  cross-source machine-identity governance. Strategically clean
  (matches UIAO_140 Single-ATO Reciprocity doctrine and would close
  the cross-source service-account governance gap UIAO_139 leaves
  open) but a much larger blast-radius change than Option A. Deferred
  to a future ADR after NERM proves out the integration pattern.
  Detailed slot drafts retained in
  `inbox/drafts/sailpoint-adapter-plan.md`.
* **Option C — IdentityIQ on-prem only.** Avoids the cloud-boundary
  question entirely; SailPoint IdentityIQ runs inside the customer's
  existing FedRAMP boundary. Loses the FICAM-aligned SaaS narrative,
  orphans NERM and Data Access Security from the substrate, and is
  inconsistent with UIAO's general modernization-toward-SaaS direction.
  Rejected.

### Out of scope

* SailPoint Data Access Security (FedRAMP Moderate, 2025-07-08).
  This is a data-plane substrate, not an identity-plane substrate;
  it would require its own ADR with data-plane scope justification
  and is deferred.
* `sailpoint-nerm-actions` modernization slot — deferred until the
  conformance-side proves the integration pattern.
* Backfill of `adr/index.md` for ADRs 032–057 (the index has not been
  updated since ADR-031). This ADR adds only its own row; broader
  backfill is a separate cleanup.

### Pattern model

This ADR is registry-shaped, not implementation-shaped, modeled on
ADR-049. No Python code, runbook, or new schema document is created
here — only the named-exception enum value extension. Activation is
left to a per-adapter follow-on ADR because adapter activation is the
governance boundary that requires Board review per ADR-027 (adapter
retirement) and the implicit symmetric rule for adapter activation in
the three-stage lifecycle (canon → docs scaffold → impl code).
