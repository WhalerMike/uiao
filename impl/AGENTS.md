# AGENTS.md — UIAO-Impl Module

> Python application code for the UIAO governance ecosystem. Tool-neutral agent entry point; a thin `CLAUDE.md` stub at the same path points here for tools looking specifically for `CLAUDE.md`.

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
impl/
├── AGENTS.md            # Agent integration (this file)
├── CLAUDE.md            # thin stub → AGENTS.md
├── pyproject.toml
├── README.md
├── src/uiao/impl/        # Python package
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
