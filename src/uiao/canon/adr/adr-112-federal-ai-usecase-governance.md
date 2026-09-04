---
adr_id: adr-112
title: "Federal AI Use Case Governance — M-25-21 IAM Obligations, OMB Inventory Integration, and ATO Drift Signal"
status: PROPOSED
decided: 2026-06-18
deciders: Michael Stratton
updated: 2026-06-18
next_review: 2026-12-18
review_trigger: M-25-21 is superseded or substantively amended; OMB publishes a 2026 AI Use Case Inventory; the sailpoint-machine-identity slot promotes from reserved to active; ADR-054 single-ATO reciprocity model is revised; a new federal mandate (EO or OMB Memo) imposes additional AI-identity obligations
impact: "Closes the M-25-21 canon gap flagged in HRIT-IAM-Findings.md §5. Positions UIAO's IAM layer against M-25-21's AI governance obligations beyond the SCIM provisioning SLA already captured in ADR-088 and Spec2-D6.1. Names the OMB 2025 Federal AI Use Case Inventory as the authoritative external AI system roster and maps its fields to UIAO's machine-identity and ATO-reciprocity surfaces. Establishes that deployed federal AI systems — especially agentic-AI-classified entries — are identity subjects within UIAO's machine-identity surface (sailpoint-machine-identity slot, ADR-059) and that their have_ato/system_name_ato fields are an external ATO enumeration source for ADR-054 drift reconciliation. Doctrine only."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-112-federal-ai-usecase-governance.html
---

# ADR-112: Federal AI Use Case Governance — M-25-21 IAM Obligations, OMB Inventory Integration, and ATO Drift Signal

## Status

**PROPOSED** — 2026-06-18.

This ADR is doctrine. It closes an explicit canon gap and names UIAO's obligations and surfaces in the federal AI governance regime. It does not change any runtime behavior, schema, or registry entry.

## Context

### The M-25-21 canon gap

OMB Memorandum M-25-21 (*Accelerating Federal Use of AI: Innovation, Governance, and Public Trust*, 2025) is the primary federal AI governance mandate currently in force, issued under Executive Order 13960. UIAO references M-25-21 in two places:

- **ADR-088 / Spec2-D6.1** — cites M-25-21 for the SCIM 2.0 ≤15-minute provisioning SLA in the HRIT federal vertical.
- **HRIT-IAM-Findings.md §5, note** — explicitly flags: *"OMB M-25-21 is referenced in Req #5 but not yet incorporated into UIAO governance canon. Pull and review when the memo is published."*

The memo is published. The AI Use Case Inventory it mandated (via EO 13960 §5) is now public at `github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory`. That gap is real and this ADR closes it.

### What M-25-21 mandates beyond the provisioning SLA

M-25-21 imposes a governance regime on federal AI systems that has IAM implications UIAO's current canon does not address:

| Obligation | M-25-21 anchor | UIAO surface it touches |
|---|---|---|
| Agency AI Use Case Inventory (public transparency, machine-readable) | EO 13960 §5 + M-25-21 §III | Machine-identity surface — every inventoried system is an identity subject |
| ATO status *reported for* deployed AI | OMB inventory `have_ato` field (a **reporting** field — M-25-21 imposes no AI-specific ATO gate and directs agencies to keep applying existing authorization requirements) | ADR-054 single-ATO reciprocity — ATO enumerability |
| High-impact AI minimum risk-management practices | M-25-21 **§4(b)** — seven practices, reported against by the inventory's six `hi_*` fields (see the coverage note below) | Evidence fabric — compliance evidence for governed AI systems |
| PII and Privacy Impact Assessment for AI systems | OMB inventory `has_pii`, `pia_url` fields | UIAO's identity fabric — PII-bearing AI systems are highest-priority identity subjects |
| Agentic AI classification | OMB inventory `classification` field | ADR-092 active governance — agentic AI systems are data planes UIAO governs |

### The OMB 2025 Federal AI Use Case Inventory

The inventory is the machine-readable realization of M-25-21's transparency obligation. As of the 2025 edition:

- **3,611 individually reported AI use cases** across 56 agencies
- **1,818 deployed or piloted** (the live attack surface for identity governance)
- **445 high-impact** (the population subject to the full M-25-21 governance checklist)
- Key fields for UIAO: `agency`, `agency_bureau`, `system_name_ato`, `have_ato`, `has_pii`, `pia_url`, `classification` (includes *Agentic AI*), `development_stage`, `vendor_name`, `operational_date`, and the full `hi_*` safety checklist battery

The inventory is published annually, machine-readable (CSV/XLSX), and openly licensed.

### What M-25-21 imposes, and what the inventory merely reports

This distinction is load-bearing and the earlier revision of this ADR blurred
it. **M-25-21 §4(b)** sets **seven** minimum risk-management practices for
high-impact AI: (1) pre-deployment testing; (2) an AI impact assessment; (3) ongoing monitoring; (4) human training; (5) human oversight and intervention; (6) remedies and appeals; and (7) public feedback. Independent review is a component *inside* the
impact assessment, not an eighth practice.

The memo imposes **no AI-specific Authorization to Operate gate**. It
directs agencies to continue applying their existing authorization
requirements to AI systems. `have_ato` is an inventory field that *reports*
an agency's existing ATO posture; it is not evidence of a gate the memo
created. Any claim that M-25-21 requires an ATO before production AI
deployment is a misattribution, and a federal evaluator who knows the memo
reads it as inventing the test you pass.

**The six `hi_*` fields do not cover all seven practices.** Mapping them:

| §4(b) practice | Inventory field |
|---|---|
| Pre-deployment testing | `hi_testing_conducted` |
| AI impact assessment | `hi_assessment_completed` (with `hi_independent_review` as its internal component) |
| Ongoing monitoring | `hi_ongoing_monitoring` |
| Human oversight and intervention | `hi_failsafe_presence` |
| Remedies and appeals | `hi_appeal_process` |
| **Human training** | **no inventory field** |
| **Public feedback** | **no inventory field** |

Two of the seven practices have no corresponding inventory field, so an
inventory-derived compliance view is structurally incomplete against §4(b).
That gap is a real finding and a better differentiator than the invented
gate it replaces: a governance substrate that reconciles the inventory can
say which practices the inventory cannot evidence.

**Two cadences, not one.** The AI use-case inventory goes to OMB **at least
annually**; compliance plans are due at 180 days and **every two years
thereafter until 2036**. All M-25-21 deadlines have now passed: a Chief AI
Officer within 60 days, and the minimum practices for high-impact AI by
**3 April 2026**.

**Companion memoranda.** M-25-21 rescinded M-24-10. **M-25-22** governs how
an agency *acquires* AI and is the memo a contracting officer works from.
**M-26-04** (11 December 2025) adds unbiased-AI principles and self-sunsets
on 11 December 2027.

### Sailpoint machine-identity slot

ADR-059 allocated a `sailpoint-machine-identity` conformance slot (status: *reserved*) to observe *"discovered service / bot / RPA / AI-agent inventory, ownership graph, lifecycle state."* The OMB inventory is the authoritative federal register that gives this slot its primary discovery feed for the federal vertical. Without naming that feed, the slot has no defined source of truth for which AI systems exist.

### ADR-092 — agentic AI as a governed data plane

ADR-092 established that UIAO is an active reconciliation control plane that *governs* provider data planes. Agentic AI systems — the fastest-growing classification in the OMB inventory — are precisely those data planes: they take autonomous action within the same org/identity substrate UIAO manages (Entra, Intune, AD, and its successors). They are not governed by UIAO today; this ADR names them as in-scope identity subjects.

## Decision

Four positions.

### 1. M-25-21's AI governance obligations bind UIAO's IAM layer

UIAO's canon acknowledges M-25-21 only for the SCIM provisioning SLA (ADR-088, Spec2-D6.1). That is insufficient. M-25-21's broader AI governance regime creates IAM obligations that UIAO's architecture must accommodate:

- Every inventoried deployed or piloted federal AI system is an **identity subject** of UIAO's machine-identity surface. It has an owning agency/bureau (maps to OrgPath), a vendor (maps to KYC/NERM), a credential surface (service accounts, API keys, workload identities), and a PII flag that places it in UIAO's privacy-sensitive identity tier.
- The **ATO requirement** for deployed AI is a FedRAMP/reciprocity artifact that UIAO's compliance evidence layer must enumerate, not merely reference.
- The **high-impact governance checklist** (`hi_*` fields) is a structured evidence obligation. For the AI systems UIAO incorporates as governed data planes, those fields become compliance evidence targets in the evidence fabric (ADR-006, ADR-014, ADR-016).
- **Agentic AI systems** — systems that *act autonomously* within the identity substrate — carry the same blast-radius exposure as a privileged service account. They must be governed at L1 (observed) at minimum, with L3 (gated actuation) as the ceiling per ADR-092 §4 until autonomous-actuation criteria are met.

### 2. The OMB 2025 Federal AI Use Case Inventory is the authoritative external AI system roster for the federal vertical

For the federal vertical (OPM HRIT instantiation and all agency tenants it serves), UIAO **MUST** treat the OMB AI Use Case Inventory as the primary external discovery feed for the machine-identity surface. Specifically:

- Every entry where `development_stage ∈ {deployed, pilot}` is a candidate identity subject for onboarding to the `sailpoint-machine-identity` slot.
- `system_name_ato` + `agency_bureau` are the join keys to UIAO's OrgPath namespace (bureau → OrgTree node; system_name_ato → machine-identity record name).
- `vendor_name` maps to the KYC / NERM non-employee identity surface (ADR-055, ADR-059); the AI system's vendor relationship is governed the same way any other non-employee relationship is.
- `classification = Agentic AI` triggers the highest governance priority tier — these systems act, not merely serve.

The inventory is annual. The machine-identity surface MUST treat inventory freshness (last published date) as a staleness signal, the same way ADR-040 treats snapshot age for the drift engine.

### 3. `have_ato` and `system_name_ato` are an external ATO enumeration source for ADR-054 drift reconciliation

ADR-054 established single-ATO reciprocity as a doctrine: OPM's ATO covers all agency use of the HRIT platform under a single SSP. It does not define how UIAO enumerates which AI systems have ATOs in the broader federal environment.

The OMB inventory's `have_ato` + `system_name_ato` fields provide that enumeration:

- An inventoried deployed AI system with `have_ato = No` is an **ATO gap** — a drift finding against the M-25-21 mandate. UIAO's drift taxonomy (ADR-012, ADR-033) can classify this as `DRIFT-COMPLIANCE::ato-gap` at L1 (observed).
- An inventoried system with `have_ato = Yes` and a `system_name_ato` that does not appear in UIAO's known ATO registry is a candidate for **ATO reciprocity lookup** against UIAO_140.
- A machine-identity record in UIAO's registry with no corresponding OMB inventory entry is a **shadow AI system** — an unregistered deployment that M-25-21 requires to be inventoried. This is the highest-severity finding class from this surface.

The L1 (observe) rung is the initial and currently authorized ceiling for this drift signal. Promotion to L2 (advise) or L3 (gated actuation) requires a separate governance decision per ADR-092.

### 4. Agentic AI systems are governed data planes under ADR-092 at L1 minimum

ADR-092 §1 establishes that UIAO governs provider data planes without competing with them. The OMB `classification = Agentic AI` entries represent a new class of provider data plane: autonomous AI agents operating within the federal identity and infrastructure substrate.

These systems:

- **MUST** be onboarded to the `sailpoint-machine-identity` slot as identity subjects (machine agent type, not human type) once the slot activates.
- **MUST** carry OrgPath — the owning agency/bureau provides the organizational placement; the `sailpoint-machine-identity` adapter stamps it.
- **MUST** have their ATO status reconciled against the OMB inventory per §3 above.
- **SHOULD** have their `hi_*` governance-checklist fields ingested as compliance evidence once the evidence-adapter for this surface is activated.

The governance mode for this population is **L1 (observe)** at activation — actual state is collected, drift is detected, no writes. Promotion to L3 requires the standard criteria: clean dry-run window, `blast_radius = low`, and an explicit governance-board record.

## Consequences

**Positive.**

- The M-25-21 canon gap flagged in HRIT-IAM-Findings.md is closed. Every future reference to M-25-21 in UIAO canon cites this ADR for the governance scope beyond the SCIM SLA.
- The `sailpoint-machine-identity` reserved slot gains a named discovery feed (OMB inventory) and a defined activation trigger (deployed/pilot entries with ATO status). It is no longer a blank reserved slot.
- ATO drift detection against the federal AI population becomes a defined, classifiable finding type (`DRIFT-COMPLIANCE::ato-gap`), not an ad-hoc observation.
- Agentic AI systems — the fastest-growing and highest-blast-radius class in the inventory — are explicitly in-scope as governed identity subjects before they proliferate further into the federal substrate.
- The evidence fabric (ADR-006, ADR-014, ADR-016) has a new structured evidence source: the `hi_*` M-25-21 governance checklist fields for high-impact AI systems.

**Negative / costs.**

- The `sailpoint-machine-identity` slot must activate before any of §2–§4 can run. That requires the Option-B boundary decision in the sailpoint-adapter-plan.md, or at minimum a narrower activation ADR.
- The OMB inventory is annual; machine-identity state changes faster. The adapter will require a supplementary discovery mechanism (continuous telemetry or quarterly scan) between inventory vintages.
- `DRIFT-COMPLIANCE::ato-gap` findings for AI systems may surface dozens of agencies simultaneously — blast radius of the *finding* is high even if the L1 remediation rung means UIAO does not auto-correct.
- Shadow AI system detection (UIAO record with no OMB entry) is politically sensitive; it names non-compliant agency behavior publicly. Scan redaction policy (ADR-045) applies.

**Neutral.**

- Doctrine only — no runtime, schema, or registry change lands with this ADR.
- Does not change ADR-054 (single-ATO reciprocity); extends its drift-detection scope by naming the OMB inventory as an enumeration source.
- Does not change ADR-059 (sailpoint adapter family); adds a named discovery feed and priority ordering to the `sailpoint-machine-identity` slot's activation criteria.

## References

- [ADR-012](adr-012-canonical-drift-taxonomy.md) — canonical drift taxonomy; source of `DRIFT-COMPLIANCE` class
- [ADR-033](adr-033-gcc-boundary-drift-class.md) — GCC boundary drift class
- [ADR-040](adr-040-drift-engine.md) — six-phase drift engine; L1 observe rung
- [ADR-045](adr-045-scan-redaction-policy.md) — scan artifact redaction policy
- [ADR-054](adr-054-single-ato-reciprocity.md) — single-ATO reciprocity model; ATO enumeration extended by §3
- [ADR-059](adr-059-sailpoint-adapter-family.md) — sailpoint adapter family; `sailpoint-machine-identity` slot
- [ADR-088](adr-088-hr-as-orgtree-truth-source.md) — HR system of record as OrgTree source; M-25-21 SCIM SLA
- [ADR-092](adr-092-active-governance.md) — active governance; L0–L4 actuation ladder; agentic AI as data plane
- [HRIT-IAM-Findings.md §5](../../../../inbox/HRIT%20Modernization/HRIT-IAM-Findings.md) — origin of the M-25-21 canon gap note
- [inbox/drafts/sailpoint-adapter-plan.md §7](../../../../inbox/drafts/sailpoint-adapter-plan.md) — extended with OMB inventory as machine-identity discovery feed
- OMB 2025 Federal AI Use Case Inventory — `github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory`
- OMB M-25-21 — *Accelerating Federal Use of AI: Innovation, Governance, and Public Trust*, 2025
- EO 13960 — *Promoting the Use of Trustworthy Artificial Intelligence in the Federal Government*, 2020
