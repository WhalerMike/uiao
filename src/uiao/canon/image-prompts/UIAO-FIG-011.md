---
id: UIAO-FIG-011
slug: evidence-fabric
title: "UIAO Evidence Fabric — Write Pipeline and Storage Tiers"
aspect: "1:1"
palette: ["#0D1B2E", "#1E8C8C", "#2E75B6", "#5A5A5A", "#FFFFFF"]
---

## Description

Architecture diagram of the UIAO Evidence Fabric write pipeline with
two-tier storage. Shows event ingestion, signature verification, Evidence
Fabric countersignature, hash-chain anchoring, the Active/Archive storage
tiers, and the Correlation Engine that serves correlation and diff
queries.

## Prompt

Technical architecture schematic in the UIAO federal-whitepaper style.
Dark navy (#0D1B2E) and teal (#1E8C8C), with mid-blue (#2E75B6) used
ONLY for the two storage cylinders. White background. 1:1 square
canvas with the diagram laid out horizontally.

CONSTRAINT (must be obeyed): Render EXACTLY 7 labeled visual elements
arranged as described below. Spell every label EXACTLY as quoted — the
word "queries" is spelled Q-U-E-R-I-E-S. The leftmost rendered element
MUST be node 1 ("Event Ingress"); do NOT draw any rectangle, box, or
shape to the left of node 1. Do NOT add decorative text, icons,
watermarks, or extra labels beyond those listed.

PIPELINE NODES (left-to-right horizontal sequence, the first 4 elements):

1. "Event Ingress"
2. "Signature Verifier"
3. "Evidence Fabric Countersigner"
4. "Hash Chain Writer"

STORAGE TIER (the next 2 elements, drawn as two database cylinders to
the right of node 4, side by side):

5. Left cylinder, larger, mid-blue (#2E75B6) fill: label "Active Storage"
   inside the cylinder, with a smaller annotation text "≤ 90 days"
   beneath the cylinder
6. Right cylinder, smaller than node 5, mid-blue (#2E75B6) fill: label
   "Archive Storage" inside the cylinder, with a smaller annotation
   text "3-7 year retention" beneath the cylinder

CORRELATION ENGINE (the 7th element, centered horizontally beneath
nodes 5 and 6):

7. Teal rectangle with white text label: "Correlation Engine"

VISUAL TREATMENT:

- Pipeline nodes 1, 2, 3, 4 are filled navy rectangles with rounded
  corners and white text labels.
- Node 4 has a small linked-hexagon pictogram inside the node (a chain
  of two or three hexagons) to suggest hash-chain anchoring.
- Cylinders 5 and 6 are mid-blue.
- Node 7 (Correlation Engine) is teal, sits below the two cylinders.

ALLOWED ARROWS AND ANNOTATIONS (the only text besides the 7 element
labels and the two retention annotations):

- Inbound arrow into node 1, label above: "adapter-signed governance
  events"
- Teal pipeline arrows: 1 to 2, 2 to 3, 3 to 4
- Annotation above the arrow between node 2 and node 3: "dedup"
- A teal arrow from node 4 forks into both cylinder 5 and cylinder 6
  (no annotation on the fork)
- Two short read arrows going DOWN, one from cylinder 5 and one from
  cylinder 6, both terminating at node 7
- Outbound arrow leaving node 7 going right off-canvas, label above:
  "correlation and diff queries"

STYLE: Clean engineering blueprint. White background. No people, no
photographs, no vendor logos, no padlock icons, no watermarks. The
leftmost rendered element is node 1; nothing renders to the left of it.

## Style notes

- Palette locked (see frontmatter). Mid-blue `#2E75B6` is used ONLY on
  the two storage cylinders.
- Aspect locked: 1:1.
- Clean engineering blueprint style.
- Publication-grade.

## History

- v1.0 (2026-05-07) — initial draft, fabric-trio pilot.
- v1.0 second render (2026-05-07) — first render produced "queriys"
  typo and a phantom empty rectangle at the left edge of the canvas.
  Prompt rewritten with explicit "leftmost element MUST be node 1"
  constraint and spelling callout for "queries".
