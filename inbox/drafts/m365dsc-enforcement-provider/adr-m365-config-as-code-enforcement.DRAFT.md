---
adr_id: adr-NNN  # PLACEHOLDER — assign next free number at promotion (ADR-092 is highest merged).
title: "Microsoft 365 Config-as-Code as a Governed Enforcement Provider"
status: DRAFT
decided: null
deciders: Michael Stratton
updated: 2026-06-03
next_review: null
review_trigger: Microsoft Graph Tenant Configuration Management APIs reach GA and supersede Microsoft365DSC; the actuator-security design (authz / immutable audit / dry-run / rollback / break-glass) required by ADR-092 lands and an op class is proposed for L3; a second config-as-code provider is incorporated; control-planes.yml slots are revised.
impact: "Incorporates Microsoft 365 config-as-code (Microsoft365DSC today; Graph Tenant Configuration Management APIs tomorrow) as a governed ENFORCEMENT provider under the ADR-092 provider-incorporation contract — the actuation counterpart to the read/assessment adapters (entra/intune/m365) and the ScubaGear/Zero-Trust-Assessment evidence producers. Decomposed per control-plane slot; defaulted to L0-L2 (record / observe / advise); L3 (gated apply) blocked until the ADR-092 actuator-security design exists; L4 prohibited for high-blast-radius identity/security classes. Closes the assess -> reconcile loop. Doctrine + adapter contract only; no auto-remediation enabled."
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: false   # draft; promote into src/uiao/canon/adr/ to publish
publication_style: include
---

# ADR-NNN (DRAFT): Microsoft 365 Config-as-Code as a Governed Enforcement Provider

## Status

**DRAFT** — 2026-06-03. Staged in `inbox/drafts/m365dsc-enforcement-provider/`.
**Subordinate to [ADR-092](../../../src/uiao/canon/adr/adr-092-active-governance.md)
(Active Governance)** — one worked instance of its provider-incorporation
contract and L0–L4 actuation ladder, on the *enforcement* side. Sibling to the
`uiao.adapters.zta` / `uiao.adapters.scuba` evidence adapters.

## Context

UIAO already **reads** the Microsoft 365 control plane (`entra_adapter`,
`intune_adapter`, `m365_adapter`, `entra_policy_targeting`) and **ingests
assessment evidence** from ScubaGear and the Microsoft Zero Trust Assessment.
What it lacks is a governed way to express and reconcile **desired state** for
that control plane — the "apply half" gestured at in the ZT-incorporation draft's
*Future: Active UIAO* section. The loop today stops at *advise*: assessment
finds drift, the remediation playbook proposes the fix, and a human re-keys it in
a portal.

[**Microsoft365DSC**](https://microsoft365dsc.com) is the mature config-as-code
engine for Microsoft 365 — declarative configuration for Entra, Intune, Exchange,
Teams, SharePoint, Defender, Purview, and Power Platform, with export, drift
detection, and enforcement modes. Microsoft's **Graph Tenant Configuration
Management APIs** (public preview, Jan 2026) are the native successor, with a
documented transition path from Microsoft365DSC.

Crucially, M365DSC's operating modes line up almost exactly with the ADR-092
ladder, so this is incorporation into existing machinery, not a new control.

## Decision

1. **Incorporate M365 config-as-code as a governed *enforcement* provider** under
   the ADR-092 provider-incorporation contract (Platform Services Layer,
   UIAO_102), routed through the existing enforcement runtime (UIAO_111,
   `enforcement/runtime.py`) with `auto_enforce=False` default and the ADR-040
   dry-run / governance-review gating. UIAO governs the data plane; it does not
   reimplement it.

2. **Bind per control-plane slot — not one monolith.** The contract requires an
   adapter bind to exactly one `control-planes.yml` slot. M365 config-as-code
   spans **identity** (Entra), **endpoint** (Intune), and **security**
   (Defender), so it is incorporated as **separate per-slot enforcement
   adapters**, starting with **identity**.

3. **Map operating modes to ADR-092 rungs:**

   | ADR-092 rung | M365 config-as-code operation |
   | --- | --- |
   | **L0 Record** | The desired-state config committed to canon/substrate |
   | **L1 Observe** | `Export` + `Test` drift report (read-only) |
   | **L2 Advise** | The drift delta / change-set, surfaced; no writes |
   | **L3 Gated actuation** | `Start-DscConfiguration` / apply behind per-scan human approval; dry-run default |
   | **L4 Autonomous** | `ApplyAndAutoCorrect` — **prohibited** for in-scope classes |

4. **Default rung is L0–L2.** Recording desired state, detecting drift, and
   emitting an advisory change-set need only read scope, are fully within the
   federal L3 ceiling, and deliver value immediately. **No write credential is
   provisioned for the default posture.**

5. **L3 (gated apply) is blocked until the ADR-092 actuator-security design
   exists.** ADR-092 §Risks requires authz, immutable audit, dry-run, rollback,
   and break-glass "designed before any op class promotes to L3, not after."
   M365 enforcement needs a broadly-scoped service principal across the M365
   surface — the highest-value attack surface UIAO would ship — so L3 promotion
   is explicitly gated on that design.

6. **L4 is prohibited for high-blast-radius identity/security classes** —
   tenant-wide Conditional Access and `directoryScopeId=/` role assignment are
   permanently L3-capped per ADR-092 §4. `ApplyAndAutoCorrect` is never enabled
   for these.

7. **Desired-state config is a materialized artifact, not a second SSOT.** UIAO
   canon + OrgPath remain the source of truth for governance *intent*; the DSC
   config is generated/owned under governance as the M365 control plane's
   materialized desired state. The read adapters (`entra`/`intune`/`m365`) feed
   L1; this provider owns L0/L2 (and, when designed, gated L3).

8. **Bind the capability, not the tool.** The verb contract (`record / observe /
   plan / apply / reconcile`) is mechanism-agnostic: **Microsoft365DSC** is the
   provider today; the **Graph Tenant Configuration Management APIs** swap in
   when GA, without re-incorporation.

9. **Runs in-boundary; FedRAMP-Moderate-compatible.** It is self-hosted (pipeline
   / admin workstation inside the GCC-Moderate boundary); GCC uses commercial
   endpoints, so no sovereign-endpoint dependency at Moderate. Output is
   Controlled.

## Consequences

**Positive.** Closes the assess→reconcile loop (ZT/SCuBA evidence L1 → remediation
playbook L2 → config-as-code reconcile L3-gated). Config-as-code is native to
UIAO's git-substrate/PR-review model. The active surface becomes
**accreditable rung-by-rung** ("identity config is at L2, roadmap to L3"), which
ADR-092 calls the sentence an AO can sign. Reuses the existing enforcement
runtime + dry-run engine rather than inventing one.

**Negative / watch.** The actuator is a crown-jewel attack surface — L3 must wait
on the security design. Per-slot decomposition is more adapters to maintain.
Two-SSOT drift risk if the exported config is mistaken for truth (guarded by §7).
M365DSC is community-maintained and may be superseded by Graph TCM (guarded by
§8). Large surface — scope discipline required (identity first).

## Phasing

1. **Now (L0–L2):** identity-slot enforcement adapter — record desired state,
   detect drift, emit advisory change-set. Read scope only.
2. **Next:** extend to the **endpoint (Intune)** slot (complements ADR-071/080
   Intune-first onboarding).
3. **Then (L3, gated):** only after the actuator-security design; human-approved,
   dry-run-default apply; high-blast classes permanently gated.
4. **Never:** L4 autonomous for identity/security high-blast classes.

## Open questions

1. Does the desired-state config live beside the relevant `control-planes.yml`
   slot, or in a dedicated `src/uiao/.../desired-state/` tree?
2. How is the L0 desired-state authored — exported-then-curated from a known-good
   tenant, or generated from canon/OrgPath intent?
3. What is the minimal read-scope service principal for L1/L2, and where is the
   (future) L3 write credential custodied (Key Vault in-boundary)?
4. Sequencing vs the Graph Tenant Configuration Management APIs — adopt M365DSC
   now and plan the swap, or wait for TCM GA?
