# Agent Coding Standards

This document defines the core coding standards and conventions for AI coding agents (e.g., GitHub Copilot) working in this repository.

## Runtime & Tooling

- **Node:** 24+ (enforce via `engines` field in `package.json` where applicable)
- **Python:** 3.12+ (see `requirements.txt` for pinned dependencies)
- **Test framework:** Vitest (for any TypeScript/JavaScript components); `unittest`/`pytest` for Python
- **Benchmarking:** `npm run bench` (for JS/TS); `pytest-benchmark` for Python

## Core Principles

### Performance-First
- Prefer lazy evaluation and generator patterns over materializing large collections.
- Profile before optimizing; add benchmark assertions for hot paths.
- Avoid synchronous I/O on the main thread in any async context.

### Single Source of Truth
- All technical standards live in `data/atlas-appendices.yml`. Do not duplicate content.
- Templates (`.j2` files under `templates/`) render from the canonical YAML graph.
- Generated artifacts in `docs/`, `site/`, and `exports/` must never be edited by hand.

### Security & Compliance
- Every script that writes files must validate output against the relevant JSON schema in `schemas/`.
- Secrets must never be hard-coded; use `${{ secrets.* }}` in workflows and `.env` files locally (see `.env.example`).
- OSCAL artifacts in `exports/oscal/` are authoritative compliance evidence — treat modifications with the same rigor as code changes.

## Workflow Conventions

- Branch names: `feat/<slug>`, `fix/<slug>`, `chore/<slug>`
- Commit messages: [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`)
- Pull Requests require passing CI before merge (see `.github/workflows/`).
- The `copilot-setup-steps.yml` pre-submission hooks run `npm test` (JS/TS) and `npm run bench` automatically.

## File Placement Rules

| Artifact type | Location |
|---|---|
| Canonical content | `canon/` |
| Data / appendices | `data/` |
| Jinja2 templates | `templates/` |
| Generator scripts | `scripts/` |
| JSON schemas | `schemas/` |
| Generated docs | `docs/` (auto-generated, do not edit) |
| OSCAL exports | `exports/oscal/` (auto-generated) |
| Tests | `tests/` |
| GitHub Actions | `.github/workflows/` |

## Testing Requirements

- Every new script in `scripts/` must have a corresponding test in `tests/`.
- Test files follow the naming convention `test_<module_name>.py`.
- All tests must pass before a PR can be merged (enforced by CI).
