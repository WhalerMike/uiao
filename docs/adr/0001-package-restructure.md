# ADR-0001: Restructure uiao-core as a Python Package with Type Safety and CLI

## Status

Accepted (2026-03-23)

## Context

The uiao-core repository has grown to 539+ commits with 20+ scripts in a flat
`scripts/` directory. Each script duplicates the `load_context()` function,
has no type annotations, and is invoked via `python scripts/foo.py` with no
argument parsing. This makes the codebase fragile, hard to test, and
unsuitable for agency piloting where reproducibility and auditability matter.

Key pain points:
- **Duplicated loader logic** across generate_docs.py, generate_oscal.py,
  generate_ssp.py, generate_poam.py, etc.
- **No type safety** - YAML data flows through untyped dicts; typos in keys
  cause silent failures.
- **No CLI** - scripts are run manually with `python scripts/X.py`;
  no `--help`, no argument validation.
- **Not installable** - no `pyproject.toml` or package structure;
  cannot `pip install -e .` for development.

## Decision

Introduce a `uiao_core/` Python package alongside the existing `scripts/`
directory (non-breaking). The package provides:

1. **`uiao_core/loader.py`** - Single canonical `load_context()` with
   caching and validation. All scripts will eventually import from here.
2. **`uiao_core/models.py`** - Pydantic v2 models for core data structures
   (ControlPlane, Parameter, ComplianceEntry, InventoryItem, etc.).
   Provides runtime validation and IDE autocompletion.
3. **`uiao_core/cli.py`** - Typer-based CLI entry point with subcommands:
   `uiao generate docs`, `uiao generate oscal`, `uiao validate`, etc.
4. **`pyproject.toml`** - PEP 621 metadata, `[project.scripts]` entry point,
   dependency declaration.
5. **`py.typed`** marker for PEP 561 type stub support.

New dependencies: `pydantic>=2.0`, `typer>=0.9`, `rich>=13.0`

### Target Package Layout

```
uiao_core/
  __init__.py          # version, public API
  py.typed             # PEP 561 marker
  models.py            # Pydantic data models
  loader.py            # Canonical YAML context loader
  cli.py               # Typer CLI entry point
  generators/          # (future) refactored generators
    __init__.py
pyproject.toml         # PEP 621 package metadata
scripts/               # (unchanged, gradually migrated)
```

## Consequences

### Positive
- Scripts can `from uiao_core.loader import load_context` - single source of truth
- Pydantic models catch data errors at load time, not deep in generation logic
- `pip install -e .` enables `uiao` CLI command system-wide
- Type annotations enable mypy/pyright checks in CI
- Agency evaluators see a professional, installable package

### Negative
- Adds 3 new dependencies (pydantic, typer, rich) to requirements.txt
- Existing scripts still work but are not yet migrated (parallel paths temporarily)
- Pydantic models must stay in sync with YAML schema changes

### Migration Strategy
- Phase 1 (this PR): Create package, loader, models, CLI shell. Non-breaking.
- Phase 2 (Week 2): Migrate scripts to import from uiao_core.loader
- Phase 3 (Week 3): Move generator logic into uiao_core.generators/
- Phase 4 (Week 4): Deprecate direct script invocation

## Technical Debt Notes
- The existing `load_context()` in each script merges ALL YAML files into
  a flat dict - key collisions are possible. The new loader should namespace
  by source file.
- No tests exist for data loading; Pydantic models will serve as implicit
  validation tests until proper test suite is added.
