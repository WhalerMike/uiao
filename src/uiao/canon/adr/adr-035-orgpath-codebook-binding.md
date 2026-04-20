---
id: ADR-035
title: "OrgPath Codebook — Executable Canon Binding"
status: accepted
date: 2026-04-20
deciders:
  - governance-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-012
  - ADR-033
  - ADR-034
canon_refs:
  - MOD_A_OrgPath_Codebook
  - MOD_H_OrgPath_JSON_Schema
  - UIAO_007_OrgTree_Modernization_AD_to_EntraID
---

# ADR-035: OrgPath Codebook — Executable Canon Binding

## Status

Accepted

## Context

MOD_A (`src/uiao/modernization/orgtree/MOD_A_OrgPath_Codebook.md`) enumerates
the canonical OrgPath codes that drive the entire OrgTree stack — dynamic
groups (MOD_B), administrative units (MOD_D), migration runbook (MOD_F), and
drift detection (MOD_M). MOD_H declares a JSON Schema for the codebook. In
practice the only machine-readable artefact was a *regex* in
`adapters/modernization/active-directory/orgpath.py` and a duplicate copy in
`governance/drift.py`. The codes themselves lived only inside the MOD_A
markdown table.

Consequences observed:

1. `governance.drift.classify_identity_drift` could flag **Format Drift** but
   not **Value Drift** against the real enumeration — the `orgpath_codebook`
   parameter was `Optional` and tests had to stub a hardcoded `set`.
2. There was no runtime check that the hierarchy in MOD_A was internally
   consistent — a code whose parent no longer existed would silently validate.
3. Phantom Drift (a user still carrying a deprecated code) had no
   machine-readable "deprecated list" to compare against.
4. MOD_A was marked CANONICAL in its front-matter but had no binding ADR,
   violating AGENTS.md §Canon-first governance.

## Decision

1. Publish the codebook as executable canon at
   `src/uiao/canon/data/orgpath/codebook.yaml`, packaged with
   `uiao.canon` so `importlib.resources` can read it at runtime.
2. Ship a JSON Schema at `src/uiao/schemas/orgpath/codebook.schema.json`
   implementing the MOD_H contract; every load validates against it.
3. Provide a loader at `src/uiao/modernization/orgtree/codebook.py` that
   additionally enforces referential integrity not expressible in JSON Schema:
   every non-root `parent` must be an active code, deprecated `replaced_by`
   must resolve to an active code, and segment descent must follow the
   canonical separator.
4. Extend `governance.drift.classify_identity_drift` to accept either the
   legacy `set[str]` or a `Codebook` instance; when a `Codebook` is passed,
   the classifier recognises **Phantom Drift** (deprecated code still in use)
   in addition to **Value Drift** (code not in the active set).
5. Register the AD OrgPath adapter in `canon/modernization-registry.yaml`
   under `id: active-directory`, with `class: modernization` and
   `mission-class: integration` — the survey half is read-only, the
   write-back half mutates AD (`extensionAttribute1..4`), and per UIAO_003
   §4.7 the pair is classified as `integration`.

MOD_A narrative remains the SSOT for human readers; the YAML is the SSOT
for the runtime. Changes to either require a governed PR that updates both
in the same commit — CI (Phase 6, MOD_V) enforces a hash cross-check in a
future ADR once the drift engine is promoted from scaffold to service.

## Consequences

**Positive**

- Drift engine can now emit four of the five MOD_A drift categories from
  data alone: Format Drift (regex), Value Drift (codebook membership),
  Phantom Drift (deprecated list), Hierarchy Drift (loader integrity check
  fires at codebook load, before any runtime inspection).
- `classify_identity_drift` remains backwards-compatible — the existing
  `set[str]` contract is preserved by duck-typing the argument.
- Adapter registry now contains the AD side of the identity story, closing
  the AGENTS.md §Adapter registration mandate for this adapter.
- Tests stop hand-maintaining a mock codebook; `load_codebook()` returns the
  real one.

**Negative / deferred**

- Orphan Drift (codebook entry with zero matching users) is *not* handled
  here — it requires tenant-state snapshots, which lands with MOD_M Phase 6.
- The narrative MOD_A markdown and the YAML can still drift apart until the
  cross-check CI job is added. Manual reconciliation is the interim control.
- Device-side OrgPath (ARM tag plane, ADR-034) continues to live outside
  this codebook binding; the YAML serves both planes but the drift engine
  only consumes the user plane today.

## Related work

- ADR-012 established the canonical drift taxonomy (five classes).
- ADR-033 added DRIFT-BOUNDARY.
- ADR-034 introduced the three-plane device model — this ADR is the user-
  plane counterpart on the canon side.
