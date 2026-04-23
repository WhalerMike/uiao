---
adr: ADR-044
title: "Substrate Governance Realignment to Post-ADR-032 Single Package"
status: Accepted
date: 2026-04-23
author: WhalerMike
supersedes: []
superseded_by: null
related:
  - ADR-028  # monorepo consolidation
  - ADR-031  # namespace package rename (superseded by ADR-032)
  - ADR-032  # single-package consolidation
---

# ADR-044: Substrate Governance Realignment to Post-ADR-032 Single Package

## Context

[ADR-032](adr-032-single-package-consolidation.md) (2026-04-20) collapsed
the pre-consolidation `impl/` + `core/` + partial `src/` tree into a
single installable Python package rooted at `src/uiao/`, with canon,
schemas, rules, and KSI shipping as package data via
`importlib.resources`. That ADR handled the *code and packaging* layer
of the consolidation.

What ADR-032 did **not** update:

1. **UIAO_200 Substrate Manifest** (`src/uiao/canon/substrate-manifest.yaml`)
   still declared the three-module topology (`core`, `docs`, `impl`)
   with `registry_refs` pointing at `core/canon/*` — every one of those
   paths was retired.
2. **UIAO_201 Workspace Contract** (`src/uiao/canon/workspace-contract.yaml`)
   had the same three modules, `build_outputs.impl_dist`, and a
   `canon_consumer_rule` pointer to the retired `impl/.claude/rules/`
   canon-consumer rule file (superseded by `src/uiao/rules/canon-consumer.md`).
3. **Workspace-contract schema** (`src/uiao/schemas/workspace-contract/
   workspace-contract.schema.json`) hardcoded
   `module_paths.required: [core, docs, impl]` and pinned
   `canon_consumer_rule.const` to a path under the retired `impl/`
   tree's hidden `.claude/rules/` directory,
   making any contract update fail schema validation.
4. **Substrate walker** (`src/uiao/substrate/walker.py`) resolved the
   manifest, contract, and registry under `core/canon/*`, and the
   canon-to-code provenance scanner looked specifically for `impl/`
   prefixes. With `core/` deleted, the walker could not find the
   manifest and returned a single "manifest missing" finding without
   validating anything else — a false negative.
5. The substrate-drift CI workflow gated on `report.ok` (any finding),
   not `report.blocking` (P1 only). With the walker inert this was
   invisible; once the walker works again, the P2-only canon-prose
   drift reported below would block every PR.

Net effect: the substrate-drift gate, re-enabled in PR #150 as part of
the CI path-filter repair, was reporting "success" only because the
walker failed to find the manifest and bailed early.

## Decision

Ratify the alignment of UIAO_200, UIAO_201, the workspace-contract
schema, the substrate walker, and the substrate-drift CI step to the
single-package topology established by ADR-032.

### Topology declared by UIAO_200 v2.0

| Module | Path | Role |
|---|---|---|
| `uiao` | `src/uiao` | `package` — installable distribution, canon + code |
| `tests` | `tests` | `consumer` |
| `docs` | `docs` | `consumer` |
| `scripts` | `scripts` | `tooling` |
| `inbox` | `inbox` | `staging` (not canon) |
| `deploy` | `deploy` | `deploy` — Windows-Server IIS entrypoint |

Sub-boundaries inside `uiao`: `canon`, `schemas`, `rules`, `ksi`,
`adapters`, `cli`.

`drift_scan.roots` covers `src/uiao`, `tests`, `docs`, `scripts`
(excludes `inbox` and `deploy` per role).

### Walker changes

- `SUBSTRATE_MANIFEST`, `WORKSPACE_CONTRACT`, `DOCUMENT_REGISTRY`
  retargeted to `src/uiao/canon/*`.
- `DOCUMENT_REGISTRY_BASE` changed from `"core"` to `"."` — paths in
  the registry are already workspace-relative (`src/uiao/canon/...`),
  no prefix needed.
- `CANON_ROOT` retargeted to `src/uiao/canon`.
- `IMPL_REF_PATTERN` renamed to `CODE_REF_PATTERN` and broadened to
  match both `src/uiao/` (current canonical layout) and `impl/`
  (retired prefix; any surviving canon citation is dangling by
  definition).
- `SubstrateReport.impl_refs_checked` renamed to `code_refs_checked`.
  JSON output contract changes accordingly.

### CI gate semantics

`.github/workflows/substrate-drift.yml` now exits `1` only on
`report.blocking` (P1 blockers), matching the semantics of the
`uiao substrate drift` CLI command. P2 canon-prose drift surfaces in
the report but does not block merge — narrative cleanup is an ongoing
editorial concern, not a gate-worthy integrity failure.

### Canon-consumer rule

`src/uiao/rules/canon-consumer.md` is rewritten from scratch for the
post-ADR-032 world: canon reads via `importlib.resources`, canon is
read-only at runtime, canon changes flow through the canon-change
process. The pre-consolidation rule — "`uiao-impl` is a consumer of
`uiao-core` canon; use `--canon-path`" — is obsolete and superseded.

## Consequences

### Positive

- `uiao substrate walk` / `uiao substrate drift` now actually validate
  the tree. The DRIFT-SCHEMA P1 finding the old manifest would have
  produced ("module 'core' does not exist") is eliminated by
  mechanically aligning the manifest to reality.
- `substrate-drift.yml` fires meaningfully on canon and substrate
  PRs, with the correct P1-only gate.
- Schema validation for workspace-contract no longer requires the
  retired `core`/`impl` keys; new top-level modules can be added to
  the manifest without editing the schema.
- Canon-consumer rule is findable again (inside the installed
  package) and matches current runtime behavior.

### Negative

- **JSON contract change.** `SubstrateReport.as_dict()` renames
  `impl_refs_checked` to `code_refs_checked`. Anything consuming
  the walker's JSON output must update. The only known consumer
  is `substrate-drift.yml`, updated in the same PR.
- **Post-alignment P2 warnings.** With the code-reference scanner
  working again, ~10 P2 DRIFT-PROVENANCE warnings surface: canon
  docs (mostly ADRs) that cite `src/uiao/impl/...` or `impl/...`
  paths that no longer exist. These are narrative drift, not
  architectural drift; cleanup is tracked as editorial
  follow-through and does not block merge under the new P1-only
  gate.

## Alternatives considered

- **Leave the walker resolving under `core/` and delete the
  substrate-drift gate.** Rejected: retiring a governance gate to
  avoid updating it is the opposite of SSOT hygiene.
- **Keep three modules `core/docs/impl` in UIAO_200 but alias them
  to the new paths via `sub_boundaries`.** Rejected: the modules
  aren't real anymore; aliasing preserves a lie. ADR-032 retired
  the three-module topology outright.
- **Author a separate ADR per artifact (manifest, contract, schema,
  walker).** Rejected: every change is a mechanical follow-through on
  ADR-032's already-ratified doctrine. One ADR ratifying the
  realignment is proportionate.

## Migration

Mechanical. Every artifact is rewritten in a single PR, the walker is
re-tested in-tree, and the substrate-drift gate is verified green
against the real repository (P2-only warnings, no P1 blockers).
