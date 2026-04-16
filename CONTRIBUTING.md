# Contributing to UIAO

Thanks for your interest in UIAO! This project is maintained by a small team with heavy reliance on AI-assisted development, so the workflow is intentionally lightweight.

## AI-Assisted Contributions Are Welcome

You are encouraged to use AI tools (Claude, ChatGPT, Copilot, etc.) to help draft code, docs, and tests. The only hard rules:

- **You** are responsible for reviewing and understanding any AI-generated code before submitting it.
- Make sure generated code runs locally and passes the checks below.
- Don't paste secrets or proprietary canon content into public AI tools.

## Small, Focused Changes

Keep pull requests small and single-purpose. Good examples:

- Add one new CLI subcommand
- Add or fix one adapter
- Update one section of the docs
- Add tests for one module

Large, sweeping refactors are hard to review and hard for AI tools to reason about. Break them up.

## Local Development Setup

```bash
git clone https://github.com/WhalerMike/uiao.git
cd uiao
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Checks Before You Push

Run these locally — CI will run the same checks:

```bash
pytest                  # run the test suite
ruff check .            # lint
ruff format --check .   # formatting
mypy src/uiao           # type checking
```

If you added a feature, add a test. If you fixed a bug, add a regression test.

## Step-by-Step Workflow

This repo is actively being consolidated from four legacy repositories (`uiao-core`, `uiao-impl`, `uiao-docs`, `uiao-gos`). While that work is in flight, we work **one file at a time**:

1. Propose or pick a single file / small change.
2. Generate it (AI-assisted is fine).
3. Review, commit, push.
4. Move to the next file.

This keeps the diffs reviewable and the monorepo migration stable.

## Commit Messages

- Short, imperative subject line (e.g., `Add drift-check CLI subcommand`).
- Optional body explaining the *why* if it's non-obvious.

## Questions

Open a GitHub Issue — or just ask in a PR description. Friendly questions are always welcome.
