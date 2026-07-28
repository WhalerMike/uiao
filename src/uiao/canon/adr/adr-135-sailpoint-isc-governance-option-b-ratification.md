---
adr_id: adr-135
title: "SailPoint ISC Governance — Option-B Ratification and Native Cloud IAM/RBAC Reconciliation Binding"
status: ACCEPTED
decided: 2026-07-28
deciders: Michael Stratton
updated: 2026-07-28
next_review: 2027-01-28
review_trigger: The `sailpoint-isc-governance` slot promotes from reserved to active (a per-adapter activation ADR is required first); a VMware/vCenter permission-governance adapter is proposed (this ADR explicitly does not cover that surface); AGENTS.md's cloud-boundary statement is next amended for an unrelated reason (verify this ADR's addition survived); ADR-092's control-plane slot model is revised
impact: "Ratifies the Option-B boundary-expansion decision that ADR-059 explicitly deferred to a future ADR — the `sailpoint-isc-governance` and `sailpoint-machine-identity` conformance slots, and the `commercial-exception-sailpoint-isc` gcc-boundary enum value, landed in PR #924 citing ADR-059 but were never actually decided by a ratifying ADR of their own; this is that ADR. Corrects a second standing gap: AGENTS.md's cloud-boundary statement was never amended to list the third Commercial exception, even though the schema enum has carried it since PR #924. Binds `sailpoint-isc-governance` to ADR-092's Active Governance identity control-plane slot as the incorporated provider for native cloud IAM/RBAC entitlement reconciliation (Azure RBAC, AWS IAM) — explicitly at governance rung L1 (Observe), read-only, feeding the same ServiceNow-coordinated evidence pipeline the OrgComp series already uses for CM-6/RA-5/SI-2, not a second parallel front door. Explicitly does not cover VMware/vCenter permissions — no evidence exists that SailPoint's CIEM reaches that surface, and this ADR does not invent a slot to paper over the gap. Does not activate the slot (still `status: reserved`); activation remains a future per-adapter ADR per existing precedent. Registry-shaped and doctrine-shaped; no runtime, schema, or registry-content change beyond the AGENTS.md sentence."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-135-sailpoint-isc-governance-option-b-ratification.html
---

# ADR-135: SailPoint ISC Governance — Option-B Ratification and Native Cloud IAM/RBAC Reconciliation Binding

## Status

**ACCEPTED** — 2026-07-28

## Context

Three loose threads converge on this ADR.

**Thread 1 — Option B was shipped without ever being decided.** [ADR-059](adr-059-sailpoint-adapter-family.md) allocated the `sailpoint-nerm` conformance slot (Option A: non-employee identity lifecycle only) and explicitly deferred the broader SailPoint Identity Security Cloud (ISC) family — general workforce identity governance, cross-source machine identity — to "a future ADR after NERM proves out the integration pattern" (§Notes, Option B). PR #924 ("add SailPoint ISC family reserved slots (ADR-059 Option B)") nonetheless landed `sailpoint-isc-governance` and `sailpoint-machine-identity` as `status: reserved` conformance-registry entries, plus the `commercial-exception-sailpoint-isc` value on the `gcc-boundary` schema enum — all citing ADR-059 in their `references:` block. ADR-059 itself never decided Option B; NERM has not proven out the integration pattern (it remains `status: reserved` too, unpromoted). The registry and schema currently assert a boundary-expansion decision that no ADR actually made. This ADR is the ratifying decision PR #924 was missing.

**Thread 2 — AGENTS.md silently fell out of sync.** AGENTS.md's cloud-boundary statement lists exactly two Commercial exceptions: Amazon Connect and SailPoint NERM. It has never listed `commercial-exception-sailpoint-isc`, even though that enum value has shipped in the schema since PR #924. Per ADR-059 §Decision 3, "new values are added to this enum in lockstep with an authorizing ADR" — the enum value shipped without its ADR, and AGENTS.md's boundary statement (the human-readable summary of the same fact) was never touched. This ADR closes both halves in lockstep, as the convention requires.

**Thread 3 — the native cloud IAM/RBAC evidence question.** A parallel line of work (the `orgcomp-vs-native-cloud-consoles.qmd` whitepaper, drafted 2026-07-28) asked whether native cloud consoles' identity/RBAC surfaces (Azure RBAC role assignments, AWS IAM policies) have the same evidence gap as their configuration/vulnerability/patch surfaces already do (CM-6/RA-5/SI-2, closed by Vol VII Books 03/06/07 through ServiceNow coordination). External research the same day confirmed: SailPoint's ISC + CIEM add-on already natively governs AWS/Azure/GCP cloud IAM entitlements (over-privileged accounts, idle entitlements, over-broad roles) — this is exactly the detection capability the reserved `sailpoint-isc-governance` slot was scoped for. The research also confirmed SailPoint's own architecture routes its findings into ServiceNow's Service Desk for ticketing and audit tracking, rather than trying to be a standalone evidence system itself — which settles a design question this ADR would otherwise have had to answer from scratch: **`sailpoint-isc-governance` is one more detection engine feeding the existing ServiceNow-coordinated evidence pipeline, structurally identical to how Security Hub, Defender for Cloud, and VCF Operations feed it today — not a second, parallel coordination layer.**

ADR-092 (Active Governance) already anticipates this: its provider-incorporation contract is domain-agnostic across six control-plane slots (`control-planes.yml`), identity among them, and §2 names "SailPoint NERM for identity (ADR-059)" as a worked example of the pattern. `sailpoint-isc-governance` fits the identical contract shape for the workforce/general-population identity surface that NERM deliberately excludes.

## Decision

Five positions.

### 1. Option B is ratified, narrowly, for `sailpoint-isc-governance` only

This ADR ratifies the boundary-expansion decision PR #924 assumed but never received: `commercial-exception-sailpoint-isc` is an authorized `gcc-boundary` value, on the same named-product-exception convention as Amazon Connect and SailPoint NERM (ADR-059 §Decision 3). This ratification is scoped to the **conformance (read-only) surface only** — `sailpoint-isc-governance`. It does **not** ratify `sailpoint-machine-identity` (cross-source machine/service-account identity — a materially different discovery surface with its own justification, better decided on its own terms) or either modernization-side slot (`sailpoint-isc-actions`, `sailpoint-machine-identity-actions` — change-making surfaces, a higher-stakes decision than a read-only observer). Those three slots remain `status: reserved`, un-ratified, exactly as ADR-059 left them; a future ADR may ratify them individually.

### 2. AGENTS.md is amended in lockstep

AGENTS.md's cloud-boundary statement is amended to list the third Commercial exception:

> "...Two named Commercial exceptions: Amazon Connect Contact Center, and SailPoint Non-Employee Risk Management (FedRAMP Moderate on AWS GovCloud, per ADR-059)."

becomes:

> "...Three named Commercial exceptions: Amazon Connect Contact Center, SailPoint Non-Employee Risk Management (FedRAMP Moderate on AWS GovCloud, per ADR-059), and SailPoint Identity Security Cloud Governance (FedRAMP Moderate on AWS GovCloud, per ADR-059 Option B, ratified by ADR-135)."

### 3. `sailpoint-isc-governance` binds to ADR-092's identity control-plane slot, at rung L1

Per the ADR-092 provider-incorporation contract (§2): `sailpoint-isc-governance` binds to the **identity** slot in `control-planes.yml`, alongside the existing Identity Provider / ICAM Governance components already named there. It is declared at **rung L1 (Observe)** on the actuation maturity ladder — read-only signal collection and drift detection, matching its existing `ssot-mutation: never` registry property exactly. This ADR does **not** promote the slot to L2 or beyond; that requires the slot's own future activation ADR, per the registry's own existing notes and the ADR-092 §4 ceiling rules.

### 4. The reconciliation target is the existing ServiceNow evidence pipeline, not a new one

`sailpoint-isc-governance`'s findings — over-privileged cloud IAM entitlements, idle role assignments, over-broad RBAC grants on Azure and AWS — reconcile into the **same ServiceNow-coordinated evidence pipeline** the OrgComp series already runs for CM-6/RA-5/SI-2 (Vol VII Books 02/03/06/07), not a separate SailPoint-fronted loop. This is a deliberate consistency decision: SailPoint's own product architecture already routes findings to ServiceNow rather than trying to be a standalone system of record, and building a second, parallel coordination layer for identity findings alone would fragment the evidence story this ADR's own Thread 3 exists to keep unified. AC-2, AC-3, and AC-6 close the same way CM-6/RA-5/SI-2 do: native surface actuates (a role is revoked, an entitlement is scoped down), ServiceNow owns the finding, the SLA, the approval, and the closure evidence.

### 5. VMware/vCenter permission governance is explicitly out of scope here

No slot is allocated, reserved, or implied for VMware/vCenter role and permission governance. External research found no evidence that SailPoint's CIEM reaches vSphere/vCenter permissions, and this ADR does not invent a slot to paper over that gap. The native cloud IAM/RBAC reconciliation this ADR describes covers Azure and AWS only; VMware's identity/RBAC surface remains unaddressed pending either a SailPoint product capability that doesn't yet exist or a different provider entirely.

## Consequences

**Positive.**

- Closes a real process gap: registry entries and a schema enum value that shipped without their authorizing decision now have one, without requiring a rebuild of anything already landed.
- AGENTS.md's boundary statement is now accurate and complete — a reader relying on it as the single source of truth for the cloud boundary no longer gets a wrong answer for `commercial-exception-sailpoint-isc`.
- Gives `sailpoint-isc-governance` a concrete, non-hypothetical reconciliation target (the existing ServiceNow pipeline) rather than leaving it as an undirected reserved slot.
- Keeps the evidence story for identity findings consistent with configuration/vulnerability/patch findings — one coordination pattern, not a fragmented one per control family.
- Explicit non-coverage of VMware and of `sailpoint-machine-identity`/the modernization-side slots keeps this ADR's blast radius narrow and honest rather than quietly implying broader closure than it delivers.

**Negative / costs.**

- `sailpoint-isc-governance` is still `status: reserved` after this ADR — no new capability ships. A future per-adapter activation ADR is still required before this binding does anything at runtime.
- The narrow scoping (this ADR ratifies exactly one of the four Option-B slots) means `sailpoint-machine-identity` and both modernization-side slots remain in the same un-ratified state ADR-059 left them in; a reader must track which of the four slots this ADR actually covers rather than assuming "Option B" is now uniformly settled.
- VMware/vCenter identity governance remains a genuine, unaddressed gap after this ADR — it does not get smaller by virtue of this ADR existing, and should not be cited as if it does.

**Neutral.**

- Doctrine and registry-decision only — no runtime, schema, or registry-content change beyond the AGENTS.md sentence (consistent with ADR-085, ADR-089, ADR-092, ADR-134).

## Alternatives considered

- **Ratify all four Option-B slots at once.** Rejected for this ADR. `sailpoint-machine-identity` and the two modernization-side slots are materially different decisions (a different discovery surface; change-making authority) that deserve their own justification rather than riding in on the conformance-only identity-governance binding this ADR is actually about.
- **Invent a VMware identity-governance slot now, to keep the story "complete."** Rejected. No SailPoint capability or alternate provider for that surface was found; allocating a slot with no adapter behind it would misstate coverage that does not exist — the same failure mode ADR-059 itself warns against.
- **Stand up a second, SailPoint-fronted coordination loop for identity findings (parallel to ServiceNow).** Rejected. SailPoint's own integration architecture already routes findings into ServiceNow; building a competing front door would fragment the evidence story for no benefit and contradicts the single-coordination-layer consistency this ADR's Decision 4 exists to preserve.

## References

- [ADR-059](adr-059-sailpoint-adapter-family.md) — the original SailPoint carve-out; deferred Option B to this ADR.
- [ADR-092](adr-092-active-governance.md) — the provider-incorporation contract and actuation maturity ladder this ADR binds `sailpoint-isc-governance` against.
- [ADR-056](adr-056-login-gov-activation-contract.md) — a worked example of the per-adapter activation-contract pattern a future ADR would use to promote this slot to active.
- `src/uiao/canon/adapter-registry.yaml` — `sailpoint-isc-governance`, `sailpoint-machine-identity` entries (PR #924).
- `src/uiao/schemas/adapter-registry/adapter-registry.schema.json` — `gcc-boundary` enum, `commercial-exception-sailpoint-isc` value.
- `src/uiao/canon/data/control-planes.yml` — the identity control-plane slot.
- `docs/customer-documents/whitepapers/orgcomp-vs-native-cloud-consoles.qmd` §7/§10 — the customer-facing argument this ADR's binding supports; see also the companion OrgComp book this ADR enables.
- `AGENTS.md` — cloud-boundary statement, amended by this ADR.
