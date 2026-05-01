# `canon/` (root) — **NOT canon authority**

> **The canon authority for this repository lives at
> [`src/uiao/canon/`](../src/uiao/canon/).** This directory has the
> same name purely by historical accident and does **not** hold canon
> documents.

## What this directory actually holds

Phase 2 source models — PowerShell data files (`.psd1`) consumed by
the generators in [`tools/`](../tools/) to produce
[`phase2/`](../phase2/).

Current contents:

| Path | Purpose |
|---|---|
| [`phase2/UIAO_Phase2_TSA.psd1`](phase2/UIAO_Phase2_TSA.psd1) | Source model for the Phase 2 Target State Architecture; consumed by [`tools/Write-Phase2TSA.ps1`](../tools/Write-Phase2TSA.ps1) which emits `phase2/UIAO_P2_TSA_Overview.md` and the `UIAO_P2_DOM_*.md` set under `phase2/_legacy/`. |

## Why the name is wrong

Per [AGENTS.md § Repository Invariants](../AGENTS.md#repository-invariants),
canon authority is at `src/uiao/canon/` (invariant I4). A top-level
`canon/` reads as a duplicate authority and confuses both contributors
and tooling.

## Planned rename

This directory is scheduled for rename to `models/` (or similar) in a
follow-up PR. The rename requires updating the `$ModelPath` default
in [`tools/Write-Phase2TSA.ps1`](../tools/Write-Phase2TSA.ps1) in
lockstep so the generator continues to find its source model.

Until that rename lands, this README serves as the disambiguation
notice.
