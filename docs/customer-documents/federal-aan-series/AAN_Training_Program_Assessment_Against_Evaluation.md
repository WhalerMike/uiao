---
title: "AAN Training Program — Assessment Against the External Evaluation"
subtitle: "Verifying each evaluation finding against the training-program tree at HEAD"
author: "Independent assessment (Claude Code, at author request)"
date: "2026-07-18"
---

> **What this is.** A point-by-point assessment of the **AAN Training
> Program** (`AAN-Training-Program/`, `Vol_V_*`, `boundary/`) **against the
> external evaluation** committed verbatim as
> `AAN_Training_Program_External_Evaluation.md` (2026-07-18, scored
> 8.7/10). For each evaluation finding this document records a **verdict**
> — *Confirmed / Partially addressed / Already addressed / Not reproduced*
> — backed by file-and-line evidence from the tree as it stands at branch
> HEAD. It changes no architecture; it grades the claims. The format
> follows `AAN_Series_Assessment_Against_Critique.md` (2026-07-13), which
> performed the same exercise for the series-level critique.
>
> **Review-medium note.** Internal evidence indicates the evaluation was
> performed against a **concatenated text/docx export**, not the rendered
> Quarto site: the reviewer states "figures are referenced but not
> embedded *here*," while the rendered training-program pages embed six
> figures with alt text (see Concern 6a). Where a finding is an artifact
> of the review medium rather than the source, the verdict says so —
> the files win.

## Scoring key

| Verdict | Meaning |
|---|---|
| **Confirmed** | The evaluation's finding reproduces against the files as stated; the recommended fix is absent. |
| **Partially addressed** | Part of the recommended fix is materially present; the remainder is a real gap. |
| **Already addressed** | The fix is materially present at HEAD; the evaluation overstates the gap. |
| **Not reproduced** | The finding does not reproduce against HEAD. |

## Scorecard

| # | Evaluation finding | Verdict | One-line status |
|---|---|---|---|
| 1a | No "Core AAN Pathway" for most learners | **Confirmed** | Both tracks walk all 20 books; no role-scoped reading subset exists anywhere |
| 1b | Progressive disclosure (briefs, quick-starts) | **Partially addressed** | Two-page Executive Brief is the series entry point; no "labs + mappings" quick-start |
| 1c | Modular certifications by plane | **Partially addressed** | Practitioner credential is per-module by design; no plane-scoped credentials |
| 2a | Recurring material repeated across books | **Partially addressed** | Slot/KSI data derives from adapter YAML (cannot drift); timeline prose still restated per page |
| 2b | Standardize book templates rigidly | **Already addressed** | All 20 module pages follow one fixed template — the exact section order the evaluation asks for |
| 2c | "Living Document" footer with version/changelog | **Partially addressed** | Living-program callout + shipped-item roadmap exist; pages stamp `date: today`, which defeats version pinning |
| 3 | `<engine>` placeholder under-explained | **Confirmed** | 12 training-program pages use `<engine>` in commands; none defines it or links the Evidence Contract that does |
| 4a | Tier labs (Fixture/Trial-Tenant/Product-Eval) with cost | **Already addressed** | F/T/P tier table, per-lab tier column, and cost notes all present; time estimates absent (minor) |
| 4b | More containerized/minimal fixtures | **Partially addressed** | DDI BIND/Kea container fixture + Tier-F B7/B8 labs exist; PIM/Sentinel/Purview are tenant-only by nature |
| 4c | "Bind the Evidence" step across all labs | **Partially addressed** | Present on the hub and 3 of 4 lab pages; absent from the PIM lab |
| 5 | B.1.x boundary content feels tacked-on | **Partially addressed** | The "promote to a reference with navigation" branch is done (`boundary/` subcategory); zero cross-links from books/modules |
| 6a | Figures referenced but not embedded | **Not reproduced** | Six figures embedded with alt text in the rendered pages; finding is a review-medium artifact |
| 6b | Make the KSI Matrix fillable/extractable | **Partially addressed** | Matrix data is machine-readable adapter YAML; no standalone extractable table ships with the program |
| 6c | More assessor/practitioner callout boxes | **Partially addressed** | Per-book "Pitfalls" sections serve the role; no per-section assessor callouts |
| 7a | Expand residual enterprise risks in Book 19 | **Already addressed** | Module objective + pitfall name mission/insider/physical/geopolitical risks outside KSI scope |
| 7b | Post-implementation KPIs beyond the rubric | **Confirmed** | No KPI/success-metric content anywhere in the program or Vol V |
| 7c | Note where alternative stacks fit | **Already addressed** | Catalog carries Palo Alto/Zscaler SASE, Tenable/Qualys ("alternative vuln-management stack"), BlueCat rows; engine neutrality is the series' design |

**Tally:** 3 Confirmed · 9 Partially addressed · 4 Already addressed ·
1 Not reproduced. The evaluation's structural instincts are sound — every
Confirmed finding is real — but roughly a third of its recommendations
describe things the program already ships, consistent with a review
performed on a flattened export that strips navigation, figures, and the
lab hub's tier machinery.

## Concern 1 — Scope & cognitive load

### 1a. "Core AAN Pathway" — **Confirmed**

No role-scoped reading subset exists. Track A walks all eight slots across
all 20 books (`AAN-Training-Program/compliance-track.qmd:48-162`, modules
A0–A8) and its capstone requires **all eight slots**
(`compliance-track.qmd:164-179`); Track B's structure is likewise
exhaustive. Greps for "core pathway," "minimum path," "fast track," and
"quick start" across `AAN-Training-Program/` and `Vol_V_*` return nothing.
The evaluation's proposed subset (Books 00, 01, 03–05, 10–11, 13, 19 +
selected labs) is a coherent spine — it feeds six of the eight slots
directly (all but slot 7/continuity/Book 14 and slot 8/training/Book 18)
and covers both capstone surfaces — and nothing at HEAD offers it.

### 1b. Progressive disclosure — **Partially addressed**

The series-level entry point already does this: the series index
(`index.qmd:25-27`) — "Start with the **two-page Executive Brief**, then
the Executive Summary" — and both `Vol_0_Book_00a_FedAAN_Executive_Brief.qmd`
and its dollar-savings docx variant exist
(`AAN-Training-Program/FedAAN_Executive_At_A_Glance.docx`,
`Vol_0_Book_00a_FedAAN_Executive_Brief_with_Dollar_Savings.docx`). The
evaluation's Next-Step 4 ("a Book 00 one-pager for leadership buy-in") is
therefore already shipped. What does **not** exist is the practitioner-side
quick start — a "just the labs + mappings" page that takes an engineer
from zero to a bound evidence artifact without reading the corpus.

### 1c. Modular certifications — **Partially addressed**

The credential model is closer to the ask than the evaluation credits:
**AAN Practitioner** requires the Track B capstone for **one module,
evidence-complete** (`Vol_V_Book_03_FedAAN_Assessment_Certification.qmd:214-219`)
— it is already modular at the module grain, and **AAN Assessor** already
plays the "full program" role the evaluation assigns to "AAN
Architect/Assessor." What is absent is the intermediate grain the
evaluation names: plane-scoped credentials (Identity, Telemetry/Detect,
Governance) that bundle several modules of one mission class.

## Concern 2 — Repetition & consistency

### 2a. Centralize recurring reference material — **Partially addressed**

The program's structural data is already centralized and
machine-derived: "Slot definitions, KSI categories, and NIST anchors come
from the adapter's mapping files — the same data the conformance pipeline
evaluates, so the curriculum cannot silently drift from the evidence
model" (`AAN-Training-Program/index.qmd:112-115`). But the *prose*
recurrence the evaluation names is real: the FedRAMP 20x timeline and
BOD 26-04 deadline are restated in at least
`AAN-Training-Program/index.qmd:128-129`,
`compliance-track.qmd:52-55`, `books/book-00.qmd:24-27`, and
`books/book-19.qmd:53-54` with no single SSOT anchor. This is the
training-program instance of series-critique Concern 7
(`AAN_Series_Assessment_Against_Critique.md:41` — "SSOTs declared but
bypassed," verdict *Still open*), and it remains open here too.

### 2b. Standardize templates — **Already addressed**

Every one of the 20 module pages follows one fixed template — Scope →
Learning objectives → Key concepts → Reading/Implementation sequence →
Compliance hooks → Labs → Pitfalls → Vendor training — which is the
*exact* section order the evaluation recommends ("Scope → Objectives →
Concepts → Sequence → Hooks → Labs → Pitfalls"). Verified against
`books/book-00.qmd:12-87` and `books/book-19.qmd:12-111`; the remaining
18 pages share the structure (uniform 89–123-line pages,
`books/book-*.qmd`). The recommendation describes the present state.

### 2c. Living-document footer / changelog — **Partially addressed**

The "living program" framing exists
(`AAN-Training-Program/index.qmd:20-27` callout) and the Expansion roadmap
(`AAN-Training-Program/index.qmd:158-191`) functions as a changelog — six
✅-marked shipped waves with dates. Two real gaps remain: (i) training
pages stamp `date: today` (`AAN-Training-Program/index.qmd:4`, all module
pages), so every
render re-dates the content and no page carries a stable content version
— the series books solved this with explicit Date Codes, and the training
pages did not inherit that discipline; (ii) there is no stated refresh
cadence tied to FedRAMP/BOD cycles, though the roadmap's "tracked in
ordinary PRs against this directory" (`index.qmd:160-161`) covers the
GitHub-contribution half of the ask.

## Concern 3 — Tooling & technical clarity — **Confirmed**

The evaluation's highest-leverage finding. `<engine>` appears in runnable
command blocks across **12** training-program pages (e.g.
`compliance-track.qmd:34-44`, `implementation-track.qmd:173-174`,
`labs/index.qmd:72`, `assessment-rubrics.qmd:24`,
`Vol_V_Book_04_FedAAN_Vendor_Training_Lab_Environments.qmd:213`) and **no
training page defines the token**. The definition exists one level up, on
the series index —
"The series is engine-neutral by design … it speaks to the **AAN Evidence
& Authorization Contract** … that any conformant evidence engine can
satisfy" (`index.qmd:29-34`, linking `AAN_Evidence_Contract_Spec.qmd`) —
but no training page links to it, and there is no tooling-stack note,
no sample output, and no fixture pointer for a learner who wants to run
the capstone "walk" (`compliance-track.qmd:164-179`) end-to-end. A new
reader hits `<engine> oscal ksi-ar` in a bash block with no way to resolve
it. The Tier-F fixture row (`labs/index.qmd:21` — "Nothing but this repo
and Python") gestures at the evaluation's "minimal fixture/repo" ask but
never says *which* commands become runnable or against what sample data.

## Concern 4 — Labs & accessibility

### 4a. Explicit lab tiers with cost — **Already addressed**

`labs/index.qmd:17-23` is a three-tier table — **Tier F — fixture / Tier
T — trial tenant / Tier P — product eval** — matching the evaluation's
proposed "Fixture/Trial-Tenant/Product-Eval" naming exactly; each lab-page
row carries its tier (`labs/index.qmd:51-56`) and a dedicated Cost notes
section covers E5 trials, Sentinel ingestion, and vendor evals
(`labs/index.qmd:40-47`). The only sliver not present is per-lab **time**
estimates. This finding is best read as validation that the tiering
(shipped in the labs wave, `index.qmd:171-177`) was the right design —
the reviewer's export evidently did not carry it.

### 4b. More containerized fixtures — **Partially addressed**

The DDI lab the evaluation praises is the pattern
(`labs/lab-b1-ddi.qmd` — BIND/Kea containers, teardown
`docker rm -f ddi-bind`), and modules B7/B8 are deliberately Tier-F —
"document- and CI-shaped … they run anywhere" (`labs/index.qmd:58-64`).
The PIM, Sentinel, and Purview labs remain trial-tenant-only, which is
inherent to their SaaS control planes; the honest containerizable
remainder is a fixture path for the *evidence side* of those labs (seeded
sign-in/audit exports a Tier-F learner could bind without a tenant).

### 4c. Bind-the-evidence step across all labs — **Partially addressed**

"The common final step — bind the evidence" is the closing section of the
lab hub (`labs/index.qmd:66-75`) and three of the four lab pages end by
regenerating verdicts and scoring against a slot rubric
(`lab-b1-ddi.qmd`, `lab-b6-sentinel.qmd`, `lab-b6-purview.qmd`). The
exception is exactly one file: **`labs/lab-b5-pim.qmd` names its slot-01
artifacts and scores against the slot 1/5 rubrics but never regenerates
verdicts** — the `<engine> oscal ksi-ar` close the other three labs end
with is missing. One-line fix.

## Concern 5 — GCC-Moderate boundary content — **Partially addressed**

The evaluation offers two alternative remedies, and the second is already
done: the boundary model is promoted to its own navigable subcategory —
`boundary/index.qmd` ("B. Boundary + Authorization," UIAO_171) with the
B.1 model and all three leaves (B.1.1 three-way TIC 3.0 × ZTMM ×
FedRAMP 20x conflict, B.1.2 Teams Phone under TIC 2.0, B.1.3 in-boundary
analytics rebuild) enumerated at `boundary/index.qmd:28-36`. The first
remedy — integration into the relevant main books — is where the
"tacked-on" feel survives: greps show **zero references** from
`AAN-Training-Program/` or any module page into `boundary/`; the
network/telecom modules the evaluation names (`books/book-05.qmd`,
`books/book-06.qmd`) do not mention B.1.2, and the telemetry modules
(11–13) do not reference the B.1.3 rebuild patterns. The material is
navigable top-down but undiscoverable from the curriculum that needs it.

## Concern 6 — Polish & usability

### 6a. Figures not embedded — **Not reproduced**

The rendered program embeds six figures with alt text: the program map and
evidence flow (`AAN-Training-Program/index.qmd:44`, `:141`), the Track A
slot-book matrix (`compliance-track.qmd:46`), the rubric ladder
(`assessment-rubrics.qmd:30`), the lab tiers (`labs/index.qmd:25`), and
the Vol V credential panel
(`Vol_V_Book_03_FedAAN_Assessment_Certification.qmd:214`). The reviewer's
own phrasing — "not embedded **here** … ensure … in the final .docx/PDF"
— places the finding in the export medium, not the source. The actionable
residue is a build-pipeline check that figures survive the docx bundle
(`BUILD-DERIVATIVES.md` / `scripts/build_aan_download.py`), not a source
change.

### 6b. KSI Matrix fillable/extractable — **Partially addressed**

The matrix's *data* is already extractable — the slot/KSI/anchor rows
derive from `fedramp_aan_catalog/mappings/` YAML (`index.qmd:112-115`),
and Vol V Book 03 makes reconstructing the matrix the exam for both
credentials (`Vol_V_Book_03…:214-219`). What does not exist is the
learner-facing artifact the evaluation asks for: a standalone
fillable/blank matrix (CSV or table) a candidate can complete offline,
shipped alongside the rubrics.

### 6c. Assessor/practitioner callouts — **Partially addressed**

Every module page carries a "Pitfalls the book calls out" section (e.g.
`books/book-00.qmd:74-81`, `books/book-19.qmd:94-105`) — functionally the
"practitioner takeaway" box — and the program pages use Quarto callouts
for scope and provenance (`index.qmd:9-27`, `index.qmd:73-80`). The
"why this matters to an assessor" companion voice exists only in Track A's
capstone framing ("deliberately, the skeleton of a ConMon narrative an
assessor could read," `compliance-track.qmd:176-179`), not per-module.

## Concern 7 — Minor gaps

### 7a. Residual enterprise risks in Book 19 — **Already addressed**

The module page carries it twice: learning objective "Map OSCAL AR risk
entries into the PM-9 risk register and **name residual risks outside KSI
scope**" (`books/book-19.qmd:34-36`) and lead pitfall "Zero open KSI risks
does not eliminate enterprise risk — **mission, insider-threat, physical,
and geopolitical supply-chain risks sit outside KSI scope**"
(`books/book-19.qmd:96-98`) — the same three categories the evaluation
asks for, plus one. The underlying manuscript
(`Vol_IV_Book_06_FedAAN_Authorization_Package_ConMon.qmd`) is the place
any *further* expansion would land, but the training program already
teaches the point.

### 7b. Post-implementation KPIs — **Confirmed**

Greps for KPI, success-metric, orphan-account, and phishing-click content
across `AAN-Training-Program/` and all five `Vol_V_*` books return
nothing. The rubrics measure *learner* competency
(`assessment-rubrics.qmd` — the four-level ladder) and the program
measures *evidence* freshness (Book 19's per-slot rules); neither defines
operational outcome KPIs (orphan-account rate, KEV remediation SLA
adherence, phishing-click reduction). The evaluation's examples map
cleanly onto existing evidence surfaces — Book 04 (joiner-mover-leaver),
Book 11 (KEV), Book 18 (training/phishing) — so the data sources already
exist; the KPI definitions do not.

### 7c. Alternative-stack notes — **Already addressed**

The vendor catalog explicitly carries the alternatives the evaluation
asks for, with rationale: Palo Alto "SASE (Prisma-track) coursework where
Palo Alto is the SASE vendor" (`vendor-training-catalog.qmd:64`), Zscaler
plus its federal Government Academy (`:65`, `:108`), Tenable —
"alternative vuln-management stack for agencies not on Defender VM"
(`:83`) — and Qualys "same alternative-stack rationale" (`:84`), and
BlueCat as the DDI alternative (`:54`; also `labs/index.qmd:23,46`).
Structurally, the "fit via adapters" mechanism the evaluation requests
*is* the series' engine-neutral design (series `index.qmd:29-34`). The
Microsoft
tilt of the reference implementation is acknowledged as such and priced
in.

## Priority actions (from the Confirmed / cheapest-Partial findings)

1. **Define `<engine>` where it is used** (Concern 3) — a short
   "tooling stack" note on the program index and both track pages: what
   the token stands for, a link to `AAN_Evidence_Contract_Spec.qmd`, the
   three commands the capstones need, and what Tier F actually runs.
   Highest leverage; pure addition.
2. **Close the PIM lab like the other three** (4c) — add the
   bind-the-evidence step and slot-1 rubric pointer to
   `labs/lab-b5-pim.qmd`. One-file consistency fix.
3. **Cross-link the boundary leaves** (5) — Book 05/06 modules →
   B.1.1/B.1.2; Books 11–13 modules → B.1.3. A sentence each; converts
   "tacked-on" into "integrated" without moving anything.
4. **Publish the Core AAN Pathway** (1a) — a section on the program
   index naming the evaluation's spine (00, 01, 03–05, 10–11, 13, 19 +
   the four labs) with its slot coverage stated, leaving both full tracks
   as the credential path.
5. **Add outcome KPIs** (7b) — a short block in Book 19's module (or the
   rubrics page) defining post-implementation KPIs bound to existing
   evidence surfaces.
6. **Stabilize page dating** (2c) — replace `date: today` with explicit
   Date Codes on the training pages, matching the series books'
   convention.

Items 6a (docx figure survival) and 6b (blank matrix artifact) are build
and packaging work in `BUILD-DERIVATIVES.md` scope, not source-tree gaps.
