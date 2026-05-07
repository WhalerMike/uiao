---
id: UIAO-FIG-011
slug: evidence-fabric
title: "UIAO Evidence Fabric — Write Pipeline and Storage Tiers"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#2E75B6", "#5A5A5A", "#FFFFFF"]
---

## Description

Architecture diagram of the UIAO Evidence Fabric write pipeline with
two-tier storage. Shows event ingestion, signature verification, Evidence
Fabric countersignature, hash-chain anchoring, the active/archive storage
tiers, and the Correlation Engine that serves correlation and diff
queries.

## Prompt

A 16:9 technical architecture schematic in the UIAO federal-whitepaper
style — dark navy (#0D1B2E) and teal (#1E8C8C) with a mid-blue (#2E75B6)
accent for the storage tier on a white background — depicting the UIAO
Evidence Fabric write pipeline.

Layout: a left-to-right pipeline that forks vertically into two storage
cylinders, with a Correlation Engine sitting beneath both stores. From
left to right:

1. **Event Ingress** — entry node with an inbound arrow labeled
   "adapter-signed governance events".
2. **Signature Verifier** — validates adapter signature; deduplicates by
   `event_id`. Pipeline edge to the next node carries a "dedup" annotation.
3. **Evidence Fabric Countersigner** — chain-link icon; adds Evidence
   Fabric countersignature.
4. **Hash Chain Writer** — small hash-chain pictogram (linked hexagons);
   appends content hash and chain link.
5. The pipeline forks into two storage cylinders drawn side-by-side to
   the right of the Hash Chain Writer:
   - **Active Storage** (left cylinder, larger, primary tier) — labeled
     "≤ 90 days".
   - **Archive Storage** (right cylinder, smaller, secondary tier) —
     labeled "3–7 year retention".
6. **Correlation Engine** — sits *below* the two storage cylinders,
   centered, with read arrows up from both Active and Archive Storage
   into the engine. An outbound arrow on the right edge of the
   Correlation Engine is labeled "correlation & diff queries".

Both storage cylinders use the mid-blue `#2E75B6` accent fill so they
stand out from the teal pipeline nodes. The Hash Chain Writer carries a
subtle linked-hexagon detail to reinforce the chain-anchoring concept.

## Style notes

- Palette locked (see frontmatter). Navy `#0D1B2E` for primary pipeline
  node fills, teal `#1E8C8C` for arrows and chain-link/hash icons,
  mid-blue `#2E75B6` reserved for the two storage cylinders, neutral
  grey `#5A5A5A` for labels, white background.
- Aspect locked: 16:9.
- Clean engineering blueprint style — no photographs, no people, no
  vendor logos.
- Only baked text permitted: the seven node labels (Event Ingress,
  Signature Verifier, Evidence Fabric Countersigner, Hash Chain Writer,
  Active Storage, Archive Storage, Correlation Engine), the retention
  labels ("≤ 90 days", "3–7 year retention"), the "dedup" pipeline
  annotation, and the inbound/outbound arrow labels. No additional
  decorative text.
- Publication-grade, suitable for inclusion in OSCAL-adjacent
  deliverables.

## History

- v1.0 (2026-05-07) — initial draft, fabric-trio pilot for canonical
  image-pipeline routing of architecture diagrams.
