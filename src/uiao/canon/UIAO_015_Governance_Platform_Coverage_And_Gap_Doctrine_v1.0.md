---
document_id: UIAO_015
title: "Governance-Platform Coverage And Gap Doctrine"
version: "1.0"
status: Draft
owner: "Michael Stratton"
created_at: "2026-08-27"
updated_at: "2026-08-27"
provenance:
  source: "ADR-139 §Decision 2 (allocation decision); sibling doctrine to UIAO_009"
  version: "1.0"
  derived_at: "2026-08-27"
  derived_by: "Doctrine synthesized from the two adapter registries (declared class / mission-class / scope / status), ADR-059 §Decision 5, ADR-092 (control-plane slots, L0–L4 ladder), ADR-135, ADR-136, and UIAO_210 / UIAO_211 vendor contract pins. Authored fresh — not derived from any external draft."
canonical_adrs:
  - ADR-139
  - ADR-049
  - ADR-059
  - ADR-092
  - ADR-135
  - ADR-136
canonical_docs:
  - UIAO_003
  - UIAO_009
  - UIAO_210
  - UIAO_211
---

# UIAO_015 — Governance-Platform Coverage And Gap Doctrine

## Overview

[UIAO_009](UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md) records
what Microsoft provides that UIAO leverages and what Microsoft does not
provide that UIAO must fill. It is deliberately Microsoft-scoped.

It leaves a symmetric question unanswered: **the same accounting for the
third-party governance platforms** — SailPoint (identity governance) and
ServiceNow (IT service management). Those platforms are declared across
both adapter registries, pinned by vendor contracts
([UIAO_210](specs/external/sailpoint-iiq/UIAO_210_identityiq-api-contract-pin.md),
[UIAO_211](specs/external/servicenow/UIAO_211_servicenow-deployment-contract-pin.md)), and
governed by four ADRs — but no single document says what they cover,
where they stop, and how to decide whether a given governance task
belongs to them or to the Microsoft-native surface.

This document is that accounting. It is the governance-plane sibling of
UIAO_009 and uses the same section shape deliberately. Its allocation and
the per-plane doctrine pattern it instantiates are decided by
[ADR-139](adr/adr-139-governance-plane-coverage-doctrine.md).

::: {.callout-note}
The recurring field question this doctrine answers is: *"Do we produce
compliance evidence through SailPoint and ServiceNow, through native
Entra / Azure / M365, or both?"* The short answer is **both, split by
behavior rather than by vendor** — §1 gives the test, §2 and §3 give the
coverage, and §4 gives the arbitration rule for the cases where the two
surfaces overlap.
:::

## 1. The Task-Classification Test

UIAO_009 §1 asks *"is this responsibility Microsoft's or UIAO's?"* That
frame still holds. It does not, by itself, resolve a task when both
Microsoft **and** a governance platform expose a usable surface — which
is the common case on the identity-governance plane.

Classify any governance or compliance task by asking these in order.
The first three questions are answered by the declared registry fields;
they are not a matter of judgement.

> **T1. Does the task mutate the estate?**
> Yes → `class: modernization`. No → `class: conformance`.
> This is the operational axis defined by the adapter-registry schema:
> *"`modernization` = change-making adapter (writes to target
> environment). `conformance` = read-only assessor (observes state,
> never mutates target)."*
>
> **T2. What kind of claim does the task produce?**
> `mission-class: identity | telemetry | policy | enforcement |
> integration`, per [UIAO_003](UIAO_003_Adapter_Segmentation_Overview_v1.0.md)
> §4.2–§4.7.
>
> **T3. What evidence does it yield, and on what cadence?**
> `evidence-class: baseline | interval | SCR | incident | annual`.
>
> **T4. Which surface is authoritative for it?**
> Microsoft-native, governance-platform, or **both**. If both, apply the
> arbitration rule in §4 — do not decide ad hoc.

The load-bearing consequence of T1 is that **a vendor is not a
category**. A product that both observes and acts receives *two*
declarations, one per registry. This is already the established pattern:

| Surface | Conformance declaration (observe) | Modernization declaration (act) |
|---|---|---|
| SailPoint ISC | `sailpoint-isc-governance` | `sailpoint-isc-actions` |
| SailPoint machine identity | `sailpoint-machine-identity` | `sailpoint-machine-identity-actions` |
| Microsoft Intune | `intune` (conformance) | `intune` (modernization) |
| CISA SCuBA | `scubagear` (assess) | `scuba` (apply) |
| Defender for Cloud Apps | `defender-for-cloud-apps` | `defender-for-cloud-apps-actions` |

The Intune pair is called out in UIAO_009 §2.2 as an explicit "two-axis
declaration per ADR-049 §Decision 1." The SailPoint pairs follow the
same precedent per [ADR-059](adr/adr-059-sailpoint-adapter-family.md).

**Therefore: "SailPoint + ServiceNow *or* native" is a malformed
question.** The registries do not split on vendor. They split on whether
a thing writes, and on what it claims.

## 2. Governance-Platform Coverage UIAO Leverages

### 2.1 SailPoint — identity governance

Every SailPoint slot is declared `mission-class: identity`. The
conformance slots observe governance *decisions*; the modernization
slots execute lifecycle *actions*.

| Concern | Adapter declaration | Class | Status | Declared scope |
|---|---|---|---|---|
| Non-employee identity (contractors, vendors, sponsored externals) | `sailpoint-nerm` | conformance | reserved | non-employee-identity-inventory, sponsorship-state, proofing-events, non-employee-risk-score, lifecycle-state-transitions |
| ISC governance plane | `sailpoint-isc-governance` | conformance | reserved | access-certification-campaigns, entitlement-management-packages, lifecycle-workflow-runs, separation-of-duties-findings, role-mining-results |
| Machine / non-human identity | `sailpoint-machine-identity` | conformance | reserved | service-account-inventory, bot-rpa-inventory, ai-agent-inventory, non-human-identity-ownership, machine-identity-lifecycle-state |
| IdentityIQ on-prem (locally branded SAM) | `sailpoint-iiq-governance` | conformance | reserved | scim-accounts-and-users, scim-entitlements-and-applications, certification-campaigns, policy-violations, launched-workflows, access-request-state |
| ISC lifecycle actuation | `sailpoint-isc-actions` | modernization | reserved | identity-lifecycle-joiner, identity-lifecycle-mover, identity-lifecycle-leaver, role-grant-revoke, certification-campaign-launch |
| Machine-identity actuation | `sailpoint-machine-identity-actions` | modernization | reserved | non-human-identity-ownership-assignment, service-account-decommission, credential-rotation-orchestration |

Boundary posture is per-slot and ADR-anchored: Option A (`sailpoint-nerm`)
by ADR-059; Option B (ISC family) ratified by
[ADR-135](adr/adr-135-sailpoint-isc-governance-option-b-ratification.md);
Option C (IdentityIQ) allocated by
[ADR-136](adr/adr-136-sailpoint-identityiq-option-c-slot-allocation.md).
The conformance slots bind to the ADR-092 identity control-plane slot at
governance rung **L1 (Observe)**.

### 2.2 ServiceNow — IT service management

| Concern | Adapter declaration | Class | Status | Declared scope |
|---|---|---|---|---|
| ITSM record plane | `service-now` | modernization | **active** | incident-tickets, change-requests, problem-records |

ServiceNow has **no conformance declaration**. It is declared purely as
a change/record actuator. Its deployment contract is pinned by
[UIAO_211](specs/external/servicenow/UIAO_211_servicenow-deployment-contract-pin.md).

### 2.3 Status reality — designed capacity is not deployed capability

::: {.callout-important}
**Of the seven governance-platform slots in §2.1–§2.2, exactly one —
`service-now` — is `status: active`. Every SailPoint slot is
`reserved`.**

Reserved means the slot is allocated and contract-shaped, not
implemented; ADR-059 §Decision 6 states activation requires a
per-adapter ADR modelled on ADR-035.

The operational consequence, which customer-facing material must not
overstate: **today, compliance evidence is produced almost entirely by
the Microsoft-native surface and the conformance telemetry adapters that
read it.** The SailPoint governance-decision evidence described in §2.1
is designed and reserved, not flowing. Any claim that an agency's
certification-campaign or SoD evidence is substrate-collected today is
false until the activating ADR lands and the slot flips to `active`.
:::

## 3. What the Governance Platforms Do Not Provide

The governance platforms are strong at what they own and silent on the
substrate's load-bearing concerns. These remain UIAO build
responsibilities, and none of them is closed by buying more SailPoint or
more ServiceNow.

1. **Cross-plane provenance binding.** Neither platform anchors a claim
   to a canon document ID and version. The provenance envelope is a
   substrate concern (UIAO_PP_001; ADR-006 determinism).
2. **Reconciliation between decision and enforced state.** SailPoint
   records that a certification was completed; Entra records what
   entitlements actually exist. Detecting divergence between them is
   neither platform's job — it is the drift engine's
   ([ADR-040](adr/adr-040-drift-engine.md)), and it is the single
   highest-value governance signal the substrate produces.
3. **OSCAL emission.** Neither platform emits FedRAMP-shaped OSCAL or
   CR26 KSI payloads from its native evidence.
4. **SSOT arbitration across overlapping writers.** See §4. Both
   platforms ship connectors that would happily write to surfaces UIAO
   holds SSOT for.

## 4. The Overlap Arbitration Rule

This is the load-bearing section, and the reason this doctrine exists
separately from UIAO_009.

**The overlap is real and specific.** `entra-id-governance` covers
Access Reviews, Entitlement Management, Lifecycle Workflows, PIM, and
SoD (UIAO_009 §2.1). `sailpoint-isc-governance` covers certification
campaigns, entitlement-management packages, lifecycle-workflow runs, and
SoD findings (§2.1 above). That is substantially **the same conceptual
surface offered by two vendors**, and SailPoint additionally ships
native Entra ID and Active Directory connectors.

[ADR-059](adr/adr-059-sailpoint-adapter-family.md) §Decision 5 already
rules on it, and that ruling is canonical. What follows is a
**restatement promoted to a discoverable location, not an extension** —
per [ADR-139](adr/adr-139-governance-plane-coverage-doctrine.md)
§Decision 4, where wording differs, ADR-059 governs:

> SailPoint ships native Entra ID and Active Directory connectors that
> overlap with the existing `entra-id`, `entra-id-governance`, and
> `active-directory` modernization adapters. Per the SSOT invariant,
> **UIAO holds SSOT for all Entra/AD writes.**

The activation ADR for any overlapping slot must declare which sources
it reads (UIAO-mediated or non-overlapping) and the failure mode if it
attempts a write to an Entra/AD object under UIAO SSOT — which **must
fail closed**.

Reduced to a rule for task classification:

| Situation | Ruling |
|---|---|
| Only Microsoft exposes the surface | Native adapter owns it. |
| Only the governance platform exposes it | Governance-platform adapter owns it. |
| **Both expose it, and the task is a _write_** | **UIAO holds SSOT. The native adapter is the write path; the governance platform is UIAO-mediated or fails closed.** |
| **Both expose it, and the task is a _read_** | Both may observe. Divergence between them is a drift finding, not a conflict to be resolved by picking a winner. |

The last row is the one most often got wrong. Two independent observers
of the same governance surface are an **asset**: the reconciliation
between "what SailPoint says was decided" and "what Entra says is
enforced" is precisely the evidence an assessor cannot obtain from
either platform alone.

## 5. What This Doctrine Implies

### 5.1 For classifying a compliance task

Run T1–T4 from §1. The answer is recorded in the registry entry, not in
prose. If a task cannot be expressed as a registry entry with a declared
`class`, `mission-class`, `evidence-class`, and `scope`, it is not yet
specified well enough to build.

### 5.2 For which control families each side feeds

Indicative, not a substitute for the per-adapter control mapping:

| Side | Answers the question | Typical control families |
|---|---|---|
| Microsoft-native + conformance telemetry (`siem`, `purview-audit`, `defender-*`) | *What did the system actually do?* | AU-2, AU-3, AU-12, SI-4 |
| SailPoint governance slots | *Was access authorized, reviewed, and certified — by whom?* | AC-2, AC-5, AC-6, AU-6 |
| ServiceNow | *Under what approved change or incident record?* | CM-3, CM-5, IR-4 |

Emission-side configuration for the first row is documented in the
[SIEM Telemetry Emission guide](../../../docs/customer-documents/operational-guides/siem-telemetry-emission/index.qmd).

### 5.3 For external claims

The UIAO_009 §4.4 rule extends here unchanged: customer-facing material
claiming "SailPoint provides X" or "ServiceNow provides Y" SHALL ground
the claim in §2 or §3 of this doctrine, **and SHALL state the slot's
`status`** so reserved capacity is never presented as deployed
capability (§2.3). Disagreement is resolved by ADR, not by ad-hoc
revision of the claim text.

## 6. Open Items

| # | Topic | Why deferred |
|---|---|---|
| 1 | Network plane (Palo Alto / Infoblox / BlueCat) and PAM (CyberArk) | Different planes with different arbitration questions; UIAO_009 §5 Open Item #2 already flags network as possibly needing a fifth gap category. |
| 2 | Federal attribute services (PIV/USAccess, SSA, IRS, GSA SAM, USCIS, DHS E-Verify, Treasury OFAC, State DMV, DCSA, VA, VITALS) | All `conformance: identity` and all reserved; they are authoritative-source consumers rather than governance platforms, and warrant their own coverage doctrine. |
| 3 | Alternate IdP families (`okta-orgpath`, `ldap-orgpath`, `keycloak-orgpath`, `auth0-orgpath`, `pingone-orgpath`) | All `proposed`; the arbitration rule in §4 is written against Entra as the SSOT holder and would need restating for a non-Entra primary IdP. |
| 4 | Per-slot control-mapping tables | §5.2 is indicative only. The authoritative mapping belongs in each adapter's spec, most of which are unwritten while the slots are reserved. |

## 7. Cross-References

- Authorizing decision: [ADR-139](adr/adr-139-governance-plane-coverage-doctrine.md).
- Microsoft half of this accounting: [UIAO_009](UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md).
- Dual-axis taxonomy: [UIAO_003](UIAO_003_Adapter_Segmentation_Overview_v1.0.md).
- Vendor contract pins: [UIAO_210](specs/external/sailpoint-iiq/UIAO_210_identityiq-api-contract-pin.md), [UIAO_211](specs/external/servicenow/UIAO_211_servicenow-deployment-contract-pin.md).
- SailPoint family and SSOT-conflict rule: [ADR-059](adr/adr-059-sailpoint-adapter-family.md); Option B [ADR-135](adr/adr-135-sailpoint-isc-governance-option-b-ratification.md); Option C [ADR-136](adr/adr-136-sailpoint-identityiq-option-c-slot-allocation.md).
- Control-plane slots and the L0–L4 actuation ladder: [ADR-092](adr/adr-092-active-governance.md).
- Adapter registries: [`adapter-registry.yaml`](adapter-registry.yaml) (conformance), [`modernization-registry.yaml`](modernization-registry.yaml) (modernization).
