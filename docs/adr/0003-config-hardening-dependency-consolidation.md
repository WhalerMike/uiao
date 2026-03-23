# ADR-0003: Configuration Hardening, Dependency Consolidation, Ruff/Mypy, and Full Generator Migration + Week 1/2 Debt Retirement

## Status

Proposed

## Date

2025-06-08

## Context

Weeks 1 and 2 established the `uiao_core` src-layout package with Typer CLI, Pydantic models, SSP generator migration, pytest infrastructure, and CI (Python 3.11/3.12). However, several debt items remain from Weeks 1/2 that must be retired before the repo is production-grade for FedRAMP agency piloting:

### Week 1/2 Carry-Over Debt (resolved in this sprint)

1. **Dual dependency tracking** - `requirements.txt` and `pyproject.toml` both declare deps
2. **`datetime.utcnow()` deprecation** - deprecated in Python 3.12+
3. **`Settings` not injected** - config.py Settings class exists but is not wired into generators or CLI
4. **No mypy / ruff / pre-commit** - no static analysis or linting
5. **No end-to-end SSP generator test** - unit tests exist but no full pipeline test
6. **`scripts/generate_ssp.py` not shimmed** - legacy entry point not redirected
7. **Remaining generators not migrated** - only SSP moved; docs, validate, assemble remain in scripts/

## Decision

### 1. Dependency Consolidation

- Make `pyproject.toml` the single source of truth for all dependencies
- Convert `requirements.txt` to dev-only (`[project.optional-dependencies.dev]`)
- Dev deps: pytest, ruff, mypy, pre-commit

### 2. Configuration Injection

- Wire `Settings` (from `config.py`) into `generators/ssp.py` for default paths
- CLI options override Settings defaults
- All file paths resolve through Settings

### 3. datetime.utcnow() Fix

- Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`
- Applies to generators and any utility modules

### 4. Generator Migration

- Migrate remaining scripts into `src/uiao_core/generators/`:
  - `docs.py` - DOCX document generation
  - `validate.py` - OSCAL validation wrapper
  - `canon_check.py` - Canon YAML validation
- Each generator follows the established pattern: pure function, Settings-aware, CLI-callable

### 5. Legacy Shims

- Add thin shims in `scripts/` for all migrated generators
- Each shim imports and calls the new module, prints deprecation warning
- Zero breakage for existing users

### 6. Static Analysis

- Add `ruff` config in `pyproject.toml` (select = ["E", "F", "I", "UP"])
- Add `mypy` config in `pyproject.toml` (strict = false initially, warn_return_any = true)
- Add `.pre-commit-config.yaml` with ruff and mypy hooks
- New `.github/workflows/lint.yml` workflow

### 7. E2E Tests

- Add `tests/test_e2e_ssp.py` - full pipeline: load canon + data -> build SSP -> validate JSON output
- Add `tests/test_e2e_docs.py` - docs generation smoke test
- Update CI to run all tests including e2e

## Consequences

### Positive

- Zero remaining Week 1/2 debt
- Single dependency source (pyproject.toml)
- Static analysis catches bugs before CI
- Legacy scripts continue to work via shims
- E2E tests prove the pipeline works end-to-end
- Repo is production-grade for agency pilot evaluation

### Negative

- Larger single PR / sprint scope
- Pre-commit adds developer setup step
- Mypy may surface type issues in existing code

### Risks

- Generator migration may reveal undocumented dependencies in legacy scripts
- Ruff/mypy may require code changes beyond simple fixes

## References

- ADR-0001: Package Restructure
- ADR-0002: Testing and SSP Migration
- Grok Week 3 recommendation: "Verdict: Forward"
