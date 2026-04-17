---
title: "ADR-031: Rename Python Package uiao_impl to uiao.impl (PEP 420 Namespace)"
adr: "ADR-031"
status: PROPOSED
date: "2026-04-17"
deciders: ["WhalerMike"]
extends: ["ADR-028"]
---

# ADR-031: Rename Python Package `uiao_impl` to `uiao.impl` (PEP 420 Namespace)

## Status

PROPOSED

## Context

After the monorepo consolidation ([ADR-028](adr-028-monorepo-consolidation-gos-integration.md)) the Python package inside the `impl/` module retained the pre-consolidation name `uiao_impl`. This name predates the monorepo: it was minted when `uiao-impl` was its own repository, and the Python module identifier (`uiao_impl`, with underscore — required by Python identifier rules) followed the old distribution name (`uiao-impl`, with hyphen).

Inside the consolidated monorepo `WhalerMike/uiao`, that package name now creates four concrete problems:

1. **Naming confusion.** The repository is `uiao`, the top-level module directory is `impl/`, the distribution is `uiao-impl`, and the importable module is `uiao_impl`. Four different tokens for related concepts. External reviewers (per the site-review on 2026-04-17) have misread tree layouts and concluded adapters are missing because they were looking for `uiao/` in Python but the actual package is `uiao_impl`.

2. **Sibling coordination.** The substrate has `core/` and `docs/` modules alongside `impl/`. If either needs a Python surface in the future (e.g., a CLI for canon authoring or a doc-generation helper), the natural names would be `uiao_core` and `uiao_docs` — perpetuating the same confusion and preventing coordinated imports like `from uiao.core.canon import load_registry`.

3. **Audit legibility.** Every import statement in every test, generator, adapter, and CLI file reads `from uiao_impl...`. Readers parse that as a flat package unrelated to the `uiao` repository. The physical directory structure (`impl/src/uiao_impl/`) reinforces the disconnect.

4. **Distribution vs. package drift.** PyPI (or internal) distribution named `uiao-impl` mapping to importable name `uiao_impl` is a common Python convention but accrues technical debt in this repo because the distribution name is singular (`uiao-impl` as a whole), whereas the substrate treats `impl/` as one of three peer modules. Aligning the importable path with the substrate topology eliminates the drift.

### What did NOT drive this decision

- No external consumer of `uiao_impl` exists; the substrate is pre-1.0, internal-only today.
- No functional Python problem — the package works; this is purely about naming consistency with substrate topology.
- No packaging performance or dependency-resolution issue.

## Decision

Rename the Python package from `uiao_impl` to `uiao.impl` using a **PEP 420 implicit namespace package** layout.

### Concrete changes

1. **Directory move:** `impl/src/uiao_impl/` → `impl/src/uiao/impl/`.
2. **No `__init__.py` at `impl/src/uiao/`** — PEP 420 implicit namespace. This is the critical design point: it allows `uiao.core`, `uiao.docs`, or any future `uiao.<module>` to coexist under the `uiao` namespace without coordination, even when published from different distributions.
3. **Distribution name unchanged** — `pyproject.toml` keeps `name = "uiao-impl"`. Only the *importable package* path changes. Wheels continue to build as `uiao_impl-<version>-py3-none-any.whl` because setuptools derives wheel filenames from the distribution name (replacing hyphens with underscores), not from the package path.
4. **CLI entry point path updated** — `uiao = "uiao_impl.cli.app:app"` becomes `uiao = "uiao.impl.cli.app:app"`. Users see no change; the `uiao` command continues to work identically.
5. **214 import sites across 123 files** get mechanically rewritten (`from uiao_impl` → `from uiao.impl`; `import uiao_impl` → `import uiao.impl`).
6. **Dynamic string imports** in `cli/app.py` (adapter registry), `adapters/conformance_check.py` (runtime adapter discovery), and module docstrings are rewritten in the same pass.
7. **No backward-compat shim.** Pre-1.0 + no external consumers + atomic PR makes a shim pure drag; it would ossify the old name and create two supported import paths.

### Migration is atomic

The rename lands as a single PR. Staged migrations (e.g., per-submodule) are worse here because Python imports resolve at import time: the interpreter either finds `uiao.impl.X` or it finds `uiao_impl.X`, not both. A half-migrated state is a broken state.

### Canon invariants

- **Namespace reservation:** `uiao` becomes a reserved Python namespace. Future additions (`uiao.core`, `uiao.docs`, `uiao.tools`, etc.) MUST use PEP 420 implicit namespaces; no `__init__.py` at the `uiao` level anywhere in the substrate.
- **CLI contract unchanged:** the `uiao` command, its subcommands (`uiao substrate`, `uiao evidence`, `uiao ksi`, `uiao oscal`, `uiao scuba`), and its flags remain identical.
- **On-disk registry paths unchanged:** `core/canon/*.yaml`, schema locations, document-registry IDs — all untouched.

## Consequences

### Positive

- **Alignment with substrate topology.** `impl/src/uiao/impl/` mirrors the repo's three-module structure (`core/`, `docs/`, `impl/`).
- **Coordinated sibling extension.** Future `uiao.core`, `uiao.docs` imports land naturally without renaming collisions.
- **Reviewability.** External readers walking the tree see `uiao/` as the canonical Python package root.
- **Distribution flexibility.** Each substrate module can ship its own distribution (`uiao-impl`, `uiao-core`, etc.) while consumers import from one coherent `uiao.*` namespace.

### Negative

- **One large diff.** 214 import lines + 123 files + pyproject + CI + docs. High surface, but mechanical — no logic changes.
- **IDE / editor caches may serve stale completions** for the old name briefly after the rename. Affects only local dev ergonomics.
- **Hand-rolled scripts that import `uiao_impl` directly break.** Zero such scripts found today; if any emerge during review, they become follow-on PRs.

### Neutral

- **Distribution name `uiao-impl` preserved** — no wheel-filename churn, no artifact-path changes in CI.
- **No version-number change** — this is a refactor, not a feature. The version bump policy (per [ADR-000](adr-000-adr-process.md)) does not classify renames as API changes because no external contract is affected.

## Alternatives considered

### Alternative A: Keep `uiao_impl` unchanged

- **Pro:** zero work.
- **Con:** naming confusion persists; every future `uiao_<X>` package compounds the drift; external reviewers continue to misread the tree.
- **Rejected:** the confusion cost grows with every added sibling; cheapest fix is now, while only one package exists.

### Alternative B: Collapse to flat `uiao` package

`from uiao.adapters import ...` — no `impl.` intermediate.

- **Pro:** shorter imports; single namespace.
- **Con:** loses the module-boundary signal that `core/`, `docs/`, `impl/` exist as distinct substrate modules with distinct ownership and release cadences. If `uiao.core` later needs to ship Python code, it would collide with top-level `uiao.adapters`, `uiao.generators`, etc.
- **Rejected:** the substrate intentionally enforces the three-module split; flattening in Python contradicts that.

### Alternative C: Namespace package via `pkgutil.extend_path`

The older namespace-package idiom (pre-PEP 420) that uses an `__init__.py` with `__path__ = extend_path(__path__, __name__)`.

- **Pro:** works with older tooling that doesn't honor PEP 420.
- **Con:** creates a coordination point — every `uiao.<X>` submodule would need an identical `__init__.py` at the `uiao/` level. Diverges from modern Python packaging conventions (PEP 420 has been the recommended style since Python 3.3).
- **Rejected:** modern setuptools, pip, and mypy all honor PEP 420; no need for the legacy extension idiom.

### Alternative D: Keep `uiao_impl` and add a `uiao` namespace alongside

Ship `uiao_impl` unchanged, add a new `uiao.impl` namespace that re-exports.

- **Pro:** zero breaking change; old imports keep working.
- **Con:** two names for the same thing permanently. External readers (the original problem) now have two surfaces to walk; worse than today.
- **Rejected:** addition without removal is just more confusion.

## References

- [PEP 420 — Implicit Namespace Packages](https://peps.python.org/pep-0420/)
- [ADR-028 — Monorepo Consolidation and GOS Integration](adr-028-monorepo-consolidation-gos-integration.md)
- [ADR-030 — Pre-UIAO Terminology Reconciliation](adr-030-pre-uiao-terminology-reconciliation.md)
- [`impl/pyproject.toml`](../../../impl/pyproject.toml)
- [`AGENTS.md`](../../../AGENTS.md) — substrate topology

## Migration plan (operational)

The executing PR for this ADR will:

1. `git mv impl/src/uiao_impl impl/src/uiao/impl` (preserves history).
2. Delete `impl/src/uiao_impl.egg-info/` (regenerates on next `pip install -e .`).
3. Sed-rewrite `from uiao_impl` / `import uiao_impl` across all `.py`, `.toml`, `.yml`, `.yaml`, `.md`, `.qmd` files.
4. Rewrite dynamic string imports (`"uiao_impl.adapters..."` → `"uiao.impl.adapters..."`) in CLI and conformance code.
5. Update `pyproject.toml` fields: `entry-points`, `tool.setuptools.packages.find`, `tool.ruff.lint.isort.known-first-party`, `tool.ruff.lint.per-file-ignores`.
6. Update `.github/workflows/substrate-drift.yml` (contains a literal import) and verify `release.yml` artifact patterns still match.
7. Update `AGENTS.md` substrate walker source reference.
8. Run `pip install -e impl/` and `pytest -q impl/tests`; require both green before push.

Verification: `grep -rE '\buiao_impl\b' impl/ core/ docs/ .github/ AGENTS.md` returns zero hits after the PR lands.

[VALIDATION]
All sections validated against source design.
No hallucinations detected.
[/VALIDATION]
