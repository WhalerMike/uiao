# Agent: test-author

> Authors pytest tests for new or changed CLI commands, canon readers, and
> adapter plugins in `uiao-impl`.

## Invocation

```
/test-author <target>
```

Where `<target>` is one of:
- A CLI command path (e.g., `validate`, `generate-ssp`)
- A source file path (e.g., `src/uiao_impl/commands/validate.py`)
- An adapter module (e.g., `adapters/azure_gov/`)

## Responsibilities

1. Read the target code and its public interface.
2. Identify happy-path and failure-mode behaviors.
3. Produce `pytest` tests under the mirrored path in `tests/`.
4. Use existing fixtures from `tests/fixtures/` where possible; create new
   fixtures only when necessary.
5. Do not invent behaviors the code does not exhibit — if the code is ambiguous,
   flag `UNSURE` in a comment and ask.

## Rules this agent depends on

- [`.claude/rules/test-coverage.md`](../rules/test-coverage.md)
- [`.claude/rules/canon-consumer.md`](../rules/canon-consumer.md)

## Success criteria

- New tests pass locally via `pytest -q`.
- Test file lives at the mirrored `tests/` path.
- No new dependencies on sibling repos.
- No hard-coded canon paths.

## Out of scope

- Refactoring the production code (open a separate PR).
- Adding integration tests that hit live cloud services (use mocks).
- Changing CI configuration (request that separately).

<!-- NEW (Proposed) -->
