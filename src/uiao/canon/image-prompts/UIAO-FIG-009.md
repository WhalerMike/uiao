---
id: UIAO-FIG-009
slug: truth-fabric
title: "UIAO Truth Fabric — Claim Intake Pipeline"
aspect: "1:1"
palette: ["#0D1B2E", "#1E8C8C", "#2E75B6", "#5A5A5A", "#FFFFFF"]
---

## Description

Architecture diagram of the UIAO Truth Fabric claim intake pipeline. Shows
the path from adapter-signed Canonical Claim submission through schema
validation, signature verification, identity anchoring, and canonical state
storage, with downstream interfaces to the Control Mapping Engine and the
Drift Fabric.

## Prompt

Technical architecture schematic in the UIAO federal-whitepaper style.
Dark navy (#0D1B2E) and teal (#1E8C8C) on a white background. 1:1
square canvas with the diagram laid out horizontally and white margin
top and bottom.

CONSTRAINT (must be obeyed): Render EXACTLY 7 labeled nodes in a
left-to-right horizontal pipeline. Spell every label EXACTLY as quoted
below — no typos, no abbreviations, no spelling variants. The word
"Canonical" is spelled C-A-N-O-N-I-C-A-L. The word "queries" is
spelled Q-U-E-R-I-E-S. Do NOT add decorative text, padlock icons,
anchor icons, watermarks, or any extra labels beyond those explicitly
listed. Do NOT render any parenthetical guidance from this prompt as
visible text in the image.

NODES (left to right):

1. "Claim Ingress API"
2. "Schema Validator"
3. "Signature Verifier"
4. "Identity Anchoring Engine"
5. "Canonical State Store"
6. "Control Mapping Engine"
7. "Drift Fabric Interface"

VISUAL TREATMENT:

- Nodes 1, 2, 3, 4, 6, 7 are filled navy rectangles with rounded corners
  and white text labels.
- Node 5 ("Canonical State Store") is a teal database cylinder, slightly
  larger than the rectangle nodes, drawn at the visual center of the
  pipeline.
- All connecting arrows are teal, left to right.

ALLOWED ANNOTATIONS (the only text permitted besides the 7 node labels):

- Above the inbound arrow into node 1: "signed Canonical Claims"
- Above the arrow between node 2 and node 3: "accept"
- Below the same arrow between node 2 and node 3: "reject"
- Above the outbound arrow leaving node 6 (going off-canvas to the right
  or downward): "Compliance Attestations"
- Above the outbound arrow leaving node 7 (going off-canvas to the
  right): "canonical state queries"

STYLE: Clean engineering blueprint. White background. No people, no
photographs, no vendor logos, no padlock icons, no anchor icons, no
watermarks.

## Style notes

- Palette locked (see frontmatter). Navy `#0D1B2E` for primary node fills,
  teal `#1E8C8C` for arrows and the central database cylinder, mid-blue
  `#2E75B6` reserved (unused in this revision), neutral grey `#5A5A5A`
  for annotation text, white background.
- Aspect locked: 1:1 (Gemini 2.5 Flash Image does not honor 16:9 prompt
  language; first render produced 1024×1024 — registry aspect updated
  accordingly).
- Clean engineering blueprint style — no photographs, no people, no
  vendor logos.
- Publication-grade, suitable for inclusion in OSCAL-adjacent
  deliverables.

## History

- v1.0 (2026-05-07) — initial draft, fabric-trio pilot.
- v1.0 second render (2026-05-07) — first render produced typos
  ("Cannocal"), missing node 3 (Signature Verifier), and prompt-text
  leakage. Prompt rewritten with explicit node count, quoted labels,
  spelling callouts, and explicit forbid list for decorations. Aspect
  changed from 16:9 to 1:1 to match what the model actually produces.
