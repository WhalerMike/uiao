---
id: UIAO-FIG-021
slug: evidence-chain
title: "The Evidence Chain — Telemetry to OSCAL"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#5A5A5A", "#FFFFFF"]
---

## Description

House-style replacement for the ASCII evidence-chain diagram: four navy
pipeline stages joined by teal arrows — Telemetry event capture (adapter
boundary) → Canonical claim normalization (ProvenanceProfile UIAO_PP_001
v1.0) → Evidence bundle assembly + seal (ADR-016 lifecycle + bundle schema)
→ OSCAL artifact emission (SSP / POA&M / KSI / Component Definition). A
footnote states every stage cites the canon ID + version it derives from,
so any artifact resolves back to its source telemetry.

## Prompt

A 16:9 blueprint-style schematic (ADR-093), white background, four navy
rounded rectangles in a row joined by teal arrows: "Telemetry event
capture", "Canonical claim normalization", "Evidence bundle assembly +
seal", "OSCAL artifact emission" (last with a teal border). Under each box a
grey sub-caption: adapter boundary; ProvenanceProfile (UIAO_PP_001 v1.0);
ADR-016 lifecycle + bundle schema; SSP · POA&M · KSI · Component Def. A
footnote on provenance anchoring. Literal SVG text; no logos, no photos.
