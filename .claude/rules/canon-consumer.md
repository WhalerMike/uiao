# Rule: Canon Consumer Boundary

> **Always-on.** This file is loaded automatically by Claude Code.

## Declaration

`uiao-impl` is a **consumer** of canon defined in
[`uiao-core`](https://github.com/WhalerMike/uiao-core). It does **not** define
canonical governance artifacts.

## Enforcement

1. **No canonical artifacts in this repo.** If a change would create a new
   canonical governance document (SSOT, document registry, adapter registry,
   modernization registry, crosswalk, etc.), stop and open a PR against
   `uiao-core` instead.

2. **No hard-coded canon paths.** All runtime canon reads go through the
   `--canon-path` CLI argument or equivalent configuration. `../uiao-core`,
   `../../uiao-core`, or any relative sibling path is forbidden in runtime
   code. Tests may use fixtures or temporary paths.

3. **Version isolation.** No references to any previous version in any context
   prior to the current version.

4. **Provenance on derived outputs.** Any artifact this repo generates from
   canon must cite the canon source (document ID and version).

## When this rule applies

- Adding a new CLI command that reads canon → must accept `--canon-path`.
- Adding a new adapter that references canon identifiers → must validate them
  against the canon schema at runtime, not against a local copy.
- Writing tests that need canon → use `tests/fixtures/` with a pinned canon
  snapshot; do not reach into a sibling checkout.

## Escape hatch

If you genuinely need a canonical artifact that does not yet exist in
`uiao-core`, the correct path is:

1. Open an issue on `uiao-core` proposing the artifact.
2. Open a stub PR on `uiao-core` with the artifact shell.
3. Land the `uiao-impl` work that consumes it **after** the `uiao-core` PR
   merges.

Do **not** fork the artifact into this repo as a workaround.

<!-- NEW (Proposed) -->
