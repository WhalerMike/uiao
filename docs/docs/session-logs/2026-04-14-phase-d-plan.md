---
title: "Phase D — Repo Split Correction Plan"
date: 2026-04-14
status: proposed
owner: michael.stratton
---

# Phase D — Repo Split Correction Plan

> This plan corrects the mis-assignment of content between `uiao-core` and `uiao-docs` that happened during the original repo split. The inventory below is based on a full top-level sweep of both repos on 2026-04-14.

## TL;DR

The original split conflated **three** concerns, not two:

1. **Canon** — invariants, registries, rules, schemas, canonical specs
2. **Documentation pipeline** — Quarto site, templates, rendered outputs, image pipeline
3. **Application code** — Python package, adapters, scripts, ingestion, data-lake, tests

Only (1) belongs in `uiao-core` by the repo's own CLAUDE.md. Only (2) belongs in `uiao-docs`. (3) currently lives in `uiao-core` and needs a decision: stay as a third concern inside `uiao-core`, or split to a new `uiao-impl` (or similar) repo.

There is also significant **root-level clutter** on both sides — dir-tree listings, one-off `.ps1` scripts, `_fix_*.py` remnants, rendered `.docx`/`.pdf` at root — that should be cleaned regardless of which repo each concern ends up in.

---

## Part 1 — Inventory classification

### `uiao-core` (106 top-level entries)

| Category | Items | Target |
|---|---|---|
| **Canon (stay)** | `canon/`, `rules/`, `schemas/`, `tools/sync_canon.py`, `tools/drift_detector.py`, `tools/metadata_validator.py`, `tools/appendix_indexer.py`, `tools/dashboard_exporter.py`, `ARCHITECTURE.md`, `CHANGELOG.md`, `CLAUDE.md`, `CONMON.md`, `PROJECT-CONTEXT.md`, `README.md`, `VISION.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `LICENSE`, `NOTICE`, `RELEASE_NOTES.md`, `pyproject.toml` | stays in `uiao-core` |
| **Doc pipeline (move out)** | `_quarto.yml`, `docs/` (rendered outputs, 30+ files), `templates/` (Jinja2 templates for docs, 53 files), `site/` (rendered site, 32 files), `visuals/` (PlantUML sources, 23 files), `exports/` (docx/pptx/pdf/oscal/sbom outputs, 56 files), `assets/`, `UIAO_003_Adapter_Segmentation_Overview_v1.0.docx`, `UIAO_SCuBA_Technical_Specification.docx`, `plantuml.jar`, `generation-inputs/` | → `uiao-docs` |
| **Application code (needs decision)** | `src/` (uiao_core Python package, 217 files), `adapters/` (21 files), `analytics/`, `api/`, `cli/`, `compliance/`, `dashboard/`, `drift/`, `enforcement/`, `evidence/`, `governance/`, `ha/`, `ksi/`, `machine/`, `orchestrator/`, `performance/`, `platform/`, `policy/`, `provenance/`, `recovery/`, `release/`, `tenancy/`, `testing/`, `tests/` (98 files), `zero-trust/`, `scripts/` (59 files), `scuba-real-run/`, `deploy/`, `config/`, `build/`, `orchestrator/`, `data-lake/`, `data/` (279 files — control library + overlays) | → **DECISION POINT A** |
| **Generated/derived (delete or gitignore)** | `dryrun-output/` (1027 files — build artifacts), `build/`, `UNKNOWN.egg-info/`, `pytest-results.txt`, `refresh_actions.json`, `check_marker.py` | delete + `.gitignore` |
| **Root clutter (delete)** | `uiao-core-tree.txt`, `uiao-core-dirtree.txt`, `uaio-core-dir.txt`, `uiao-tree.txt`, `Deploy-uiao-core-Claude.ps1`, `inject_ssp.py`, `write_engine.py` | delete (personal dumps, one-off scripts) |

### `uiao-docs` (75 top-level entries)

| Category | Items | Target |
|---|---|---|
| **Doc pipeline (stay)** | `_quarto.yml`, `docs/`, `tools/aggregate_prompts.py`, `tools/generate_images.py`, `narrative/`, `appendices/`, `publications/`, `diagrams/`, `images/`, `references/`, `index.qmd`, `runbook/`, `ato/`, `productization/`, `security/`, `reports/`, `exports/`, `overrides/`, `requirements.txt`, `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `LICENSE`, `SUMMARY.md` | stays in `uiao-docs` |
| **Canon content (move out)** | `schemas/dashboard-schema.json`, `schemas/uiao-governance.schema.json`, `ssot/UIAO-SSOT.md`, `data/canon-spec.yml`, `data/cisa_zt_mapping.yml`, `data/ksi-mappings.yml`, `data/parameters.yml`, `data/trust_chain.yml`, `data/poam_rules.yaml`, `data/poam_status_overrides.yaml`, `data/unified_compliance_matrix.yml`, `data/nist_crosswalk.yml`, `data/format-decision-matrix.yml`, `data/style-guide.yml` | → `uiao-docs`→`uiao-core` |
| **Data: stays in docs** | `data/appendices.yml`, `data/atlas-appendices.yml`, `data/document-skeleton.yml`, `data/quarto-frontmatter.yml`, `data/diagrams.yml`, `data/docx-reference.docx`, `data/pptx-reference.pptx`, `data/image-cache.json`, `data/image-manifest.json`, `data/roadmap.yml`, `data/project-plans.yml`, `data/leadership-briefing.yml`, `data/perimeter_collapse.yml` | stays (doc-rendering metadata) |
| **Data: ambiguous** | `data/control-planes.yml`, `data/core-stack.yml`, `data/crosswalk-index.yml`, `data/fedramp-20x.yml`, `data/fedramp_ssp_template_structure.yaml`, `data/inventory-items.yml`, `data/management-stack.yml`, `data/monitoring-sources.yml`, `data/overlay-config.yml`, `data/poam-findings.yml`, `data/program.yml`, `data/seven-layer-model.yml`, `data/vendor-stack.yml` | → **DECISION POINT B** |
| **Generated/derived (delete or gitignore)** | `_site/` (664 files — Quarto build output), `site/` (440 files — legacy mkdocs output) | delete + `.gitignore` |
| **Legacy tooling (delete)** | `mkdocs.yml`, `mkdocs.yml.backup-20260407-130309`, `_fix_de.py`, `_fix_docs_workflows.py`, `_fix_ds.py`, `_fix_mv.py`, `dashfix.py`, `generate_images.py` (root; real one is in `tools/`), `generate_images_from_prompts.py`, `generate_scuba_images.py`, `Initialize-UIAOCanonStructure.ps1`, `Split-UIAODocs.ps1`, `Deploy-uiao-docs-Claude.ps1` | delete |
| **Root clutter (delete)** | `DocTree.txt`, `uiao-docs-dirtree.txt`, `uiao-docs-tree.txt`, `uaio-docs-dir.txt`, `uaio-docs-files.txt`, `uaio-docs_docx.txt`, `uiao-docs_DirTree.txt`, `uiao-docs_tree.txt`, `mdout.txt`, `Assessment Current SCuBA Implementa.txt`, `prompts.json`, `scuba_prompts.json`, `index-scuba.md`, `index.md` (superseded by `index.qmd`), `1/` (unknown numeric dir) | delete |
| **Misrouted DOCX/PDF at root (move)** | `Continuous_Monitoring_Playbook.pdf`, `UIAO SCuBA Pipeline - Complete Deliverables Package.docx`, `UIAO-Core SCuBA Documentation Suite.docx`, `nistspecialpublication800-137.pdf`, `page-01.png`…`page3-11.png` (11 loose pngs) | → `uiao-docs/references/` or `uiao-docs/publications/` (depending on origin); pngs likely belong under `images/` |
| **SUMMARY.md** | `SUMMARY.md` at root | check — if mkdocs artifact, delete; if authored index, move into `docs/` |

### Workflows (`.github/workflows/`)

32 in `uiao-core`, 40 in `uiao-docs`. Significant overlap — many appear duplicated across repos, some with subtle differences. Needs a separate reconciliation pass. See Part 4, Stage 5.

---

## Part 2 — Decision points

### Note on `uiao-gos` (third repo, visible in uploaded tree)

Your `UIAO-TreeOut.txt` confirms `uiao-gos` exists at `c:\Users\whale\uiao-gos` with **121 files total**: `ARCHITECTURE.md`, `README.md`, `pyproject.toml`, plus eight directories (`adapters/`, `core/`, `docs/`, `marketplace/`, `scripts/`, `sdk/`, `tenant/`, `.github/`). Most of those directories are empty or near-empty. This is the commercial AD→Entra-ID migration product, firewalled from the federal pair.

Relevant to DECISION POINT A: `uiao-gos` already has `core/` and `sdk/` scaffolding, which means it *could* be re-purposed as the app-code home (A2) — but only if you're willing to mix commercial and federal implementation. My read of your earlier guidance ("commercial, firewalled from federal") says no: `uiao-gos` stays commercial-only, and A2 still means a **new fourth repo** (`uiao-impl` or similar) for the federal reference implementation. I'm flagging this so you can correct me if I've misread the boundary.

### DECISION POINT A — Application code (the `src/` question)

`uiao-core` currently carries a full Python implementation: `src/uiao_core/` with 20+ sub-modules (adapters, auditor, cli, collectors, coverage, dashboard, diff, evidence, freshness, generators, governance, ir, ksi, models, monitoring, onboarding, oscal, …), plus parallel top-level trees (`adapters/`, `analytics/`, `api/`, `enforcement/`, `orchestrator/`, `policy/`, `platform/`, `ksi/`, `compliance/`) that look like fragmented scaffolding from an earlier refactor.

Per `uiao-core/CLAUDE.md`, this repo is "core governance framework — canonical artifacts, state machines, enforcement rules, and operational playbooks." That reads as specification, not runtime.

**Three options:**

| Option | What it looks like | Pros | Cons |
|---|---|---|---|
| **A1. Keep app code in `uiao-core`** | Treat `src/uiao_core` as the reference implementation of canon. Delete the parallel top-level scaffolding (`adapters/`, `api/`, `analytics/`, etc.) that duplicates what's in `src/`. | No new repo. Canon + reference impl in one place — easier provenance. | Violates `CLAUDE.md` stated purpose. Mixes spec concerns with runtime concerns. Makes canon repo heavy. |
| **A2. Split app code into new `uiao-impl` repo** (Recommended) | New repo for `src/`, `adapters/`, `scripts/`, `tests/`, `data/control-library/`, `scuba-real-run/`, `deploy/`, `config/`, etc. `uiao-core` becomes truly lean: just canon, rules, schemas, tools that validate canon. | Matches stated `CLAUDE.md` intent. Clean separation. Canon repo becomes reviewable. | Third repo to manage. Import paths and CI workflows need update. |
| **A3. Defer** | Do doc-pipeline move now (Stages 1–4), leave app-code in `uiao-core` untouched. Revisit after doc pipeline lands. | Lowest-risk Phase D. Tight scope. | Leaves `uiao-core` in a semi-consistent state — canon repo still carries runtime. |

### DECISION POINT B — Ambiguous `uiao-docs/data/*.yml` files

Some YAML files in `uiao-docs/data/` could plausibly be canon (drives invariants, read by validators) OR doc-rendering metadata (consumed only by Quarto/Jinja). Listed above under "Data: ambiguous." I can resolve each by grepping for usage patterns in both repos — one evening's work — and propose a per-file target. Do you want me to do that now, or make a judgement call per file during the move?

---

## Part 3 — Cross-reference breakage inventory

Before any move, these reference types need to be located and rewritten:

1. **Canon pointers in docs**: `uiao-docs/docs/**/*.qmd` frontmatter with `source:` keys pointing at `uiao-core/canon/...`. Already present. After move, paths that change must be updated.
2. **Workflow inputs**: `uiao-core/.github/workflows/*.yml` that reference files about to leave (e.g. `generate-docs.yml`, `generate-docx-exports.yml`, `render-and-insert-diagrams.yml`, `rename-visuals.yml`). These either move with the pipeline or get retired.
3. **Workflow outputs**: `uiao-docs/.github/workflows/*.yml` that reference inputs about to arrive (e.g. `canon-sync-receive.yml` already exists but will need to find schemas at new paths).
4. **Python imports**: `uiao-core/tools/*.py` that import siblings. `sync_canon.py` reads registries from `canon/` — stays. `appendix_indexer.py`, `dashboard_exporter.py` need grep to confirm.
5. **Dashboard schema consumers**: whoever validates against `uiao-docs/schemas/dashboard-schema.json` or `uiao-core/schemas/dashboard-schema.json` (both exist — confirm they're identical or reconcile).
6. **Hardcoded paths in README / CLAUDE.md / ARCHITECTURE.md on both sides.**

I will produce a reference-breakage scan as part of Stage 0 (see Part 4).

---

## Part 4 — Proposed staged execution

Each stage is one or more PowerShell commit batches. Nothing lands without your confirmation between stages.

### Stage 0 — Pre-flight (no file moves)

- Produce a `phase-d-reference-scan.md` listing every cross-repo reference and every in-repo reference to files about to move.
- Resolve DECISION POINT A and DECISION POINT B.
- Optionally: create `uiao-impl` repo if A2 chosen.

### Stage 1 — Cleanup (both repos, no cross-repo moves)

Low-risk: just delete clearly-junk files and build artifacts. Shrinks both repos before the harder moves.

- `uiao-core`: delete `dryrun-output/`, `build/`, `UNKNOWN.egg-info/`, `pytest-results.txt`, `refresh_actions.json`, `check_marker.py`, 4× `*tree*.txt`, `Deploy-uiao-core-Claude.ps1`. Add `.gitignore` entries for `dryrun-output/`, `build/`, `*.egg-info/`, `pytest-results.txt`.
- `uiao-docs`: delete `_site/`, `site/`, `mkdocs.yml*`, all 4× `_fix_*.py`, `dashfix.py`, 3× root `generate_*.py` (real ones are in `tools/`), 3× ps1 files, 8× `*tree*.txt`, `mdout.txt`, `prompts.json`, `scuba_prompts.json`, `1/`, `index.md` (superseded), `index-scuba.md`. Add `.gitignore` for `_site/`, `site/`.

### Stage 2 — Canon content: `uiao-docs` → `uiao-core`

Small, surgical. Moves SSOT and canonical YAML/JSON to where they belong.

- Move `uiao-docs/ssot/UIAO-SSOT.md` → `uiao-core/canon/UIAO-SSOT.md`
- Move `uiao-docs/schemas/uiao-governance.schema.json` → `uiao-core/schemas/`
- Reconcile `uiao-docs/schemas/dashboard-schema.json` with `uiao-core/schemas/dashboard-schema.json` (pick one; delete the other)
- Move canon YAMLs from DECISION POINT B decisions into `uiao-core/canon/data/` or `uiao-core/schemas/`

### Stage 3 — Doc pipeline: `uiao-core` → `uiao-docs`

The largest single move. Stage carefully.

- Move `uiao-core/_quarto.yml` → delete (canonical one is already in `uiao-docs`)
- Move `uiao-core/templates/` → `uiao-docs/templates/` (Jinja2 doc templates)
- Move `uiao-core/visuals/` → `uiao-docs/diagrams/src/` (PlantUML sources, image prompts)
- Move `uiao-core/exports/` → `uiao-docs/exports/` (merge with existing)
- Move `uiao-core/docs/` → either delete (if truly rendered-output) or merge into `uiao-docs/docs/` per file
- Move `uiao-core/site/` → delete (Quarto build output)
- Move `uiao-core/assets/` → `uiao-docs/docs/images/` or `uiao-docs/assets/`
- Move `uiao-core/plantuml.jar` → `uiao-docs/tools/` or delete (prefer `plantweb` per `_quarto.yml` comment)
- Move `uiao-core/generation-inputs/` → `uiao-docs/data/generation-inputs/`
- Move root-level `uiao-core/UIAO_003_*.docx` and `UIAO_SCuBA_*.docx` → `uiao-docs/exports/docx/`

### Stage 4 — Application code (only if DECISION POINT A = A2)

New `uiao-impl` repo. Move `src/`, `adapters/`, `scripts/`, `tests/`, `data/control-library/`, `cli/`, `compliance/`, `dashboard/`, `drift/`, `enforcement/`, `evidence/`, `governance/` (app side), `ha/`, `ksi/`, `machine/`, `orchestrator/`, `performance/`, `platform/`, `policy/`, `provenance/`, `recovery/`, `release/`, `tenancy/`, `testing/`, `zero-trust/`, `analytics/`, `api/`, `artifacts/`, `config/`, `data-lake/`, `deploy/`, `scuba-real-run/`, `inject_ssp.py`, `write_engine.py`, `pyproject.toml` → `uiao-impl`.

If A1 or A3, this stage skips. If A1: still delete the parallel top-level scaffolding (`adapters/`, `analytics/`, `api/`, etc.) that duplicates `src/uiao_core/`.

### Stage 5 — Workflow reconciliation

Walk the intersection of `.github/workflows/` on both sides. For each duplicate pair, decide:
- Keep in `uiao-core` if it enforces canon
- Keep in `uiao-docs` if it builds docs
- Delete one copy in every other case

Expected outcome: `uiao-core` drops to ~10 workflows, `uiao-docs` drops to ~15 workflows. Current count is 32/40.

### Stage 6 — Reference fixup

Run the reference-breakage scan from Stage 0 and rewrite every broken path. Add CI check to block merges with broken relative links (`lychee` or similar).

### Stage 7 — Documentation update

Update `ARCHITECTURE.md`, both `CLAUDE.md`s, both `README.md`s to reflect the new split. Append Turn 8 to this session log. Regenerate DOCX mirror.

---

## Part 5 — Estimated effort (per stage, rough)

| Stage | Work | Risk |
|---|---|---|
| 0 Pre-flight | 1 session (scan + decisions) | None — read-only |
| 1 Cleanup | 1 session | Low — only deletes obvious junk |
| 2 Canon move | 1 session | Low — few files, well-defined targets |
| 3 Doc pipeline | 2 sessions | Medium — many references to fix |
| 4 App code split | 2–3 sessions (if A2) | High — new repo wiring |
| 5 Workflows | 1 session | Medium — CI breakage possible |
| 6 Reference fixup | 1 session | Low if Stage 0 scan was complete |
| 7 Docs update | 0.5 session | None |

**Total**: 7–10 sessions if A2, 5–7 sessions if A1 or A3.

---

## Ask for this turn

Please pick on:

1. **DECISION POINT A**: A1, A2 (recommended), or A3?
2. **DECISION POINT B**: resolve ambiguous YAMLs now with a usage scan, or judgement-call per file during Stage 2?
3. **Stage 0 scan**: want me to produce the reference-breakage scan now as a separate artifact, or roll it into Stage 1?
4. **Stage 1 (cleanup)**: approve? (This is low-risk and can ship immediately after you decide on the other three.)

Once you answer, next turn I produce the Stage 0 scan and/or the Stage 1 cleanup commit batch.
