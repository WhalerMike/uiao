---
id: UIAO-FIG-012
slug: orgpath-storage-topology
title: "OrgPath Storage Topology — HR, Entra ID, and the Codebook"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#2E75B6", "#5A5A5A", "#FFFFFF"]
---

## Description

Architecture diagram that answers the question "where does OrgPath data
live?" by showing the three storage layers and the one-directional data
flow between them: the HR system (authority) feeds a provisioning
pipeline that writes the `extensionAttribute1` slot on every Entra ID
principal (assignment), while a Git-versioned Codebook (vocabulary) is
read by the Drift Engine to validate every assigned value. Downstream
governance consumers — Dynamic Groups, Administrative Units, Conditional
Access, Licensing — read the assignment from Entra ID.

## Prompt

A 16:9 technical architecture schematic in the UIAO federal-whitepaper
style — dark navy (#0D1B2E) and teal (#1E8C8C) with a mid-blue (#2E75B6)
accent for the Entra ID directory store on a white background — depicting
the three storage layers that hold OrgPath data.

Layout: three labeled vertical bands stacked top-to-bottom, with a
right-side column of downstream consumers.

1. **Top band — "Authority Layer"** — a single rounded rectangle on the
   left labeled "HR System (Workday / SAP HR / HRIS)" with a small
   building-and-org-chart icon. A downward teal arrow labeled
   "authoritative org assignment" exits the bottom of the HR box.

2. **Middle band — "Assignment Layer"** — the arrow from the HR box
   passes through an intermediate rounded rectangle labeled
   "Provisioning Pipeline (HR-driven inbound · Entra Connect · custom
   adapter)". A second downward teal arrow labeled "writes
   extensionAttribute1" then enters a large mid-blue (#2E75B6) cylinder
   labeled "Entra ID Directory". Inside the cylinder, three small
   stacked tiles read "User · extensionAttribute1", "Device ·
   extensionAttribute1", and "Azure Resource · OrgPath tag".

3. **Bottom band — "Vocabulary Layer"** — on the left, a Git-repository
   icon (folder with the Git logomark) labeled "src/uiao/canon/data/
   orgpath/codebook.yaml" sits beside a small document tile labeled
   "JSON Schema (UIAO_158)". To its right, centered beneath the Entra ID
   cylinder, a hexagonal node labeled "Drift Engine (UIAO_163)". A teal
   arrow runs from the codebook tile rightward into the Drift Engine
   labeled "reads valid codes"; a second teal arrow runs upward from the
   Drift Engine into the Entra ID cylinder labeled "validates
   extensionAttribute1".

4. **Right column — downstream consumers** — four small rounded
   rectangles stacked vertically to the right of the Entra ID cylinder,
   each connected to the cylinder by a thin teal arrow labeled "reads":
   "Dynamic Groups (UIAO_152)", "Administrative Units (UIAO_154)",
   "Conditional Access", "Licensing".

5. **Forbidden-write annotation** — a small red-outlined "no-entry"
   pictogram beside the Entra ID cylinder with the label "IT never
   manually edits extensionAttribute1" — this is the only red element in
   the diagram.

The three band labels ("Authority Layer", "Assignment Layer",
"Vocabulary Layer") appear as faint neutral-grey `#5A5A5A` tags on the
far left margin of each band.

## Style notes

- Palette locked (see frontmatter). Navy `#0D1B2E` for primary node
  fills, teal `#1E8C8C` for arrows and connectors, mid-blue `#2E75B6`
  reserved exclusively for the Entra ID directory cylinder, neutral grey
  `#5A5A5A` for band labels, white background. The single no-entry
  pictogram is the only red element permitted.
- Aspect locked: 16:9.
- Clean engineering blueprint style — no photographs, no people, no
  vendor logos beyond the Git logomark on the codebook folder icon.
- Only baked text permitted: the layer band labels (Authority Layer,
  Assignment Layer, Vocabulary Layer), the node labels (HR System,
  Provisioning Pipeline, Entra ID Directory, User · extensionAttribute1,
  Device · extensionAttribute1, Azure Resource · OrgPath tag, codebook.yaml
  path, JSON Schema (UIAO_158), Drift Engine (UIAO_163), Dynamic Groups,
  Administrative Units, Conditional Access, Licensing), the arrow labels
  ("authoritative org assignment", "writes extensionAttribute1", "reads
  valid codes", "validates extensionAttribute1", "reads"), and the
  forbidden-write annotation ("IT never manually edits
  extensionAttribute1"). No additional decorative text.
- Publication-grade, suitable for inclusion in the modernization canon
  and customer-facing OrgPath narrative deliverables.

## Renders into

- `docs/modernization/where-data-lives.qmd` — the explanatory doc this
  figure illustrates.
- `src/uiao/canon/UIAO_151_OrgPath_Codebook.md` — canonical "storage"
  section reference image.

## History

- v1.0 (2026-05-11) — initial draft authored to accompany the
  "Where OrgTree & OrgPath Data Lives" explainer; answers the recurring
  "is OrgPath in a registry?" question by visualizing the three storage
  layers (HR → Entra extensionAttribute1 ← Codebook).
