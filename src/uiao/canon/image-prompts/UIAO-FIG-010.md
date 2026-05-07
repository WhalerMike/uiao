---
id: UIAO-FIG-010
slug: drift-fabric
title: "UIAO Drift Fabric — Detection Pipeline"
aspect: "1:1"
palette: ["#0D1B2E", "#1E8C8C", "#D4A017", "#5A5A5A", "#FFFFFF"]
---

## Description

Architecture diagram of the UIAO Drift Fabric detection pipeline. Shows
the path from canonical state read, through delta comparison and drift
classification, to immutable Drift Record emission and HIGH/CRITICAL
escalation into the Governance Plane.

## Prompt

Technical architecture schematic in the UIAO federal-whitepaper style.
Dark navy (#0D1B2E) and teal (#1E8C8C), with amber (#D4A017) used ONLY
for HIGH/CRITICAL escalation visuals. White background. 1:1 square
canvas with the diagram laid out horizontally.

CONSTRAINT (must be obeyed): Render EXACTLY 5 labeled nodes in a
left-to-right horizontal pipeline, plus ONE additional node
("Governance Plane") in the upper-right corner of the canvas. Spell
every label EXACTLY as quoted below — no typos. The word "CRITICAL"
is spelled C-R-I-T-I-C-A-L. The word "Fabric" is spelled F-A-B-R-I-C
(not "Fabrier"). Node 5 is "Reconciliation Trigger" (not "Writer").
Do NOT add decorative text, icons, watermarks, or extra labels beyond
those explicitly listed.

PIPELINE NODES (left to right):

1. "Truth Fabric State Reader"
2. "Drift Comparator"
3. "Drift Classifier"
4. "Evidence Fabric Writer"
5. "Reconciliation Trigger"

CORNER NODE (upper-right of canvas):

6. "Governance Plane"

VISUAL TREATMENT:

- All pipeline nodes are filled navy rectangles with rounded corners and
  white text labels.
- Node 3 ("Drift Classifier") is centered horizontally and slightly
  larger than its neighbours.
- Beneath node 3, render a small horizontal severity legend with FOUR
  distinct chips — each chip is its own colored rounded rectangle with
  the chip's text label inside:
    - Teal chip with white text: "LOW"
    - Teal chip with white text: "MODERATE"
    - Amber chip with dark text: "HIGH"
    - Amber chip with dark text: "CRITICAL"
- Node 6 ("Governance Plane") is a navy rectangle with an amber border
  (no fill change) to indicate it is the escalation target.

ALLOWED ARROWS AND ANNOTATIONS (the only text besides the 6 node labels
and 4 severity chips):

- Inbound arrow into node 1, label above: "canonical state records"
- Teal pipeline arrows: 1 to 2, 2 to 3, 3 to 4, 4 to 5
- Amber-colored arrow from node 5 going UP to node 6 (Governance
  Plane), label above the arrow: "HIGH/CRITICAL escalation"
- Outbound arrow leaving node 4 going right off-canvas, label above:
  "Drift Records"

STYLE: Clean engineering blueprint. White background. No people, no
photographs, no vendor logos, no padlock icons, no watermarks.

## Style notes

- Palette locked (see frontmatter). Amber `#D4A017` is used ONLY on the
  HIGH/CRITICAL escalation arrow, the HIGH and CRITICAL severity chips,
  and the Governance Plane border.
- Aspect locked: 1:1.
- Clean engineering blueprint style.
- Publication-grade.

## History

- v1.0 (2026-05-07) — initial draft, fabric-trio pilot.
- v1.0 second render (2026-05-07) — first render produced typos
  ("Fabrier", "CRITCIAL"), labeled node 5 as "Reconciliation Writer"
  instead of "Trigger", and rendered only 2 severity chips instead of
  4. Prompt rewritten with explicit node count, quoted labels, spelling
  callouts, and explicit four-chip severity legend.
