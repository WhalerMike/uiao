# CLAUDE.md — UIAO-Impl Repository

> Python application code for the UIAO governance ecosystem.

## Repository Identity
- **Name:** uiao-impl
- **Purpose:** Python library, CLI, generators, adapters, and pytest suite.
- **Canon Authority:** CONSUMER of `uiao-core` canon. Does NOT define canonical artifacts.
- **Cloud Boundary:** GCC-Moderate (Microsoft 365 SaaS). Exception: Amazon Connect in Commercial Cloud.

## Operating Principles
1. No-Hallucination Protocol available on demand.
2. All runtime canon reads go through `--canon-path` (no hard-coded `../uiao-core` paths).
3. Every CLI command is covered by pytest.
4. Breaking changes bump the minor version until `v1.0.0`.

## Directory Convention
```
uiao-impl/
├── CLAUDE.md
├── pyproject.toml
├── README.md
├── src/uiao_impl/        # Python package
├── tests/                # pytest suite
├── scripts/              # one-off generators, assemblers
├── adapters/             # cloud/database/government/scuba adapter plugins
└── .github/workflows/    # CI: pytest + wheel build
```

## Commit Convention
```
[UIAO-IMPL] <verb>: <module> — <short description>
```
Verbs: `CREATE`, `UPDATE`, `FIX`, `REFACTOR`, `TEST`, `DEPRECATE`.
