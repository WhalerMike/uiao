---
id: UIAO-FIG-013
slug: drift-engine-six-phase-loop
title: "Drift Detection Engine — Six-Phase Loop and Severity Ladder"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#2E75B6", "#5A5A5A", "#FFFFFF"]
---

## Description

Architecture diagram of the UIAO Drift Detection Engine's six-phase
control loop (Snapshot → Compare → Classify → Alert → Remediate →
Verify), with the five drift categories fanning out from the Classify
stage and a severity-to-SLA ladder hanging off the Alert stage. Designed
to accompany the Drift Walk-through explainer in the modernization
canon.

## Prompt

A 16:9 technical architecture schematic in the UIAO federal-whitepaper
style — dark navy (#0D1B2E) and teal (#1E8C8C) with a mid-blue (#2E75B6)
accent for the Evidence Fabric handoff on a white background —
depicting the Drift Detection Engine control loop.

Layout: a horizontal six-stage pipeline along the top, a fan-out of five
drift-category tiles below the third stage, and a severity ladder on
the right side connected to the fourth stage.

1. **Top row — the six-phase loop** — six rounded rectangles arranged
   left-to-right with teal arrows between them:
   1. **Snapshot** — small camera/Microsoft-Graph icon; label "Microsoft
      Graph state pull".
   2. **Compare** — small diff pictogram; label "diff vs. canonical
      baseline".
   3. **Classify** — small sorter/funnel pictogram; this node has five
      teal arrows fanning out downward to the category tiles described
      below.
   4. **Alert** — small bell pictogram; this node has one teal arrow
      exiting to the right into the severity ladder, AND a mid-blue
      (#2E75B6) arrow pointing down-right into a small Evidence Fabric
      cylinder labeled "Evidence Fabric (UIAO-FIG-011)".
   5. **Remediate** — small wrench pictogram; label "Execution
      Substrate" beneath.
   6. **Verify** — small checkmark/loop pictogram; a long teal return
      arrow loops back from the right edge of Verify, over the top of
      the diagram, to re-enter the left edge of Snapshot — drawn as a
      gentle arc so it reads as "re-scan".

2. **Lower middle — five drift category tiles** — five smaller rounded
   rectangles arranged in a row beneath the Classify node, each
   connected upward to Classify by a thin teal arrow. From left to
   right:
   - **Schema Drift** — P1 badge in the top-right corner of the tile.
   - **Value Drift** — P2 badge.
   - **Hierarchy Drift** — P1 badge.
   - **Orphan Drift** — P3 badge.
   - **Phantom Drift** — P3 badge.
   The P-badges are small filled circles in teal with white text.

3. **Right column — severity ladder** — a vertical four-rung ladder to
   the right of the Alert node, connected to it by a teal arrow labeled
   "DriftFinding". Top-to-bottom rungs, each a small rounded rectangle:
   - **P1 Critical** — "Halt pass · Board L3+"
   - **P2 High** — "Manager · L2 at 100% SLA"
   - **P3 Medium** — "Standard ticket · L1 at 75%"
   - **P4 Low** — "Logged for trend"
   The four rungs are vertically stacked, equal-sized, with a faint
   neutral-grey `#5A5A5A` vertical guide running through their left
   edges to imply ladder continuity.

4. **Evidence Fabric handoff** — small mid-blue (#2E75B6) cylinder
   labeled "Evidence Fabric (UIAO-FIG-011)" positioned below-right of
   the Alert node. The arrow from Alert into this cylinder carries the
   label "hash-chained, immutable".

## Style notes

- Palette locked (see frontmatter). Navy `#0D1B2E` for primary loop
  node fills and category tiles, teal `#1E8C8C` for arrows / P-badges /
  pictograms, mid-blue `#2E75B6` reserved exclusively for the Evidence
  Fabric handoff arrow and cylinder, neutral grey `#5A5A5A` for the
  severity ladder guide line and label text, white background.
- Aspect locked: 16:9.
- Clean engineering blueprint style — no photographs, no people, no
  vendor logos beyond the Microsoft Graph wordmark/icon on the Snapshot
  node.
- Only baked text permitted: the six loop labels (Snapshot, Compare,
  Classify, Alert, Remediate, Verify); the five category labels
  (Schema Drift, Value Drift, Hierarchy Drift, Orphan Drift, Phantom
  Drift); the four severity-rung labels (P1 Critical · Halt pass ·
  Board L3+, P2 High · Manager · L2 at 100% SLA, P3 Medium · Standard
  ticket · L1 at 75%, P4 Low · Logged for trend); the inter-node arrow
  annotations (Microsoft Graph state pull, diff vs. canonical baseline,
  DriftFinding, hash-chained immutable, re-scan); and the Evidence
  Fabric cylinder label. No additional decorative text.
- Publication-grade, suitable for inclusion in the modernization canon
  and customer-facing OrgPath drift deliverables.

## Renders into

- `docs/modernization/drift-walkthrough.qmd` — the explainer this
  figure illustrates.
- `src/uiao/canon/UIAO_163_Drift_Detection_Engine_Specification.md` —
  canonical engine spec reference image.

## History

- v1.0 (2026-05-11) — initial draft authored to accompany the Drift
  Walk-through explainer; visualizes the six-phase loop, the five drift
  categories with severity badges, the severity-to-SLA ladder, and the
  Evidence Fabric hand-off.
