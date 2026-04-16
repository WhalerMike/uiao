---
title: "Phase D — Stage 4 App-Code Split (uiao-impl) Plan + Stage-0 Scan"
date: 2026-04-14
status: plan-and-scan (execution pending Stage 1-3 push)
parent: 2026-04-14-phase-d-plan.md
prerequisite: Stages 1, 2, and 3 must all be pushed first
---

# Phase D — Stage 4 app-code split (plan + scan)

Creates a fourth repository `WhalerMike/uiao-impl` and moves application code (library, CLI, generators, adapters, tests, app-side scripts) out of `uiao-core`. After Stage 4, `uiao-core` contains only canon, schemas, validator tooling, and canon workflows. Both CI pipelines install `uiao-impl` as a pip dependency.

**Status**: plan + stage-0 scan only. Execution hand-off batch follows in the next session (Stage 4.1, 4.2, 4.3 commit blocks) once Stages 1–3 are on `main`.

---

## Why Stage 4 needs its own session

Scans found **~150 internal `from uiao_core.*` imports spanning 94 files**. Mechanical `grep`+`sed` moves would break the import graph because the Python package name changes (`uiao_core` → `uiao_impl`). The move must be atomic across: source tree, tests, CLI entry, pyproject, workflow callers.

Safe sequencing:
1. Create `uiao-impl` repo, migrate code, rename package, re-pin tests — one commit cluster on `uiao-impl`.
2. Publish `uiao-impl` to the project index (git tag or private PyPI; minimum: installable via `pip install git+ssh://...@v0.1.0`).
3. Strip app-code out of `uiao-core`, rewire `uiao-core` workflows to `pip install uiao-impl` — second commit cluster on `uiao-core`.
4. Update `uiao-docs` if any `.qmd` has live code execution importing `uiao_core` (Stage-0 scan says: none).

---

## Stage-0 scan — what moves, what stays

### A. Moves to `uiao-impl` (leaves `uiao-core`)

| Path | Size/count | Notes |
|---|---|---|
| `src/uiao_core/` | 217 files | Entire Python package. Rename to `uiao_impl/` at destination. |
| `adapters/` | 21 files | Adapter implementations (AD, Entra, F5, SCuBA, etc.) |
| `scripts/` | 59 files | `generate_*.py`, `assemble_*.py`, `validate_with_trestle.py` — all `uiao_core`-importing |
| `tests/` | 98 files | All pytest suites; 38 files with `from uiao_core.*` imports |
| `cli/` | 1 file | Thin CLI wrapper; Typer app entry |
| `compliance/` | 8 files | Trestle/OSCAL implementation helpers |
| `orchestrator/` | (small) | `orchestrator.py` imports `uiao_core` |
| `inject_ssp.py` (root) | 1 file | `uiao_core`-importing |
| `write_engine.py` (root) | 1 file | `uiao_core`-importing |
| `pyproject.toml` | — | Rename `name = "uiao-core"` → `"uiao-impl"`, CLI entry `uiao_core.cli.app:app` → `uiao_impl.cli.app:app` |

### B. Stays in `uiao-core`

| Path | Why |
|---|---|
| `canon/` | Canonical data (SSOT, YAMLs) — post-Stage-2 already here |
| `schemas/` | JSON schemas — post-Stage-2 already here |
| `tools/` | Canon enforcement (`sync_canon.py`, `metadata_validator.py`, `drift_detector.py`, `dashboard_exporter.py`, `appendix_indexer.py`) — **zero imports of `uiao_core`** per scan |
| `playbooks/` | Operational docs |
| `appendices/` | Canon appendices |
| `.claude/`, `CLAUDE.md` | Canon-side agent config |
| Canon-side workflows (see C below) | |

### C. Workflow split

Canon-side workflows stay in `uiao-core`; app-side workflows move (or get rewritten to install `uiao-impl`):

| Workflow | Currently calls | Disposition |
|---|---|---|
| `appendix-sync.yml` | `tools/appendix_indexer.py` | **Stay** — canon tool |
| `canon-sync-dispatch.yml` | `tools/sync_canon.py` | **Stay** — canon plumbing |
| `dashboard-export.yml` | `tools/dashboard_exporter.py` | **Stay** — canon tool |
| `drift-scan.yml` | `tools/drift_detector.py` | **Stay** — canon tool |
| `metadata-validator.yml` | `tools/metadata_validator.py` | **Stay** — canon tool |
| `canon-validation.yml` | `scripts/*.py` | **Rewrite**: `pip install uiao-impl` then call CLI |
| `ai-security-audit.yml` | `scripts/*.py` | **Rewrite**: `pip install uiao-impl` |
| `crosswalk-regeneration.yml` | `scripts/*.py` | **Rewrite** or **move to uiao-impl** |
| `repo-hygiene.yml` | `scripts/*.py` | **Rewrite** or **retire** |
| `deploy.yml` | `scripts/*.py` | **Retire** (Stage 3 already targets it) |

The `scripts/` callers that remain relevant post-Stage-3 boil down to: OSCAL generation, POAM generation, SSP assembly, trestle validation, Rich-formatted DOCX for canon appendices, chart generation for dashboard export. All of these are app-code-adjacent and follow `uiao_impl` to the new repo; `uiao-core` calls them via `pip install uiao-impl && uiao <subcommand>`.

### D. Cross-repo impact

| Consumer | Change |
|---|---|
| `uiao-docs` `.qmd` code blocks | **None** — scan confirms no `.qmd` file imports `uiao_core` |
| `uiao-docs` `deploy-docs.yml` | **None** — Quarto render is pure-docs |
| `uiao-docs` `dashboard-export.yml` | **None** — calls `../uiao-core/tools/dashboard_exporter.py` which stays |
| `uiao-gos` | **None** — firewalled commercial scaffold, no uiao_core import |
| External pip consumers | `uiao-core` no longer installable as a package; install `uiao-impl` instead. Release note in CHANGELOG. |

---

## Package rename boundary

**Choice**: rename `uiao_core` → `uiao_impl` during the split, not after.

Rationale:
- Keeps the *repository* name semantically accurate (`uiao-core` = canon, `uiao-impl` = implementation)
- Prevents confusion where a `uiao-core` pypi package lives in a `uiao-impl` git repo
- One atomic rename pass is cheaper than two (rename now vs. rename later)

Mechanical scope of rename:
- `src/uiao_core/` → `src/uiao_impl/` (directory)
- `from uiao_core` → `from uiao_impl` (~150 occurrences across 94 files)
- `import uiao_core` → `import uiao_impl` (handful)
- `pyproject.toml`: `name`, `[project.scripts]` entry, `[tool.setuptools.packages.find]`
- `src/uiao_core/__init__.py` references to `__version__` — stay local
- `src/uiao_core/__version__.py` — carried over, namespace follows
- Docstrings / README / comments mentioning `uiao_core` the package — sweep with `sed` in one pass, review diff

A clean one-shot sed pass works because `uiao_core` the string only appears as:
- the Python package namespace (rename target)
- occasional references in prose documentation (rename is still correct — prose now describes the new `uiao_impl` package)

Verified: no clashes with repository name strings or canon file names — `canon/data/` YAMLs use kebab-case and never reference the Python namespace.

---

## Stage 4 execution plan (hand-off batch in next session)

Four batches:

### Batch 4.0 — Create `uiao-impl` repo (manual + gh CLI)

Happens on Michael's side via GitHub web UI or `gh repo create WhalerMike/uiao-impl --private --clone`. Before running Batch 4.1.

### Batch 4.1 — Populate `uiao-impl` from `uiao-core` tree

PowerShell block on Michael's machine:
1. `cd C:\Users\whale\uiao-impl`
2. Copy `src/uiao_core/` → `src/uiao_impl/`
3. Copy `adapters/`, `scripts/`, `tests/`, `cli/`, `compliance/`, `orchestrator/`
4. Copy `inject_ssp.py`, `write_engine.py`
5. Copy `pyproject.toml`, rename package, update CLI entry
6. Run the rename sweep: `Get-ChildItem -Recurse -Include *.py | ForEach-Object { (Get-Content $_) -replace 'from uiao_core', 'from uiao_impl' -replace 'import uiao_core', 'import uiao_impl' | Set-Content $_ }`
7. Add a minimal `README.md`, `CLAUDE.md`, `.github/workflows/ci.yml`
8. `pip install -e .` locally, `pytest` to verify nothing broke
9. Commit + push + tag `v0.1.0`

### Batch 4.2 — Strip app-code from `uiao-core`

PowerShell block:
1. `git rm -r src adapters scripts tests cli compliance orchestrator`
2. `git rm inject_ssp.py write_engine.py`
3. Rewrite `pyproject.toml` to a minimal canon-only declaration (remove `[project.scripts]`, remove package-find config, keep only tooling deps — `pyyaml`, `jsonschema`, `click` if `tools/` uses it)
4. `git rm` the four app-side workflows that won't be rewritten: `deploy.yml` (already in Stage 3), `generate_artifacts.yml` (already in Stage 3). Rewrite `canon-validation.yml`, `ai-security-audit.yml`, `crosswalk-regeneration.yml`, `repo-hygiene.yml` to `pip install uiao-impl@v0.1.0` and call the CLI
5. Update `.gitignore` to drop `src/` / `adapters/` / `tests/` etc.
6. Commit + push

### Batch 4.3 — Smoke test both repos

1. Push triggers `uiao-core` CI: canon validators + metadata validators run without app code.
2. Push triggers `uiao-impl` CI: full pytest suite.
3. Manual: `pip install uiao-impl` from tag, run `uiao --help`, `uiao validate`, `uiao generate-ssp`.

---

## Deferred — known unknowns

| Item | Resolution |
|---|---|
| Does `uiao-impl` need access to canon YAMLs at runtime? | **Yes** — `generate_ssp`, `generate_poam`, `validate` all read `canon/data/*.yml`. Pattern: `uiao-impl` CLI takes `--canon-path` flag, defaults to `./canon` (CI passes the cross-repo-checked-out path). |
| Does `uiao-impl` depend on `uiao-core` schemas? | **Yes** — `metadata_validator.py` references `schemas/uiao-governance.schema.json`. Options: (a) publish schemas as a data dependency `uiao-core-schemas` pip package, (b) `uiao-impl` CLI takes `--schema-path` (simpler; ship schemas as canon). **Recommend (b)** — schemas are small and canon-side. |
| Does `uiao-impl` need Python 3.11 vs 3.12? | Whatever `uiao-core/pyproject.toml` currently pins. Carry over. |
| GitHub branch protection rules | Apply same rules (`main` protected, required checks) to new `uiao-impl` repo. |
| Secrets propagation | `CROSS_REPO_TOKEN`, `CANON_SYNC_PAT` must be added to `uiao-impl` org/repo secrets. |

---

## Expected outcomes after Stage 4

| Repo | Role | Top-level entries (approx) |
|---|---|---|
| `uiao-core` | Canon + schemas + enforcement | `canon/`, `schemas/`, `tools/`, `playbooks/`, `appendices/`, `.claude/`, `.github/workflows/` (5 validators), root docs |
| `uiao-impl` | Python package + CLI + tests | `src/uiao_impl/`, `adapters/`, `tests/`, `scripts/`, `cli/`, `compliance/`, `pyproject.toml`, `README.md`, `.github/workflows/` (ci, publish) |
| `uiao-docs` | Documentation + Quarto | `docs/`, `visuals/`, `assets/`, `exports/`, `canon` (if docs need local canon reference) |
| `uiao-gos` | Commercial AD→Entra product | unchanged (separate boundary) |

After Stage 4, `uiao-core` drops from ~72 top-level entries (post Stage 3) to ~15, and the `uiao-core` clone size drops another ~50 MB (tests + wheels + caches).

---

## What Stage 4 does NOT fix

| Issue | Stage |
|---|---|
| Remaining duplicate workflow pairs between `uiao-core` and `uiao-docs` | Stage 5 |
| Relative path cleanup in `.qmd` files post-pipeline move | Stage 6 |
| `ARCHITECTURE.md`, `CLAUDE.md`, `README.md` refresh across all four repos | Stage 7 |
| `canon-sync` scaffold scanner update for the new four-repo topology | Stage 5 |

---

## Next up

After Stages 1–3 are pushed, return here to execute Stage 4. The hand-off batch (4.0, 4.1, 4.2, 4.3 PowerShell blocks with exact commands) will be drafted in the next session against the actually-shipped Stage 3 state, since Stage 3 retires several files that the current plan assumes absent.

---

## Addendum — 2026-04-14 session resumption (post-recovery)

Between the initial plan draft and execution, a cleanup-script mishap over-deleted tracked files in `uiao-core`. Full `git restore .` recovered the working tree at `HEAD 02af2e63` with no permanent damage. The empty `WhalerMike/uiao-impl` repo was created on GitHub during the same session. Batch 4.0 is therefore already partially complete (GitHub-side shell created; local clone pending).

### Resolved decisions (locked)

| Q | Decision | Rationale |
|---|---|---|
| Q1 — package namespace | **Rename `uiao_core` → `uiao_impl`** | No external `import uiao_core` consumers exist; rename is one atomic sed pass; keeps repo-name semantically aligned with package-name. |
| Q2 — spec-dir handling | **Consolidate 18 single-`.md` spec dirs into `canon/specs/`** | Eighteen top-level dirs each containing one `.md` is an anti-pattern; flat `canon/specs/*.md` is the canon convention. |
| Q3 — top-level `adapters/` and `orchestrator/` | **Both move to `uiao-impl`** | Per-file import scan: both are self-contained (stdlib + rich + typer); zero `uiao_core` imports; active Python code. Orchestrator's `Compliance-Orchestrator.md` spec splits off to `canon/specs/`. |

### Revised directory classification (final)

Fresh scan confirmed the following buckets. Differences from the initial plan are flagged **(CORRECTION)**.

**Bucket A — moves to `uiao-impl`** (Python app code)
- `src/uiao_core/` → `src/uiao_impl/` (rename during copy)
- `tests/` (43 files with `from uiao_core` imports)
- `scripts/` (9 files with `from uiao_core` imports)
- `adapters/` (top-level; 4 subdirs; no `uiao_core` imports — move as-is)
- `orchestrator/orchestrator.py` + `orchestrator/__init__.py` (active CLI; no `uiao_core` imports)
- `inject_ssp.py` (root)
- `write_engine.py` (root)
- `pyproject.toml` (rewrite as `uiao-impl`)
- `.coveragerc`

**Bucket B — stays in `uiao-core`** (canon + enforcement)
- `canon/`, `schemas/`, `data/`, `rules/` (167 YAML), `ksi/` (10 YAML), `analytics/`, `config/` (4 JSON)
- `tools/` (canon enforcement; zero `uiao_core` imports)
- `compliance/reference/` (NIST PDFs, FedRAMP playbook, ATO overlay) — canon reference material
- `playbooks/`, `appendices/`, `.claude/`, `.github/workflows/` (canon-side only)
- Root docs: `ARCHITECTURE.md`, `CHANGELOG.md`, `CLAUDE.md`, `CODE_OF_CONDUCT.md`, `CONMON.md`, `CONTRIBUTING.md`, `LICENSE`, `NOTICE`, `PROJECT-CONTEXT.md`, `README.md`, `RELEASE_NOTES.md`, `SECURITY.md`, `VISION.md`

**Bucket C — purge** (Stage 3 residue + build cruft)
- `dryrun-output/` (generator output)
- `scuba-real-run/` (one-off run artifacts)
- `site/` (Quarto render output)
- `artifacts/`, `reports/`, `provenance/` (build outputs)
- `dashboard/_quarto.yml`, `dashboard/index.qmd` **(CORRECTION — Stage 3 missed this subdirectory)**
- `src/uiao_core.egg-info/` (build metadata)
- `.coverage` (pytest cache artifact)
- `machine/` (skeleton — five subdirs containing only empty-scaffold READMEs)

**Bucket D — consolidate to `canon/specs/`** (single-`.md` spec dirs)
- `api/api-contract.md` → `canon/specs/api-contract.md`
- `cli/uiao-cli.md` → `canon/specs/cli.md` **(CORRECTION — plan previously misclassified top-level `cli/` as app code; actual CLI is `src/uiao_core/cli/`)**
- `cql/*.md` → `canon/specs/cql.md`
- `drift/*.md` → `canon/specs/drift.md`
- `enforcement/runtime/enforcement-runtime.md` → `canon/specs/enforcement.md`
- `evidence/*.md` (2 files) → `canon/specs/evidence-*.md`
- `governance/*.md` → `canon/specs/governance.md`
- `ha/*.md` → `canon/specs/ha.md`
- `machine/README.md` (root) → `canon/specs/machine-scaffold.md` (then purge the subdir skeletons)
- `performance/*.md` → `canon/specs/performance.md`
- `platform/*.md` (2 files) → `canon/specs/platform-*.md`
- `policy/*.md` → `canon/specs/policy.md`
- `recovery/*.md` → `canon/specs/recovery.md`
- `release/*.md` → `canon/specs/release.md`
- `tenancy/*.md` → `canon/specs/tenancy.md`
- `testing/*.md` (2 files) → `canon/specs/testing-*.md`
- `zero-trust/*.md` → `canon/specs/zero-trust.md`
- `data-lake/Data-Lake-Model.md` → `canon/specs/data-lake.md`
- `orchestrator/Compliance-Orchestrator.md` → `canon/specs/orchestrator.md` (the `.py` siblings move to `uiao-impl` in Bucket A)

**Bucket E — holding** (decide in Stage 5)
- `deploy/sentinel_alerts.bicep` — Azure Bicep infra definition. Neither canon nor Python. Stays in `uiao-core` under `infra/` until the infra-split story lands.

### Import footprint (measured)

- `tests/`: 43 files with `from uiao_core` / `import uiao_core`
- `scripts/`: 9 files
- root `.py`: 0 (both `inject_ssp.py` and `write_engine.py` are standalone)
- `.qmd` files across all three docs repos: 0
- Total sed-rename sites: ~150 occurrences across 94 files (matches initial scan)

### Execution hand-off — PowerShell batches

Four scripts now live under `docs/session-logs/scripts/`:

1. `stage-4-batch-4.0-init-uiao-impl.ps1` — clone empty `uiao-impl`, seed `pyproject.toml`, `README.md`, `CLAUDE.md`, `.gitignore`, `.github/workflows/ci.yml`, commit as `chore(init)`.
2. `stage-4-batch-4.1-populate-uiao-impl.ps1` — copy Bucket A from `uiao-core` working tree into `uiao-impl`, rename `src/uiao_core/` → `src/uiao_impl/`, sed-sweep `uiao_core` → `uiao_impl` across `*.py` and `pyproject.toml`, `pip install -e .`, `pytest`, commit as `feat(split): migrate app code from uiao-core`, tag `v0.1.0`.
3. `stage-4-batch-4.2-strip-uiao-core.ps1` — in `uiao-core`: `git rm` Bucket A + Bucket C, consolidate Bucket D to `canon/specs/`, rewrite `pyproject.toml` to canon-only, update `.gitignore`, commit as `[UIAO-CORE] MIGRATE: uiao_impl — app code split out, canon spec consolidation`.
4. `stage-4-batch-4.3-smoke-test.ps1` — verify `uiao-impl` is pip-installable from tag, `uiao --help` works, canon tools in `uiao-core/tools/` still import without the app package.

Each script is idempotent-where-possible and opens with a `Set-Location` + git-status check; none runs `git push` without an interactive confirm prompt.
