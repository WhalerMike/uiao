# Documentation

The canonical documentation for UIAO has moved to **[uiao-docs](https://github.com/WhalerMike/uiao-docs)**.

All `.qmd` source files, YAML data schemas, styled reference templates, and the Quarto rendering pipeline live there. The rendered HTML site is at **[whalermike.github.io/uiao-docs](https://whalermike.github.io/uiao-docs/docs/index.html)**.

## What remains here

This directory retains only non-document assets used by `uiao-core` tooling:

| File | Purpose |
|------|---------|
| `docs/images/` | Diagram images referenced by generation scripts |
| `docs/index.html` | Static redirect page |
| `docs/modernization_atlas_pitch.pptx` | Standalone pitch deck |
| `docs/modernization_atlas_planner_import.csv` | Project planner import data |

## Repository Ownership

| Repository | Owns |
|------------|------|
| **[uiao-docs](https://github.com/WhalerMike/uiao-docs)** | Documentation canon (`.qmd` sources), YAML schemas, Quarto pipeline, CI/CD |
| **[uiao-core](https://github.com/WhalerMike/uiao-core)** (this repo) | OSCAL generation engine, adapter framework, Python tooling, schemas |

See the [SSOT Policy](https://github.com/WhalerMike/uiao-docs/wiki/Repository-Ownership-and-SSOT-Policy) for the full ownership table and duplication rules.
