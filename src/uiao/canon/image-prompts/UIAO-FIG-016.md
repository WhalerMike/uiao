---
id: UIAO-FIG-016
slug: uiao135-transformation-inventory
title: "UIAO_135 — AD → Entra ID Transformation Inventory"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#D4A017", "#C0392B", "#5A5A5A", "#FFFFFF"]
---

## Description

Engineering schematic of the UIAO_135 identity & directory transformation
inventory: the seventeen transformations recast across four categories
(Structural, Identity Object, Policy, Governance & Lifecycle), each shown
as a legacy Active Directory construct (navy) transformed by a teal arrow
into a modern Entra/cloud control (ice with navy border). A coverage
legend encodes the three maturity states — well-defined (teal), partially
defined (amber), and gap (red) — and the open gaps are named in a footer.

## Prompt

A 16:9 technical schematic in the UIAO federal-whitepaper blueprint style
(ADR-093) on a white background. Two labelled columns — "ACTIVE DIRECTORY
(legacy)" and "ENTRA ID / CLOUD (modern)". Four horizontal lanes, one per
transformation category (Structural; Identity Object; Policy; Governance &
Lifecycle). Each lane: a navy box on the left holding the legacy construct
(e.g. X.500 OU tree, domain-joined PCs, GPOs linked to OUs, manual
provisioning), a teal arrow, and an ice/navy-border box on the right
holding the modern control (OrgPath path + Dynamic Groups + Administrative
Units; Entra/Arc devices; Intune Settings Catalog + Scope Tags +
Conditional Access; HR-driven JML + OSCAL baselines + drift detection). A
coverage legend at the bottom: teal dot = well-defined, amber dot =
partially defined, red dot = gap; plus a one-line list of the open gaps.
All text literal SVG; no photographs, no vendor logos.
