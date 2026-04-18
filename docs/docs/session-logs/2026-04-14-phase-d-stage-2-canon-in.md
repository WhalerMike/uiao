---
title: "Phase D — Stage 2 Canon-In Commit Batch"
date: 2026-04-14
status: ready-to-ship
parent: 2026-04-14-phase-d-plan.md
prerequisite: Stage 1 cleanup must be pushed first
---

# Phase D — Stage 2 canon-in (hand-off)

Moves canon content from `uiao-docs` into `uiao-core`. Per the Stage 0 scan: 13 YAML files, 1 SSOT markdown, 1 schema, plus the forked `dashboard-schema.json` reconciliation.

**Prerequisite**: Stage 1 must be pushed on both repos first. Stage 1 deletes `_fix_de.py` and `dashfix.py`, which both reference `dashboard-schema.json` — removing those callers simplifies Stage 2.

**Method**: two commit batches executed in order. Batch 2.1 adds the canon files to `uiao-core` (copy from `uiao-docs` working tree). Batch 2.2 removes them from `uiao-docs`. Two-commit pattern preserves git history on both sides.

---

## Pre-flight — confirm repos are in sync

```powershell
Set-Location 'C:\Users\whale\uiao-core'
git status   # expect: nothing to commit, working tree clean
git pull --rebase origin main

Set-Location 'C:\Users\whale\uiao-docs'
git status   # expect: nothing to commit, working tree clean
git pull --rebase origin main
```

If either `git status` shows uncommitted changes, pause and resolve before proceeding.

---

## Batch 2.1 — add canon to `uiao-core`

```powershell
Set-Location 'C:\Users\whale\uiao-core'

# Create target directory
New-Item -ItemType Directory -Force -Path 'canon\data' | Out-Null

# Copy canon YAMLs (9 pure-canon + 3 dual-use) from uiao-docs/data → uiao-core/canon/data
$canonYamls = @(
    'control-planes.yml',
    'core-stack.yml',
    'crosswalk-index.yml',
    'fedramp-20x.yml',
    'fedramp_ssp_template_structure.yaml',
    'inventory-items.yml',
    'monitoring-sources.yml',
    'overlay-config.yml',
    'poam-findings.yml',
    'management-stack.yml',
    'program.yml',
    'vendor-stack.yml'
)
foreach ($f in $canonYamls) {
    Copy-Item "..\uiao-docs\data\$f" -Destination "canon\data\$f"
}

# Copy SSOT markdown: uiao-docs/ssot/UIAO-SSOT.md → uiao-core/canon/UIAO-SSOT.md
Copy-Item '..\uiao-docs\ssot\UIAO-SSOT.md' -Destination 'canon\UIAO-SSOT.md'

# Copy governance schema: uiao-docs/schemas/uiao-governance.schema.json → uiao-core/schemas/
Copy-Item '..\uiao-docs\schemas\uiao-governance.schema.json' -Destination 'schemas\uiao-governance.schema.json'

# NOTE on dashboard-schema.json: Stage 0 diff showed the uiao-core copy is COMPLETE (4563 bytes,
# with proper closing braces) and the uiao-docs copy is TRUNCATED (4432 bytes, missing tail).
# Keep the uiao-core copy as canonical. No copy step needed for this file.

git add canon/ schemas/
git commit -m "[UIAO-CORE] MIGRATE: Phase D Stage 2 — pull 12 canon YAMLs, UIAO-SSOT.md, governance schema from uiao-docs"
git push
```

---

## Batch 2.2 — remove from `uiao-docs` + patch workflows affected by the move

This batch was widened to fold in the CI-stabilization fixes (previously scoped as Stage 5a). Two workflow edits make the moved files' absence a non-event for CI.

```powershell
Set-Location 'C:\Users\whale\uiao-docs'

# --- File removals ---

# Remove the 12 YAMLs that moved to uiao-core (seven-layer-model.yml stays — doc-only per Stage 0)
git rm `
    data/control-planes.yml `
    data/core-stack.yml `
    data/crosswalk-index.yml `
    data/fedramp-20x.yml `
    data/fedramp_ssp_template_structure.yaml `
    data/inventory-items.yml `
    data/monitoring-sources.yml `
    data/overlay-config.yml `
    data/poam-findings.yml `
    data/management-stack.yml `
    data/program.yml `
    data/vendor-stack.yml

# Remove SSOT markdown
git rm ssot/UIAO-SSOT.md

# Remove governance schema
git rm schemas/uiao-governance.schema.json

# Remove the truncated dashboard-schema.json (canonical copy is in uiao-core)
git rm schemas/dashboard-schema.json

# Retire validate-uiao-metadata.yml: it triggers on a schema that now lives in uiao-core,
# and canon validation already runs in uiao-core/.github/workflows/canon-validation.yml.
git rm .github/workflows/validate-uiao-metadata.yml

# If ssot/ directory is now empty, remove it
if ((Get-ChildItem 'ssot' -Force -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
    Remove-Item 'ssot' -Force -ErrorAction SilentlyContinue
}
# If schemas/ directory is now empty, remove it
if ((Get-ChildItem 'schemas' -Force -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
    Remove-Item 'schemas' -Force -ErrorAction SilentlyContinue
}

# --- Workflow patch: dashboard-export.yml ---
# The "Export dashboard data" step reads dashboard-schema.json. That file is now in uiao-core.
# The workflow already does a cross-repo checkout of uiao-core (path: uiao-core), so we just
# update the --schema flag to reach across.
(Get-Content .github/workflows/dashboard-export.yml) `
    -replace '--schema schemas/dashboard-schema\.json', '--schema ../uiao-core/schemas/dashboard-schema.json' `
    | Set-Content .github/workflows/dashboard-export.yml
git add .github/workflows/dashboard-export.yml

git commit -m "[UIAO-DOCS] MIGRATE: Phase D Stage 2 — release canon content to uiao-core + rewire dashboard-export workflow"
git push
```

### Verify the workflow patch before push

```powershell
git diff HEAD~1 -- .github/workflows/dashboard-export.yml
```

Expected diff (single-line change):
```
-            --schema schemas/dashboard-schema.json \
+            --schema ../uiao-core/schemas/dashboard-schema.json \
```

If you see more than one changed line, stop and inspect — the `-replace` pattern should have matched exactly once.

---

## What Stage 2 does NOT fix (deferred)

After investigation (see inline check against the actual workflow files), the CI-stabilization fixes turned out to be exactly two line-edits, small enough to fold directly into Batch 2.2 above. So there is no Stage 5a — it's merged. The remaining deferred items are not triggered by Stage 2 moves:

| Issue | Why deferred |
|---|---|
| `uiao-docs/tools/dashboard_exporter.py` hardcodes no schema path — it takes `--schema` as a CLI argument | Not broken by Stage 2; the workflow passes the right path. Tool itself needs no change. |
| `uiao-docs/tools/appendix_indexer.py` default `--core-path ../uiao-core/appendices/` | Not triggered by Stage 2 moves. Full workflow-reconciliation pass (Stage 5) will revisit. |
| `uiao-docs/tools/drift_detector.py` default `--cross-repo ../uiao-core` | Already used cross-repo-aware by `dashboard-export.yml`, which checks out both repos. No change needed. |
| Doc templates (`templates/*.j2`) consuming the 3 dual-use YAMLs (`management-stack`, `program`, `vendor-stack`) from their old `uiao-docs/data/` paths | `templates/` is part of the doc pipeline move (Stage 3). Once templates land in `uiao-docs`, Stage 3 will also update their data-source paths. |
| Canon-sync workflow doesn't yet walk `canon/data/` | Stage 3/5 — `sync_canon.py` scaffold scanner update. |
| Pre-existing reference to missing `schemas/docs-metadata-schema.json` in `dashboard-export.yml` lines 47 and 60 | **Already broken before Phase D** — those steps use `continue-on-error: true` and fail silently. Noting for visibility; not my fix. |

---

## Expected outcomes after Stage 2

- `uiao-core/canon/` gains `UIAO-SSOT.md` and a new `data/` subdirectory containing 12 canonical YAMLs.
- `uiao-core/schemas/` gains `uiao-governance.schema.json` (dashboard-schema.json already present).
- `uiao-docs/ssot/` and `uiao-docs/schemas/` directories are gone (or empty).
- `uiao-docs/data/` loses 12 files, retains `seven-layer-model.yml` + all doc-rendering YAMLs + `image-cache.json` + `image-manifest.json` + reference binaries (`docx-reference.docx`, `pptx-reference.pptx`).
- Git log records the move as delete+add; path-aware diff tools (`git log --follow`) can rebuild the history.

## Validation post-push

```powershell
Set-Location 'C:\Users\whale\uiao-core'
# Verify all canon files landed
Test-Path canon\UIAO-SSOT.md
Test-Path canon\data\program.yml
Test-Path schemas\uiao-governance.schema.json

Set-Location 'C:\Users\whale\uiao-docs'
# Verify all canon files departed
-not (Test-Path ssot\UIAO-SSOT.md)
-not (Test-Path schemas\uiao-governance.schema.json)
-not (Test-Path schemas\dashboard-schema.json)
-not (Test-Path data\program.yml)
# Verify doc-only YAML stayed
Test-Path data\seven-layer-model.yml
```

All nine should return `True`.

---

## Next up after Stage 2 lands

Stage 3 (doc pipeline out: `_quarto.yml`, `templates/`, `visuals/`, `exports/`, `assets/`, `plantuml.jar`, `generation-inputs/`, root `.docx` files, possibly `docs/` contents from `uiao-core` → `uiao-docs`).

Stage 3 is the biggest move in Phase D — ~170 MB of content, dozens of files, and the `templates/` move needs to also retarget `management-stack.yml` / `program.yml` / `vendor-stack.yml` reads to the new `uiao-core/canon/data/` paths. Plan-and-batch next session.
