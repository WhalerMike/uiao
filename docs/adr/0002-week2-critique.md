# ADR-0002 Week 2 Self-Critique

## What Was Delivered

- ADR-0002 (testing infrastructure and SSP migration)
- `tests/conftest.py` with shared fixtures (project_root, canon_dir, data_dir, exports_dir)
- `tests/test_models.py` with CanonEntry model tests and data dir assertions
- `tests/test_cli.py` with CLI --version, --help, and subcommand tests
- Full SSP generator migration: `src/uiao_core/generators/ssp.py` (~288 lines)
  - `load_context()`, `build_set_parameters()`, `build_ssp_skeleton()`, `build_ssp()`
- Updated `cli/app.py` with `--canon`, `--data-dir`, `--output` options
- New CI workflow `.github/workflows/ci.yml` (Python 3.11/3.12 matrix)
  - `pip install -e .` + `pytest` on every push
- `pytest>=7.0` added to requirements.txt

## What Went Well

1. **SSP migration is 1:1 faithful.** Same logic as scripts/, now importable.
2. **CI now validates the package is installable.** Biggest risk from Week 1 eliminated.
3. **Tests exercise real CLI surface.** Typer CliRunner catches import/wiring errors.
4. **ADR-first approach continues to work.** Decision documented before code.

## What Needs Improvement

1. **Tests don't run the actual SSP generator end-to-end.** Would need data/ and canon/ in CI.
2. **No test for generators/ssp.py functions directly.** Only CLI and models tested.
3. **scripts/generate_ssp.py not updated to shim.** Dual code path still exists.
4. **Dependency duplication still present.** requirements.txt + pyproject.toml.
5. **datetime.utcnow() is deprecated in Python 3.12+.** Should use datetime.now(UTC).
6. **No mypy or ruff config yet.** Type checking not enforced in CI.

## Risk Assessment

- **LOW:** SSP migration is backward-compatible. Old script still works.
- **MEDIUM:** CI may fail on first run if trestle deps have install issues.
- **HIGH:** No end-to-end SSP test = generator could silently break.

## Week 3 Priorities

1. Add end-to-end test for SSP generator (with real data/)
2. Convert scripts/generate_ssp.py to a thin shim
3. Add mypy + ruff to CI
4. Begin ADR-0003 for remaining script migration (generate_docs, generate_oscal)
5. Fix datetime.utcnow() deprecation
