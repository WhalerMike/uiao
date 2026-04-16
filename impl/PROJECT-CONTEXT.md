# PROJECT-CONTEXT.md — UIAO-Impl

> Quick-start context for Claude Code sessions and new contributors.
> For the authoritative Claude Code control surface, see [`CLAUDE.md`](CLAUDE.md).

## What this repo is

`uiao-impl` is the **Python application code** for the UIAO governance ecosystem:
library, CLI, generators, adapters, and the pytest suite. It is a **consumer** of
canon — it does not define canonical artifacts. All canonical governance
artifacts live in [`uiao-core`](https://github.com/WhalerMike/uiao-core).

## The four-repo split

| Repo | Role | Canon authority |
|---|---|---|
| [`uiao-core`](https://github.com/WhalerMike/uiao-core) | Canonical governance framework | **Source of truth** |
| [`uiao-docs`](https://github.com/WhalerMike/uiao-docs) | Derived documentation (articles, guides, playbooks) | Consumer |
| [`uiao-impl`](https://github.com/WhalerMike/uiao-impl) | Python library + CLI + adapters | Consumer |
| `uiao-gos` | Commercial product (separate architecture) | Out of scope |

## Runtime canon resolution

All runtime canon reads go through the `--canon-path` CLI argument. **Do not
hard-code `../uiao-core` paths.** See `src/uiao_impl/canon.py` for the
resolution helpers.

```bash
uiao-impl validate --canon-path /path/to/uiao-core
```

## Test-first convention

Every CLI command is covered by `pytest`. New commands land with their tests
in the same PR — no exceptions. Run the suite locally with:

```bash
pytest -q
```

## Cloud boundary

**GCC-Moderate (Microsoft 365 SaaS).** Exception: Amazon Connect Contact Center
operates in Commercial Cloud. No GCC-High or DoD targets unless explicitly
noted in an ADR.

## Where to look first

| Question | File |
|---|---|
| How does Claude Code work in this repo? | [`CLAUDE.md`](CLAUDE.md) |
| Repo-level Claude rules, agents, skills, commands | [`.claude/`](.claude/) |
| Python package entry point | `src/uiao_impl/` |
| Adapter plugins (cloud / database / gov / SCuBA) | `adapters/` |
| Test suite | `tests/` |
| CI workflows | `.github/workflows/` |

## Commit convention

```
[UIAO-IMPL] <verb>: <module> — <short description>
```

Verbs: `CREATE`, `UPDATE`, `FIX`, `REFACTOR`, `TEST`, `DEPRECATE`.

## Related canon

- **SSOT reference:** `uiao-core/canon/UIAO-SSOT.md`
- **Architecture (federal pair):** `uiao-core/ARCHITECTURE.md`

<!-- NEW (Proposed) -->
