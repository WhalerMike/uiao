# Federal AAN — ConMon Pipeline Critique Response & Remediation Backlog
**Internal CSI Team Working Document — Draft for SSA review**

**Date Code:** 2026-07-09 17:30 ET

---

## Purpose and Status

This document records an external senior-engineer critique of the ConMon
Evidence Pipeline (Vol VI Book 07 and its supporting Vol III/IV architecture)
and converts it into a **grounded, prioritized remediation backlog**. It is a
companion to the [Value Assessment](federal-aan-value-assessment.md), the
[ConMon Gap Roadmap](federal-aan-conmon-gap-roadmap.md), and the
[Governance & Ownership Model](federal-aan-governance-ownership-model.md).

It is a **draft**, marked **INTERNAL — NOT FOR PUBLIC DISTRIBUTION**, unreviewed
by the CIO Office or OIS, and asserts no authorization decision.

> **Provenance note.** The critique is a third-party (LLM) outside-in review.
> It is a useful readiness signal but is not canon and not evidence. Every
> point below was checked against the repository before being accepted. The
> verdicts distinguish **Confirmed** (ground truth agrees), **Confirmed but
> overstated** (the direction is right, the specifics are wrong), and
> **Corrected** (the claim does not hold against the source). The remediation
> backlog is built only from the parts that survive that check — which is most
> of them. The critique's central thesis is correct and worth stating plainly:
> the architecture is strong; the gap is between *self-assessed* and
> *assessor-ready / multi-person-operable*.

---

## 1. Verification — Critique vs. Ground Truth

| # | Critique point | Verdict | Evidence in repo |
|---|---|---|---|
| 1 | 29 ADR-111 rules not reconciled to the ~56–63 CR26 Moderate catalog; "29/29 satisfied" is a credibility risk | **Confirmed** | No crosswalk artifact exists on disk; the Gap Roadmap already flags this as the open item. This is the top finding, and it agrees with the Value Assessment §2. |
| 2 | Vol VI Book 07 §"Deployable Artifacts" and §"Closure Necessity" are *empty headings*; pipeline is four bullets; no schemas/queries/DCRs/retention/failure modes/SLOs | **Confirmed but overstated** | Book 07 is 103 lines and *is* pointer-level for a deployment view — the pipeline is four bullets (lines 68–71) and it carries no sample KQL, DCR specs, or failure-mode analysis. **But the two sections are not empty:** "Deployable Artifacts" is a 4-row artifact table (lines 55–64) and "Closure Necessity" is a closure callout (lines 75–78). The concrete deployable detail that *does* exist lives in **Book VI-08**, not VI-07. |
| 3 | Emitter completeness is asserted, not measured — no inventory, no coverage %, no regression test that fails on a silent emitter | **Confirmed (with nuance)** | There is no coverage *report/percentage*. The *mechanism* to catch silent emitters exists: Book VI-08's telemetry-completeness workbook (illustrative KQL, per-table freshness SLA, "STALE" flag). What's missing is a measured completeness inventory and a wired CI regression, not the detection concept. |
| 4 | Single-person / single-team risk on the evidence-governance layer (Conformance Adapter, ADR-111 engine, ScubaDrift, `uiao oscal bundle`) | **Confirmed** | Ownership Model assigns CSI (R) / AO (A) but names no **backup operators** and carries no regeneration/triage runbook. A "can the AR regenerate if the author is out two weeks?" runbook does not exist. |
| 5 | Microsoft gravity exceeds the "engine-neutral" claim; non-MS emitter depth (AWS SSM, OCI, Red Hat) and cross-cloud correlation not demonstrated at equal fidelity | **Confirmed (readiness gap)** | The contract *is* engine-neutral by design (Book 07 §"Evidence Contract"), and the Multi-Cloud Evidence Fabric states the doctrine — but the demonstrated working path is ScuBAGear → ScubaDrift → Log Analytics/Sentinel → `uiao`. Concrete multi-vendor evidence examples are not yet on hand for an SCA. |
| 6 | Freshness/latency/reproducibility **SLOs** missing | **Confirmed but overstated** | Program-level SLOs (source→lake latency, AR-generation success rate, correlation-completeness %) are genuinely absent. But per-table **freshness SLAs already exist** (Book VI-08 `SlaMinutes`), AU-11 retention floor is set (1095 days, Vol III Book 06), and `--as-of` gives reproducibility. The gap is program SLOs, not "no freshness thinking." |
| 7 | Exception/POA&M **human governance** (who may mark `governed_exception`; formal risk-acceptance workflow feeding the register) is under-specified vs. the technical pipeline | **Confirmed** | The ScubaDrift disposition pipeline is well-specified technically; the *approval authority* and risk-acceptance workflow that authorizes an exception are not. The register's edit-authority model is not documented. |
| 8 | No short, assessor-facing "ConMon Evidence Guide" (contract → current AR → regenerate → ScubaDrift history → CR26 crosswalk → Sentinel workbooks) | **Confirmed** | No such artifact exists. The corpus is 23 books + tooling; a 3PAO needs a 10–15 page navigator. High value, low effort. |
| L1 | Telemetry lake sizing/cost/**retention** not addressed | **Corrected on retention; confirmed on sizing/cost** | Retention *is* addressed: AU-11 / GRS 3.2 floor, `TotalRetentionInDays 1095` (Vol III Book 06 line 246). Lake **sizing and cost** at SSA scale are genuinely not addressed. |
| L2 | "Invalid Date" appears on multiple documents | **Not reproduced** | `grep "Invalid Date"` across the AAN source returns **zero** hits. If seen, it is a render-time artifact in a specific viewer (a `date:` field a renderer failed to parse), not a string in the source — track it as a render-QA item, not a content defect. |
| L3 | Emitters may not be validated against a completed Product Inventory Questionnaire | **Confirmed (unverified linkage)** | The PIQ exists (Vol 0 Book 01); there is no artifact tying the *live emitter set* back to a completed inventory. |
| L4 | No failure-mode analysis for the pipeline itself (OSCAL emitter / ScubaDrift gate down 48h) | **Confirmed** | VI-08 catches silent *sources*; there is no FMEA/runbook for the *pipeline* components themselves. |

**Net:** of the twelve points, eight are confirmed outright, three are directionally
right but overstated in specifics (Book 07 "empty," "no SLOs," "retention not
addressed"), and one ("Invalid Date") does not reproduce against the source.
The critique's thesis holds: the remaining work is operability and
assessor-readiness, not more architecture.

---

## 2. Remediation Backlog (Prioritized)

Priorities follow "what an SCA/AO writes up first." Each item states a
**definition of done** so it is verifiable, not aspirational. Owner hints are
recommendations pending the Ownership Model ratification.

### P1 — Before any SCA or AO briefing

| ID | Item | Definition of done | Owner (rec.) |
|---|---|---|---|
| P1-A | **KSI crosswalk** (critique #1) | A versioned artifact: `ADR-111 rule ID → CR26 indicator ID(s) → evidence slot → confidence`, covering the full ~56–63 CR26 Moderate set (not just the 29). Any CR26 indicator with no ADR-111 rule is listed as a **known gap**, not silently omitted. Becomes the single source of truth cited by the bundle. | CSI + OIS |
| P1-B | **Assessor Evidence Guide** (critique #8) | A 10–15 page navigator: the contract, the current AR, how to regenerate it (`uiao oscal bundle`), the ScubaDrift history, the P1-A crosswalk, and the Sentinel workbooks. Standalone; readable without the 23 books. | CSI |
| P1-C | **Backup operators + regeneration runbook** (critique #4) | A named second operator (role, per the Ownership Model) and a runbook that regenerates the AR and triages ScubaDrift dispositions end-to-end without the primary author. Validated by a dry run performed by the backup. | CSI + AO |

### P2 — Before ATO / early ConMon

| ID | Item | Definition of done | Owner (rec.) |
|---|---|---|---|
| P2-A | **Emitter completeness report + CI regression** (critique #3) | A generated inventory: expected emitters, live emitters, coverage %; plus a CI check (extend Book VI-08's telemetry-completeness workbook) that **fails the pipeline** when a required emitter goes silent. | CSI |
| P2-B | **Program SLOs** (critique #6) | Three measured SLOs to start: source→lake evidence latency, AR-generation success rate, correlation-completeness % (records joined on `assetId`). Baseline + target for each; dashboarded. Keep the existing per-table freshness SLAs; these sit above them. | CSI |
| P2-C | **Exception approval workflow** (critique #7) | A documented risk-acceptance workflow: who may authorize a `governed_exception`, the approval record that feeds the register, and expiry/review. The register moves from "editable file" to authority-gated change. | OIS + AO |
| P2-D | **Multi-CSP evidence proof** (critique #5) | At least one concrete non-Microsoft evidence example (e.g., AWS SSM or OCI) traversing the full contract → correlation → KSI → bundle path, demonstrating the fabric is contract-real, not Microsoft-plus-adapters. | CSI |
| P2-E | **Vol VI Book 07 depth or honest demotion** (critique #2) | Either flesh Book 07 with real deployable detail (sample DCRs, diagnostic settings, retention policy references, KQL, failure modes) **or** explicitly demote it to an overview and move the operational meat into a living "ConMon Pipeline Runbook." Do not leave it reading as a deployment view it does not deliver. | CSI |

### P3 — Operational hardening

| ID | Item | Definition of done | Owner (rec.) |
|---|---|---|---|
| P3-A | **Pipeline FMEA** (critique L4) | Failure-mode analysis + runbooks for the pipeline components: OSCAL emitter down, ScubaDrift gate down 48h, lake ingestion stalled — detection, fallback, and catch-up procedure for each. | CSI |
| P3-B | **Lake sizing & cost model** (critique L1) | Retention is set (AU-11, 1095 days); add ingestion-volume, storage-cost, and archive-tier projections at SSA scale. | CSI |
| P3-C | **Emitter↔PIQ validation** (critique L3) | An artifact tying the live emitter set to a completed Product Inventory Questionnaire for the target boundary, so completeness is measured against a real inventory. | CSI |
| P3-D | **Render QA for date fields** (critique L2) | Confirm every `date:` frontmatter value parses in the Quarto/DOCX pipeline; add a render-lint check so a viewer never shows "Invalid Date." (No source hits today — this is prevention.) | CSI |

---

## 3. Corrections to the Record

Stated so this response is not mistaken for wholesale agreement:

1. **Book 07's sections are thin, not empty.** "Deployable Artifacts" carries a
   4-row table and "Closure Necessity" a closure callout. The valid critique is
   *depth*, not *absence* — and the concrete artifacts largely live in Book
   VI-08.
2. **Freshness thinking already exists.** Per-table freshness SLAs (VI-08) and
   `--as-of` reproducibility are present. The real gap is *program-level* SLOs.
3. **Retention is addressed.** AU-11 / GRS 3.2, 1095-day floor (Vol III Book
   06). Lake *sizing/cost* is the open item, not retention.
4. **"Invalid Date" does not appear in the source.** Zero grep hits — a
   render-QA item at most, not a content defect.

---

## 4. What Is Already Strong (Keep / Amplify)

The critique's "keep" list is accurate and worth preserving as design
invariants: the evidence contract and the `assetId` join key; ScubaDrift as a
lifecycle layer over point-in-time scanning; the zero-scaffold achievement and
generated OSCAL bundle; the truth-plane / enforcement-plane separation; the
honest-limits sections; and the freshness/cadence thinking already in the
corpus. None of the P1–P3 work requires walking any of these back — it turns a
high-quality self-assessment into something that survives independent scrutiny
and multi-person operation.

---

*This document is an internal UIAO working artifact. It does not constitute an
authorization package or official assessment. All verdicts are advisory pending
formal SCA/ATO review.*
