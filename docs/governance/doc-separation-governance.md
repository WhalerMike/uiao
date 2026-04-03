# Governance: Separation of User Documents and Machine Documents

**Status:** Active  
**Effective Date:** 2026-04-03  
**Scope:** All directories and files in the `uiao-core` repository

## 1. Core Principle

User Documents and Machine Documents must never share a directory, a naming convention, or a lifecycle. They serve different audiences, different update cadences, and different validation pipelines.

## 2. Definitions

| Term | Definition |
|------|------------|
| **User Document** | Human-readable content: README files, architecture guides, user manuals, onboarding docs, governance policies, pattern descriptions |
| **Machine Document** | Machine-generated or machine-consumed artifacts: YAML schemas, JSON configs, OSCAL artifacts, CI/CD pipeline definitions, auto-generated specs |
| **Canonical Document** | Authoritative definitions referenced by both humans and machines, stored in `/canon/` |

## 3. Directory Assignment

| Directory | Type | Contents |
|-----------|------|----------|
| `docs/user-guides/` | User | How-tos, walkthroughs, user manuals |
| `docs/architecture/` | User | High-level diagrams, conceptual models |
| `docs/onboarding/` | User | Developer onboarding, contributor guides |
| `docs/governance/` | User | Policies, rules, decision logs |
| `docs/patterns/` | User | Architecture patterns, best practices |
| `machine/schemas/` | Machine | JSON Schema, YAML Schema, OSCAL, OpenAPI |
| `machine/configs/` | Machine | Machine-consumed configs (YAML, JSON) |
| `machine/pipelines/` | Machine | CI/CD definitions, GitHub Actions fragments |
| `machine/generators/` | Machine | Auto-generated specs, compiler outputs |
| `machine/adapters/` | Machine | Machine contracts for adapters |
| `canon/` | Canonical | Core principles, versioned rules, cross-layer references |

## 4. Governance Rules

### Rule 1: No machine artifacts in /docs/
If a PR adds JSON or YAML to `/docs/`, the reviewer must reject it.

### Rule 2: No Markdown in /machine/
If a PR adds `.md` files to `/machine/`, the reviewer must reject it.

### Rule 3: Every machine artifact must have a human-facing explanation
The explanation lives in `/docs/architecture/` or `/docs/governance/`, not alongside the artifact.

### Rule 4: Generated artifacts must never be edited by humans
Place them in `/machine/generators/` with timestamps. Update only via scripts.

### Rule 5: Schemas must be versioned
Use semantic versioning in filenames (e.g., `schema.uiao-core.v1.2.0.json`).

### Rule 6: Cross-linking is allowed, duplication is not
User docs link to machine docs; they do not copy them.

## 5. Migration Notes

Existing files in the repo root and in mixed directories will be migrated incrementally. Priority order:
1. Establish new directory structure (complete)
2. Move existing user docs into appropriate `docs/` subdirectories
3. Move existing machine artifacts into `machine/` subdirectories
4. Update all cross-references and links
5. Add CI checks to enforce separation rules

## 6. Exceptions

- The root `README.md` remains at the repository root.
- The `.github/` directory follows GitHub conventions.
- The `canon/` directory serves both audiences by design.
- `scripts/` contains utility tools, not artifacts.
