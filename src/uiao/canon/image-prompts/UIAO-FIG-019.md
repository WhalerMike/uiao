---
id: UIAO-FIG-019
slug: uiao195-addressing-drift-taxonomy
title: "UIAO_195 — Addressing-Plane Drift Taxonomy"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#5A5A5A", "#FFFFFF"]
---

## Description

Engineering schematic of the UIAO_195 addressing-plane drift taxonomy: the
two coordinate planes the substrate governs — the identity plane (OrgPath /
UIAO_151) and the addressing plane (DNS namespace / UIAO_195) — both
converging on the shared `drift_core` gate (ADR-108) that emits Finding
objects with identical semantics on both planes. The addressing plane's
twelve drift classes are grouped into two observability tiers (satisfiable
from a zone-read + manifest + resource list vs deferred, requiring live
observation). A left-side strip maps the taxonomy onto the OrgPath
five-class taxonomy (DRIFT-SCHEMA / SEMANTIC / PROVENANCE / AUTHZ /
IDENTITY).

## Prompt

A 16:9 technical schematic in the UIAO federal-whitepaper blueprint style
(ADR-093) on a white background. Two navy plane boxes at the top: "Identity
plane — OrgPath (UIAO_151): who/what an object is; where it sits
organisationally" and "Addressing plane — DNS namespace (UIAO_195): where it
is reachable; under whose naming authority". Under the addressing plane, two
ice/navy-border tier boxes — "Satisfiable (zone-read + manifest + resource
list)" and "Deferred (require live observation)". Teal arrows from the
identity plane and from the addressing tiers converge into a central
teal-bordered navy box "drift_core (ADR-108) — shared gate, emits Finding
objects", with a teal arrow down to a teal-tint "Finding objects" box. A
left-side strip of five small white boxes maps to the OrgPath five-class
taxonomy: DRIFT-SCHEMA, SEMANTIC, PROVENANCE, AUTHZ, IDENTITY. All text
literal SVG; no photographs, no vendor logos.
