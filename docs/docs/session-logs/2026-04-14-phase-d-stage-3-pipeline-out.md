---
title: "Phase D — Stage 3 Doc Pipeline Out Commit Batch"
date: 2026-04-14
status: ready-to-ship
parent: 2026-04-14-phase-d-plan.md
prerequisite: Stage 2 canon-in must be pushed first
---

# Phase D — Stage 3 doc pipeline out (hand-off)

Relocates the documentation rendering pipeline from `uiao-core` into `uiao-docs` and retires the redundant Jinja2 sub-pipeline. After Stage 3, `uiao-core` contains canon + enforcement only; `uiao-docs` owns all authoring, rendering, and derived outputs.

**Prerequisite**: Stages 1 and 2 must be pushed on both repos first.

**Scope**: ~170 MB across several dozen files. Breaks into four batches.

---

## Architectural decision recorded: Jinja2 pipeline retired

Stage 0 inspection surfaced a duplication: `uiao-core/templates/` holds 51 `.j2` files that `generate_docs.py` renders into `uiao-core/docs/*.md`. Meanwhile `uiao-docs/docs/` contains 128 hand-authored `.qmd` files covering the same topic space with richer content (the Quarto sources).

The two pipelines produce overlapping outputs (e.g. both generate `executive_summary`, `management_stack`, `vendor_stack`, `fedramp_crosswalk` documents). The `.qmd` sources are authoritative going forward — they are human-edited, richer, and feed the Quarto rendering that `uiao-docs/.github/workflows/deploy-docs.yml` already publishes.

**Decision (recommended default — applied in this batch): retire the Jinja2 pipeline.**

This means:
- Delete `uiao-core/templates/` (51 `.j2` files)
- Delete `uiao-core/docs/*.md` (Jinja2 outputs — `.qmd` equivalents already live in `uiao-docs/docs/`)
- Delete `uiao-core/generation-inputs/` (Jinja2 YAML inputs)
- Retire 6 Jinja2-dependent workflows in `uiao-core`
- The dual-use YAMLs (`management-stack.yml`, `program.yml`, `vendor-stack.yml`) still live in `uiao-core/canon/data/` after Stage 2; post-retirement they are consumed by `generators/docs.py` (canon-side) and by `.qmd` Quarto code blocks (docs-side) only — no more `.j2` consumers

**If you reject this decision**, stop here and tell me. The alternative is Option B: move `templates/` + `generation-inputs/` + 6 workflows into `uiao-docs`, rewire their data-source paths to `../uiao-core/canon/data/`, and keep both pipelines alive. Cost: ~2x the CI minutes, ongoing drift risk between the two output sets, and three additional workflow cross-repo checkouts to maintain.

Silent = consent to retire.

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

---

## Batch 3.1 — move static doc assets into `uiao-docs`

Moves files that `uiao-docs` Quarto pipeline needs but that currently live in `uiao-core`: PlantUML sources, PNG visuals, SVG assets, and the two root-level branded `.docx` exports.

```powershell
Set-Location 'C:\Users\whale\uiao-docs'

# Ensure target directories exist
New-Item -ItemType Directory -Force -Path 'visuals' | Out-Null
New-Item -ItemType Directory -Force -Path 'assets' | Out-Null
New-Item -ItemType Directory -Force -Path 'assets\images' | Out-Null
New-Item -ItemType Directory -Force -Path 'exports\docx' | Out-Null
New-Item -ItemType Directory -Force -Path 'exports\pptx' | Out-Null

# Copy visuals/ (23 files: PlantUML + PNG + IMAGE-PROMPTS + README)
Copy-Item '..\uiao-core\visuals\*' -Destination 'visuals\' -Recurse -Force

# Copy assets/ (demo.svg + images/)
Copy-Item '..\uiao-core\assets\demo.svg' -Destination 'assets\demo.svg' -Force
if (Test-Path '..\uiao-core\assets\images') {
    Copy-Item '..\uiao-core\assets\images\*' -Destination 'assets\images\' -Recurse -Force
}

# Copy the two root-level branded DOCX exports into exports/docx/
Copy-Item '..\uiao-core\UIAO_003_Adapter_Segmentation_Overview_v1.0.docx' `
          -Destination 'exports\docx\UIAO_003_Adapter_Segmentation_Overview_v1.0.docx' -Force
Copy-Item '..\uiao-core\UIAO_SCuBA_Technical_Specification.docx' `
          -Destination 'exports\docx\UIAO_SCuBA_Technical_Specification.docx' -Force

# Move the PPTX leadership briefing (only one that exists)
if (Test-Path '..\uiao-core\exports\pptx\UIAO_Leadership_Briefing_v1.0.pptx') {
    Copy-Item '..\uiao-core\exports\pptx\UIAO_Leadership_Briefing_v1.0.pptx' `
              -Destination 'exports\pptx\UIAO_Leadership_Briefing_v1.0.pptx' -Force
}

git add visuals/ assets/ exports/docx/ exports/pptx/
git commit -m "[UIAO-DOCS] MIGRATE: Phase D Stage 3 — pull visuals, assets, and branded DOCX/PPTX exports from uiao-core"
git push
```

### What moved and why

| Source | Destination | Reason |
|---|---|---|
| `uiao-core/visuals/` (23 files) | `uiao-docs/visuals/` | PlantUML sources + rendered PNGs feed Quarto diagrams |
| `uiao-core/assets/demo.svg` | `uiao-docs/assets/demo.svg` | Referenced by `.qmd` render |
| `uiao-core/assets/images/` | `uiao-docs/assets/images/` | Images consumed by doc build |
| `uiao-core/UIAO_003_*.docx` (root) | `uiao-docs/exports/docx/` | Branded deliverable lives with other exports |
| `uiao-core/UIAO_SCuBA_*.docx` (root) | `uiao-docs/exports/docx/` | Same — belongs with other exports |
| `uiao-core/exports/pptx/UIAO_Leadership_Briefing_v1.0.pptx` | `uiao-docs/exports/pptx/` | Only file in that dir; rest of exports are deletable build artifacts |

### What is NOT copied (deleted in Batch 3.2 instead)

- `uiao-core/exports/docx/` (28 auto-generated `.docx` — regeneratable from `.qmd` via Quarto+pandoc)
- `uiao-core/exports/quarto/` (Quarto build output tree — regeneratable)
- `uiao-core/exports/ksi/`, `oscal/`, `sbom/`, `schedule/` — canon-generation build outputs, regenerated by Stage 4 tools
- `uiao-core/exports/uiao-component-definition.json`, `uiao-poam.json` — if still needed, regenerate from `canon/`

---

## Batch 3.2 — remove doc pipeline from `uiao-core`

Deletes the Jinja2 template pipeline, `_quarto.yml`, the rendered doc tree, build outputs, and retires the six workflows that drove Jinja2 generation.

```powershell
Set-Location 'C:\Users\whale\uiao-core'

# --- Jinja2 pipeline retirement ---

# 51 Jinja2 templates
git rm -r templates

# Jinja2 inputs
git rm -r generation-inputs

# Rendered Jinja2 output (.md files) — the .qmd equivalents already live in uiao-docs/docs/
git rm -r docs

# --- Static assets (moved in Batch 3.1) ---
git rm -r visuals
git rm -r assets

# --- Quarto config (canonical copy is uiao-docs/_quarto.yml) ---
git rm _quarto.yml

# --- Export build artifacts ---
git rm -r exports

# --- Branded root-level DOCX (moved in Batch 3.1 into exports/docx/) ---
git rm UIAO_003_Adapter_Segmentation_Overview_v1.0.docx
git rm UIAO_SCuBA_Technical_Specification.docx

# --- plantuml.jar (29 MB) — prefer `plantweb` Python package for rendering ---
git rm plantuml.jar

# --- Workflow retirements: the 6 workflows that drove the Jinja2 pipeline ---
# Content generation & docx export are now Quarto-owned in uiao-docs.
git rm .github/workflows/generate-docs.yml
git rm .github/workflows/generate-docx-exports.yml
git rm .github/workflows/render-and-insert-diagrams.yml
git rm .github/workflows/deploy-docs.yml

# generate-artifacts.yml and generate_artifacts.yml (note: underscore variant
# is a duplicate — remove both; Stage 5 will rebuild a canon-only artifact workflow)
git rm .github/workflows/generate-artifacts.yml
git rm .github/workflows/generate_artifacts.yml

# docs.yml — generic docs trigger, superseded by uiao-docs/.github/workflows/deploy-docs.yml
git rm .github/workflows/docs.yml

# --- Update .gitignore for any regeneration attempts ---
@"

# Phase D Stage 3 additions — doc pipeline now lives in uiao-docs
_quarto.yml
docs/
templates/
generation-inputs/
visuals/
assets/
exports/
plantuml.jar
"@ | Add-Content -Path .gitignore

git add .gitignore

git commit -m "[UIAO-CORE] MIGRATE: Phase D Stage 3 — release doc pipeline to uiao-docs, retire Jinja2 template chain"
git push
```

### Workflow retirement rationale

| Workflow | Why retire |
|---|---|
| `generate-docs.yml` | Calls `generate_docs.py`; Jinja2 pipeline gone |
| `generate-docx-exports.yml` | Produces `.docx` from Jinja2 `.md` output; `.qmd`→`.docx` handled by `uiao-docs/deploy-docs.yml` via pandoc |
| `render-and-insert-diagrams.yml` | Renders PlantUML into now-deleted `visuals/` + inserts into now-deleted `docs/` |
| `deploy-docs.yml` (uiao-core) | Duplicate pair with `uiao-docs/deploy-docs.yml`; docs publish from uiao-docs |
| `generate-artifacts.yml` / `generate_artifacts.yml` | Both triggered Jinja2; Stage 5 will introduce a canon-only artifact refresh workflow if needed |
| `docs.yml` | Generic docs trigger, redundant with uiao-docs publish path |

### Workflows intentionally kept in `uiao-core` (not retired here)

- `drift-detection.yml`, `drift-scan.yml` — canon drift enforcement (references Jinja2 in comments only per inspection; if a grep-check finds actual Jinja2 calls, Stage 5 will prune those steps)
- `canon-validation.yml` — core canon gate
- `metadata-validator.yml` — schema gate
- `ai-security-audit.yml`, `security-scan.yml`, `lint.yml`, `ci.yml` — generic gates
- `push-adapters-workflow.yml`, `canon-sync-receive.yml` — cross-repo plumbing

### Verify before push

```powershell
git status   # review the staged deletions/additions
git diff --cached --stat   # should show ~170 MB of deletions and a .gitignore change
```

If the stat shows unexpected additions or untouched files, stop and inspect.

---

## Batch 3.3 — `uiao-docs` picks up publish responsibility

Confirms that `uiao-docs/_quarto.yml` and the publish workflow still resolve after the moves, and adds a minimal README pointing at the new layout.

```powershell
Set-Location 'C:\Users\whale\uiao-docs'

# Sanity: Quarto config present?
if (-not (Test-Path '_quarto.yml')) {
    Write-Warning "_quarto.yml missing in uiao-docs — Stage 3 cannot complete"
}

# Sanity: deploy-docs workflow present?
if (-not (Test-Path '.github/workflows/deploy-docs.yml')) {
    Write-Warning "deploy-docs.yml missing in uiao-docs — docs publish path broken"
}

# Update the exports/README.md stub to reflect the new DOCX/PPTX arrivals
# (only if you want a short note — optional; skip if README is already comprehensive)

# No commit needed unless you edit exports/README.md.
```

---

## Validation post-push

```powershell
Set-Location 'C:\Users\whale\uiao-docs'
Test-Path visuals\authorization_boundary.puml
Test-Path visuals\uiao-vibrant-20x-governance-hub.png
Test-Path assets\demo.svg
Test-Path exports\docx\UIAO_003_Adapter_Segmentation_Overview_v1.0.docx
Test-Path exports\docx\UIAO_SCuBA_Technical_Specification.docx
Test-Path exports\pptx\UIAO_Leadership_Briefing_v1.0.pptx

Set-Location 'C:\Users\whale\uiao-core'
-not (Test-Path templates)
-not (Test-Path generation-inputs)
-not (Test-Path visuals)
-not (Test-Path assets)
-not (Test-Path exports)
-not (Test-Path docs)
-not (Test-Path _quarto.yml)
-not (Test-Path plantuml.jar)
-not (Test-Path UIAO_003_Adapter_Segmentation_Overview_v1.0.docx)
-not (Test-Path UIAO_SCuBA_Technical_Specification.docx)
-not (Test-Path .github\workflows\generate-docs.yml)
-not (Test-Path .github\workflows\generate-docx-exports.yml)
-not (Test-Path .github\workflows\render-and-insert-diagrams.yml)
-not (Test-Path .github\workflows\deploy-docs.yml)
```

All 20 lines should print `True`.

### Smoke test: docs build still succeeds

```powershell
Set-Location 'C:\Users\whale\uiao-docs'
# Kick a manual build run — requires Quarto installed locally.
# Skip if you don't have Quarto locally; the deploy-docs.yml workflow will catch breakage on next push.
quarto render --to html
```

If `quarto render` errors on missing assets, the most likely cause is a `.qmd` file referencing `../visuals/foo.puml` or `../assets/bar.png` — those relative paths now need to be `visuals/foo.puml` and `assets/bar.png` (sibling, not parent). Flag me if you hit this; Stage 6 (reference fixup) will sweep for this pattern across `.qmd` files. For now, note any failures but don't block on them.

---

## Expected outcomes after Stage 3

| Repo | Before | After | Change |
|---|---|---|---|
| `uiao-core` tracked size | ~XX MB | **~XX MB − 170 MB** | massive drop |
| `uiao-core` top-level entries (post-Stage-1) | ~90 | ~72 | drops `_quarto.yml`, `templates/`, `docs/`, `generation-inputs/`, `visuals/`, `assets/`, `exports/`, `plantuml.jar`, 2 root `.docx`, 7 workflows |
| `uiao-docs` tracked size | ~XX MB | +~30 MB (visuals, assets, branded DOCX) | modest increase |
| `uiao-docs` top-level entries (post-Stage-1) | ~45 | ~48 | gains `visuals/`, `assets/`; `exports/` populates |
| Jinja2 pipeline | active in `uiao-core` | **retired** | one canonical rendering path (Quarto in uiao-docs) |
| Cross-repo workflow references | 2 (drift-scan, dashboard-export — already cross-repo-aware) | 2 | no new cross-repo plumbing |

---

## What Stage 3 does NOT fix (deferred)

| Issue | Stage |
|---|---|
| `.qmd` files referencing `../visuals/` or `../assets/` need path updates | **Stage 6** (ref fixup sweep) |
| Duplicate workflow pairs remaining between repos (~21 pairs post-Stage-3) | **Stage 5** |
| `uiao-core/src/`, `adapters/`, `scripts/`, `tests/`, `cli/`, `compliance/`, `pyproject.toml` — app code | **Stage 4** (uiao-impl split) |
| `uiao-core/inject_ssp.py`, `write_engine.py` | **Stage 4** |
| Canon-sync scaffold scanner update (`sync_canon.py` walk `canon/data/`) | **Stage 5** |
| Refresh of `ARCHITECTURE.md`, both `CLAUDE.md`, both `README.md` | **Stage 7** |

---

## Next up after Stage 3 lands

**Stage 4** (uiao-impl repo creation and app-code split). This is the biggest conceptual change remaining — creates a fourth repo `WhalerMike/uiao-impl` and moves `src/`, `adapters/`, `scripts/`, `tests/`, `cli/`, `compliance/`, `pyproject.toml`, `inject_ssp.py`, `write_engine.py` out of `uiao-core`. After Stage 4, `uiao-core` is pure canon: YAMLs, schemas, SSOT markdown, and the handful of validator workflows that enforce them. Both CIs switch to installing `uiao-impl` as a pip dependency.

Planning for Stage 4 needs its own scan pass (150+ internal `from uiao_core.*` imports to trace) and will produce its own plan + stage-0 artifact + hand-off batch in the next session.
