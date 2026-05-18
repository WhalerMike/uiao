# `models/` (root) — Phase 2 source models

> **The canon authority for this repository lives at
> [`src/uiao/canon/`](../src/uiao/canon/).** This directory holds
> generator-input source models — not canon — and was renamed from
> `canon/` to `models/` to remove the naming collision.

## What this directory holds

Phase 2 source models — PowerShell data files (`.psd1`) consumed by
the generators in [`tools/`](../tools/) to produce
[`phase2/`](../phase2/).

Current contents:

| Path | Purpose |
|---|---|
| [`phase2/UIAO_Phase2_TSA.psd1`](phase2/UIAO_Phase2_TSA.psd1) | Source model for the Phase 2 Target State Architecture; consumed by [`tools/Write-Phase2TSA.ps1`](../tools/Write-Phase2TSA.ps1) which emits `phase2/UIAO_P2_TSA_Overview.md` and the `UIAO_P2_DOM_*.md` set under `phase2/_legacy/`. |

## Why the rename

Per [AGENTS.md § Repository Invariants](../AGENTS.md#repository-invariants),
canon authority is at `src/uiao/canon/` (invariant I4). A top-level
`canon/` read as a duplicate authority and confused both contributors
and tooling. The rename to `models/` makes the role explicit:
generator-input source models, not canonical governance documents.

## Adding a new source model

New `.psd1` (or other generator-input) files belong here, organized by
the phase they feed (`phase2/`, `phase3/`, etc.). The matching generator
under `tools/` should default its `$ModelPath` to a path inside this
directory.
