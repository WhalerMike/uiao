# Week 4 Critique: Final Migration, Lint, DRY, and Pilot Packaging

**Date:** 2026-03-23
**ADR:** ADR-0004
**Status:** Complete

---

## Scope of Work

Week 4 targeted the final technical debt items identified in Weeks 1-3 critiques
and Grok's external assessment. The deliverables were:

1. **ADR-0004** - Decision record for DRY refactor, migration, lint, and packaging
2. **DRY Refactor** - Extract `load_context()`, `load_canon()`, `get_settings()` into `utils/context.py`
3. **Generator Updates** - All 5 generators (`oscal`, `poam`, `charts`, `ssp`, `docs`) refactored to use shared utils
4. **Rich DOCX Migration** - `scripts/generate_rich_docx.py` ported to `generators/rich_docx.py`
5. **Trestle Migration** - `scripts/assemble_with_trestle.py` ported to `generators/trestle.py`
6. **Legacy Shims** - Scripts in `scripts/` now import from package generators
7. **Lint Workflow** - `ci/lint.yml` with ruff and mypy
8. **Pre-commit** - `.pre-commit-config.yaml` with ruff hooks
9. **Integration Tests** - `test_integration.py` verifying imports and API signatures
10. **Packaging** - `docxtpl` added to `pyproject.toml` dependencies

## What Went Well

- **DRY elimination was clean.** The shared `utils/context.py` module reduced ~150 lines of
  duplicated context-loading logic across 5 generators to a single source of truth.
- **CI stayed green throughout.** Every commit (CI #16 through #31) passed, demonstrating
  incremental, non-breaking changes.
- **Conventional commits** maintained throughout, enabling automated changelog generation.
- **ADR-first discipline** held: ADR-0004 was committed before any code changes.
- **Settings injection** via `pydantic-settings` preserved `.env`-less CI compatibility
  with `_env_file=None` fallback.

## What Could Be Improved

- **No end-to-end generation test.** Integration tests verify imports and signatures but
  do not exercise actual document generation against test fixtures. A `tests/data/` fixture
  with minimal canon YAML would enable smoke tests.
- **Rich DOCX hardcoded visual filenames.** The `evidence_map` and `visuals` lists in
  `rich_docx.py` contain hardcoded image filenames rather than reading from canon data.
  This should be data-driven in a future iteration.
- **Type annotations incomplete.** While mypy is configured, `disallow_untyped_defs = false`
  means many functions lack type hints. Week 5 should tighten this.
- **No `py.typed` marker.** The package does not yet declare PEP 561 compliance.
- **Legacy shims still exist.** The scripts/ shims should eventually be deprecated with
  clear messaging directing users to `uiao` CLI or direct package imports.

## Remaining Technical Debt

| Item | Priority | Notes |
|------|----------|-------|
| E2E generation smoke tests | High | Need test canon fixtures |
| Tighten mypy (`disallow_untyped_defs = true`) | Medium | Incremental per-module |
| Data-driven visual references in rich_docx | Medium | Read from canon YAML |
| Add `py.typed` marker | Low | PEP 561 compliance |
| Deprecation warnings in legacy shims | Low | Warn users to migrate |
| SBOM / license scanning | Low | Supply chain security |

## Metrics

- **Commits this week:** 15 (CI #16 through #31)
- **CI pass rate:** 100% on CI workflow
- **New files:** 6 (`utils/__init__.py`, `utils/context.py`, `generators/rich_docx.py`,
  `generators/trestle.py`, `test_integration.py`, `.pre-commit-config.yaml`)
- **Modified files:** 8 (5 generators, `pyproject.toml`, 2 script shims)
- **Lines of duplication removed:** ~150 (estimated across generators)

## Conclusion

Week 4 successfully retired the remaining Week 1-3 technical debt. The codebase now
has a single shared context loader, all generators live in the installable package,
linting and pre-commit enforce code quality, and integration tests verify public APIs.
The project is in a solid position for a v0.2.0 milestone release with the remaining
debt items tracked above as post-release improvements.
