---
id: UIAO-FIG-010
slug: drift-fabric
title: "UIAO Drift Fabric — Detection Pipeline"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#D4A017", "#5A5A5A", "#FFFFFF"]
---

## Description

Architecture diagram of the UIAO Drift Fabric detection pipeline. Shows the
path from canonical state read, through delta comparison and drift
classification, to immutable Drift Record emission and HIGH/CRITICAL
escalation into the Governance Plane.

## Prompt

A 16:9 technical architecture schematic in the UIAO federal-whitepaper
style — dark navy (#0D1B2E) and teal (#1E8C8C), with a severity accent in
amber (#D4A017) reserved for HIGH/CRITICAL escalation, on a white
background — depicting the UIAO Drift Fabric detection pipeline.

Layout: a left-to-right pipeline of five labeled rectangular nodes
connected by directional arrows. From left to right:

1. **Truth Fabric State Reader** — entry node with an inbound arrow from
   an off-canvas Truth Fabric labeled "canonical state records".
2. **Drift Comparator** — pictogram of two overlapping documents with a
   delta (Δ) symbol between them; computes deltas between observed and
   canonical state.
3. **Drift Classifier** — central node, slightly larger than its
   neighbours; assigns drift type (DT-01 through DT-05) and severity
   (LOW / MODERATE / HIGH / CRITICAL). A small severity color legend sits
   beneath the node showing four chips: teal for LOW/MODERATE, amber for
   HIGH/CRITICAL.
4. **Evidence Fabric Writer** — emits immutable Drift Records via an
   outbound arrow on the right edge labeled "Drift Records →" pointing
   off-canvas toward an unseen Evidence Fabric (sibling diagram).
5. **Reconciliation Trigger** — branches off the Drift Classifier
   *upward* with an amber-highlighted arrow that escalates HIGH/CRITICAL
   drift to a "Governance Plane" component drawn in the upper-right
   corner of the canvas.

The HIGH/CRITICAL escalation path is visually distinct — amber arrow and
amber border on the Reconciliation Trigger node — versus the teal
horizontal pipeline arrows.

## Style notes

- Palette locked (see frontmatter). Navy `#0D1B2E` for primary node
  fills, teal `#1E8C8C` for the horizontal pipeline arrows, amber
  `#D4A017` reserved exclusively for HIGH/CRITICAL escalation visuals,
  neutral grey `#5A5A5A` for labels, white background.
- Aspect locked: 16:9.
- Clean engineering blueprint style — no photographs, no people, no
  vendor logos.
- Only baked text permitted: the five node labels, the severity legend
  chips (LOW / MODERATE / HIGH / CRITICAL), the escalation arrow label,
  the inbound/outbound pipeline labels, and the "Governance Plane"
  upper-right component label. No additional decorative text.
- Publication-grade, suitable for inclusion in OSCAL-adjacent
  deliverables.

## History

- v1.0 (2026-05-07) — initial draft, fabric-trio pilot for canonical
  image-pipeline routing of architecture diagrams.
