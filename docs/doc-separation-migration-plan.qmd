---
title: "Doc-Separation-Migration-Plan"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# Migration Plan: Separation of User and Machine Documents

## Objective

Migrate the existing `uiao-core` repository to a structure that clearly separates user-facing documentation, machine-facing artifacts, and canonical definitions.

## Phases

### Phase 1: Inventory

1. Scan the repo for all documentation and config files.
2. Tag each file as: `user-doc`, `machine-artifact`, `canonical`, `script`, `template`, `runtime-code`, or `generated-output`.
3. Produce an inventory file: `docs/appendix/doc-inventory.md`.

### Phase 2: Directory Creation (COMPLETE)

Created:
- `docs/{architecture,governance,onboarding,patterns,user-guides,appendix}`
- `machine/{schemas,configs,pipelines,generators,adapters}`
- `templates/{user-docs,machine-docs}`
- `scripts/check-drift.ps1`

### Phase 3: File Moves

**Move to docs/**
- All standalone Markdown files (assessments, rubrics, narratives)
- `visuals/` content

**Move to machine/**
- `schemas/` -> `machine/schemas/`
- `rules/` -> `machine/configs/`
- `validation-targets/` -> `machine/configs/`
- `exports/` -> `machine/generators/`
- `output/` -> `machine/generators/`
- Machine configs: `mkdocs.yml`, `.pre-commit-config.yaml`, `pyproject.toml`, `requirements.txt`

**Merge canon/**
- Merge `01_Canon/` into `canon/`

**Move scripts/**
- All `.ps1` and `.py` utility scripts -> `scripts/`

### Phase 4: Link Updates

1. Search for broken links caused by file moves.
2. Update Markdown links to reflect new paths.
3. Use relative links for portability.

### Phase 5: CI Enforcement

Add CI steps to:
- Run `scripts/check-drift.ps1`
- Reject Markdown in `machine/`
- Reject JSON/YAML/OSCAL in `docs/`
- Validate schemas

### Phase 6: Communication

1. Update top-level `README.md` with new structure.
2. Announce the change to contributors.
3. Provide before/after mapping in `docs/appendix/doc-inventory.md`.

## Success Criteria

- No Markdown files under `machine/`
- No JSON/YAML/OSCAL files under `docs/`
- All canonical principles reside in `canon/`
- CI enforces the separation and drift checks pass
