# Changelog

All notable changes to UIAO are documented here. Format adapted from [Keep a Changelog](https://keepachangelog.com/); versioning follows [Semantic Versioning](https://semver.org/). Pre-1.0 minor versions may carry breaking changes.

## [0.4.0] — 2026-04-23

**Theme: substrate-governance realignment + CI-gate restoration.** Landing this arc closes every silently-disabled quality gate that accumulated after the ADR-032 single-package consolidation (2026-04-20). Every Python quality signal on `main` is now actively enforced.

### Added

- **ADR-044** (`src/uiao/canon/adr/adr-044-substrate-governance-realignment.md`) — ratifies the post-ADR-032 alignment of UIAO_200, UIAO_201, the workspace-contract schema, the substrate walker, and the substrate-drift CI step to the single-package topology (#151).
- **UIAO_200 Substrate Manifest v2.0** — six-module topology (`uiao`, `tests`, `docs`, `scripts`, `inbox`, `deploy`); sub-boundaries inside `uiao/`; `role` enum widened from `[authority, consumer]` to `[authority, consumer, package, tooling, staging, deploy]` (#151).
- **UIAO_201 Workspace Contract v2.0** — `module_paths` mirrors v2.0 manifest; `build_outputs.package_dist` (was `impl_dist`); `canon_consumer_rule` retargeted (#151).
- **UIAO_008 CLI Reference v1.0** — promoted from top-level shadow `canon/UIAO_132_CLI_Reference_v1.0.md`; reallocated from UIAO_132 (collision with FedRAMP RFC-0026 spec) into the UIAO_002-099 top-level-canon range (#154).
- **UIAO_005 / UIAO_006 / UIAO_007** — promoted from top-level shadow canon (`SCuBA Value Proposition`, `AODIM Architecture`, `OrgTree Modernization`) with schema-conformant provenance (#154).
- **UIAO_001 SSOT v1.1** — expanded from a 21-line stub into a full authoritative doctrine: post-ADR-032 topology table, canon-consumer rule pointer, provenance chain model, 5-class drift taxonomy, canon change process (#167).
- **`src/uiao/rules/canon-consumer.md`** — new post-ADR-032 canon-consumer rule (importlib.resources reads, read-only runtime); supersedes the retired pre-consolidation rule under `impl/.claude/rules/` (#151).
- **`tests/test_api_smoke.py`** — three smoke tests on `uiao.api.app:app` (importability, route-prefix presence, openapi schema generation). Caught a latent production-deploy import bug that no other test surfaced (#158).
- **`[api]` optional extra** — declares `fastapi>=0.110`, `httpx>=0.27`, `uvicorn>=0.29`, `msal>=1.28` so `uiao.api.*` and the gcc-boundary-probe adapter actually resolve (#152, #158).
- **`[dev]` extra** — adds `types-PyYAML`, `types-requests` for mypy typeshed stubs.
- **Substrate-walker `docs/` scan** — extended to walk `docs/**/*.{md,qmd}` for code-path citations; new tests; 42 P2 narrative-drift warnings surface on current tree (non-blocking) (#166).
- **Two new walker tests** covering the docs-scan behavior (#166).

### Changed

- **Ruff gate → blocking.** 230-finding baseline cleared (128 via `ruff check --fix`, 7 via `--unsafe-fixes`, ~76 via `ruff format` splitting one-line dataclasses, 13 manual). Step-level `continue-on-error` on `ruff format --check` also removed (Copilot review) (#153).
- **Mypy gate → blocking with strict flags.** 130 findings burned down across four batches (#161, #162, #163, #164); `disallow_untyped_defs = true` + `warn_return_any = true` restored with 77 additional fixes (#165). Per-module overrides for docx-heavy generators + adapter-reflection surfaces documented inline.
- **Full pytest gate → blocking.** Restored after `[api]` dep declaration unblocked `tests/test_auditor_api.py` collection (#152).
- **`substrate-drift.yml`** — gates on `report.blocking` (P1) rather than `report.ok` (any finding), matching the `uiao substrate drift` CLI semantics; push-path filters made symmetric with pull_request filters (#151, #157).
- **CI path filters** repaired in all 7 workflows that still referenced the retired `impl/**` / `core/canon/` / `src/uiao/impl/**` paths (#150, #151). `adapter-conformance.yml` triggers widened to include registry + schema edits (#157).
- **Substrate walker** (`src/uiao/substrate/walker.py`) retargeted from `core/canon/*` to `src/uiao/canon/*`; `IMPL_REF_PATTERN` renamed `CODE_REF_PATTERN` and broadened to match both `src/uiao/` and `impl/` prefixes; `SubstrateReport.impl_refs_checked` renamed `code_refs_checked` (JSON contract change) (#151).
- **`workspace-contract.schema.json`** — `module_paths.required` narrowed to `[uiao, tests, docs]` with `minProperties: 3`; `build_outputs.impl_dist` → `package_dist`; `canon_consumer_rule.const` retargeted (#151).
- **`src/uiao/api/routes/routes.py`** split into `health.py` / `survey.py` / `orgpath.py`. The stitched file had been preventing `uiao.api.app` from importing — another latent production bug (#158).
- **README.md / Makefile / AGENTS.md** — rewritten for the flattened `src/uiao/` layout; obsolete `core/` / `impl/` references removed (#147, #151, #153-165).
- **`adapter-conformance.yml`** — now triggers on registry + schema edits in addition to adapter code (#157).
- **`release.yml`** — job renamed ("Build impl/ wheel and sdist" → "Build wheel and sdist"); `impl-dist-*` artifact → `uiao-dist-*`; `working-directory: impl` dropped; sigstore-verify snippet retargeted `uiao_impl-*` → `uiao-*` to match the distribution name (#150).
- **Schema-description cleanup** across `src/uiao/schemas/` — 4 stale `core/schemas/` / `core/canon/` path references in description strings retired to `src/uiao/schemas/` / `src/uiao/canon/` (#159).
- **Canon narrative drift cleared** — 11 P2 DRIFT-PROVENANCE warnings from ADR prose retired (ADR-028/029/031/032/044, UIAO_121/122/126) by retargeting `impl/...` citations to current `src/uiao/...` paths with historical notes (#156).

### Fixed

- **Production-deploy bug #1** — `deploy/windows-server/run.py` retargeted from the retired `uiao.impl.api.app:app` to `uiao.api.app:app`; `C:\srv\uiao\impl\src` sys.path shim removed (#150, #153).
- **Production-deploy bug #2** — two adapter directories with hyphens in their names (`active-directory/`, `gcc-boundary-probe/`) renamed to the underscore form (`active_directory/`, `gcc_boundary_probe/`). Hyphenated dir names are invalid Python package identifiers; every `from uiao.adapters.modernization.active_directory...` import was literally unresolvable. Locally masked because `msal` was missing; would have failed at startup on IIS (#155).
- **Production-deploy bug #3** — `src/uiao/api/app.py` imported `health`, `survey`, `orgpath` from `.routes` as if they were modules, but the symbols lived inside a single stitched `routes.py`. Split into separate files (#158).
- **Production-deploy bug #4** — `src/uiao/ir/mapping/ksi_to_ir.py` passed `hash=None` to `ProvenanceRecord(...)`; the field is `content_hash` (#165).
- **Hyphen-named dirs elsewhere** — substrate-walker now discoverable by mypy (was aborting at startup) (#155).

### Deprecated / Removed

- Top-level shadow canon directory (`canon/UIAO_005_*.md`, etc.) removed; contents promoted under `src/uiao/canon/` with registry entries (#154).

### Canon

- UIAO_001 SSOT v1.0 → **v1.1** (CANONICAL)
- UIAO_200 Substrate Manifest v1.0 → **v2.0** (OPERATIONAL)
- UIAO_201 Workspace Contract v1.0 → **v2.0** (OPERATIONAL)
- **UIAO_005** SCuBA Value Proposition (new registered) (CANONICAL)
- **UIAO_006** AODIM Architecture (new registered) (CANONICAL)
- **UIAO_007** OrgTree Modernization — AD to Entra ID (new registered) (CANONICAL)
- **UIAO_008** UIAO-Core CLI Reference (new registered) (CANONICAL, Draft)
- **ADR-044** Substrate Governance Realignment to Post-ADR-032 Single Package (ACCEPTED)
- **`src/uiao/rules/canon-consumer.md`** rewritten for the post-ADR-032 world

### CI stack state after 0.4.0

| Gate | Status |
|---|---|
| `schema-validation.yml` | ✅ blocking |
| `pytest.yml` | ✅ blocking (substrate fast + full suite) |
| `substrate-drift.yml` | ✅ blocking (P1 only; walker now works) |
| `metadata-validator.yml` | ✅ blocking |
| `adapter-conformance.yml` | ✅ blocking (330/330) |
| `ruff.yml` | ✅ blocking |
| `mypy.yml` | ✅ blocking (strict flags) |
| `quarto.yml` | ✅ render; deploy on main |
| `link-check.yml` | 🟡 soft-fail (repo config) |
| `release.yml` | build/sigstore/SBOM on tag |

### Infrastructure

- **Release workflow dry-run** — `python -m build --sdist --wheel` verified clean from the repo root; `uiao-0.4.0-py3-none-any.whl` + `uiao-0.4.0.tar.gz` produced; wheel filename pattern matches `release.yml`'s sigstore verification snippet. End-to-end run with sigstore signing requires a tag push from the owner's session.

### Local verification (pre-0.4.0 cut)

- `mypy src/uiao --ignore-missing-imports` → Success: no issues found in 171 source files.
- `pytest -q` → 1587 passed, 156 skipped, 0 failed.
- `ruff check .` → All checks passed.
- `ruff format --check .` → clean.
- `uiao substrate drift` → PASS with 42 P2 docs-narrative warnings (P1-only gate, non-blocking).
- `python -m build` → wheel + sdist produced clean.

---

## [Unreleased]

### Added
- Contributor foundation at repo root: `CONTRIBUTING.md`, `SECURITY.md`, `CLAUDE.md`, PR template, four structured issue templates (bug, canon-change, adapter-activation, governance-drift) (#37).
- `CODEOWNERS` re-established at `.github/CODEOWNERS` with canon/adapter-scoped ownership (#36).
- Tag-triggered release workflow building `impl/` wheel + sdist and attaching to GitHub Releases (#36).
- `.lycheeignore` baseline covering CI-predictable false-positive link-check patterns (#35).
- `dependabot.yml` at `.github/dependabot.yml` tracking `pip` (under `/impl`) and `github-actions` weekly (#21).
- First live CI at repo root:
  - `schema-validation.yml` — adapter registries, substrate manifest, workspace contract, metadata schema (#6)
  - `pytest.yml` — substrate walker (blocking) + full impl (blocking as of #19) (#11, #19)
  - `substrate-drift.yml` — `uiao substrate drift` on every canon PR (#16)
  - `metadata-validator.yml` — canon document frontmatter, blocking as of #20 (#17, #20)
  - `quarto.yml` — render on PR + deploy to GitHub Pages on push to main (#22)
  - `ruff.yml` — blocking as of #34 (#28, #34)
  - `link-check.yml` — lychee baseline, soft-fail initial state (#29)
- `UIAO_200` Substrate Manifest (`core/canon/substrate-manifest.yaml`) + schema (#4).
- `UIAO_201` Workspace Contract (`core/canon/workspace-contract.yaml`) + schema (#7).
- `UIAO_121–UIAO_124` adapter-framework specs properly registered in `document-registry.yaml` after renumbering from slug-style IDs (#20).
- Substrate walker + drift bootstrap at `impl/src/uiao_impl/substrate/walker.py` with `uiao substrate walk` / `uiao substrate drift` CLI, 10 tests (#8).
- `ADR-028` ratifying monorepo consolidation and retiring the `uiao-gos` federal/commercial firewall (#5).

### Changed
- **CyberArk adapter promoted** from `reserved/phase-planning` → `active/phase-1` in `core/canon/modernization-registry.yaml` (#32). 9 of 10 modernization adapters now active; only `mainframe` remains reserved (z/OS Connect infrastructure dependency).
- **Infoblox adapter promoted** from `reserved/phase-planning` → `active/phase-1` with NIOS >=8.0 runtime and FedRAMP-authorized annotation (#3).
- `docs/narrative/governance-os-directory-migration.md` rewritten from the migrated `uiao-gos` README into a substrate-aligned canonical narrative that closes the ADR-028 doctrinal loop (#31).
- `core/ARCHITECTURE.md` §2 rewritten from four-repository topology to three-module monorepo topology; `uiao-gos` firewall section replaced with "Uniform canon invariants" (#5).
- `core/CONMON.md` scope line retargeted from "federal pair, uiao-gos out of scope" to all monorepo modules (#5).
- `ADR-025 §D7` marked SUPERSEDED by ADR-028; partial-supersession banner added at ADR-025 top so readers arriving from any section see the relationship immediately (#14).
- Monorepo-aware canon path resolution in `impl/src/uiao_impl/config.py` and `impl/tests/canon_paths.py` — unblocks the full impl pytest suite (#15).
- Typer arguments: `B008` added to ruff ignore list (legitimate Typer idiom, not a bug) (#34).
- `docs/_quarto.yml`: `site-url` and `repo-url` retargeted from `uiao-docs` to the consolidated `uiao` repo (#22).
- Metadata validator soft-fail → blocking after renumbering 4 slug-style adapter-spec IDs (#20).
- Ruff soft-fail → blocking after burning down the 16 residual lint errors (#34).
- Pytest full-impl soft-fail → blocking after canon-path fix merged (#19).

### Removed
- `gos/` directory retired; its contents integrated into the canonical UIAO substrate (#3). Python code relocated to `impl/src/uiao_impl/directory_migration/`; IPAM adapters registered canonically; narrative moved to `docs/narrative/`.
- `impl/src/uiao_impl/directory_migration/` Python scaffolding (38 files, ~1,600 LOC) — all ARC-5 stubs with broken `from core.*` imports and zero callers. Markdown reference docs pointed to by registry entries retained (#12).
- `impl/src/uiao_impl/directory_migration/drift/drift_engine.py` — unused duplicate of `impl/src/uiao_impl/governance/drift.py` (#9).
- 3 stub provider adapters (entra, m365, servicenow) under `directory_migration/providers/` that duplicated mature implementations under `impl/src/uiao_impl/adapters/*.py` (#10).
- `core/.github/` tree (33 files — 24 inert workflows + CODEOWNERS + 7 issue templates + dependabot.yml) — GitHub only reads `/.github/`; these contributed nothing post-consolidation (#13).
- 211 tracked build artifacts from `docs/site/` (Quarto rendered output) and `docs/exports/{docx,pptx}` — already in `.gitignore` but predated the rule (#2). Working-tree savings: 160 MB.
- 128.9 MB of redundant PNG bytes via two pngquant passes (PR #18: 120.7 MB from 30 files ≥1 MB; PR #30: 8.2 MB from 26 files 100 KB–1 MB).

### Canon
- UIAO_200 UIAO Substrate Manifest (OPERATIONAL)
- UIAO_201 UIAO Workspace Contract (OPERATIONAL)
- UIAO_121 UIAO Adapter Conformance Test Plan — Template (CANONICAL)
- UIAO_122 UIAO Adapter Developer Training Program (CANONICAL)
- UIAO_123 UIAO Adapter Integration & Test Plan — Canonical Template (CANONICAL)
- UIAO_124 UIAO Adapter Operations Runbook (CANONICAL)
- ADR-028 Monorepo Consolidation and Integration of `uiao-gos` (ACCEPTED)

### Infrastructure
- Four predecessor repos (`uiao-core`, `uiao-docs`, `uiao-gos`, `uiao-impl`) merged into `WhalerMike/uiao` with **3,549 commits of history preserved** via git subtree merges (#1).

---

## Conventions

**Version tagging:** `vMAJOR.MINOR.PATCH` pushed as git tag → triggers `.github/workflows/release.yml` → builds wheel + sdist from `impl/`, creates GitHub Release with auto-generated notes.

**Pre-1.0 semantics:** minor version bumps may include breaking changes; read the [Unreleased] section carefully before upgrading across minor versions.

**Issue links:** `(#NN)` refers to `https://github.com/WhalerMike/uiao/pull/NN` unless otherwise noted.

## [0.3.0] — 2026-04-20

### Added
- **Single-package monorepo** consolidating `core/`, `impl/`, and partial `src/` into one `src/uiao/` Python package. `pip install -e .` now installs everything in one step; canon, rules, schemas, and KSI library ship as package data via `importlib.resources`. See [ADR-032](src/uiao/canon/adr/adr-032-single-package-consolidation.md).
- Full runtime dependency declarations in `pyproject.toml` (`jinja2`, `jsonschema`, `python-docx`, `python-pptx`, `openpyxl`, `matplotlib`, `compliance-trestle`, `compliance-trestle-fedramp`, `lxml`, etc.) — previously inherited from the separate `uiao-impl` editable install.
- Dynamic version from `src/uiao/__version__.py` via `[tool.setuptools.dynamic]` (SSOT; resolves prior drift between `pyproject.toml` and the module).
- Optional extras: `[dev]`, `[visuals]`, `[plantuml]`. Classifiers, keywords, `[project.urls]`, and root-level `[tool.pytest.ini_options]` added.
- `BlueCatAdapter` (BAM Tier-4 IPAM adapter) under `src/uiao/adapters/bluecat_{adapter,parser}.py` with 69 unit/OSCAL tests and fixtures (#114).
- Briefing generator test suite — 39 tests across `collect_ci_status`, `collect_memory_entries`, `collect_adapter_status`, `collect_control_coverage`, `collect_oscal_status`, `collect_priorities`, `collect_changelog`, and end-to-end `build_briefing()` (#112).
- Mypy CI workflow (`.github/workflows/mypy.yml`) — non-blocking while the 57 pre-existing type debts are burned down.
- `docs/governance/` — promoted governance docs (`ARCHITECTURE.md`, `VISION.md`, `CONMON.md`, `PROJECT-CONTEXT.md`, `CODE_OF_CONDUCT.md`, `NOTICE`) from the old `core/` root.

### Changed
- CLI entry point: `uiao = "uiao.cli.app:app"` (was `uiao.cli:main`); `uiao --version` now prints `uiao X.Y.Z` (was `uiao-core X.Y.Z`).
- `scuba_adapter` renamed to `scubagear_adapter`; class `ScubaAdapter` → `ScubaGearAdapter`; `ADAPTER_ID` `"scuba"` → `"scubagear"`. Resolves the canon/code inversion where the `scubagear` adapter-registry entry had no implementation while the `scuba` modernization entry had a conformance-behavior implementation (#113).
- All imports rewritten: `uiao.impl.*` → `uiao.*` across ~150 files.
- `uiao-core` / `uiao-impl` narrative references sanitized across 430+ non-ADR files. ADRs, `CHANGELOG.md`, and `RELEASE_NOTES.md` preserved as the archival record.
- `Settings._resolve_canon_root()` simplified to a two-tier resolver (`UIAO_CANON_PATH` env var, then packaged canon at `src/uiao/canon/`). Dead `../core` and `../uiao-core` sibling-checkout fallbacks removed.
- KSI `collector_id: uiao-core-ksi-builder` → `uiao-ksi-builder` across 84 YAMLs (metadata only; not matched by any runtime `COLLECTOR_ID`).

### Removed
- `core/` directory (content absorbed into `src/uiao/canon/`, `docs/governance/`, `scripts/tools/`, or removed as obsolete duplicates).
- `impl/` directory (content absorbed into `src/uiao/`, `tests/`, `scripts/`, `.github/workflows/`). `impl/pyproject.toml` and the `uiao-impl` editable distribution retired; `pip uninstall uiao-impl` clears the old install.
- Per-module `CLAUDE.md` / `AGENTS.md` under `core/` and `impl/` (module-scoped docs consolidated into the repo-root pair).

### Fixed
- `src/uiao/__version__.py` normalized to LF-only, no trailing blank.
- `ScubaGearAdapter` conformance: `ConnectionProvenance.identity`, `claim_id`, `entity`, `evidence.source`, `DriftReport.drift_type`, and `DriftReport.details["adapter"]` now carry the `scubagear` prefix (was `scuba`) — 30/30 conformance criteria pass.

### Migration

```bash
pip uninstall uiao-impl -y   # retire the old editable install (if present)
git pull origin main
pip install -e .             # single install step — all runtime deps declared
uiao --version               # -> uiao 0.3.0
pytest -q                    # baseline: ~1071 passed, ~156 skipped
```

Code that still imports from `uiao.impl.*` should be rewritten to import from `uiao.*`.

