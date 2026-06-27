---
id: UIAO-FIG-029
slug: hierarchical-ou-vs-flat
title: "Hierarchical OUs vs the Flat Directory"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#C0392B", "#5A5A5A", "#FFFFFF"]
---

## Description
House-style replacement for the OU-tree contrast sketch: left, an Active Directory OU tree (domain → OU=Washington → OU=Finance/OU=HR → user, with "inherits policy" notes); right, the flat Entra directory where users, groups, devices, and service principals all sit at one level — no OUs, no parent-child, no inheritance — so policy must be targeted explicitly.

## Prompt
A 16:9 blueprint schematic (ADR-093), white background, split into two halves. Left "Active Directory (hierarchical)": a monospace OU tree with teal "(inherits policy)" notes and a "policy flows down the tree" tag. Right "Entra ID (flat)": an ice box of mixed objects at one level with a red "no OUs, no parent-child, no inheritance" caption and a red "policy must be targeted explicitly" tag. Literal SVG text; no logos, no photos.
