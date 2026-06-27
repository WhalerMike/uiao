---
id: UIAO-FIG-018
slug: uiao194-locpath-codebook
title: "UIAO_194 — LocPath Codebook"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#5A5A5A", "#FFFFFF"]
---

## Description

Engineering schematic of the UIAO_194 LocPath codebook: the six-level
governed location hierarchy (Country → Region → Site → Building → Floor →
Space) as a path of navy boxes joined by teal arrows, with Site emphasised
(teal border) as the primary classification anchor, and a worked path value
shown in monospace. Below, the three classification surfaces (E911
dispatchable location; Network / TIC 3.0; telemetry / service boundaries).
Then the two-layer location model — governed Primary LocPath (navy) vs
observational Dynamic Location Context (ice). A footer band states matrix
governance with OrgPath: LocPath is a second addressing dimension, not a
sixteenth facet.

## Prompt

A 16:9 technical schematic in the UIAO federal-whitepaper blueprint style
(ADR-093) on a white background. A top row of six navy boxes joined by teal
arrows — Country, Region, Site (teal border), Building, Floor, Space — with
a monospace example path "/US / EAST / BALT-DC1 / BLDG-A / FL-03 / RM-3120"
beneath. A row of three ice/navy-border boxes for the classification
surfaces: "E911 dispatchable location (Building / Floor / Space)", "Network
/ TIC 3.0 (trust-zone & ingress)", "Telemetry / service boundaries". A
two-box two-layer model: navy "Primary LocPath — governed (SSOT
assignment)" and ice "Dynamic Location Context — observational (never
overwrites the governed value)". A teal-tint footer band: matrix governance
with OrgPath; orthogonal addressing dimensions; out-of-scope note. All text
literal SVG; no photographs, no vendor logos.
