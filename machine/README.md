# Machine-Facing Artifacts

This directory contains **machine-generated and machine-consumed documents** for the UIAO-Core project.

## Purpose

All artifacts in this directory are intended for consumption by automation, validators, compilers, or CI/CD pipelines — **not for direct human reading**.

## Subdirectories

| Directory | Contents |
|-----------|----------|
| `schemas/` | JSON Schema, YAML Schema, OSCAL definitions, OpenAPI specs |
| `configs/` | Machine-consumed configuration files (YAML, JSON) |
| `pipelines/` | CI/CD definitions, GitHub Actions workflow fragments |
| `generators/` | Auto-generated specs, compiler outputs (never manually edited) |
| `adapters/` | Machine contracts for adapter onboarding |

## Governance Rules

1. **No Markdown files** are permitted in this directory or its subdirectories.
2. **All content must be 100% machine-parseable** — no prose, no diagrams, no commentary.
3. **Generated artifacts** (`generators/`) must never be manually edited; they are updated via scripts only.
4. **Schemas must be versioned** using semantic versioning in filenames.
5. **Cross-linking is allowed** — user docs in `/docs/` may link here, but content must not be duplicated.

## Naming Conventions

- `schema.<domain>.<name>.json`
- `config.<module>.yaml`
- `pipeline.<name>.yaml`
- `adapter.<name>.contract.json`
- `generated.<source>.<name>.json`

## Related

- Human-readable documentation: [`/docs/`](../docs/)
- Canonical definitions: [`/canon/`](../canon/)
- Utility scripts: [`/scripts/`](../scripts/)
