# ADR-0004: Final Migration, Lint Enforcement, DRY Refactoring, and Agency Pilot Packaging

## Status

Accepted

## Date

2025-06-15

## Context

Weeks 1-3 of the UIAO-Core modernization established:
- **Week 1 (ADR-0001):** src-layout package structure, Typer CLI, Pydantic models, generator stubs.
- **Week 2 (ADR-0002):** pytest infrastructure, CI pipeline, SSP generator migration.
- **Week 3 (ADR-0003):** Config hardening, dependency consolidation, datetime fix, migration of docs/oscal/poam/charts generators, 11 e2e tests.

The Week 3 self-critique (0003-week3-critique.md) and external assessment (Grade: B+ 88/100) identified the following **remaining technical debt**:

1. `generate_rich_docx.py` and trestle scripts (`validate_with_trestle.py`, `assemble_with_trestle.py`) still in legacy `/scripts/` -- not yet ported.
2. Legacy shims missing -- external callers/CI could break if they call old scripts directly.
3. No lint workflow -- ruff/mypy are configured in pyproject.toml but not enforced in CI.
4. `load_context()` duplicated across oscal.py, poam.py, and charts.py (DRY violation).
5. Settings injection incomplete -- not all generators and CLI commands use the Pydantic Settings model.
6. No true integration tests against real canon YAML data.

This ADR **retires all remaining Week 1-3 debt** and brings the repository to agency-pilot readiness.

## Decision

We will execute the following changes in priority order:

### 1. DRY Refactor: Shared Context Loader
Extract the duplicated `load_context()` function into `src/uiao_core/utils/context.py` and update all generators (oscal, poam, charts) to import from the shared module.

### 2. Final Generator Migrations
- **Rich DOCX:** Port `scripts/generate_rich_docx.py` to `src/uiao_core/generators/rich_docx.py` with Settings injection, type hints, and python-docx integration.
- **Trestle:** Combine `scripts/validate_with_trestle.py` and `scripts/assemble_with_trestle.py` into `src/uiao_core/generators/trestle.py` with two public functions: `validate_with_trestle()` and `assemble_with_trestle()`.

### 3. Legacy Shims
Add thin wrapper scripts in `scripts/` that import and call the new `uiao_core` package functions. This ensures zero-downtime for any external callers or CI jobs referencing the old script paths.

### 4. Complete Settings Injection
Ensure every generator, CLI command, and model uses the Pydantic `Settings` class for configuration (canon paths, output directories, template paths).

### 5. Lint Enforcement
- Create `.github/workflows/lint.yml` running ruff check + mypy on every push/PR.
- Add `.pre-commit-config.yaml` with ruff, mypy, and trailing-whitespace hooks.

### 6. Integration Tests
Add `tests/test_integration.py` with end-to-end tests using real canon YAML fixtures and `tmp_path`, covering at least one test per generator.

### 7. Agency Pilot Packaging
- Update `README.md` and `USAGE.md` with complete CLI examples and "Agency Pilot Quickstart" section.
- Add `LICENSE` (MIT), `CONTRIBUTING.md`.
- Add `docs/pilot-artifacts/` with example outputs and a FedRAMP Pilot Checklist.
- Verify sdist/wheel build instructions work.

## Consequences

### Positive
- **Zero remaining technical debt** from the original 4-week plan.
- **Full CI enforcement** -- lint, type checking, and tests run automatically.
- **DRY codebase** -- shared utilities eliminate duplication.
- **Agency-pilot ready** -- any federal agency can `pip install`, run CLI, and generate FedRAMP artifacts in under 5 minutes.
- **Backward compatible** -- legacy shims preserve old script paths.

### Negative
- Additional maintenance burden for legacy shims (mitigated by deprecation warnings).
- Pre-commit hooks add friction for contributors (mitigated by clear CONTRIBUTING.md docs).

### Risks
- Rich DOCX and trestle generators depend on external packages (python-docx, compliance-trestle) that may have version conflicts. Mitigated by pinning in pyproject.toml extras.
- Integration tests with real canon data may be brittle if canon schema changes. Mitigated by using minimal fixture data.

## Alternatives Considered

1. **Skip legacy shims:** Would break backward compatibility for any existing automation. Rejected.
2. **Defer lint enforcement to a separate PR:** Would leave the debt open. Rejected -- this ADR closes everything.
3. **Keep load_context() per-module:** Simpler but violates DRY and increases maintenance cost. Rejected.

## References

- ADR-0001: Package Restructure (Week 1)
- ADR-0002: Testing and SSP Migration (Week 2)
- ADR-0003: Config Hardening, Dependency Consolidation, Generator Migration (Week 3)
- 0001-week1-critique.md, 0002-week2-critique.md, 0003-week3-critique.md
- External assessment: B+ (88/100) with explicit debt items listed above
