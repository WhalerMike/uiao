# Command: /test

> Run the pytest suite with sensible defaults.

## Usage

```
/test                 # run full suite
/test <expr>          # run tests matching pytest -k <expr>
/test --cov           # run with coverage
```

## Behavior

1. Runs `pytest -q` from the repo root.
2. With `<expr>`, appends `-k <expr>`.
3. With `--cov`, appends `--cov=src/uiao/impl --cov-report=term-missing`.
4. Reports pass/fail summary and surfaces first-failure traceback if any.

## Guardrails

- Does not modify source or test files.
- Does not install dependencies (CI handles that).
- Does not touch sibling repos.

## Related

- Rule: [`.claude/rules/test-coverage.md`](../rules/test-coverage.md)
- Agent: [`.claude/agents/test-author.md`](../agents/test-author.md) — use when
  a command is missing tests that `/test` reveals.

<!-- NEW (Proposed) -->
