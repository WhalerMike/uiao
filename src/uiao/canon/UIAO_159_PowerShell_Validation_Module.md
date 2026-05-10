---
document_id: UIAO_159
title: "OrgTree Validation Surface — Python CLI + PowerShell module"
version: "2.0"
status: Current
classification: CANONICAL
owner: Michael Stratton
created_at: "2026-04-18"
updated_at: "2026-05-12"
boundary: GCC-Moderate
provenance_flatten:
  prior_id: "MOD_I"
  flattened_at: "2026-05-10"
  flattened_by: "ADR-060"
provenance_v2:
  prior_version: "1.0 (Draft, single-surface PowerShell scaffold)"
  derived_at: "2026-05-10"
  derived_by: "Promotion to Current; reframed as dual surface (Python canonical + PowerShell M365-admin UX). Implementation lands in the same PR as this revision."
---

# UIAO_159 — OrgTree Validation Surface

## Purpose

This appendix defines the validation surface for the OrgTree corpus
(UIAO_150 through UIAO_176). Validation has **two complementary
implementations**, with a single source of truth for shared logic:

| Surface | Lives at | Use it for |
|---|---|---|
| **Python (canonical)** | `src/uiao/modernization/orgtree/*.py`, exposed via `uiao orgtree validate ...` | Schema and integrity validation of every corpus artifact: codebook (UIAO_151), dynamic groups (UIAO_152), admin units (UIAO_154), device planes (UIAO_153), policy targets (UIAO_164), drift-engine config (UIAO_163). Invoked from CI, the substrate walker, and adapter pipelines. |
| **PowerShell (UX layer)** | `tools/powershell/OrgTreeValidation/` | M365-admin tenant operations that benefit from the Microsoft Graph PowerShell SDK: live tenant audits, snapshot export, snapshot diff, dynamic-group alignment checks. |

**Authority rule.** When the two surfaces overlap (offline regex,
codebook hierarchy, snapshot diff), the Python implementation is
canonical. The PowerShell module either calls back to the Python CLI
(`Invoke-UiaoOrgTreeValidate`) or carries a small offline implementation
that is **parity-tested** against the Python source-of-truth (see the
`Canonical regex parity` test in `OrgTreeValidation.Tests.ps1`).

This authority rule is what allows the two surfaces to coexist without
becoming a drift source. It directly reflects ADR-060 §"Why" — every
authoritative artifact has exactly one canonical home; mirrors must be
generated from canon, never authored independently.

## Surface 1 — Python CLI

Four verb groups under `uiao orgtree`:

### `validate` — schema + integrity check

```
uiao orgtree validate codebook                [--data PATH]
uiao orgtree validate dynamic-groups          [--data PATH]
uiao orgtree validate admin-units             [--data PATH]
uiao orgtree validate device-planes           [--data PATH]
uiao orgtree validate policy-targets          [--data PATH]
uiao orgtree validate drift-engine-config     [--data PATH]
uiao orgtree validate all
```

Each verb wraps the corresponding `load_*` function under
`uiao.modernization.orgtree`. With no `--data`, the canonical artifact
shipped under `uiao.canon.data.orgpath` is loaded; with `--data`, an
alternate file is loaded. Success prints a one-line PASS summary;
failure prints the typed validation error and exits 1. `validate all`
runs all six in dependency order (codebook → dynamic groups →
admin units → device planes → policy targets → drift-engine
config) and aggregates pass/fail.

### `show` — print one canonical entry

```
uiao orgtree show codebook       <ORG-PATH-CODE>
uiao orgtree show dynamic-group  <NAME>
uiao orgtree show admin-unit     <NAME>
uiao orgtree show device-plane   <NAME>
```

Loads the artifact, looks up the entry by id, renders it as a Rich
table. Exits 1 with a `NOT FOUND` line listing up to five known keys
when the id is missing.

### `list` — enumerate all entries

```
uiao orgtree list codebook        [--prefix PREFIX]
uiao orgtree list dynamic-groups  [--prefix PREFIX]
uiao orgtree list admin-units     [--prefix PREFIX]
uiao orgtree list device-planes   [--prefix PREFIX]
```

Renders every entry in the artifact as a sortable Rich table, one row
per entry with the most-scannable columns (id + 2-3 summary fields).
`--prefix` filters by id-prefix — e.g.
`uiao orgtree list codebook --prefix ORG-FIN` shows only Finance-tree
codes. Output title displays "X of Y" so the operator knows whether
the filter matched everything or trimmed.

### `resolve` — cross-reference against the codebook

```
uiao orgtree resolve dynamic-group <NAME>
```

Prints the group's membership rule, then walks each `orgpath_refs`
entry and reports OK / MISSING against the codebook (UIAO_151). Exits
1 if any reference is unregistered. Useful for "what does this group
target?" without reading raw YAML.

### `export` — emit canon as downstream-consumable JSON

```
uiao orgtree export codebook [--out PATH]
```

Serializes the codebook (UIAO_151) to JSON. Shape matches what the
PowerShell `Get-OrgTreeValidationReport -CodebookPath` cmdlet
(UIAO_159 §F3) expects: an object with `entries` as a list of
`{code, level, description, parent}`. Use it to bridge the canonical
YAML and the pwsh-side JSON file:

```bash
uiao orgtree export codebook --out /tmp/codebook.json
pwsh -c "Get-OrgTreeValidationReport -TenantId \$env:TENANT_ID -CodebookPath /tmp/codebook.json"
```

Tests: `tests/test_cli_orgtree.py` (34 tests covering validate, show,
resolve, export, and list).

## Surface 2 — PowerShell module

Module: `tools/powershell/OrgTreeValidation/OrgTreeValidation.psm1`.
Manifest: `tools/powershell/OrgTreeValidation/OrgTreeValidation.psd1`.
Tests: `tools/powershell/OrgTreeValidation/tests/OrgTreeValidation.Tests.ps1`
(Pester 5.x; runs in CI under `.github/workflows/pester.yml`).

| Cmdlet | Scope | Purpose |
|---|---|---|
| `Test-OrgPathFormat` | offline | Validates an OrgPath string against UIAO_151's canonical regex. |
| `Test-OrgPathHierarchy` | offline | Validates that a child OrgPath has a registered parent in the supplied codebook hashtable. |
| `Get-OrgTreeValidationReport` | live tenant | Walks tenant users via `Connect-MgGraph` + `Get-MgUser`; classifies each user's OrgPath against the codebook; returns a summary report. |
| `Test-DynamicGroupAlignment` | live tenant | Compares tenant dynamic groups against the canonical UIAO_152 library (passed as JSON); reports aligned / misaligned / missing. |
| `Export-OrgTreeSnapshot` | live tenant | Snapshots tenant users + OrgTree-* groups to a JSON file. |
| `Compare-OrgTreeSnapshots` | offline | Diffs two snapshot JSON files; emits drift entries (`NewObject`, `ValueDrift`). |
| `Invoke-UiaoOrgTreeValidate` | bridge | Shells out to `uiao orgtree validate all`; surfaces exit-code as `$result.Passed`. |

### Dependencies

Functions 3, 4, 5 require `Microsoft.Graph` (`Install-Module Microsoft.Graph`).
Functions 1, 2, 6 are pure pwsh and have no external module dependency.
The bridge cmdlet requires the `uiao` CLI on `PATH`.

### Test coverage

Pester covers all four offline-testable cmdlets:

- `Test-OrgPathFormat` — 8 cases (valid root, valid 1–4 level paths, lowercase rejection, missing prefix, under-min and over-max segment lengths).
- `Test-OrgPathHierarchy` — 4 cases (root, child of registered parent, leaf, missing parent).
- `Compare-OrgTreeSnapshots` — 3 cases (`ValueDrift`, `NewObject`, identical snapshots).
- **Canonical regex parity test** — extracts the `CANONICAL_REGEX` literal from `src/uiao/modernization/orgtree/codebook.py` at test time and asserts that `Test-OrgPathFormat` matches Python's behavior on a known sample. This is the load-bearing test that prevents the two surfaces from drifting.

Tenant-scope cmdlets (3, 4, 5) are smoke-tested manually against a
non-production tenant.

## Boundary rules

All cmdlets call Microsoft Graph, which is in-boundary for GCC-Moderate.
No cmdlet calls Azure Resource Manager, Azure CLI, or any commercial-cloud
API. The Python side has the same boundary contract, enforced by the
substrate walker's `boundary: GCC-Moderate` frontmatter requirement.

## Drift considerations

Both surfaces are governance artifacts. Behavior changes go through
the Workflow 8 (Governance Artifact Update) review per UIAO_155.
Cmdlet outputs and CLI outputs are first-class inputs to drift
classification (UIAO_163).

The canonical-regex parity test is the early-warning system: if either
side mutates the OrgPath regex without updating the other, Pester fails
on the next PR.

## Governance alignment

Implements Principle 4 (Drift Resistance): provides the tooling that
detects deviations.

Implements Principle 6 (Two-Brain Execution): the cmdlets and CLI verbs
are the tools the Execution Substrate (Microsoft Graph PowerShell SDK
session, or Python adapter session) runs against tenants; the
governance brain (Copilot review of PRs that change validation logic)
reviews the *implementations* of those tools.

Implements Principle 1 (Single Source of Truth): the Python side
authors the validation logic; the PowerShell side either calls back to
that authority or carries a parity-tested mirror. The mirror is
narrow (one regex literal today) and is asserted programmatically on
every PR via Pester.
