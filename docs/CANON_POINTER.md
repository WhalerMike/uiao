# CANON POINTER

The UIAO Governance Canon — all human-readable documentation, appendices,
ADRs, diagrams, glossary, and onboarding guides — lives exclusively in:

  https://github.com/WhalerMike/uiao-docs

## Do NOT duplicate canon content in this repository.

This repository (uiao-core) contains **machine artifacts only**:

| Artifact Type | Location |
|---|---|
| Adapter schemas and transforms | `adapters/scuba/schemas/` |
| KSI evaluation scripts | `ksi/evaluations/` |
| KSI rules (YAML) | `ksi/rules/` |
| Provenance manifests | `provenance/manifests/` |
| Normalized SCuBA artifacts | `artifacts/scuba/normalized/` |
| GitHub Actions workflows | `.github/workflows/` |

## Governance Separation Rule

> Machine artifacts → `uiao-core` ONLY
> Human artifacts → `uiao-docs` ONLY
> No duplication across repos. This rule is non-negotiable.

## Links

- Canon site: https://whalermike.github.io/uiao-docs/
- Canon repo: https://github.com/WhalerMike/uiao-docs
- Machine repo: https://github.com/WhalerMike/uiao-core
