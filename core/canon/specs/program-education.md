---
document_id: UIAO_128
title: "UIAO Education Program — Narrative-Led Agency Onboarding"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-17"
updated_at: "2026-04-17"
boundary: "GCC-Moderate"
---

# UIAO Education Program

Narrative-led agency onboarding. This program is distinct from
UIAO_125 (Training): **Training teaches how to use and contribute
to the substrate; Education builds the conceptual mental model that
makes the training stick.** It is aimed at decision-makers,
auditors, and new-to-UIAO agency staff who need to understand
*why* the substrate is shaped the way it is before they consume the
how.

---

## 1. Audience

Both internal and external, with the external case as the primary
driver.

- **External (primary)** — agency CIOs, CISOs, compliance leads,
  new program staff, incoming auditors. First contact with UIAO.
- **Internal (secondary)** — new contributors during onboarding
  week; anyone joining a cross-team project that touches UIAO but
  is not writing canon.

---

## 2. Format

Narrative-first, diagram-anchored. The program is led by the
**UIAO narrative comics** (the illustrated series under
`docs/publications/series-assets/`), which render each core
abstraction into a single legible image. Each module pairs one
comic with one short written walkthrough in the corresponding
narrative page.

### 2.1 The comic-led modules

| Module | Comic asset | Concept |
|---|---|---|
| The Governance OS | `UIAO-Governance-OS-Overview.jpg` | Why UIAO is an *OS for governance*, not a scanner or a doc generator |
| The Canonical Object | `UIAO-Canonical-Object-Record.jpg` | How an object gets one canonical record — the SSOT anchor |
| The Unified Environment Map | `UIAO-Unified-Environment-Map.jpg` | How adapters collapse many vendor surfaces into one map |
| Provenance | `UIAO-Provenance-Chain.jpg` | Why every artifact traces back to a canonical source |
| The Modernization Lifecycle | `UIAO-Modernization-Lifecycle.jpg` | How a modernization runs end-to-end through UIAO |
| Address Governance | `UIAO-Address-Governance-Flow.jpg` | The directory / IPAM flow formerly in GOS |
| Drift Detection | `UIAO-Drift-Detection-Loop.jpg` | The closed loop: scan → classify → remediate |
| Drift Remediation | `UIAO-Drift-Remediation-Path.jpg` | How a finding becomes a POA&M item and then a closed ticket |

### 2.2 Written walkthrough

Each module has a paired `docs/narrative/program-education.qmd`
section (or, for larger modules, an expanded page under
`docs/narrative/`) that walks the reader through the comic,
grounds each element in the canon, and closes with one concrete
question the reader should now be able to answer.

### 2.3 Session format

- **90-minute facilitated walkthrough** for agency kickoff. One
  comic per ~10 minutes, with Q&A between.
- **Self-serve written path** for anyone who cannot attend live.
  The written pages are sufficient on their own.
- **Auditor briefing** — a 45-minute condensed variant that runs
  only the Provenance, Drift Detection, and Drift Remediation
  modules.

---

## 3. Learning Arc

The program is not a feature tour. It builds a mental model in a
specific order:

1. **Governance is a system** — not a report, not a checklist.
2. **Identity is the primitive** — everything the system reasons
   about attaches to a canonical object.
3. **Maps replace inventories** — adapters produce a unified
   environment map, not a set of spreadsheets.
4. **Provenance is non-negotiable** — every derived artifact
   names its canonical source and version.
5. **Modernization is a lifecycle** — not a project. UIAO runs it
   end-to-end.
6. **Drift is the feedback signal** — the substrate knows when
   reality has diverged from canon, and it tells you in a
   classified, prioritized form.

A learner who has internalized these six ideas can then
productively enter the Training program (UIAO_125) and pick the
Operator or Contributor track.

---

## 4. Materials

All materials are canon-anchored and live inside the substrate:

- Comics — `docs/publications/series-assets/*.jpg`
- Walkthrough pages — `docs/narrative/program-education.qmd` and
  its expansions
- Glossary — `docs/docs/glossary.qmd`
- Status page — `docs/docs/substrate-status.qmd`
- This document — the syllabus and canonical index

No material required for this program lives outside the repository.

---

## 5. Assessment

Agency onboarding completion is demonstrated by a short written
self-assessment in which the learner answers, in their own words,
the six questions at the close of the learning arc (§3). The
self-assessment is not scored; it is the artifact that marks
readiness to enter the Operator track of UIAO_125.

---

## 6. Maintenance

When a new comic is published, it is added to the catalog in §2.1
in the same PR, together with its paired walkthrough. When a
canon concept is renamed or retired, the affected comic and
walkthrough are updated; otherwise a DRIFT-PROVENANCE finding is
raised against the education materials.

---

## 7. Cross-References

- UIAO_001 — Single Source of Truth
- UIAO_003 — Adapter Segmentation Overview
- UIAO_101 — Platform Overview
- UIAO_125 — Training Program (the how that follows the why)
- UIAO_126 — Test Plans Program
- UIAO_127 — Project Plans Program
- UIAO_200 — Substrate Manifest
- `docs/narrative/UIAO-Narrative-Layer.md` — narrative constructs
  for the broader comms layer
