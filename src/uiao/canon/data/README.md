# YAML Data Schemas

These YAML files are **synced from [uiao-docs/data/](https://github.com/WhalerMike/uiao-docs/tree/main/data)**.

**Do not edit these files here.** Edit them in `uiao-docs` and they will be automatically synced via the `sync-data-to-core` GitHub Actions workflow.

## Why the copy exists

The Python generation engine (`src/`) and scripts (`scripts/`) read from `data/` at runtime. Rather than adding a submodule or remote fetch dependency, we sync the authoritative copy from `uiao-docs` on every push to `main` that touches `data/`.

## Files unique to uiao-core

| File | Purpose |
|------|---------|
| `(removed — was Legacy PlantUML CLI config)` | Legacy PlantUML CLI config (deprecated) |
| `schema.json` | JSON validation schema for data files |
| `control-library/` | NIST control library YAML files |

## Authority

`uiao-docs/data/` is the single source of truth.

See the [SSOT Policy](https://github.com/WhalerMike/uiao-docs/wiki/Repository-Ownership-and-SSOT-Policy).
