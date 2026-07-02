# Contributing to ScubaDrift

Thanks for helping. ScubaDrift's value is that it is small, correct, and stays
in its lane — contributions should preserve all three.

## Setup

```bash
pip install './scubadrift[dev]'   # pytest + ruff, editable install
pytest -q
ruff check src tests
```

Python 3.10+ is required. There are **no runtime dependencies** and adding one
needs a strong justification — the parser's optional YAML support (`[yaml]`) is
the only tolerated example, and it degrades gracefully when absent.

## Ground rules (the scope contract)

Before proposing a feature, check it against the **Design & scope** section of
`ScubaDrift-Documentation.docx`.
ScubaDrift is not a scanner, not a baseline, not a remediator, not an OSCAL
generator, and not a policy-inheritance engine. Changes that pull it toward any
of those will be declined, however useful — that is a different tool.

In scope: better ScubaGear-shape tolerance, richer drift/triage reporting,
additional output formats, register ergonomics, docs.

## Coding standards

- **Determinism.** Never read the wall clock (`date.today()` / `datetime.now()`)
  inside library code. Time enters only as an injected `as_of: date`, defaulted
  solely at the CLI edge. Tests must pin `as_of`. This rule is non-negotiable —
  it is why the suite cannot rot.
- **Immutability.** Model objects are frozen dataclasses with a `to_dict()`. Keep
  the `--json` output and the library shape identical.
- **Tolerant in, strict out.** Be forgiving parsing ScubaGear (aliases,
  variants); be strict validating the register (reject duplicates and bad
  dates loudly).
- **Style.** `ruff` with `line-length = 120` (see `pyproject.toml`). Run
  `ruff check src tests` before pushing.

## Tests

- Every behavior change needs a test. The suite is offline and deterministic;
  keep it that way (use the fixtures under `tests/fixtures/`, or add new ones).
- Prefer characterization tests that pin *observable* behavior (dispositions,
  counts, exit codes) over implementation details.
- Run the whole suite (`pytest -q`) and the linter before opening a PR.

## Commit / PR

- Keep changes focused; update `docs/` and `CHANGELOG.md` in the same PR as the
  behavior they describe.
- Describe *what observable behavior changed* and *why*, and note any new
  ScubaGear shape or register field you now accept.

## Reporting issues

Include: the ScubaDrift version (`scubadrift --version`), the command you ran,
the (sanitized) input shape, and what you expected vs. what happened. Never paste
real tenant identifiers, credentials, or unredacted `TenantId`s.
