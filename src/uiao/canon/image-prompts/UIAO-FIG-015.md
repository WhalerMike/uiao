---
id: UIAO-FIG-015
slug: uiao014-gpo-modernization-pipeline
title: "UIAO_014 — GPO Modernization Pipeline: Parse → Consume → Join"
aspect: "16:9"
palette: ["#0D1B2E", "#1E8C8C", "#EAF1FB", "#C0392B", "#5A5A5A", "#FFFFFF"]
---

## Description

Engineering schematic for the UIAO_014 GPO modernization surface — the
three-stage `parse → consume → join` pipeline. It encodes the ADR-122
build/consume/differentiate posture in colour: navy for the UIAO-owned
offline parser (Build), an ice/navy-border box for the Microsoft Group
Policy Analytics dependency consumed live over Graph beta (Consume), and a
teal-bordered navy box for the OrgPath join that produces the sequenced,
cohort-bound, drift-classified Migration Plan (Differentiate). A footnote
records the two first-class outcomes: unsupported settings route to the
residual-GPO backlog, and a half-migrated GPO surfaces as a DRIFT- finding.

## Prompt

A 16:9 technical architecture schematic in the UIAO federal-whitepaper
blueprint style (ADR-093) — navy `#0D1B2E`, teal `#1E8C8C`, ice `#EAF1FB`
with a navy border, red `#C0392B` for the residual/loss marker, on a white
background — depicting the UIAO_014 three-stage pipeline.

Layout, left to right:

1. **Inputs (left).** A stack of three white, grey-bordered boxes labelled
   in monospace — `GPO backup XML`, `registry.pol`, `SYSVOL scope` — under
   the heading "ON-DISK GPO ARTIFACTS"; and below them an ice box labelled
   "Group Policy Analytics / Graph beta" under "MICROSOFT SURFACE (LIVE
   TENANT)". Teal arrows feed the two stages.

2. **Stage 1 — Parse** — a navy box ("offline · no tenant · no Graph")
   carrying a teal "BUILD" pill. Emits `GPO-IR`.

3. **Stage 2 — Consume** — an ice box with navy border ("live tenant ·
   annotates the IR") carrying a "CONSUME" pill. Emits `Crosswalk Result`.

4. **Stage 3 — Join** — a navy box with a teal border (the differentiator),
   "pure over IR + OrgPath", carrying a teal "DIFFERENTIATE" pill. The
   `GPO-IR` and `Crosswalk Result` arrows converge into it.

5. **Output (right).** A teal-tint box "Migration Plan — cohort-bound,
   topologically sequenced, drift-classified".

Footnote band: a red dot — "Unsupported settings … routed to the
residual-GPO backlog, never silently dropped"; an amber dot — "A
half-migrated GPO surfaces as a DRIFT- finding (ADR-040)".

All text is literal SVG `<text>`/`<tspan>`; no photographs, no vendor logos.
