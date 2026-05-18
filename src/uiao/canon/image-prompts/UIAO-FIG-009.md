---
id: UIAO-FIG-009
slug: truth-fabric
title: "UIAO Truth Fabric — Claim Intake Pipeline"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#2E75B6", "#5A5A5A", "#FFFFFF"]
---

## Description

Architecture diagram of the UIAO Truth Fabric claim intake pipeline. Shows
the path from adapter-signed Canonical Claim submission through schema
validation, signature verification, identity anchoring, and canonical state
storage, with downstream interfaces to the Control Mapping Engine and the
Drift Fabric.

## Prompt

A 16:9 technical architecture schematic in the UIAO federal-whitepaper
style — dark navy (#0D1B2E) and teal (#1E8C8C) on a white background —
depicting the UIAO Truth Fabric claim intake pipeline.

Layout: a left-to-right horizontal pipeline of seven labeled rectangular
nodes connected by directional arrows. From left to right:

1. **Claim Ingress API** — entry node with an inbound arrow labeled
   "signed Canonical Claims from adapters".
2. **Schema Validator** — gear icon; validates against the Canonical
   Claim Schema. Pipeline edge to the next node carries an
   "accept / reject" branch label.
3. **Signature Verifier** — key/lock icon; verifies adapter digital
   signatures.
4. **Identity Anchoring Engine** — anchor icon; correlates subject
   identifiers to Canonical Identity Records.
5. **Canonical State Store** — large database cylinder, slightly larger
   than other nodes and visually emphasized as the central authority;
   authoritative storage for accepted claims and identity records.
6. **Control Mapping Engine** — branches off the Canonical State Store
   toward an outbound arrow labeled "Compliance Attestations".
7. **Drift Fabric Interface** — outbound arrow on the right edge labeled
   "canonical state for drift queries", pointing off-canvas toward an
   unseen Drift Fabric (sibling diagram).

## Style notes

- Palette locked (see frontmatter). Navy `#0D1B2E` for primary node fills,
  teal `#1E8C8C` for arrows and accents, mid-blue `#2E75B6` for the
  Canonical State Store cylinder, neutral grey `#5A5A5A` for labels and
  branch annotations, white background.
- Aspect locked: 16:9.
- Clean engineering blueprint style — no photographs, no people, no
  vendor logos.
- Only baked text permitted: the seven node labels and the four arrow
  labels enumerated in the prompt body. No additional decorative text,
  taglines, or watermarks.
- Publication-grade, suitable for inclusion in OSCAL-adjacent
  deliverables.

## History

- v1.0 (2026-05-07) — initial draft, fabric-trio pilot for canonical
  image-pipeline routing of architecture diagrams.
