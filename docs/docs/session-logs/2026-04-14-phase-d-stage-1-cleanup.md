---
title: "Phase D — Stage 1 Cleanup Commit Batch"
date: 2026-04-14
status: ready-to-ship
parent: 2026-04-14-phase-d-plan.md
---

# Phase D — Stage 1 cleanup (hand-off)

Two commit batches, one per repo. Each deletes only items with **zero external references** per the Stage 0 scan. No cross-repo dependencies touched. Total: ~170 MB of deleted tracked cruft across both repos (the biggest individual item is `plantuml.jar` at 29 MB, which is Stage 3 — not Stage 1 — so Stage 1 is mostly small text/dump deletions plus two large rendered-output directories).

Run from a clean working tree in each repo. If `git status` shows untracked changes before you start, commit them first (or stash).

---

## Block 1 — `uiao-core` cleanup

```powershell
Set-Location 'C:\Users\whale\uiao-core'
git pull --rebase origin main

# Remove generated/derived directories
git rm -r `
    dryrun-output `
    build `
    UNKNOWN.egg-info `
    site

# Remove personal / one-off scripts and dump files
git rm `
    check_marker.py `
    pytest-results.txt `
    refresh_actions.json `
    uaio-core-dir.txt `
    uiao-core-dirtree.txt `
    uiao-core-tree.txt `
    uiao-tree.txt `
    Deploy-uiao-core-Claude.ps1

# Update .gitignore to prevent regeneration
@"

# Phase D Stage 1 additions
dryrun-output/
build/
*.egg-info/
pytest-results.txt
refresh_actions.json
_output/
.pytest_cache/
.coverage
"@ | Add-Content -Path .gitignore

git add .gitignore

git commit -m "[UIAO-CORE] FIX: Phase D Stage 1 — drop generated artifacts + personal dumps"
git push
```

### What this removes

| Path | Why |
|---|---|
| `dryrun-output/` | 1027 files of build artifacts, not canon |
| `build/` | pip/setuptools build output |
| `UNKNOWN.egg-info/` | stale setuptools metadata (package name should be `uiao-core`, so `UNKNOWN` name is itself a bug) |
| `site/` | 32 files — rendered-site output (canonical rendered site lives in uiao-docs) |
| `check_marker.py` | 254-byte one-off script |
| `pytest-results.txt` | 117 KB test run artifact |
| `refresh_actions.json` | zero-byte placeholder |
| `uaio-core-dir.txt`, `uiao-core-dirtree.txt`, `uiao-core-tree.txt`, `uiao-tree.txt` | 185–354 KB each, directory-listing dumps |
| `Deploy-uiao-core-Claude.ps1` | 88 KB personal deploy script, not repo infra |

### What this does NOT remove (deferred to later stages)

- `_quarto.yml` (Stage 3 — doc pipeline out)
- `docs/`, `templates/`, `visuals/`, `exports/`, `assets/`, `plantuml.jar` (Stage 3)
- `src/`, `adapters/`, `scripts/`, `tests/`, `cli/`, `pyproject.toml`, etc. (Stage 4 — `uiao-impl` split)
- `inject_ssp.py`, `write_engine.py` (Stage 4)
- Root `.docx` files (Stage 3 — move to uiao-docs/exports/docx/)

---

## Block 2 — `uiao-docs` cleanup

```powershell
Set-Location 'C:\Users\whale\uiao-docs'
git pull --rebase origin main

# Remove generated/derived directories
git rm -r `
    _site `
    site

# Remove legacy mkdocs tooling (superseded by Quarto)
git rm `
    mkdocs.yml `
    mkdocs.yml.backup-20260407-130309

# Remove one-off fix scripts and root-level duplicate tools
git rm `
    _fix_de.py `
    _fix_docs_workflows.py `
    _fix_ds.py `
    _fix_mv.py `
    dashfix.py `
    generate_images.py `
    generate_images_from_prompts.py `
    generate_scuba_images.py

# Remove root-level personal scripts
git rm `
    Initialize-UIAOCanonStructure.ps1 `
    Split-UIAODocs.ps1 `
    Deploy-uiao-docs-Claude.ps1

# Remove directory-listing dumps and one-off text artifacts
git rm `
    DocTree.txt `
    mdout.txt `
    uaio-docs-dir.txt `
    uaio-docs-files.txt `
    uaio-docs_docx.txt `
    uiao-docs-dirtree.txt `
    uiao-docs-tree.txt `
    uiao-docs_DirTree.txt `
    uiao-docs_tree.txt `
    "Assessment Current SCuBA Implementa.txt"

# Remove superseded / orphaned content
git rm `
    index.md `
    index-scuba.md `
    prompts.json `
    scuba_prompts.json

# Remove the mystery "1" file at root
git rm "1"

# Update .gitignore
@"

# Phase D Stage 1 additions
_site/
site/
.quarto/
"@ | Add-Content -Path .gitignore

git add .gitignore

git commit -m "[UIAO-DOCS] FIX: Phase D Stage 1 — drop generated artifacts + mkdocs remnants + personal dumps"
git push
```

### What this removes

| Path | Why |
|---|---|
| `_site/` | 664 files — Quarto build output |
| `site/` | 440 files — legacy mkdocs build output |
| `mkdocs.yml`, `mkdocs.yml.backup-20260407-130309` | old static-site generator, replaced by Quarto |
| `_fix_de.py`, `_fix_docs_workflows.py`, `_fix_ds.py`, `_fix_mv.py`, `dashfix.py` | one-off fix scripts |
| `generate_images.py` (root) | duplicate; real one is at `tools/generate_images.py` |
| `generate_images_from_prompts.py` | zero bytes |
| `generate_scuba_images.py` | superseded by new `tools/generate_images.py` + `tools/aggregate_prompts.py` |
| `Initialize-UIAOCanonStructure.ps1`, `Split-UIAODocs.ps1`, `Deploy-uiao-docs-Claude.ps1` | personal scripts |
| All `*tree*.txt` / `*dir*.txt` / `*files*.txt` / `*DirTree*.txt` | 8 directory-listing dumps |
| `mdout.txt` | pandoc dump |
| `"Assessment Current SCuBA Implementa.txt"` | truncated filename fragment |
| `index.md`, `index-scuba.md` | superseded by `index.qmd` |
| `prompts.json`, `scuba_prompts.json` | old prompt scratch files |
| `1` | mystery file — 319 bytes, no known referrer |

### What this does NOT remove (deferred)

- Root-level `.pdf` / `.docx` / `.png` files (Stage 3 — move them into proper locations in `docs/` subtree)
- `ssot/UIAO-SSOT.md`, `schemas/*.json` (Stage 2 — move to uiao-core)
- Any content under `docs/` (no bulk deletions planned)

---

## Expected outcomes after Stage 1

| Repo | Before | After | Drop |
|---|---|---|---|
| `uiao-core` top-level entries | ~106 | ~90 | 16 files/dirs |
| `uiao-docs` top-level entries | ~75 | ~45 | 30 files/dirs |
| `uiao-core` tracked size | ~XX MB | ~XX MB − (dryrun-output + build + pytest-results + site + tree dumps + PS1) | substantial |
| `uiao-docs` tracked size | ~XX MB | ~XX MB − (_site + site + tree dumps + mkdocs + PS1 + _fix scripts) | substantial |
| Workflows untouched | 32 / 40 | 32 / 40 | deferred to Stage 5 |

## Post-Stage-1 sanity checks

After both pushes land:

1. `git log --stat -1` on each repo — confirm the deletions are in the commit.
2. Check GitHub web UI — repo root should look noticeably cleaner.
3. Re-run any CI. If any of the deleted `_fix_*.py` or `mkdocs.yml` were still referenced by a workflow, that workflow will fail — that's the signal to retire that workflow in Stage 5.
4. Resume `sync_canon.py` smoke test from Michael's manifest (Phase A from last session) if not already done — unrelated to Stage 1 but still outstanding.

Stage 2 (canon-in) is next. It's a 13-file targeted move plus one schema reconciliation and will be handed off the same way.
