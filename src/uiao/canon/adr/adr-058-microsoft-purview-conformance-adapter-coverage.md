---
id: ADR-058
title: "Microsoft Purview Conformance Adapter Coverage — Read-Only Telemetry Slot for Audit, DLP, Information Protection, and Insider Risk State"
status: accepted
date: 2026-05-07
accepted: 2026-05-07
deciders:
  - governance-steward
  - security-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-027
  - ADR-035
  - ADR-047
  - ADR-049
canon_refs:
  - UIAO_003_Adapter_Segmentation_Overview
  - UIAO_009_Microsoft_Coverage_And_Gap_Doctrine
  - UIAO_132_continuous-monitoring-program
related_findings:
  - FINDING-008
related_issues:
  - WhalerMike/uiao#322
---

# ADR-058: Microsoft Purview Conformance Adapter Coverage

## Status

ACCEPTED — 2026-05-07

## Context

ADR-049 (2026-04-30) declared eight Microsoft surfaces as reserved
adapter slots, expanding registry coverage across the Defender suite,
Azure Migrate, Azure Policy for Arc, Entra Governance, Entra Workload
Identity, and the modernization side of Intune. ADR-049 explicitly
scoped its coverage matrix to those eight surfaces. **Microsoft Purview
was not in that matrix and fell through.**

Purview is currently covered only on the **modernization** axis: the
`m365` entry in `canon/modernization-registry.yaml` lists `purview` in
its `scope` (line 100), giving the adapter authority to write
tenant-config changes to Purview surfaces. The **conformance** axis —
read-only telemetry observation of Purview state — has no slot.

### What is already declared

Modernization side (write-path) coverage exists implicitly inside the
`m365` adapter:

* `m365.scope` includes `purview` alongside Exchange Online, SharePoint
  Online, Teams, and Defender for Office 365.
* `m365.controls` covers CM-2, CM-3, CM-8 — configuration management
  for tenant-wide settings, including any Purview-side configuration
  the adapter writes.

Conformance side (read-only observation) has no entry under any vendor
prefix. There is no `purview-*` slot on either registry.

### What is missing

The conformance-side observation surface for Purview state is the gap.
Concretely:

| Surface | Why UIAO needs to observe it |
|---|---|
| **Unified-audit retention tier** (Standard 180d / Premium 1y / 10-year add-on) | Drives the FINDING-008 retention cliff. Today this is detected by static finding; a conformance adapter converts it to a continuous drift signal. |
| **Audit-event coverage** (which UAL workloads enabled per tenant) | OMB M-21-31 Tier 3 logging compliance is workload-scoped — a tenant can be on Premium and still have UAL coverage gaps. |
| **DLP policy state** (SC-4 evidence) | Control-library entry `data/control-library/sc/SC-4.yml` already names Purview DLP as the SC-4 evidence source; no adapter currently produces that evidence. |
| **Sensitivity-label policy state and coverage** (MP-3, RA-2 evidence) | Control-library entries `mp/MP-3.yml` and `ra/RA-2.yml` name Purview Information Protection as the evidence source for media labeling and information classification — same gap as SC-4. |
| **Litigation-hold state** | Spec2-D2.3 (leaver workflow) names litigation-hold orchestration as a Purview reference (D2.3 §4 step 9, §6.2, §11). With no observation surface, the leaver workflow cannot verify the hold actually applied. |
| **Insider-risk policy state** | Referenced informally in canon but not connected to any adapter; Purview Insider Risk policy state is the natural conformance surface. |

### Why the gap matters

Three concrete consequences of leaving the Purview conformance surface
undeclared:

1. **FINDING-008 stays static.** The 180-day retention cliff is a
   measurable, agency-side control gap with named OMB M-21-31, CISA BOD
   25-01, and ZTMM v2.0 implications. Without a conformance adapter,
   each agency's posture against the cliff is checked once at
   onboarding and not continuously. The ConMon program (ADR-047,
   UIAO_132) cannot include retention-tier drift in monthly packs.
2. **SC-4 / MP-3 / RA-2 evidence is unsourced.** Three control-library
   entries name Purview as the evidence source. With no adapter
   producing the evidence, those controls fail the
   `DRIFT-PROVENANCE` check at the registry layer the same way the
   ADR-049 missing surfaces did.
3. **Leaver-workflow litigation-hold cannot be closed-loop.** The
   D2.3 specification references Purview litigation hold but defers
   the messaging-adapter family per ADR-049 reserved slots. Without a
   Purview conformance slot, the spec's "verify hold applied"
   acceptance step (D4.4 line 136) has no canonical observation surface.

The omission is the natural follow-up to ADR-049, not a new doctrine.

## Decision

1. **Reserve one new conformance adapter slot** in
   `canon/adapter-registry.yaml`: `purview-audit`. The slot's `scope`
   covers seven surfaces — unified-audit retention tier, audit-event
   coverage, DLP policy state, sensitivity-label policy state,
   information-protection coverage, litigation-hold state, and
   insider-risk policy state — capturing the full conformance surface
   without subdividing the slot per surface. If a future operational
   need demands it, the slot can be split per ADR-049 §Decision 1's
   `defender-for-cloud-apps` precedent, but the default is one slot.

2. **Do not extract a `purview-actions` modernization slot.** Purview
   change-making operations remain inside the `m365` modernization
   adapter's `purview` scope until a concrete change-making workflow
   demands extraction. The read-only slot is the load-bearing
   addition; the modernization-side split can be deferred without cost
   to FINDING-008 closure or ConMon coverage. (This explicitly differs
   from ADR-049's `defender-for-cloud-apps` split, which was justified
   by the OAuth-app governance write-path being operationally distinct
   from MDCA Discovery; no equivalent operational pressure exists for
   Purview today.)

3. **Land the registry slot in this PR, not a follow-on.** ADR-049
   §Decision 4 deferred registry edits to follow-on PRs because eight
   slots were too many to bundle with the doctrine. ADR-058 reserves
   one slot — bundling it with the ADR keeps stage 1 of the
   three-stage lifecycle (canon → docs scaffold → impl) atomic. The
   docs scaffold and impl remain separate stages.

4. **Bind FINDING-008 to ADR-058 forward.** Add a §5 cross-reference
   from `docs/findings/fedramp-gcc-moderate-purview-audit-180day-cliff.qmd`
   to ADR-058 / `purview-audit`, so the finding↔adapter link is visible
   from both directions. FINDING-008's "Awaiting-Internal-Remediation"
   status remains correct; the conformance adapter is not the remedy
   itself — it is the continuous-detection surface that turns the
   remedy decision into a measurable posture.

5. **No new registry schema required.** The slot validates against
   `schemas/adapter-registry/adapter-registry.schema.json` (schema
   version 1.0.0) at the same shape as the ADR-049 Defender slots.
   Specifically: `automation-domain` uses the canonical NIST SP 800-137
   Appendix D values `event-management` (audit log management) and
   `information-management` (DLP / information protection / insider
   risk) — no new domain values are introduced.

## Consequences

### Positive

* FINDING-008 becomes a live drift signal in monthly ConMon packs
  rather than a static one-shot finding. Agencies on Audit Standard
  surface as a continuous KSI-AU-11 gap until they upgrade or stand up
  the compensating long-term forensic store.
* SC-4, MP-3, and RA-2 control-library evidence sources gain a named
  adapter on the conformance axis, closing three `DRIFT-PROVENANCE`
  registry-layer gaps.
* Spec2-D2.3 leaver-workflow litigation-hold acceptance criterion
  (D4.4 line 136) gains a canonical observation surface for the
  "verify hold applied" check.
* The ADR-049 coverage-expansion pattern is exercised once more on a
  Microsoft surface that was missed in the original ADR, demonstrating
  the doctrine handles incremental discoveries without requiring an
  ADR-049 amendment.

### Negative / costs

* One additional `reserved` entry in the conformance registry. Cost is
  the same as any ADR-049 slot: schema validation surface grows by one
  entry; substrate walker scans grow by one entry. No runtime cost
  while reserved.
* This ADR breaks slightly with ADR-049's "no registry edits in the
  ADR PR" pattern (ADR-049 §Decision 4). The deviation is justified by
  scale: bundling one slot with one ADR keeps the stage-1 PR atomic
  without enlarging it. Future single-slot ADRs may follow this
  pattern; future multi-slot ADRs (>3 slots) should follow ADR-049's
  separate-PR pattern.
* Insider-risk policy state coverage in the slot's `scope` is somewhat
  forward-looking — canon references it informally but no current spec
  binds it to a control. The scope entry is included so the slot can
  cover the surface without a slot edit later; if the surface never
  gets canonical binding, the scope entry is harmless.

### Risks

* Microsoft has historically reorganized Purview surfaces (the brand
  itself was reshaped in 2022 to absorb Compliance + Information
  Governance). If a future reorganization splits unified audit out of
  Purview (e.g., into a Defender or Sentinel sub-product), the
  `purview-audit` slot must be retired per ADR-027 and a successor
  named. This is a known cost of declaring vendor-named surfaces
  eagerly.
* The single-slot decision (Decision 1) deliberately bundles seven
  surfaces under one adapter. If activation reveals that operational
  ownership of any one surface (e.g., insider-risk) is so distinct
  that it deserves its own runtime, the slot can be split per the
  ADR-049 `defender-for-cloud-apps` precedent. The risk is bounded
  because the slot is reserved (no implementation yet).

## Follow-on work

1. **PR (this one)** — Land ADR-058, append the `purview-audit`
   reserved entry to `canon/adapter-registry.yaml`, and add the §5
   forward-reference to FINDING-008.
2. **Stage 2** — Create `docs/customer-documents/adapter-specs/
   purview-audit/` scaffold via `scripts/tools/sync_canon.py
   --scaffold` once stage 1 lands. Separate PR.
3. **Stage 3** — Per-adapter activation ADR (modeled on ADR-035) when
   `purview-audit` is promoted from `reserved` to `active`. Activation
   binds the slot to a Python implementation under
   `src/uiao/adapters/purview_audit_adapter.py` and a workflow under
   `.github/workflows/`. Activation order is an implementation-track
   decision and is not fixed by this ADR.
4. **(Deferred)** — Re-evaluate Decision 2 (no `purview-actions`
   modernization split) if a concrete change-making workflow against
   Purview emerges that the `m365` adapter cannot cleanly absorb.

## Notes

* This ADR is registry-shaped, not implementation-shaped. No Python
  code, schema, or test fixture is created here.
* The driver is FINDING-008, filed 2026-04-27 with
  `Awaiting-Internal-Remediation` status. The conformance adapter does
  not change the remediation calculus (Sentinel long-retention archive
  vs. Audit Premium upgrade vs. Premium + 10-year add-on); it changes
  the detection cadence from one-shot finding to continuous drift.
* Issue tracking: WhalerMike/uiao#322 (canon change request).
