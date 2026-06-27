---
id: UIAO-FIG-020
slug: adr003-api-driven-inbound-provisioning
title: "ADR-003 — API-Driven Inbound Provisioning Architecture"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#C0392B", "#5A5A5A", "#FFFFFF"]
---

## Description

Engineering schematic of the ADR-003 HR-agnostic inbound provisioning
architecture (a house-style replacement for the ASCII diagram in the ADR
source). A navy HR System box (Workday OR Oracle OR any source) flows
through a teal-bordered Middleware Layer (Azure Functions / Logic Apps —
schema normalization, OrgPath calculation, validation, provenance logging)
into the ice Entra ID Provisioning Service (attribute mapping, JML
workflows, group assignment, license assignment). A red dashed branch drops
to the on-prem Provisioning Agent (HA) doing AD writeback, marked
coexistence-only / transitional. A callout notes OrgPath is computed in the
middleware, independent of the HR source, so a future HR change never
re-opens the provisioning contract.

## Prompt

A 16:9 technical schematic in the UIAO federal-whitepaper blueprint style
(ADR-093) on a white background. Left to right: a navy "HR System (Workday
OR Oracle OR any source)" box; a teal arrow into a teal-bordered ice
"Middleware Layer (Azure Functions / Logic Apps)" box listing schema
normalization, OrgPath calculation, validation, provenance logging; a teal
arrow into an ice/navy-border "Entra ID Provisioning Service" box listing
attribute mapping, JML workflows, group assignment, license assignment. A
red dashed arrow drops from the Entra box to a red-tinted "Provisioning
Agent (On-prem, HA) — AD writeback" box tagged "coexistence only —
transitional". A teal-tint callout under the middleware states OrgPath is
computed there, independent of the HR source. All text literal SVG; no
photographs, no vendor logos.
