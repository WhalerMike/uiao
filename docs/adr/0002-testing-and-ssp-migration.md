# ADR-0002: Testing Infrastructure and SSP Generator Migration

## Status

Accepted (Week 2 - 2026-03-23)

## Context

Week 1 (ADR-0001) established the src-layout package structure but shipped zero tests.
The `generators/ssp.py` stub raises NotImplementedError, while the real SSP logic
lives in `scripts/generate_ssp.py` (~180 lines). This creates two risks:

1. No confidence gate on refactoring (any change could silently break output)
2. Dual code paths (scripts/ vs src/) will drift over time

Additionally, CI does not exercise `pip install -e .` so the package is untested
as an installable artifact.

## Decision

1. **Add pytest infrastructure**: `tests/conftest.py` with shared fixtures,
   `tests/test_models.py`, `tests/test_cli.py`, `tests/test_generators.py`
2. **Migrate `scripts/generate_ssp.py`** logic into `src/uiao_core/generators/ssp.py`
   as importable functions (`load_context()`, `build_set_parameters()`,
   `build_ssp_skeleton()`, `build_ssp()`)
3. **Add `pip install -e .` to CI** so package installation is validated on every push
4. **Add pytest to requirements.txt** as a dev dependency

## Consequences

### Positive
- First automated test coverage for the package
- SSP generation becomes importable and testable (not just script-runnable)
- CI validates the package is installable
- Foundation for Week 3+ validation and further migration

### Negative
- Test fixtures need real YAML data files (canon/, data/) to be meaningful
- Migration may introduce subtle differences vs. scripts/ output
- pytest adds a dev dependency

### Alternatives Considered
- unittest (rejected: pytest is standard for modern Python, better fixtures)
- Mocking all YAML (rejected: real data tests catch schema drift)
- Keeping scripts/ as primary (rejected: defeats Week 1 restructure purpose)
