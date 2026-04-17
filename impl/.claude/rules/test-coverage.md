# Rule: Test Coverage for CLI Commands

> **Always-on.** This file is loaded automatically by Claude Code.

## Declaration

Every CLI command in `uiao-impl` is covered by `pytest`. New commands land
with their tests in the same PR.

## Enforcement

1. **A new CLI command (subcommand added to `argparse` / `click` / equivalent)
   must ship with at least one happy-path test and one failure-mode test.**
2. **A CLI behavior change must update the existing tests** — no silent
   behavior drift.
3. **Tests live under `tests/`** mirroring the source tree
   (`src/uiao/impl/commands/foo.py` → `tests/commands/test_foo.py`).
4. **Fixtures for canon paths** live under `tests/fixtures/canon/`. Do not
   reach into a sibling `uiao-core` checkout from tests.

## What counts as "a CLI command"

- A new subparser / subcommand → covered.
- A new flag that changes observable behavior → covered.
- A new adapter invoked via CLI → covered end-to-end (from CLI entry to
  adapter boundary; mock the cloud side).
- A pure refactor with no behavioral change → existing tests still pass; no
  new tests required.

## Running the suite

```bash
pytest -q              # fast path
pytest -q --cov        # with coverage
pytest -q -k cli_foo   # target a specific command
```

## CI

CI runs `pytest` on every PR and blocks merge on failure. See
`.github/workflows/ci.yml`.

<!-- NEW (Proposed) -->
