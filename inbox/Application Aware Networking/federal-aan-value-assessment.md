# Federal AAN — Series Value Assessment (Adoption Artifact)
**Internal CSI Team Working Document — Draft for SSA review**

**Date Code:** 2026-07-10 (rev. 2 — empirical pass + self-critique applied)

---

## Purpose and Status

This document assesses the value of the Federal Application-Aware Networking
(AAN) series to SSA and to peer federal agencies. It is a companion to the
[ConMon Gap Roadmap](federal-aan-conmon-gap-roadmap.md), the
[Governance & Ownership Model](federal-aan-governance-ownership-model.md), and
the [ConMon Critique Response](federal-aan-conmon-critique-response.md).

It is a **draft**, marked **INTERNAL — NOT FOR PUBLIC DISTRIBUTION**, unreviewed
by the CIO Office or OIS, and asserts no authorization decision.

> **Revision note (rev. 2).** The first revision was, on its own terms, the same
> kind of artifact it assessed: self-referential, self-attested, and
> count-anchored, written in the language of empirical grounding without an
> empirical pass. This revision corrects that. It (a) records what was actually
> executed versus asserted, (b) removes an unsourced replacement-cost figure and
> an unsupported comparative claim, (c) adds absorbability and opportunity-cost
> as first-order value factors, and (d) conditions the headline verdict on the
> open items rather than asserting it and hedging afterward.

## Method and Its Limits

What this assessment can and cannot establish, stated plainly so the verdict is
not read as more than it is:

- **It verifies corpus-internal consistency and file-level facts** — counts,
  named artifacts, whether the committed OSCAL bundle exists, whether the
  tooling runs. Those are checked (§2).
- **It does not establish that the architecture is correct.** The artifacts it
  reasons from — the executive summary, the gap roadmap, the committed
  Assessment Results — are **self-assessments authored by the same team**.
  "29/29 satisfied" traces to a bundle the team generated from its own 29 rules;
  that is self-attestation, not independent validation. Only an independent SCA
  can convert self-attestation into assessed fact. Where this document says a
  claim is "corroborated," it means *corroborated against a self-generated
  artifact*, not independently assessed.
- **Book count is not a value proxy.** The series' depth varies widely — some
  books are deep implementation guides, others (e.g. Vol VI Book 07, 103 lines)
  are pointer-level. Counting them equally measures volume, not value. The value
  judgment below weights operability and depth, not the headline count.

---

## 1. What the Package Actually Is (Ground Truth)

The series is a **draft, control-mapped technical roadmap and
authorization-package corpus** developed by the CSI Team as an internal UIAO
working document. Its authoritative self-description is
[Vol 0 Book 00 — Executive Summary](Vol_0_Book_00_FedAAN_Executive_Summary.qmd);
its delivery status is the [Gap Roadmap](federal-aan-conmon-gap-roadmap.md). The
counts below are read directly from those artifacts and the files on disk.

| Dimension | Ground truth (this repo) | Note |
|---|---|---|
| Series structure | Six volumes (Vol 0 program + Vols I–IV implementation + Vol V enablement + Vol VI deployable-artifact layer) | — |
| Content books | **23 implementation books**, plus the Executive Summary, the Product Inventory Questionnaire, five volume overviews, and four Volume V enablement books (43 `.qmd` files on disk) | Do **not** conflate the 23 with the 43 files; and do not read "23" as 23 books of equal depth (see Method) |
| Controls | **34 distinct controls** for the *original six tracks*; extension and Vols III–IV books close additional controls in their own "Authorities Closed Here" tables | The exact additional count is per-book, generated from the compliance spine, not a single audited total |
| KSI rules | **29** — the ADR-111 rule-set decomposition, **not** the published CR26 Moderate catalog (~56–63 indicators) | The single most important open caveat (§2) |
| Framing | SSA is a **consumer** of FedRAMP-authorized services seeking an agency RMF/FISMA ATO; **not** a CSP seeking FedRAMP authorization | — |

---

## 2. Delivery Status — Executed, Not Asserted

The first revision asserted the evidence tooling "exists and runs." This
revision **ran it**. Results as of 2026-07-10 on a fresh editable install:

| Check | Command | Observed result |
|---|---|---|
| Test suite (KSI/OSCAL surface) | `pytest -k "ksi or oscal or bundle"` | **691 passed, 21 skipped, 8 xfailed** (~36s). The emitter/evaluator surface is genuinely tested and green. |
| Committed OSCAL bundle exists | `ls output/artifacts/ksi-bundle/` | Present: `ksi-ap.json`, `ksi-ar.json` (149 KB), `ksi-poam.json`, `scubadrift-verdicts.json`, `artifact-index.json` (generated 2026-07-05) |
| AR content | parse `ksi-ar.json` | **29 findings, all `state: satisfied`; POA&M empty; all 10 KSI theme codes present** (CED, CMT, CNA, IAM, INR, MLA, PIY, RPL, SCR, SVC). "29/29 satisfied, 0 POA&M" is corroborated *against the self-generated artifact*. |
| Bundle regenerates | `uiao oscal bundle` | Command exists (`src/uiao/cli/oscal.py`) |
| **Schema validation** | `uiao oscal validate <ar>` | ⚠ **Stub — "OSCAL validate is not implemented yet," exits 0.** A no-op that reports success is worse than a failure; it can be mistaken for a passing gate. |
| **Trestle validation** | `uiao oscal validate-ssp -d output/artifacts/ksi-bundle` | ⚠ **FAILS** on `ksi-poam.json`: `type object 'PlanOfActionAndMilestones' has no attribute 'model_validate'` (a pydantic-v1/v2 code defect in the validation path). |
| Tree integrity | `uiao substrate walk` | Runs; emits pre-existing `DRIFT-PROVENANCE` P2 findings (ADRs citing retired slug `MOD_V`). Not blocking; not related to this series. |

**What the empirical pass changes.** The generation and test story is real and
positive — the bundle is produced, the surface is tested, and the AR is
internally clean. But **independent schema validation of the committed bundle
does not currently pass**: one validator is an unimplemented stub that exits 0,
and the trestle validator errors out on the POA&M model. This is the
"self-assessed vs. assessor-ready" gap made concrete — a 3PAO who runs the
repo's own validators today gets a no-op and a crash, not a green check. It
belongs on the P1 list and was invisible to a documents-only reading.

**Honest open items** (unchanged in substance from rev. 1, now with the
validation finding added):

1. **KSI reconciliation.** The 29 ADR-111 rules must be diffed rule-by-rule
   against the finalized CR26 Moderate catalog (~56–63 indicators). Until then,
   "29/29 satisfied" is a claim about the internal rule set, **not** coverage of
   the full CR26 set. All 10 theme codes are present, which bounds the gap to
   *within-theme* indicator coverage, not whole missing themes — but that is a
   floor, not the reconciliation.
2. **OSCAL validation is not operational.** Per the pass above — fix the stub
   and the trestle POA&M defect before any SCA relies on machine validation.
3. **Release 5.2.0 deltas.** SA-15(13), SA-24, SI-2(7) not yet mapped in the
   Part 11 / Part 15 closure tables.
4. **Ratification.** The series names no owners by design; adoption depends on
   CIO/OIS ratifying the ownership model. Self-assessment is not an SCA or an AO
   decision.

---

## 3. Value Drivers, Grounded

Each driver ties to an artifact that exists in this repository. Grounding here
means *the design is present and internally consistent* — not that it is
independently validated (see Method).

| Driver | What delivers it (in-repo) | Why it matters (federal context) |
|---|---|---|
| **Plane separation** | Seven functional planes run through every volume; "truth planes" vs. "enforcement planes" is series doctrine | Survives reorganization; prevents treating ZTNA/SASE/NAC as "the solution" instead of an enforcement surface that depends on clean identity/DNS/PKI truth |
| **Closure-necessity doctrine** | Stated as *mechanism classes, never products* in the Gap Roadmap, with a per-layer alternatives table | Moves claims toward falsifiable protocol behavior and corrects the misread that the series locks a single vendor |
| **Evidence-first ConMon** | OSCAL emitter, KSI packages, `uiao oscal bundle`, ScubaDrift disposition pipeline, CA-7 program (Vol IV Book 06, Vol VI Book 07) | Serves M-24-15 ConMon, CDM, FISMA CIO metrics, and the 2027 CR26 clock — *contingent on §2 item 2 (validation) being fixed* |
| **Identity/org SSOT** | HRIT (Oracle HCM / OPM) → event-driven SCIM/Entra provisioning, OrgTree/OrgPath (Vol I Book 04) | Attacks the chronic federal identity failure (orphaned accounts, stale OUs); closes AC-2, IA-4, PS-4/5, SI-12 |
| **Implementation-as-code** | Vol VI: Network/Identity-as-Code, Detection Engineering, SOAR, baselines, evidence pipeline, validation harnesses | Version-controlled auditable artifacts rather than slides + tickets — where the books are deep; depth is uneven (Method) |
| **Portability** | Plane model + ownership model + Product Inventory Questionnaire (Vol 0 Book 01) | A path for a peer agency to re-map, not a finished deliverable (§5) |

---

## 4. Value — What Can and Cannot Be Quantified

**Removed in this revision: the "$8–15M / 18–36 month" replacement-cost
figure.** It was carried from the external review, had no basis in an SOW or a
labor model, and — even labelled an estimate — lends false authority and travels
without its caveat. **This series has not been costed.** A defensible number
requires a costing exercise (labor hours by role × rate, or a benchmarked SOW);
until then, no dollar figure should be attached to it, in this document or
downstream.

What *can* be stated with more confidence, because it follows from the design
rather than a price model:

- **Risk reduction (qualitative).** The corpus avoids the common federal pattern
  of repeated failed ZT/NAC/identity projects, and an evidence-first design
  should reduce SCA finding volume — *once the validation path (§2) actually
  runs*. This is the most defensible value claim.
- **Deadline exposure reduced.** Whatever its absolute worth, the corpus reduces
  SSA's exposure to the 2027 CR26 date by having control mappings and a working
  emitter rather than a blank SSP. The magnitude is unquantified.
- **Recurring capability.** The ConMon pipeline and as-code baselines are an
  operating capability, not a one-time deliverable — the value most likely to be
  understated by any point-in-time cost estimate.

### The absorbability discount (first-order)

The largest determinant of *realizable* value is not the corpus's quality but
whether SSA can **operate it without its authors**. The
[Critique Response](federal-aan-conmon-critique-response.md) (P1-C) and the
Ownership Model both flag that the evidence-governance layer — the Conformance
Adapter, the ADR-111 engine, ScubaDrift dispositions, `uiao oscal bundle` — has
no named backup operators and no regeneration/triage runbook validated by a
second person. **An asset only its author can run is worth a fraction of its
face value.** Until a backup operator regenerates the AR end-to-end unaided,
apply a heavy discount to every value statement above. This is not a footnote;
it is the swing factor.

### Opportunity cost (the missing comparison)

Value is relative to the next-best alternative, which rev. 1 never named:

| Alternative | What SSA would get | Trade vs. the AAN series |
|---|---|---|
| Adopt free federal templates (CISA SCuBA, NIST OSCAL profiles) + a commercial GRC platform | Baseline ConMon + vendor-supported tooling | Less bespoke architecture and no truth-plane doctrine; but vendor-operable out of the box, lower absorbability risk |
| Commission an FFRDC/SI reference architecture | Externally authored, arguably more defensible provenance | Higher cost and lead time; less tailored to SSA's actual estate |
| Inherit-and-minimize | Lean on leveraged FedRAMP authorizations, minimal agency-native evidence | Lowest effort; highest risk against M-24-15/FISMA ConMon expectations |

The AAN series' advantage over all three is fit-to-estate and the working
emitter; its disadvantage is absorbability and single-team provenance. A real
value case weighs those explicitly rather than assuming replacement cost is the
counterfactual.

---

## 5. Limitations and Risks

Ordered by effect on realizable value, not by ease of stating:

- **Absorbability / single-team provenance (highest).** As §4 — the corpus may
  be operable only by its authors today. This caps realizable value more than
  any technical gap.
- **Validation not operational.** Per §2, the repo's own OSCAL validators
  either no-op or crash on the committed bundle. "Machine-readable evidence" is
  true for *generation*; it is not yet true for *verification*.
- **KSI mapping open.** The 29-rule set is not reconciled to the CR26 catalog.
  Most likely first SCA finding.
- **SSA-centric.** Pre-filled inventory, Oracle HCM, Infoblox DDI, M365 GCC,
  specific landing-zone assumptions. Portability is a path requiring the PIQ to
  be completed, not a shipped product.
- **Draft, not ratified.** Every book carries the "Draft Proposal" banner; no
  owners are bound; nothing here is an ATO.
- **Uneven depth.** Book depth ranges from deep guides to pointer-level stubs
  (Vol VI Book 07). The headline count overstates uniform substance.
- **Density.** Senior-engineer level; requires strong technical leadership to
  implement.
- **No resource/budget model.** Resource loading, contract sequencing, and
  field-office change management are out of scope.
- **Internal-only marking.** Any external-reference-architecture or
  shared-service path is an option to explore **after** SSA's own authorization
  is secured, through a formal release process — not a near-term action.

### Provenance note (why this doc is inbox-only)

By the repo's own SSOT doctrine (AGENTS.md — external facts must trace to a
source), the value statements here that are *judgments* rather than
*repo-derived facts* carry no external citation and would not survive promotion
to canon as written. That is appropriate: this is an `inbox/` working artifact,
not canon, and should stay there until (and unless) its claims are either
sourced or converted to assessed facts by an SCA.

---

## 6. Bottom-Line Value Judgment (Conditional)

The verdict is stated as a condition, not an assertion, because the value moves
materially on items still open:

> **If** a backup operator can regenerate the AR unaided (absorbability), **and**
> the OSCAL validation path is made to run, **and** the 29 rules reconcile to
> CR26 without a large unmapped remainder, **then** the AAN series is a high-value,
> unusually advanced modernization asset for SSA — already at
> authorization-package assembly, fit to SSA's estate, with a working evidence
> emitter most agencies lack. **Absent those,** it is a strong but
> single-team-dependent self-assessment whose realizable value is materially
> discounted and whose "assessor-ready" status is not yet demonstrated.

For SSA, the value is realized by closing those conditions and presenting the
package — not by authoring more books. For a peer agency, the corpus is a
serious reference implementation of application-aware networking + truth-plane
Zero Trust + automated ConMon, **provided** that agency treats the SSA specifics
as a template to re-derive and does not inherit the absorbability risk. (Rev. 1
claimed the series is "more implementable than most published federal reference
architectures"; that comparison is unsourced — this revision withdraws it
pending an actual survey.)

### Recommended next actions (priority order)

1. **Prove absorbability** — a named backup operator regenerates the AR and
   triages ScubaDrift dispositions end-to-end, unaided. Highest leverage.
2. **Make validation run** — fix the `oscal validate` stub (it must not exit 0
   as a no-op) and the `validate-ssp` POA&M defect, so a 3PAO gets a real check.
3. **Close the KSI reconciliation** (29 ADR-111 ↔ CR26 Moderate) and map the
   Release 5.2.0 deltas.
4. **Socialize** the Executive Summary, Gap Roadmap, and Ownership Model with
   CIO/OIS/AO as the ratification ask.
5. **Do not attach a dollar figure** until a costing exercise produces one; do
   not compare to other agencies' architectures without a survey.

---

*This document is an internal UIAO working artifact. It does not constitute an
authorization package, an appraisal, or an assessment. Judgments are advisory;
all control-closure and value claims are pending independent SCA/ATO review.*
