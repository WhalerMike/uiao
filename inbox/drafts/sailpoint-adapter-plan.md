# Implementation Plan — SailPoint IDM + System Account Management Adapter Family

> **Branch:** `claude/brave-hermann-1c1dff`
> **Date:** 2026-05-07
> **Status:** draft (partially landed — Option A landed in ADR-058 + `sailpoint-nerm` slot; remaining 4 ISC/Machine-Identity slots stay in this draft as future work pending Option-B decision)
> **Target ADR:** `src/uiao/canon/adr/adr-058-sailpoint-adapter-family.md` (new; ADR-057 is `thousandeyes-networks-pillar-scope`)
> **Target canon entries (Option A, this PR-set):**
> - `src/uiao/canon/adapter-registry.yaml` — 1 new conformance slot (`sailpoint-nerm`)
> - `src/uiao/schemas/adapter-registry/adapter-registry.schema.json` — `gcc-boundary` enum gains `commercial-exception-sailpoint-nerm` (matching Amazon Connect's named-product-exception pattern)
> - `src/uiao/canon/adr/index.md` — list ADR-058
> **Future PRs (Option B, deferred):** 2 conformance slots (`sailpoint-isc-governance`, `sailpoint-machine-identity`) + 2 modernization slots (`sailpoint-isc-actions`, `sailpoint-machine-identity-actions`) — drafted in §6 below; not landed.
> **Schema-pattern correction (2026-05-07):** initial draft proposed `gcc-boundary: fedramp-moderate-aws-govcloud`; on schema inspection the canon convention is *named-product-exception* (`commercial-exception-amazon-connect`). Switched to `commercial-exception-sailpoint-nerm` for the NERM slot. Each future Commercial-exception will add one schema enum value lockstep with its ADR.
> **Pattern model:** ADR-049 (multi-slot Microsoft adapter coverage expansion) — registry-shaped, not implementation-shaped; per-adapter activation ADRs follow when slots promote to `active`.

## 1. Goal

Establish the SailPoint product family as a first-class adapter surface in UIAO, paired across the dual-axis taxonomy. The decision is gated on a **boundary-expansion question** that does not yet have an ADR-level answer: SailPoint Identity Security Cloud and its FedRAMP-Moderate add-ons (NERM, Data Access Security, Machine Identity Security) run on AWS GovCloud, outside UIAO's stated GCC-Moderate / M365-only cloud boundary. The Amazon Connect carve-out (current sole exception) is the precedent.

## 2. Context recap

### What SailPoint sells (as of 2026-05)

| Product | Scope | FedRAMP-Moderate status |
|---|---|---|
| Identity Security Cloud (ISC) | SaaS IGA — lifecycle, access requests, certifications, role mining | ATO 2024-06-05, package `FR2001938710A` (Rev5), AWS GovCloud |
| Machine Identity Security (ISC add-on) | Discovery, ownership, lifecycle of service accounts / bots / RPAs / AI agents | Inside ISC ATO |
| Non-Employee Risk Management (NERM, ISC add-on) | Third-party / contractor / vendor identity lifecycle + risk | Authorized 2025-03-04 |
| Data Access Security (ISC add-on) | Unstructured-data access governance | Authorized 2025-07-08 |
| IdentityIQ (IIQ) | On-prem IGA, customer-deployed | Inherits customer boundary |

API surfaces: ISC V3 REST + SCIM 2.0; IIQ SCIM 2.0 REST. Both ship Microsoft Entra ID and Active Directory connectors out of the box (Graph-based for Entra).

### Existing canon SailPoint would touch

- **UIAO_139 ([Spec3-D1.1 Service Account Discovery Scan](../../src/uiao/canon/specs/Spec3-D1.1-Get-ServiceAccountScan.md))** — current AD service-account scan; SailPoint Machine Identity Security generalizes the discovery surface to non-AD sources and adds *ownership*.
- **UIAO_141 / UIAO_142 ([Customer Identity Model](../../src/uiao/canon/specs/customer-identity-model.md) + KYC runbook)** — NERM is the natural lifecycle substrate for the non-employee branch of CIRs.
- **UIAO_129 (Application Identity Model)** — SailPoint role/entitlement model is one possible governance overlay for app-identity bindings.
- **ADR-004 (workload identity federation default)** — UIAO_139 *recommends* modernization targets; SailPoint Machine Identity would *execute* the migration choreography.
- **ADR-049 (Microsoft adapter coverage expansion)** — direct template for this ADR (multi-slot allocation, dual-registry split, deferred per-adapter activation ADRs).
- **ADR-052 / ADR-055 / ADR-056** — most-recent identity-class adapter ADRs; precedent for `mission-class: identity` in the conformance registry.

No current canon, docs, or inbox file mentions SailPoint — this is greenfield.

## 3. The boundary-expansion question (gates everything else)

UIAO's [AGENTS.md](../../AGENTS.md): *"Cloud boundary: GCC-Moderate (Microsoft 365 SaaS only). Amazon Connect Contact Center is the sole Commercial exception."*

SailPoint ISC + add-ons run on AWS GovCloud — FedRAMP-Moderate, but a different cloud than the M365 GCC-Moderate substrate. Three viable paths, in order of architectural conservatism:

| Option | Carve-out shape | Pro | Con |
|---|---|---|---|
| **A. NERM-only** (recommended first move) | Narrow Commercial-exception ADR, scoped to non-employee/third-party identity lifecycle | Smallest surface; pairs cleanly with UIAO_141/142; FedRAMP Moderate authorized 2025-03-04 | Leaves Machine Identity, Data Access Security, full ISC out of registry |
| **B. Full ISC family** | Boundary-expansion ADR redefining substrate as "FedRAMP Moderate cloud(s)" rather than "M365 only" | Strategic — opens the entire FedRAMP Moderate ecosystem; matches Single-ATO Reciprocity (UIAO_140) doctrine | Larger blast radius; needs more justification; affects every future cloud-vendor decision |
| **C. IdentityIQ on-prem only** | No boundary change; SailPoint runs inside customer's existing FedRAMP boundary | Cloud-boundary-clean; avoids Commercial-exception precedent | Loses the FICAM-aligned SaaS modernization narrative; orphans NERM and Data Access Security from the substrate |

**Recommendation: Option A first, with Option B left as a deliberate follow-on if NERM proves out the integration pattern.** This mirrors how Amazon Connect entered as a single-product carve-out before any broader AWS posture was contemplated.

The ADR below presents all three options; the Decision section selects A.

## 4. Recommended adapter slot allocation (5 slots, all `status: reserved`)

Per UIAO_003 §4.2–§4.7 and ADR-049 precedent. Read-only signal sources go to `adapter-registry.yaml` (conformance); change-making surfaces go to `modernization-registry.yaml` with `mission-class: integration`.

### Conformance side (read-only, populates evidence graph)

| id | mission-class | Observes | Initial status |
|---|---|---|---|
| `sailpoint-isc-governance` | identity | Access certifications, entitlement-management packages, lifecycle-workflow runs, separation-of-duties findings | reserved |
| `sailpoint-machine-identity` | identity | Discovered service / bot / RPA / AI-agent inventory, ownership graph, lifecycle state | reserved |
| `sailpoint-nerm` | identity | Non-employee CIRs (per UIAO_141), proofing events, sponsorship state, risk score | reserved |

### Modernization side (change-making)

| id | mission-class | Mutates | Initial status |
|---|---|---|---|
| `sailpoint-isc-actions` | integration | Identity lifecycle joiner/mover/leaver, role grants/revokes, certification campaigns | reserved |
| `sailpoint-machine-identity-actions` | integration | Service-account ownership assignment, decommission, rotation orchestration | reserved |

NERM is split conformance-only in this draft because non-employee *lifecycle* writes overlap heavily with `sailpoint-isc-actions` — a separate `sailpoint-nerm-actions` slot can be allocated later if the boundary between general-population and non-employee write surfaces proves operationally distinct.

**Mission-class precedent.** Three conformance entries with `mission-class: identity` would be the second-largest such block (after the UIAO_141/142 KYC block). Doctrinally permitted; just deliberate.

**Conflict surface.** SailPoint's own Entra/AD connectors overlap with `entra-id`, `entra-id-governance`, `active-directory`. Per the ADR §Decision 5 below, UIAO holds SSOT for all Entra/AD writes; SailPoint reads from UIAO or operates against non-overlapping sources only.

## 5. Draft ADR-058

```markdown
---
id: ADR-058
title: "SailPoint Adapter Family — Boundary-Exception Carve-Out and Slot Allocation"
status: draft
date: 2026-05-07
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

# ADR-058: SailPoint Adapter Family — Boundary-Exception Carve-Out and Slot Allocation

## Status

Draft.

## Context

UIAO has substantial canon for Microsoft-native identity governance: the
Entra ID / M365 modernization adapters (ADR-035..040, ADR-049), the
Customer Identity Canon Block (ADR-055, UIAO_141/142), the Service
Account Discovery Scan (UIAO_139), and the Application Identity Model
(UIAO_129). Three structural gaps remain:

1. **Cross-source service / machine identity governance.** UIAO_139
   covers Active Directory service accounts only. Non-AD sources
   (cloud IAM, SaaS apps, RPA platforms, AI agents) have no canonical
   discovery or ownership surface.
2. **Non-employee identity lifecycle.** UIAO_141/142 declare the
   Customer Identity primitive but provide no operational substrate
   for the non-employee branch (contractors, vendors, business
   partners, sponsored external identities) at scale.
3. **Cross-platform IGA.** UIAO's Entra ID Governance slot
   (`entra-id-governance`, reserved per ADR-049) covers Microsoft-
   native governance only. Federal agencies routinely run an IGA
   platform that spans Microsoft + non-Microsoft sources; UIAO has
   no registry surface for that platform.

SailPoint is the leading FedRAMP-authorized commercial substrate for
all three gaps:

* **Identity Security Cloud (ISC)** — FedRAMP Moderate (Rev5), ATO
  2024-06-05, package `FR2001938710A`, hosted on AWS GovCloud.
* **Non-Employee Risk Management (NERM)** — FedRAMP Moderate add-on
  to ISC, authorized 2025-03-04. FICAM-aligned per SailPoint's own
  attestation.
* **Machine Identity Security** — ISC add-on for service-account /
  bot / RPA / AI-agent governance.
* **Data Access Security** — ISC add-on, FedRAMP Moderate authorized
  2025-07-08. (Out of scope for this ADR; tracked for a future
  data-plane carve-out.)
* **IdentityIQ (IIQ)** — on-prem variant; inherits customer boundary.

API surfaces: ISC V3 REST + SCIM 2.0; IIQ SCIM 2.0 REST.

### The boundary problem

UIAO's published cloud boundary (AGENTS.md) is *"GCC-Moderate
(Microsoft 365 SaaS only). Amazon Connect Contact Center is the sole
Commercial exception."* SailPoint ISC + add-ons run on AWS GovCloud,
which is FedRAMP Moderate but is not the M365 GCC-Moderate substrate.
Three options exist and are listed below; option A is selected.

## Decision

1. **Boundary carve-out — Option A (NERM-only first).** The cloud
   boundary statement in AGENTS.md is amended to add SailPoint NERM
   as a second narrow Commercial-exception, scoped to non-employee
   identity lifecycle and risk management. This carve-out is
   justified by:

   * NERM's FedRAMP Moderate authorization (2025-03-04).
   * The direct functional fit with UIAO_141 (Customer Identity
     Model) non-employee branch.
   * The smallest possible cloud-boundary-expansion blast radius.

   Options B (full ISC family with a redefined "FedRAMP Moderate
   cloud(s)" boundary) and C (IdentityIQ on-prem only) are documented
   as deliberate alternatives in the §Notes section. Adoption of
   Option B is left to a future ADR after NERM proves out the
   integration pattern.

2. **Allocate five new adapter entries** across the conformance and
   modernization registries per the table below. Per-axis assignment
   follows UIAO_003 §4.2–§4.7. Entries 2–5 (the non-NERM slots) are
   allocated as `status: reserved` *pending* the Option-B decision —
   they are catalog placeholders that the substrate walker can see
   without committing to activation.

   | Adapter id | Registry | class | mission-class | Initial status | Boundary path |
   |---|---|---|---|---|---|
   | `sailpoint-nerm` | conformance | conformance | identity | reserved | Option A (carve-out approved) |
   | `sailpoint-isc-governance` | conformance | conformance | identity | reserved | Option B pending |
   | `sailpoint-machine-identity` | conformance | conformance | identity | reserved | Option B pending |
   | `sailpoint-isc-actions` | modernization | modernization | integration | reserved | Option B pending |
   | `sailpoint-machine-identity-actions` | modernization | modernization | integration | reserved | Option B pending |

   `sailpoint-nerm` is allocated as conformance-only in this ADR.
   A `sailpoint-nerm-actions` modernization slot can be allocated in a
   follow-on ADR if non-employee lifecycle *writes* prove operationally
   distinct from general-population writes.

3. **No registry edits in this ADR.** Each new adapter ships in a
   follow-on PR that:
   * appends the entry to the appropriate registry YAML;
   * passes `schema-validation.yml` against
     `schemas/adapter-registry/adapter-registry.schema.json`;
   * lands while `status: reserved` until activation, at which point a
     per-adapter ADR (modeled on ADR-035) promotes it to `active`.

4. **No new registry schemas required.** All five entries are expected
   to validate against the existing `adapter-registry.schema.json`
   (schema version `1.0.0`). The `mission-class: identity` value on
   conformance entries is already exercised by `piv-usaccess` and the
   UIAO_141/142 KYC block; no schema gap is anticipated.

5. **SSOT-conflict resolution.** SailPoint ships native Entra ID and
   Active Directory connectors that overlap with the existing
   `entra-id`, `entra-id-governance`, and `active-directory`
   modernization adapters. Per the SSOT invariant
   (AGENTS.md §Operating principles 1), UIAO holds SSOT for all
   Entra/AD writes. The activation ADR for any SailPoint
   modernization slot must declare:
   * which sources SailPoint reads (UIAO-mediated or native);
   * which sources SailPoint writes (must be non-overlapping with
     existing UIAO modernization adapters, or explicitly UIAO-
     mediated);
   * the failure mode if SailPoint attempts an overlapping write
     (must fail closed).

6. **Reciprocal-consumption entitlements (NERM-specific).** Because
   NERM holds non-employee Customer Identity Records per UIAO_141,
   every NERM-served attribute disclosure must be tied to a
   reciprocal-consumption entitlement in
   `canon/reciprocal-consumption-registry.yaml` per the ADR-055
   doctrine. The activation ADR for `sailpoint-nerm` documents the
   sponsoring-agency entitlement model and the audit-event format.

## Consequences

### Positive

* Closes the cross-source service-account governance gap (current
  UIAO_139 is AD-only).
* Provides a FedRAMP-Moderate, FICAM-aligned substrate for the
  non-employee branch of UIAO_141 — operational depth the canon
  block currently lacks.
* Preserves the conservative cloud-boundary posture: only one new
  Commercial-exception carve-out is made (NERM); the broader ISC
  family is reserved but not activated.
* Three conformance entries with `mission-class: identity` exercise
  a doctrinally-permitted slot the registry has under-used.

### Negative / costs

* The cloud boundary now has two Commercial exceptions instead of
  one. Future vendor requests will cite this precedent — the next
  carve-out ADR has to argue against the slippery-slope explicitly.
* SailPoint's native Entra/AD overlap requires per-activation SSOT
  conflict resolution (Decision 5). This is more review work per
  activation than for non-overlapping vendors.
* Five reserved entries enlarge the registry surface that schema
  validation, the substrate walker, and reviewers must scan.
  Mitigated by `reserved` status (no runtime, no CI workflow, no
  trust anchor obligations until promoted).

### Risks

* If SailPoint's product reorganization merges NERM into core ISC
  (the add-on architecture is a 2024 reshuffle and could continue),
  the reserved entries may need consolidation per ADR-027.
* If FedRAMP redefines AWS GovCloud authorization scope (unlikely
  but possible under FedRAMP 20x evolution per ADR-043 / UIAO_132),
  the boundary carve-out justification may need to be re-anchored.

## Follow-on work

1. PR #1 — append `sailpoint-nerm` to `adapter-registry.yaml`
   (`status: reserved`). NERM-only Option-A carve-out.
2. PR #2 — append `sailpoint-isc-governance`,
   `sailpoint-machine-identity` to `adapter-registry.yaml` and
   `sailpoint-isc-actions`, `sailpoint-machine-identity-actions` to
   `modernization-registry.yaml` (all `status: reserved`).
3. PR #3 — amend `AGENTS.md` cloud-boundary statement to list NERM
   as second Commercial-exception.
4. Per-adapter activation ADR (modeled on ADR-035) when any reserved
   entry promotes to `active`. Activation order is an
   implementation-track decision and is not fixed by this ADR.
5. Update `src/uiao/canon/adr/index.md` to list ADR-058 under
   the Adapter Model theme.

## Notes

### Alternatives considered (recorded for traceability)

* **Option B — Full ISC family with substrate redefinition.**
  Redefine the cloud boundary as "FedRAMP Moderate cloud(s)" rather
  than "M365 only." Strategically clean (matches UIAO_140 Single-ATO
  Reciprocity doctrine) but is a much larger blast-radius change
  than this ADR is willing to commit to without an integration
  proof-out via NERM.
* **Option C — IdentityIQ on-prem only.** Avoids the cloud-boundary
  question entirely. Loses the FICAM-aligned SaaS narrative,
  orphans NERM and Data Access Security from the substrate, and is
  inconsistent with UIAO's general modernization-toward-SaaS
  direction.

### Out of scope

* SailPoint Data Access Security (FedRAMP Moderate, 2025-07-08).
  This is a data-plane substrate, not an identity-plane substrate;
  it would require its own ADR with data-plane scope justification
  and is deferred.
* `sailpoint-nerm-actions` modernization slot — deferred until the
  conformance-side proves the integration pattern.

### Pattern model

This ADR is registry-shaped, not implementation-shaped, modeled on
ADR-049. No Python code, schema, or runbook is created here.
Activation is left to per-adapter follow-on ADRs because adapter
activation is the governance boundary that requires Board review
per ADR-027 (adapter retirement) and the implicit symmetric rule
for adapter activation in the three-stage lifecycle (canon → docs
scaffold → impl code).
```

## 6. Draft registry stubs

All five entries are `status: reserved`. Append-only; ordering follows the existing registry convention (new entries at the bottom of each file).

### 6.1 `adapter-registry.yaml` — three new conformance entries

```yaml
  # ──────────────────────────────────────────────────────────────────
  # Reserved adapter slots allocated by ADR-058 (2026-05-07)
  # SailPoint adapter family — boundary-exception carve-out (Option A: NERM only)
  # ──────────────────────────────────────────────────────────────────

  - id: sailpoint-nerm
    name: SailPoint Non-Employee Risk Management (Conformance)
    class: conformance
    mission-class: identity
    status: reserved
    phase: phase-planning
    vendor: SailPoint
    license: Commercial
    runtime: python-3.12
    runner-class: github-hosted
    tenancy: per-customer
    scope:
      - non-employee-identity-inventory
      - sponsorship-state
      - proofing-events
      - non-employee-risk-score
      - lifecycle-state-transitions
    outputs:
      - nerm-identity-inventory.json
      - nerm-disclosure-audit.json
    triggers:
      - workflow_dispatch
      - schedule
    evidence-class: interval
    retention-years: 7
    controls:
      - IA-2
      - IA-4
      - IA-5(6)
      - AC-2
      - AC-2(3)
      - AU-2
      - AU-12
      - CA-9
    automation-domain:
      - information-management
    gcc-boundary: fedramp-moderate-aws-govcloud
    ssot-mutation: never
    certificate-anchored: true
    object-identity-only: true
    ztmm-pillars:
      - identity
    references:
      - UIAO-CANON-003
      - ADR-058
      - UIAO_141
      - UIAO_142
      - https://www.sailpoint.com/products/identity-security-cloud/atlas/add-ons/non-employee-risk-management
      - https://www.sailpoint.com/press-releases/sailpoint-non-employee-risk-management-fedramp-authorized
    notes: >-
      SailPoint NERM is the FICAM-aligned, FedRAMP-Moderate-authorized
      (2025-03-04) substrate for the non-employee branch of UIAO_141
      Customer Identity Records (contractors, vendors, business
      partners, sponsored externals). Allocated under the Option-A
      Commercial-exception carve-out per ADR-058 §Decision 1; the
      `gcc-boundary: fedramp-moderate-aws-govcloud` value is a new
      enum value that ADR-058 introduces and that
      `adapter-registry.schema.json` will need to accept (schema
      change tracked as a follow-on PR if validation fails). Every
      NERM-served disclosure must be tied to a reciprocal-consumption
      entitlement in canon/reciprocal-consumption-registry.yaml per
      ADR-055 doctrine. Activation requires a per-adapter ADR modeled
      on ADR-035.

  - id: sailpoint-isc-governance
    name: SailPoint Identity Security Cloud — Governance (Conformance, Reserved)
    class: conformance
    mission-class: identity
    status: reserved
    phase: phase-planning
    vendor: SailPoint
    license: Commercial
    runtime: python-3.12
    runner-class: github-hosted
    tenancy: per-customer
    scope:
      - access-certification-campaigns
      - entitlement-management-packages
      - lifecycle-workflow-runs
      - separation-of-duties-findings
      - role-mining-results
    outputs:
      - isc-governance-findings.json
      - isc-certification-audit.json
    triggers:
      - workflow_dispatch
      - schedule
    evidence-class: interval
    retention-years: 3
    controls:
      - AC-2
      - AC-2(3)
      - AC-5
      - AC-6
      - AC-6(2)
      - AU-2
      - IA-4
      - CA-7
    automation-domain:
      - configuration-management
    gcc-boundary: fedramp-moderate-aws-govcloud
    ssot-mutation: never
    certificate-anchored: true
    object-identity-only: true
    ztmm-pillars:
      - identity
    references:
      - UIAO-CANON-003
      - ADR-058
      - UIAO_129
      - https://developer.sailpoint.com/docs/api/v3/
    notes: >-
      Reserved pending Option-B boundary-expansion decision per
      ADR-058 §Notes. Read-only governance-plane observer for ISC:
      certification campaigns, entitlement-management packages,
      lifecycle workflows, separation-of-duties policies. Sibling
      pair to `sailpoint-isc-actions` (modernization-registry).
      Overlaps with `entra-id-governance` on the Entra surface — per
      ADR-058 §Decision 5, UIAO holds SSOT for Entra writes; SailPoint
      reads via UIAO-mediated channels or non-Entra sources only.

  - id: sailpoint-machine-identity
    name: SailPoint Machine Identity Security (Conformance, Reserved)
    class: conformance
    mission-class: identity
    status: reserved
    phase: phase-planning
    vendor: SailPoint
    license: Commercial
    runtime: python-3.12
    runner-class: github-hosted
    tenancy: per-customer
    scope:
      - service-account-inventory
      - bot-rpa-inventory
      - ai-agent-inventory
      - non-human-identity-ownership
      - machine-identity-lifecycle-state
    outputs:
      - machine-identity-inventory.json
      - machine-identity-ownership-graph.json
    triggers:
      - workflow_dispatch
      - schedule
    evidence-class: interval
    retention-years: 3
    controls:
      - IA-2
      - IA-4
      - IA-5
      - IA-5(6)
      - AC-2
      - AC-6
    automation-domain:
      - configuration-management
      - asset-management
    gcc-boundary: fedramp-moderate-aws-govcloud
    ssot-mutation: never
    certificate-anchored: true
    object-identity-only: true
    ztmm-pillars:
      - identity
    references:
      - UIAO-CANON-003
      - ADR-058
      - UIAO_139
      - ADR-004
      - https://www.sailpoint.com/products/identity-security-cloud/atlas/add-ons/machine-identity-security
    notes: >-
      Reserved pending Option-B boundary-expansion decision per
      ADR-058 §Notes. Cross-source machine / service / bot / RPA /
      AI-agent inventory and ownership observer. Generalizes the
      AD-only surface of UIAO_139 (Spec3-D1.1 Service Account
      Discovery Scan) to cloud IAM, SaaS apps, and RPA platforms;
      adds ownership-graph data UIAO_139 does not produce. Sibling
      pair to `sailpoint-machine-identity-actions` (modernization-
      registry). Activation requires a per-adapter ADR modeled on
      ADR-035 plus the Option-B carve-out decision.
```

### 6.2 `modernization-registry.yaml` — two new modernization entries

```yaml
  # ──────────────────────────────────────────────────────────────────
  # Reserved adapter slots allocated by ADR-058 (2026-05-07)
  # SailPoint modernization side — Option-B pending
  # ──────────────────────────────────────────────────────────────────

  - id: sailpoint-isc-actions
    name: SailPoint Identity Security Cloud — Actions (Modernization, Reserved)
    class: modernization
    mission-class: integration
    mission-class-notes: >-
      Modernization adapter — change-making writes against ISC for
      identity lifecycle joiner/mover/leaver, role grants/revokes,
      and certification-campaign launch. Sibling of
      `sailpoint-isc-governance` (conformance side). Classified per
      UIAO_003 §4.7 `integration`.
    status: reserved
    phase: phase-planning
    vendor: SailPoint
    license: Commercial
    tenancy: per-customer
    scope:
      - identity-lifecycle-joiner
      - identity-lifecycle-mover
      - identity-lifecycle-leaver
      - role-grant-revoke
      - certification-campaign-launch
    outputs:
      - isc-action-manifest.json
      - isc-action-audit.json
    triggers:
      - workflow_dispatch
      - repository_dispatch
    evidence-class: baseline
    retention-years: 3
    controls:
      - AC-2
      - AC-2(3)
      - AC-5
      - AC-6
      - IA-4
      - AU-2
    automation-domain:
      - configuration-management
    gcc-boundary: fedramp-moderate-aws-govcloud
    ssot-mutation: never
    certificate-anchored: true
    object-identity-only: true
    references:
      - UIAO-CANON-003
      - ADR-058
      - UIAO_129
    notes: >-
      Reserved pending Option-B boundary-expansion decision per
      ADR-058 §Notes. SSOT-conflict resolution per ADR-058 §Decision
      5 is required at activation: SailPoint write paths that overlap
      with `entra-id`, `entra-id-governance`, or `active-directory`
      must either be UIAO-mediated or fail closed. Activation
      requires a per-adapter ADR modeled on ADR-035.

  - id: sailpoint-machine-identity-actions
    name: SailPoint Machine Identity Security — Actions (Modernization, Reserved)
    class: modernization
    mission-class: integration
    mission-class-notes: >-
      Modernization adapter — change-making writes against the
      Machine Identity Security surface for ownership assignment,
      service-account decommission, and rotation orchestration.
      Sibling of `sailpoint-machine-identity` (conformance side).
      Classified per UIAO_003 §4.7 `integration`.
    status: reserved
    phase: phase-planning
    vendor: SailPoint
    license: Commercial
    tenancy: per-customer
    scope:
      - non-human-identity-ownership-assignment
      - service-account-decommission
      - credential-rotation-orchestration
    outputs:
      - machine-identity-action-manifest.json
      - machine-identity-action-audit.json
    triggers:
      - workflow_dispatch
      - repository_dispatch
    evidence-class: baseline
    retention-years: 3
    controls:
      - IA-2
      - IA-4
      - IA-5
      - IA-5(6)
      - AC-2
      - AC-6
      - AU-2
    automation-domain:
      - configuration-management
    gcc-boundary: fedramp-moderate-aws-govcloud
    ssot-mutation: never
    certificate-anchored: true
    object-identity-only: true
    references:
      - UIAO-CANON-003
      - ADR-058
      - UIAO_139
      - ADR-004
    notes: >-
      Reserved pending Option-B boundary-expansion decision per
      ADR-058 §Notes. Operational counterpart to UIAO_139's
      *recommended modernization targets* — UIAO_139 produces the
      decision (Managed Identity / Workload Identity Federation /
      gMSA / App Registration); this adapter executes the migration
      choreography under SailPoint orchestration. Activation requires
      a per-adapter ADR modeled on ADR-035 plus the Option-B carve-
      out decision.
```

## 7. Schema-validation note

The five entries above introduce one new value in the `gcc-boundary` enum:
`fedramp-moderate-aws-govcloud`. The existing schema constrains
`gcc-boundary` to `gcc-moderate` based on every current entry. Two
options:

1. **Extend the schema enum** — small PR amending
   `schemas/adapter-registry/adapter-registry.schema.json` to accept
   `fedramp-moderate-aws-govcloud` alongside `gcc-moderate`. Cleanest;
   one schema-validation cycle catches future Commercial-exception
   carve-outs.
2. **Keep `gcc-boundary: gcc-moderate`** on all five entries and rely
   on the `notes:` block to document the actual cloud. Avoids a schema
   change but loses substrate-walker visibility into the carve-out.

**Recommendation: Option 1.** Schema is the right place for boundary
classification; doing it in `notes` defeats the schema-first governance
invariant (AGENTS.md §Operating principles 4).

## 8. Follow-on PR sequencing

Three small, independently reviewable PRs, in order:

| PR | Change | Reviewer scope |
|---|---|---|
| 1 | Land ADR-058 (`src/uiao/canon/adr/adr-058-sailpoint-adapter-family.md`) + update `adr/index.md` | Governance Board (boundary-exception decision) |
| 2 | Schema enum extension (`gcc-boundary` += `fedramp-moderate-aws-govcloud`) | Schema steward |
| 3 | Append five `reserved` registry entries (3 conformance + 2 modernization) | Governance steward + adapter steward |

Optional follow-on:
- PR 4 — amend AGENTS.md cloud-boundary statement to list NERM as second Commercial-exception (per ADR-058 Decision 1).
- PR 5+ — per-adapter activation ADRs (one per slot promoted to `active`).

## 9. Open questions for architect review

1. **Boundary path** — confirm Option A (NERM-only first) over Option B (full ISC family) and Option C (IIQ on-prem only). Draft selects A; confirm or redirect.
2. **Schema enum value** — is `fedramp-moderate-aws-govcloud` the right name, or should it be `fedramp-moderate` (cloud-agnostic) with a new `cloud-substrate` field naming AWS GovCloud? The latter is more future-proof if Option B ever lands.
3. **NERM scope** — does the conformance-only allocation match operational intent, or should `sailpoint-nerm-actions` be allocated immediately as a sibling? Default in this draft is conformance-only.
4. **Overlap policy** — Decision 5 says UIAO holds SSOT for Entra/AD writes. Is "fail closed on overlap" the right enforcement, or should overlapping writes be permitted under a documented mediation contract?
5. **Ordering vs. ADR-057 (ThousandEyes)** — ADR-057 was just merged; this is ADR-058. No content conflict, but flagging for awareness.
