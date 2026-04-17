# Security Policy

## Supported versions

| Version | Security support |
|---|---|
| `main` (unreleased) | ✅ active |
| Latest tagged release | ✅ active |
| Older tagged releases | ❌ upgrade to latest |

UIAO is a pre-1.0 project. Breaking changes can land in any minor version; please track `main` or the latest release tag for security updates.

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

### Preferred channel

Use GitHub's [private vulnerability reporting](https://github.com/WhalerMike/uiao/security/advisories/new) to file a report. This creates a private advisory visible only to maintainers.

### What to include

- **Affected component** — `core/`, `docs/`, `impl/`, CI workflow, or specific adapter
- **Affected version** — commit SHA or release tag
- **Description** — what the vulnerability is and its potential impact
- **Reproduction steps** — minimal steps to trigger the issue
- **Proposed mitigation** (optional) — if you have a fix in mind

### Expected response

- **Acknowledgement** within 3 business days
- **Initial triage** within 7 business days
- **Fix or mitigation timeline** communicated after triage

Fix velocity depends on severity, reproduction complexity, and whether the affected surface is a canon doc, CI pipeline, runtime adapter, or released wheel.

## Scope

### In scope

- Any code, canon document, schema, workflow, or configuration under `core/`, `docs/`, `impl/`, or `.github/`
- Published artifacts: wheels, sdists, releases, rendered documentation site
- Supply-chain: dependencies declared in `impl/pyproject.toml`, GitHub Actions used in workflows

### Out of scope

- Issues in upstream dependencies — report to their maintainers; we can cut a dependency-bump release once upstream fixes land
- Vulnerabilities requiring compromised developer credentials (that's a credentials issue, not a code issue)
- Rate-limiting or DoS concerns on the public Quarto docs site — that's GitHub Pages

## FedRAMP-Moderate posture

UIAO is designed to operate within a FedRAMP-Moderate boundary. Vulnerabilities that could affect:

- Boundary isolation (GCC-Moderate tenant confinement)
- Certificate-anchored provenance integrity
- SSOT mutation invariants (`ssot-mutation: never` per `core/schemas/adapter-registry/adapter-registry.schema.json`)
- Drift detection bypass paths (see `docs/docs/16_DriftDetectionStandard.qmd`)

…are treated as **high-severity** and take priority in triage.

## Attribution

Vulnerability reporters are credited in the resulting GitHub Security Advisory unless anonymity is requested. If a CVE is assigned, the reporter is named as the discoverer.
