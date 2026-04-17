# Changelog

All notable changes to UIAO are documented here. Format adapted from [Keep a Changelog](https://keepachangelog.com/); versioning follows [Semantic Versioning](https://semver.org/). Pre-1.0 minor versions may carry breaking changes.

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
