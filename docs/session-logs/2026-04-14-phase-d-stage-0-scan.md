---
title: "Phase D — Stage 0 Reference & Usage Scan"
date: 2026-04-14
status: scan-output
parent: 2026-04-14-phase-d-plan.md
---

# Phase D — Stage 0 scan output

Read-only analysis. No files have moved yet. Use this to validate the move plan before Stage 2+ executes.

---

## Part A — Ambiguous YAML usage resolution

Scan target: 13 YAML files in `uiao-docs/data/` whose target repo was undecided.

Method: every file grepped by name across both repos; each caller classified as canon-side (validators, generators, tools that enforce invariants) or docs-side (Quarto `.qmd`, Jinja2 `.j2`, doc-render tools).

| File | Canon-side callers | Docs-side callers | Target |
|---|---|---|---|
| `control-planes.yml` | `tests/test_overlay_loader.py`, `generators/docs.py`, `test_generators.py` | `.qmd` comments only | **→ uiao-core** |
| `core-stack.yml` | `generators/ssp.py`, `generators/poam.py`, `test_generators.py` | comments only | **→ uiao-core** |
| `crosswalk-index.yml` | `tools/validators/crosswalk_validator.py`, `generators/docs.py` | `09_CrosswalkIndex.qmd` metadata | **→ uiao-core** |
| `fedramp-20x.yml` | `generators/poam.py` | metadata | **→ uiao-core** |
| `fedramp_ssp_template_structure.yaml` | `generators/ssp.py` actively loads | references only | **→ uiao-core** |
| `inventory-items.yml` | `generators/ssp.py`, `test_generators.py` | comment | **→ uiao-core** |
| `monitoring-sources.yml` | `monitoring/sentinel_hook.py` (4 refs), `monitoring/event_processor.py`, `update_poam_from_monitoring.py` | comment | **→ uiao-core** |
| `overlay-config.yml` | `generators/docs.py`, `test_overlay_loader.py` | comment | **→ uiao-core** |
| `poam-findings.yml` | `monitoring/sentinel_hook.py`, `update_poam_from_monitoring.py` | comment | **→ uiao-core** |
| `seven-layer-model.yml` | none | `templates/vendor_stack_v1.0.md.j2`, multiple `.qmd` | **→ uiao-docs (stays)** |
| `management-stack.yml` | `test_overlay_loader.py` | `templates/management-stack.md.j2`, `05_ManagementStack.qmd` | **DUAL** — see below |
| `program.yml` | `generators/docs.py` spreads keys | `templates/system_inventory_*.md.j2`, multiple `.qmd` | **DUAL** |
| `vendor-stack.yml` | `generators/docs.py`, `templates/system_inventory_*.md.j2` | `templates/vendor_stack_v1.0.md.j2`, `vendor_stack_v1.0.qmd` | **DUAL** |

### Dual-consumption decision

Three files — `management-stack.yml`, `program.yml`, `vendor-stack.yml` — are canonical structure that doc templates also read directly. Options:

- **D1 (Recommended): canonical home in `uiao-core/canon/data/`**, and Stage 5 workflow reconciliation adds a copy-step or submodule fetch so templates resolve them via `uiao-core/canon/data/<file>.yml`. Matches the SSOT principle; one source of truth per file.
- **D2**: keep in `uiao-docs/data/`, and canon validators pull cross-repo. Reverses the provenance flow — canon depends on docs for its own data. Not recommended.

Will proceed with D1 unless you redirect.

---

## Part B — Cross-reference breakage inventory

### Group 1 — `uiao-core → uiao-docs` (doc pipeline out)

| Path | External refs | Action needed |
|---|---|---|
| `uiao-core/_quarto.yml` | none | delete; canonical is `uiao-docs/_quarto.yml` |
| `uiao-core/docs/` | plan doc only | move or delete |
| `uiao-core/templates/` | internal only (Python imports within uiao-core) | move cleanly |
| `uiao-core/visuals/` | none outside plan doc | move cleanly |
| `uiao-core/exports/` | none outside plan doc | move cleanly |
| `uiao-core/site/` | none | delete (build output) |
| `uiao-core/assets/` | none outside plan doc | move cleanly |
| `uiao-core/plantuml.jar` | none | delete (prefer `plantweb`) |
| `uiao-core/generation-inputs/` | none outside plan doc | move cleanly |
| `uiao-core/UIAO_003_*.docx` | none | move to `uiao-docs/exports/docx/` |
| `uiao-core/UIAO_SCuBA_*.docx` | none | move to `uiao-docs/exports/docx/` |

**Result**: Group 1 is surprisingly clean. Almost all items move with zero cross-repo rewriting required.

### Group 2 — `uiao-docs → uiao-core` (canon in)

| Path | External refs | Action needed |
|---|---|---|
| `uiao-docs/schemas/uiao-governance.schema.json` | plan doc only | move cleanly |
| `uiao-docs/schemas/dashboard-schema.json` | **4 callers** — see below | reconcile with `uiao-core/schemas/dashboard-schema.json`, update callers |
| `uiao-docs/ssot/UIAO-SSOT.md` | plan doc only | move cleanly |

**`dashboard-schema.json` callers:**
- `uiao-docs/tools/dashboard_exporter.py` — reads relative path `schemas/dashboard-schema.json`
- `uiao-docs/_fix_de.py` — same (deleting file in Stage 1, so moot)
- `uiao-docs/dashfix.py` — same (deleting file in Stage 1, so moot)
- `uiao-core/tools/dashboard_exporter.py` — reads relative path `schemas/dashboard-schema.json`

Both `uiao-docs/schemas/dashboard-schema.json` and `uiao-core/schemas/dashboard-schema.json` exist. **Diff result: FORKED.** Sizes 4563 vs 4432 bytes; uiao-docs copy is 3 days newer (Apr 12 vs Apr 9). Stage 2 reconciliation must compare property-by-property and adopt the canonical one (likely the newer uiao-docs copy, but needs human review to confirm no regressions).

**After move**: `uiao-docs/tools/dashboard_exporter.py` must look in `../uiao-core/schemas/` (cross-repo) OR fetch canon via CI artifact download OR be deprecated (drift check runs in canon repo, not docs repo).

### Group 3 — `uiao-core → uiao-impl` (app-code split, new fourth repo)

| Path | External refs | Migration complexity |
|---|---|---|
| `uiao-core/src/` | 150+ internal `from uiao_core.*` imports; `ci.yml` in both repos | **High** — package moves with `pyproject.toml`, CIs re-pull from `uiao-impl` |
| `uiao-core/adapters/` | `uiao_core.adapters.*` imports (20+); `push-adapters-workflow.yml` | moves with `src/` |
| `uiao-core/scripts/` | 3 workflow refs: `canon-sync-receive.yml`, `drift-scan.yml`, `dashboard-export.yml`; tool comments | each workflow needs post-move rewrite |
| `uiao-core/tests/` | `uiao-core/.github/workflows/ci.yml` | moves with src/ |
| `uiao-core/cli/` | `uiao-core/ci.yml` (`uiao --help`), `uiao-docs/ci.yml` (`from uiao_core import __version__`) | moves with src/ |
| `uiao-core/compliance/` | none | clean move |
| `uiao-core/data/control-library/` (254 files) | unknown callers — needs deeper scan | likely moves with impl |
| `uiao-core/pyproject.toml` | both CIs run `pip install -e .[dev]` | both CIs switch to pulling from `uiao-impl` |
| `uiao-core/inject_ssp.py`, `write_engine.py` | internal only | moves with src/ |

**Critical cross-repo workflow integration points (to be fixed in Stage 5):**

1. `uiao-docs/.github/workflows/canon-sync-receive.yml` explicitly checks out `WhalerMike/uiao-core` and runs `sync_canon.py`. **Already cross-repo-aware** — post-Phase-D it keeps working because `sync_canon.py` stays in `uiao-core/tools/`.
2. `uiao-docs/.github/workflows/dashboard-export.yml` and `drift-scan.yml` use `../uiao-core` relative path. **Already broken** on CI runners (no sibling checkout). Will be rewritten to use `actions/checkout@v4` against `WhalerMike/uiao-core` + possibly `WhalerMike/uiao-impl`.
3. `uiao-docs/tools/appendix_indexer.py` accepts `--core-path ../uiao-core/appendices/`. **Needs** a default that works on CI (e.g. read from env var or expect a `uiao-core-checkout` sibling dir produced by workflow).
4. `uiao-docs/tools/drift_detector.py` accepts `--cross-repo ../uiao-core`. Same pattern — env var or workflow-produced checkout.

### Group 4 — Items unambiguously safe to delete (Stage 1)

These have zero external references and are listed in the plan as junk:
- `uiao-core/dryrun-output/` (1027 files)
- `uiao-core/build/`
- `uiao-core/UNKNOWN.egg-info/`
- `uiao-core/pytest-results.txt`
- `uiao-core/refresh_actions.json`
- `uiao-core/check_marker.py`
- `uiao-core/*tree*.txt` (4 files)
- `uiao-core/Deploy-uiao-core-Claude.ps1`
- `uiao-docs/_site/` (664 files)
- `uiao-docs/site/` (440 files)
- `uiao-docs/mkdocs.yml*`
- `uiao-docs/_fix_*.py` (4 files)
- `uiao-docs/dashfix.py`
- `uiao-docs/generate_images.py` (root; real one is in `tools/`)
- `uiao-docs/generate_images_from_prompts.py` (zero bytes)
- `uiao-docs/generate_scuba_images.py`
- `uiao-docs/*tree*.txt`, `uiao-docs/*dir*.txt` (8 files)
- `uiao-docs/mdout.txt`
- `uiao-docs/Assessment Current SCuBA Implementa.txt`
- `uiao-docs/prompts.json`, `uiao-docs/scuba_prompts.json`
- `uiao-docs/1/`
- `uiao-docs/index.md`, `uiao-docs/index-scuba.md`
- `uiao-docs/Initialize-UIAOCanonStructure.ps1`, `uiao-docs/Split-UIAODocs.ps1`, `uiao-docs/Deploy-uiao-docs-Claude.ps1`

---

## Part C — Revised ambiguous-YAML targets (after scan)

Replaces DECISION POINT B in the parent plan. No further decision needed unless you reject D1:

- **To `uiao-core/canon/data/`**: control-planes.yml, core-stack.yml, crosswalk-index.yml, fedramp-20x.yml, fedramp_ssp_template_structure.yaml, inventory-items.yml, monitoring-sources.yml, overlay-config.yml, poam-findings.yml
- **Stays in `uiao-docs/data/`**: seven-layer-model.yml
- **To `uiao-core/canon/data/` with canon-sync replication for docs use**: management-stack.yml, program.yml, vendor-stack.yml

Total: 12 files move into uiao-core, 1 stays in uiao-docs.

---

## Part D — Workflow reconciliation preview (for Stage 5 later)

Duplicate workflow pairs between repos (same filename in both `.github/workflows/`):

- `ai-security-audit.yml`, `appendix-sync.yml`, `canon-validation.yml`, `changelog.yml`, `ci.yml`, `compliance-mapping.yml`, `create-roadmap-issues.yml`, `crosswalk-regeneration.yml`, `dashboard-export.yml`, `deploy-docs.yml`, `deploy.yml`, `docs.yml`, `drift-detection.yml`, `drift-scan.yml`, `generate-artifacts.yml`, `generate-docs.yml`, `generate_artifacts.yml` (note: underscore variant), `lint.yml`, `metadata-validator.yml`, `publish.yml`, `push-adapters-workflow.yml`, `rename-visuals.yml`, `render-and-insert-diagrams.yml`, `repo-hygiene.yml`, `security-scan.yml`, `validate-workflow-serialization.yml`, `verify-signatures.yml`

Count: **27 duplicate pairs** out of 32 (`uiao-core`) and 40 (`uiao-docs`). Stage 5 reconciliation will resolve each. Rough estimate: target ~10 workflows per repo after dedup.

---

## Next action

Awaiting your acknowledgement of Part C (D1 acceptable? — if yes, silent is consent). Then:

1. **Stage 1 commit batch** ships next turn (cleanup of all items in Part B/Group 4).
2. **Stage 2** follows with Group 2 + Part C targeted moves (canon into uiao-core).
3. **Stage 3** (doc pipeline out) in a subsequent session.
4. **Stage 4** (`uiao-impl` creation) after that.
