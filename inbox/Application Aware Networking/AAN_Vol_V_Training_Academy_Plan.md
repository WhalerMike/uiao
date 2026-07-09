# AAN Series Expansion Plan — Volume V: Training & Certification (the Academy)

> Status: DRAFT for author review · Surface: `inbox/` (not canon)
> Scope: `inbox/Application Aware Networking/` — new **Volume V**
> Companion to: `AAN_Series_Build_Plan.md` (the 00–19 → volume restructure) and
> `AAN_Series_Expansion_Plan_Substrate_Accreditation.md` (Vols I–IV substrate)
> Source material: `inbox/Application Aware Networking/AAN-Training-Program/`
> (the staged 20-book training curriculum, relocated from the docs/ website)

## 1. Objective

Fold the AAN Training Program into the series as its enablement volume:
**Volume V — Training & Certification.** Volumes 0–IV build the system;
Volume V builds the people who implement, operate, and attest it — and produces
the *certification evidence* that closes the training slot (slot 8, KSI-CED) the
authorization package depends on.

The staged `AAN-Training-Program/` folder holds the raw curriculum (a program
charter, two tracks, assessment rubrics, a vendor catalog, lab setups, and 20
per-book module summaries) authored as website pages. This plan **expands that
curriculum to full manuscript depth** and restructures it into the volume shape
every other volume uses (a `Book_00` Overview plus themed content books, each
with a deck spec and an authorities table), so it reads as Volume V of the
series rather than as a companion website.

The unifying editorial thesis for the volume: **a control the series closes is
not closed until someone can build the mechanism, land its evidence, and prove
they can trace it — and that competency is itself an evidence-producing control
(AT-2/AT-3, KSI-CED).** Volume V teaches the other volumes *and* is itself one
of their closure paths.

## 2. How Volume V Fits the Series

Volume V is the only volume that **depends on all of the others** — it teaches
them. It **produces** two things the rest of the series needs:

1. **Trained operators** who can execute Volumes I–IV (the implementation track)
   and assessors who can trace book → control → KSI → evidence (the compliance
   track).
2. **The training-effectiveness evidence** (`training-effectiveness-record`
   JSON) that Volume IV's Authorization Package & ConMon book (Vol IV Book 06)
   freezes into the OSCAL bundle as the slot-8 / KSI-CED closure.

Truth is separated from enforcement here too: the **certification record is a
truth-plane artifact** (it attests competency and feeds the KSI pipeline); the
**courses and labs are enforcement-plane** (re-platformable per vendor — the
realization layer of Theme F). Remove Volume V and Volumes I–IV still stand as
documents, but the program has no defined path from "the books exist" to
"the workforce closes the controls and the training KSI evaluates."

## 3. Doctrine Themes as Teaching Lenses

Volume V does not add a theme; it teaches the existing six (Build Plan §2 A–E,
Expansion Plan §2 F) as pedagogy:

- **Theme A — Closure Necessity** becomes the compliance track's core exercise:
  for each slot, state *why no alternate mechanism closes the control.*
- **Theme B — "DIA Fixes Nothing"** and **Theme D — Functional Planes** frame
  the implementation track's sequencing (name → identify → transport → enforce).
- **Theme C — ADC/Proxy Dissolution** and **Theme F — Accreditation Substrate**
  are the vendor-catalog book's organizing logic: one mechanism, N accredited
  products.
- **Theme E — Conformance-Tooling Coverage Gap** is the volume's spine: the
  **10-of-29** split (ScuBA rules vs. architecture-bound evidence slots) is the
  capstone's central argument and the certification exam's answer key
  (the KSI Closure Necessity Matrix, Vol IV Book 06 §appendix).

## 4. Volume V Book Map

| Book | Title | Role |
|---|---|---|
| **Vol V Book 00** | Training & Certification — Volume V Overview | The academy's purpose, the two-track model, and the 10-of-29 thesis that a workforce — not tooling — authors the evidence state |
| **Vol V Book 01** | The Compliance Track | The eight evidence slots taught as curriculum: book → NIST control → FedRAMP 20x KSI → evidence, with the eight-slot capstone |
| **Vol V Book 02** | The Implementation Track | Building the Vol I–IV architectures and *landing the evidence* Track A consumes; the lab exercises as worked builds |
| **Vol V Book 03** | Assessment, Rubrics & Certification | The four-level rubric ladder, the eight-slot-walk capstone, and the KSI Closure Necessity Matrix as the certification exam |
| **Vol V Book 04** | Vendor Training & Lab Environments | The realization layer (Theme F): external courses mapped per volume, and scripted fixture/tenant/eval lab environments |

: Volume V — Training & Certification

The 20 per-book module summaries in the staged folder are **not** promoted to 20
manuscripts — that would duplicate Volumes 0–IV. They are absorbed as reference
tables/appendices inside Books 01–02 (each maps to the volume/book it teaches).

## 5. Per-Book Deliverable Set

Every book lands the standard series artifact set:

- `Vol_V_Book_NN_FedAAN_<Title>.qmd` — the manuscript (content books at series
  depth; Book 00 at overview depth, ~75 lines).
- `specs/Vol_V_Book_NN.yaml` — the deck spec consumed by
  `uiao generate aan-deck` (schema: `src/uiao/generators/aan_deck.py`).
- `authorities/authorities-book-<slug>.md` — the authority/source table (content
  books only).
- Figures per ADR-093 committed-SVG house style where a book needs them
  (the staged `tp-fig-*` set is re-homed and re-captioned into Books 01–03).

Source mapping from the staged curriculum:

| Staged source | Lands in |
|---|---|
| `index.qmd` (charter) | Vol V Book 00 (overview) + Book 01 front matter |
| `compliance-track.qmd` + the A-module content | Vol V Book 01 |
| `implementation-track.qmd` + `labs/**` | Vol V Book 02 |
| `assessment-rubrics.qmd` | Vol V Book 03 |
| `vendor-training-catalog.qmd` + lab tiers | Vol V Book 04 |
| `books/book-00…19.qmd` (module summaries) | Reference appendices in Books 01–02 |

## 6. Execution Phases

Each phase lands as its own commit/PR so review is per-phase, not one monolith.

| Phase | Work | Gate |
|---|---|---|
| **0** | This plan reviewed; book map + volume theme confirmed | Author sign-off |
| **1** | `Vol_V_Book_00` Overview + `specs/Vol_V_Book_00.yaml` (this wave) | Renders clean; matches overview template |
| **2** | `Vol_V_Book_01` Compliance Track (full manuscript + spec + authorities) | Slot → control → KSI chains verified against the mappings |
| **3** | `Vol_V_Book_02` Implementation Track (+ labs as worked builds) | Every module ends in a bindable evidence artifact |
| **4** | `Vol_V_Book_03` Assessment/Certification + the KSI Closure Necessity Matrix | KSI counts reconcile with Vol IV Book 06 and the roadmap |
| **5** | `Vol_V_Book_04` Vendor Training & Labs | Vendor rows re-verified by link-check; Theme F framing |
| **6** | Companion updates (§8); retire the staged `AAN-Training-Program/` folder once its content is fully absorbed | Grep audit: no orphaned staged references |

## 7. Consistency Rules (apply to every Volume V edit)

1. **No organizational owner names.** Functions and planes only (Theme D). Naming
   vendors/products/courses is fine (Theme F, the realization layer); assigning
   *who in the org runs them* is not.
2. **Every "required" is falsifiable.** The compliance track teaches necessity as
   control-text/physics/protocol argument, never as adjective.
3. **Numbers reconcile.** The 10-of-29 coverage split, the 29 CR26 KSIs, and the
   eight evidence slots must match Vol 0 Book 00, Vol IV Book 06, and the roadmap
   in every commit that cites them.
4. **Teach the series, don't restate it.** Books 01–02 reference the Vol I–IV
   books by their volume/book coordinates; they do not re-derive their content.
5. **Diagrams per ADR-093.** Committed house-style SVG; PNG is a build artifact.

## 8. Companion Updates

- **Vol 0 Book 00 (Executive Summary):** add Volume V to the series map and the
  volume-overview cross-references; note that the training slot (slot 8) is
  taught and evidenced here.
- **Vol IV Book 06 (Authorization Package & ConMon):** cross-reference Vol V
  Book 03 as the home of the KSI Closure Necessity Matrix / certification exam.
- **Staged folder:** once Books 00–04 absorb it, remove
  `inbox/Application Aware Networking/AAN-Training-Program/` (Phase 6) so the
  volume is the single source; until then it stays as the working source and is
  excluded from link-check (already in place).

## 9. Open Items for Author Decision

1. Volume theme name: **"Training & Certification"** (this plan's assumption) vs.
   "Enablement & Certification" or "The Academy."
2. Book count: five (Book 00 + four content books) as mapped, vs. splitting the
   vendor catalog and labs into two books (→ six).
3. Whether the certification is a named credential (e.g., "AAN Practitioner /
   Assessor") the volume should define, or left as a competency rubric only.
