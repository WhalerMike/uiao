# Rule: Canon Consumer Boundary

> **Always-on.** Loaded automatically by repo-aware agents (Claude Code,
> Codex, etc.) via `AGENTS.md` at repo root.

## Post-ADR-032 context

Canon and runtime code ship together in the single installable `uiao`
package rooted at `src/uiao/`. Canon lives under `src/uiao/canon/`,
`src/uiao/schemas/`, `src/uiao/rules/`, and `src/uiao/ksi/`; every other
subpackage (`adapters/`, `cli/`, `governance/`, `evidence/`, `oscal/`,
`ssp/`, `ir/`, `substrate/`, etc.) is a canon **consumer**.

The pre-ADR-032 distinction between `uiao-core` (canon) and `uiao-impl`
(consumer) no longer applies — see ADR-028 (monorepo consolidation) and
ADR-032 (single-package flattening).

## Enforcement

1. **Canon reads use `importlib.resources`, never filesystem paths.**
   Runtime code must resolve canon artifacts via
   `importlib.resources.files("uiao.canon") / "..."` (or equivalent for
   `uiao.schemas`, `uiao.rules`, `uiao.ksi`). This survives installation
   from a wheel and works regardless of CWD. Hardcoded absolute paths,
   `Path(__file__).parent / "../canon/..."`-style reach-arounds, and
   sibling-checkout fallbacks are forbidden outside test fixtures.

2. **Canon is read-only at runtime.** Code must not write to canon
   files via normal execution paths. The only writers are the
   canon-change process (human PRs + ADRs) and scripts under `scripts/`
   explicitly marked as canon-edit tooling.

3. **Canon changes flow through the canon-change process.** Adding,
   modifying, retiring, or superseding anything under `src/uiao/canon/`
   requires:
   - A new `UIAO_NNN` allocation in `src/uiao/canon/document-registry.yaml`
     (for new documents)
   - A new ADR in `src/uiao/canon/adr/` (for doctrinal changes)
   - Governance review before merge

4. **Provenance on derived outputs.** Any artifact generated from canon
   (OSCAL bundles, SSPs, reports, exports) must cite the canon document
   ID and version it was derived from.

5. **Version isolation.** No references to any previous version of a
   canon document inside the current canon context. Supersession is
   recorded via append-only ADRs plus explicit `superseded_by:` fields,
   not by in-place rewrites.

## Invariants this rule rests on

The repo-level invariants in `AGENTS.md § Repository Invariants` encode
these constraints at the packaging layer:

- **I1** — `src/uiao/` is a regular Python package with a single
  `__init__.py`; canon ships as package data via `importlib.resources`.
- **I4** — Canon is a read-only dependency of code; no runtime writes.
- **I5** — Canon changes flow through the canon-change process above.

Violating this rule is a governance drift signal and should be caught
in code review or by the substrate-drift CI gate.

## Sub-app surface map: `evidence` vs `ir`

Two CLI sub-apps appear to overlap on first read of `uiao --help`:
`uiao evidence` (2 commands: `build`, `graph`) and `uiao ir` (14
commands, several of which produce or consume evidence). The split is
principled — adopters and contributors should know which to use.

**`uiao evidence`** is the **canonical bundle surface**. Two commands:

- `evidence build` — assemble an `EvidenceBundle` (content-hashed,
  provenance-anchored) from a KSI result JSON. The bundle is the
  authoritative artifact-of-record consumed by auditors.
- `evidence graph` — build and inspect the Evidence Graph (UIAO_113)
  spanning controls → evidence → policies → drift findings. Read API
  surface for the OSCAL back-matter graph.

Use `uiao evidence` when the goal is **the bundle / graph itself**.

**`uiao ir`** is the **pipeline-stage surface**. 14 commands operating
on the IR (Intermediate Representation) of a SCuBA assessment:
transform, validate, freshness, drift-detect, governance-report,
poam-export, ssp-report, ssp-inject, generate-sar, auditor-bundle,
diff, dashboard, and (singular) `evidence-bundle` — which is a thin
convenience wrapper that runs `transform` then calls
`evidence.bundle.build_bundle_from_transform_result`.

Use `uiao ir` when the goal is **a pipeline stage** (transform, drift,
report) operating on a SCuBA → IR → evidence flow.

**Decision rule for new commands:**

- If the operation produces or inspects the canonical evidence bundle
  shape itself, it belongs under `evidence`.
- If the operation runs a stage of the SCuBA → IR → evidence → OSCAL
  pipeline, it belongs under `ir`.

This division was ratified by the [M5 public-surface audit](../../../docs/reports/public-surface-audit-v0.5.0.md)
F4/D4a; rejected alternatives were flattening (drop `evidence`,
everything routes through `ir`) and expansion (move `linker`,
`collector`, `poam` builders to `evidence`).
