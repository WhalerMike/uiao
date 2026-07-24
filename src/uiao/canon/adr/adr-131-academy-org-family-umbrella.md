---
adr_id: adr-131
title: "UIAO Academy — Umbrella Learning Entry Point for the Org Family"
status: PROPOSED
decided: 2026-07-24
deciders: Michael Stratton
updated: 2026-07-24
next_review: 2027-01-24
review_trigger: UIAO_125 (Training Program) or UIAO_128 (Education Program) is substantially revised; a new operational expression joins the Org family; the OrgComp Training Program is re-scoped or re-homed; the Academy rebuild phases named in D4 complete (retire the under-construction banners and re-review this ADR's Consequences)
impact: "Re-anchors the UIAO Academy from the pre-Org-family UIAO_125/UIAO_128 presentation to an umbrella learning entry point over the three Org pillars — OrgPath (Governance), OrgComp (Compliance), OrgMod (Modernization) — plus a repo-facing Contributor path. Pillar curricula stay owned where they live: the Academy routes into the series-owned OrgComp Training Program rather than duplicating it, ending the 'two academies' ambiguity with one front door."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-131-academy-org-family-umbrella.html
---

# ADR-131: UIAO Academy — Umbrella Learning Entry Point for the Org Family

## Status

**PROPOSED** — 2026-07-24.

## Context

The UIAO Academy (`docs/academy/`) was built as the "rendered consumer view"
of two canon programs: UIAO_125 (Training Program — the Contributor and
Operator tracks) and UIAO_128 (Education Program — the comic-led learning
arc). That framing predates the Org-family reorganization of the published
site (PRs #1275, #1278, #1280), which made the site pillar-first: **OrgPath**
(Governance), **OrgComp** (Federal Organizational Compliance), and **OrgMod**
(Modernization) — three operational expressions of one substrate.

The Academy is the one top-level site section that never crossed that line.
Three problems follow:

1. **Framing drift.** The Academy teaches the substrate through raw
   UIAO_NNN specs and a contributor/operator split, while every adjacent
   section speaks the pillar language. A learner arriving from the navbar
   changes vocabulary the moment they enter the Academy.
2. **The "two academies" ambiguity.** The OrgComp Training Program (under
   `docs/customer-documents/orgcomp-series/OrgComp-Training-Program/`) is a
   maintained, series-owned two-track curriculum with labs, assessment
   rubrics, and a vendor training catalog. The Academy index papers over the
   overlap with a "two academies on this site" callout — a symptom, not a
   design. No ADR states which academy is the front door.
3. **Factual staleness.** The Academy's document-generation guide taught the
   Gemini "Nano Banana" image pipeline as current, a workflow retired by
   ADR-093 (committed Claude-authored SVG). PR #1347 stamped every Academy
   page under construction as Phase 0 of the rebuild this ADR governs.

## Decision

### D1 — The Academy is the umbrella learning entry point

The UIAO Academy becomes the site's single learning front door, organized
pillar-first. Its landing page presents four paths:

- **OrgPath (Governance)** — sequenced over the published OrgPath shelf:
  the orgpath-narrative reading sequence, the reference-architecture pages,
  the implementation guides, and the MACD-R / Closure Provenance doctrine.
- **OrgComp (Compliance)** — a routing path that hands off to the OrgComp
  Training Program (see D2).
- **OrgMod (Modernization)** — sequenced over the transformation series,
  the Intune + Azure Arc guides, the HRIT execution plan, and the Day-2 kit.
- **Contributor** — the repo-facing path for people working the substrate
  itself; the existing tier-1 tenant setup and adapter integration guides
  live here.

### D2 — Pillar curricula are owned where they live; the Academy routes

The OrgComp Training Program remains **series-owned**: its curriculum,
labs, rubrics, and vendor catalog stay under the orgcomp-series tree and
evolve with the series. The Academy's OrgComp path routes into it and
authors no parallel compliance curriculum. This is the general rule for any
pillar that grows its own curriculum: the Academy is an entry point and
sequencer over published material, never a second home for it. The "two
academies" framing is retired — one front door, pillar-owned curricula
behind it.

### D3 — UIAO_125 and UIAO_128 remain canon; the presentation re-anchors

This ADR changes the Academy's presentation, not the training canon.
UIAO_125's track definitions, completion criteria, and shared core remain
authoritative; the Contributor path carries UIAO_125 §1.2 forward
substantially unchanged, and the Operator track's substance redistributes
into the OrgPath and OrgMod paths (running the substrate against an
environment is what those pillars teach). UIAO_128's comic arc is retained
as optional orientation material, not the mandatory top of the funnel. If
the redistribution surfaces contradictions with UIAO_125/UIAO_128 text,
those are resolved by amending the specs through the normal canon change
process — not by the Academy silently diverging.

### D4 — Phased rebuild, honest at every step

The rebuild proceeds in the phases already begun, each phase a separate PR:

- **Phase 0 (done, PR #1347)** — every Academy page carries an
  under-construction banner; the retired Nano Banana guide carries a
  retired-workflow banner citing ADR-093.
- **Phase 2** — pillar-first rebuild of `academy/index.qmd` per D1.
- **Phase 3** — the per-pillar path pages (read / do / verify staging over
  existing published material).
- **Phase 4** — repair or retire the stale mechanics pages: the
  document-generation guide is rewritten for the ADR-093 SVG workflow or
  folded into the image-pipeline guide; every renamed or removed page gets
  a URL alias per the rebrand convention.

Banners come off a page only when its replacement content ships.

## Consequences

- One learning front door, in the same pillar vocabulary as the rest of the
  site; the navbar's "UIAO Academy" entry stops being the odd one out.
- The OrgComp Training Program gains an unambiguous charter: series-owned,
  Academy-routed. No duplicated curriculum to keep in sync.
- The OrgPath and OrgMod paths are curation over already-published
  material, which keeps the rebuild tractable and keeps the Academy true to
  its original doctrine of inventing no parallel curriculum.
- The contributor/operator page URLs survive as aliases even where the
  operator track's content redistributes, so external links keep resolving.
- Until Phases 2–4 land, the Academy remains banner-stamped; this ADR is
  the authority the banners implicitly reference.

## Date

2026-07-24
