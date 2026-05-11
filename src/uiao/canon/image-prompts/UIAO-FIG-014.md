---
id: UIAO-FIG-014
slug: orgpath-device-azure-storage-routing
title: "OrgPath Storage on Devices and Azure — Disposition-Driven Routing"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#2E75B6", "#5A5A5A", "#FFFFFF"]
---

## Description

Architecture diagram that answers "where does OrgPath data live for
devices and Azure resources?" by visualizing the disposition decision
on the left, the two write transports in the middle (Microsoft Graph
and Azure Resource Manager), and the two resulting storage slots on
the right (`extensionAttribute1` on the Entra device and the `OrgPath`
ARM tag on the Arc machine). The codebook hovers above as the shared
validator for both slots, mirroring the three-layer structure of
UIAO-FIG-012 but specialized for the device/Azure surface.

## Prompt

A 16:9 technical architecture schematic in the UIAO federal-whitepaper
style — dark navy (#0D1B2E) and teal (#1E8C8C) with a mid-blue
(#2E75B6) accent on the two storage cylinders, on a white background —
depicting OrgPath storage routing for devices and Azure resources.

Layout: a left-to-right, three-column composition with a codebook tile
hovering above the middle column.

1. **Left column — Disposition decision** — a single rounded
   rectangle labeled "Computer Disposition Matrix" with a small
   branching pictogram inside. Five labeled outbound arrows fan out
   to the right from this node, one per disposition:
   - "ENTRA-DEVICE" — teal arrow heading into the upper write
     transport (Microsoft Graph).
   - "ARC-SERVER" — teal arrow heading into the lower write
     transport (Azure Resource Manager).
   - "STAY-AD-DEPENDENCY" — teal arrow into the lower transport.
   - "MANAGED-IDENTITY-CANDIDATE" — teal arrow into the lower
     transport.
   - "STAY-AD-DC" and "DECOMMISSION" — a single combined teal arrow
     ending in a small red-outlined "no-entry" pictogram with the
     label "no write". This is the only red element in the diagram.

2. **Middle column — Two write transports** — two stacked rounded
   rectangles, labeled top-to-bottom:
   - **Microsoft Graph** — small Microsoft Graph wordmark/icon; sub-
     label "PATCH /devices/{object_id}".
   - **Azure Resource Manager** — small ARM wordmark/icon; sub-label
     "PATCH api-version=2023-03-15-preview".
   Each transport rectangle has a single teal arrow exiting its right
   edge into the corresponding storage cylinder in the right column.

3. **Right column — Two storage cylinders** — two mid-blue
   (#2E75B6) cylinders drawn vertically stacked:
   - **Entra Device** cylinder (top) — sub-label "extensionAttribute1".
   - **Arc Machine** cylinder (bottom) — sub-label "ARM tag: OrgPath".
   A small horizontal teal double-arrow connects the two cylinders'
   inner edges, labeled "must agree (regex-equal)".

4. **Top — shared validator** — a single rounded rectangle labeled
   "Codebook (UIAO_151)" centered above the middle column, with a
   small folder/Git pictogram. Two teal downward arrows from this
   tile, one to each storage cylinder, both labeled "validates".

5. **Bottom-right — inheritance arrows** — two small rounded
   rectangles below the storage cylinders, drawn smaller:
   - "Intune scope tag" — connected upward to the Entra Device
     cylinder by a thin grey `#5A5A5A` dashed arrow labeled "derives
     from".
   - "Azure Policy targeting" — connected upward to the Arc Machine
     cylinder by a thin grey dashed arrow labeled "reads".
   These two are visually de-emphasized to convey "derived, not
   stored."

## Style notes

- Palette locked (see frontmatter). Navy `#0D1B2E` for primary node
  fills (disposition matrix, transports, codebook tile), teal
  `#1E8C8C` for primary arrows and connectors, mid-blue `#2E75B6`
  reserved exclusively for the two storage cylinders, neutral grey
  `#5A5A5A` for the inheritance dashed arrows and small annotations,
  white background. The single no-entry pictogram is the only red
  element permitted.
- Aspect locked: 16:9.
- Clean engineering blueprint style — no photographs, no people, no
  vendor logos beyond the Microsoft Graph and Azure Resource Manager
  wordmarks/icons on their respective transport nodes.
- Only baked text permitted: the node labels (Computer Disposition
  Matrix, Microsoft Graph, Azure Resource Manager, Entra Device,
  Arc Machine, Codebook (UIAO_151), Intune scope tag, Azure Policy
  targeting); the disposition arrow labels (ENTRA-DEVICE, ARC-SERVER,
  STAY-AD-DEPENDENCY, MANAGED-IDENTITY-CANDIDATE, STAY-AD-DC,
  DECOMMISSION); the transport sub-labels (PATCH /devices/{object_id},
  PATCH api-version=2023-03-15-preview); the storage sub-labels
  (extensionAttribute1, ARM tag: OrgPath); and the connector
  annotations (no write, must agree (regex-equal), validates, derives
  from, reads). No additional decorative text.
- Publication-grade, suitable for inclusion in the modernization
  canon and customer-facing device-governance deliverables.

## Renders into

- `docs/modernization/where-data-lives-devices-and-azure.qmd` — the
  explainer this figure illustrates.
- `src/uiao/canon/adr/adr-038-device-plane-orgpath.md` — the binding
  ADR reference image.

## History

- v1.0 (2026-05-11) — initial draft, accompanies the
  Where-Data-Lives-Devices-and-Azure explainer. Visualizes the
  disposition-driven dispatch between the Microsoft Graph and Azure
  Resource Manager write transports, with the shared codebook
  hovering above both storage cylinders, and the inherited
  Intune/Azure Policy consumers de-emphasized below.
