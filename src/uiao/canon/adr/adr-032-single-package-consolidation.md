---
title: "ADR-032: Single-Package Consolidation — flatten src/uiao/"
adr: "ADR-032"
status: ACCEPTED
date: "2026-04-20"
deciders: ["WhalerMike"]
extends: ["ADR-028", "ADR-031"]
---

# ADR-032: Single-Package Consolidation — flatten `src/uiao/`

## Status

ACCEPTED

## Context

ADR-028 consolidated the four predecessor repos (`uiao-core`, `uiao-docs`, `uiao-gos`, `uiao-impl`) into a single monorepo. ADR-031 renamed the `uiao_impl` distribution to expose its modules under the `uiao.impl.*` PEP 420 namespace. Both ADRs landed but preserved the pre-consolidation tree shape:

```
uiao/
├── core/                    # canon, schemas, rules, control library
│   └── pyproject.toml       # (not actually published)
├── impl/
│   ├── src/uiao/impl/       # Python code under uiao.impl.*
│   ├── scuba-runtime/       # PowerShell assets
│   ├── scripts/
│   ├── tests/
│   ├── pyproject.toml       # published as `uiao-impl`
│   └── .github/workflows/
├── docs/                    # Quarto site
├── src/uiao/                # partial scaffold, canon partially moved in
│   └── pyproject.toml       # published as `uiao`
└── .github/workflows/
```

Installing the codebase required **two** editable installs (`pip install -e . && pip install -e ./impl`), canon lived in two places (`core/data/`, `src/uiao/canon/`), three `pyproject.toml` files existed, and CI configs were split across `impl/.github/workflows/` and `.github/workflows/`. Fresh contributors (and AI agents) consistently tripped over which directory to edit, and `uiao.impl.*` imports required the sibling install to resolve at runtime.

Symptoms observed pre-consolidation:

1. **Two-step install.** A fresh clone needed both `pip install -e .` and `pip install -e ./impl` to bring a working CLI up. The first install gave you `uiao` as a namespace package with canon; the second populated `uiao.impl.*`. Either alone failed silently in surprising ways (e.g., `uiao --help` worked but every subcommand errored on import).
2. **Canon duplication.** `core/data/control-library/*.yml` and `src/uiao/canon/data/control-library/*.yml` held divergent snapshots because the reorg was mid-flight. The divergence wasn't detected until content comparison.
3. **Path drift in runtime code.** `Settings._resolve_canon_root()` searched `../core`, `../uiao-core`, and CWD-relative fallbacks in sequence to cope with the half-moved canon.
4. **Dependency inheritance.** Runtime deps (`jinja2`, `jsonschema`, `compliance-trestle`, `python-docx`, etc.) were declared only in `impl/pyproject.toml`; the root `pyproject.toml` listed a minimal set. `pip install -e .` alone therefore failed on first adapter invocation.
5. **Test authority unclear.** `impl/tests/` was authoritative but `core/tests/` also had a single test that duplicated coverage.

## Decision

Flatten the tree to a single Python package rooted at `src/uiao/`, with no sibling `core/` or `impl/` directories:

```
uiao/
├── src/uiao/
│   ├── __init__.py
│   ├── __version__.py       # SSOT for distribution version
│   ├── cli/                 # Typer app (was uiao.impl.cli)
│   ├── adapters/            # all adapters incl. scuba/, scubagear_adapter, bluecat_*
│   ├── canon/               # YAML SSOT, ADRs, specs (was core/canon + core/data)
│   ├── rules/               # KSI + NIST rule library
│   ├── schemas/             # JSON schemas for every registry/manifest
│   ├── ksi/                 # KSI evaluation (Plane 2)
│   ├── ir/                  # intermediate representation (Plane 1)
│   ├── evidence/ governance/ oscal/ ssp/ substrate/ ...
├── tests/
├── scripts/
├── docs/
├── .github/workflows/       # single CI stack
├── pyproject.toml           # single, with all runtime deps + dynamic version
└── AGENTS.md
```

Concretely:

1. **Move** `impl/src/uiao/impl/*` → `src/uiao/*`; rewrite every `uiao.impl.X` import to `uiao.X`.
2. **Move** `core/data/` + `core/compliance/reference/` → `src/uiao/canon/data/` + `src/uiao/canon/compliance/reference/`, letting pre-populated destinations win on conflict.
3. **Move** `impl/tests/` → `tests/`, `impl/scripts/` → `scripts/`, `impl/orchestrator/` → `src/uiao/orchestrator/`, unique workflows under `impl/.github/workflows/` → `.github/workflows/`.
4. **Consolidate packaging.** One `pyproject.toml` at the root with:
   - `dynamic = ["version"]` reading from `src/uiao/__version__.py` (SSOT).
   - All runtime deps declared (not inherited).
   - Optional extras: `dev`, `visuals`, `plantuml`.
   - `[tool.setuptools.package-data]` for `uiao.canon`, `uiao.rules`, `uiao.schemas`, `uiao.ksi`, `uiao.adapters` so canon ships with the wheel.
   - `[tool.pytest.ini_options]` with `testpaths = ["tests"]`.
5. **Collapse canon resolution.** `Settings._resolve_canon_root()` becomes a two-tier chain: `UIAO_CANON_PATH` env override, then `Path(__file__).parent` (the installed package). Sibling-checkout fallbacks retired.
6. **Delete** `core/` and `impl/` entirely. Unique governance docs from `core/` (`ARCHITECTURE.md`, `VISION.md`, `CONMON.md`, `PROJECT-CONTEXT.md`, `CODE_OF_CONDUCT.md`, `NOTICE`) promote to `docs/governance/`. Everything else is absorbed or retired.
7. **Sanitize** narrative `uiao-core` / `uiao-impl` references to `uiao` everywhere except ADRs, `CHANGELOG.md`, and `RELEASE_NOTES.md` (which are the historical record).

ADR-031's `uiao.impl.*` namespace is superseded: there is no `uiao.impl` anymore.

## Consequences

### Positive

- **One install step.** `pip install -e .` from a clean clone produces a working CLI and passing test suite.
- **Canon is addressable.** `importlib.resources.files("uiao.canon") / "data/control-library/AC-2.yml"` works from any CWD and survives `pip install --wheel`.
- **Version SSOT.** Drift between `pyproject.toml` and `__version__.py` (0.3.0 vs 0.2.1 pre-flatten) is mechanically impossible.
- **CI simplification.** One workflows directory, one pyproject, one package-data manifest. Future CI changes don't risk skew between the `impl/` and root copies.
- **AI agent onboarding.** Subagents no longer need to reason about which of `core/`, `impl/src/uiao/impl/`, or `src/uiao/` owns a given concern. The answer is always `src/uiao/<subpackage>/`.

### Negative

- **Bigger blast radius on the landing PR.** The consolidation PR (#111) touched 915 files. Most are renames and GitHub displays them as such, but review ergonomics suffer. Mitigated by committing in reviewable phases (canon, adapters, flatten, pyproject, sanitize) rather than one squash.
- **Rebase cost for in-flight branches.** Three open PRs (#108, #109, #110) at merge time needed rebasing onto new paths. Handled by superseding them with rebased equivalents (#112, #113, #114).
- **History archaeology.** `git log --follow <path>` still traces files through the moves, but casual browsers landing on `src/uiao/adapters/scubagear_adapter.py` in the GitHub UI won't see the pre-flatten history without the `--follow` flag.

### Neutral / noted

- **Mypy debt surfaced.** First type-check pass on the unified `src/uiao/` turned up 57 errors across 31 files — previously latent. Mypy runs non-blocking (`continue-on-error: true` in `.github/workflows/mypy.yml`) until burndown completes. Tracked separately.
- **`scripts/legacy-core/`** briefly held pre-flatten duplicates of 3 scripts that `core/scripts/` owned richer versions of; those were reconciled during cleanup. Prior versions remain in git history.

## Alternatives considered

1. **Leave the hybrid layout in place.** Rejected — installs were brittle, canon duplication was already causing silent bugs, and onboarding friction was measurable (three separate external reviewers asked "where are the adapters?" in PR comments over the preceding two weeks).

2. **Publish `uiao-core` and `uiao-impl` as separate distributions long-term.** Rejected — the two distributions had no independent consumer; every `uiao-impl` user also installed `uiao-core`. The split existed for historical (pre-consolidation) reasons, not architectural ones.

3. **Keep `core/` as the canon authority and `src/uiao/` as a consumer.** Rejected — canon belongs with the code that reads it so `importlib.resources` works. A sibling `core/` would re-introduce the path-resolution fallback chain that this ADR removes.

## References

- [ADR-028](adr-028-monorepo-consolidation-gos-integration.md) — monorepo consolidation (the four-repo merge)
- [ADR-031](adr-031-namespace-package-rename.md) — `uiao_impl` → `uiao.impl` rename, superseded by this ADR
- PR #111 — the consolidation implementation
- PRs #112, #113, #114 — rebased follow-ups (briefing tests, scubagear rename, BlueCat adapter) that landed against the flattened tree
