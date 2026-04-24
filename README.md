# UIAO — Unified Identity-Addressing-Overlay Architecture

[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![FedRAMP Moderate](https://img.shields.io/badge/FedRAMP-Moderate%20Rev%205-orange.svg)](src/uiao/canon/compliance/executive-orders.md)
[![Substrate](https://img.shields.io/badge/substrate-3%20modules%20%7C%2027%20canon%20docs-blueviolet.svg)](src/uiao/canon/substrate-manifest.yaml)
[![Adapters](https://img.shields.io/badge/modernization%20adapters-9%20active%20%7C%201%20reserved-success.svg)](src/uiao/canon/modernization-registry.yaml)
[![CI](https://img.shields.io/badge/CI-7%20workflows-informational.svg)](.github/workflows/)

Governance OS for FedRAMP-Moderate identity, telemetry, policy, and enforcement
modernization. Identity-first. Canon-anchored. Drift-detected.

> **Canonical substrate manifest:** [`src/uiao/canon/substrate-manifest.yaml`](src/uiao/canon/substrate-manifest.yaml) (UIAO_200).
> **Document registry:** [`src/uiao/canon/document-registry.yaml`](src/uiao/canon/document-registry.yaml).
> **Schemas:** [`src/uiao/schemas/`](src/uiao/schemas/).
> **Contributing:** [`CONTRIBUTING.md`](CONTRIBUTING.md) · **Security:** [`SECURITY.md`](SECURITY.md) · **Changelog:** [`CHANGELOG.md`](CHANGELOG.md).

## What UIAO is

UIAO is a governance substrate, not a product. It defines:

- **SSOT** — a single source of truth per claim, certificate-anchored,
  certified via provenance chains that cannot be backfilled.
- **Canon** — the authoritative artifacts (schemas, registries, policies,
  executive-order mappings). Canon lives under [`src/uiao/canon/`](src/uiao/canon/) and ships with the wheel as package data; everything else derives.
- **Substrate** — the cross-cutting data and control layer that adapters
  consume and emit against. Documented here in the substrate manifest.
- **Overlay** — the identity-derived certificate-anchored tunnel abstraction.
- **Adapters** — externally-facing connectors. Two operational classes
  (`conformance` = read-only, `modernization` = change-making) × five
  mission classes (`identity | telemetry | policy | enforcement | integration`).
  Registered in [`src/uiao/canon/adapter-registry.yaml`](src/uiao/canon/adapter-registry.yaml) and
  [`src/uiao/canon/modernization-registry.yaml`](src/uiao/canon/modernization-registry.yaml).
- **Drift** — deviation between live state and canon, detected in five
  classes (`DRIFT-SCHEMA`, `DRIFT-SEMANTIC`, `DRIFT-PROVENANCE`, `DRIFT-AUTHZ`,
  `DRIFT-IDENTITY`) at four severities (`P1`–`P4`). Taxonomy defined in
  [`docs/docs/16_DriftDetectionStandard.qmd`](docs/docs/16_DriftDetectionStandard.qmd).
- **KSI** — Key Security Indicators. 163 continuous-compliance signals,
  cryptographically signed.

## Repository layout

As of [ADR-032](src/uiao/canon/adr/adr-032-single-package-consolidation.md) (2026-04-20) UIAO is a **single Python package** rooted at `src/uiao/`. The pre-consolidation `core/` and `impl/` directories no longer exist — every concern they held now lives under `src/uiao/<subpackage>/`.

| Path | Role | Notes |
|---|---|---|
| [`src/uiao/`](src/uiao/) | Installable `uiao` distribution | Single source of all runtime code, canon, schemas, rules, KSI library, adapters. |
| [`src/uiao/canon/`](src/uiao/canon/) | Canon authority (SSOT) | Governance documents, ADRs, registries, control library, specs. Canon-change rules in [`AGENTS.md`](AGENTS.md#repository-invariants). |
| [`src/uiao/schemas/`](src/uiao/schemas/) | Schema authority | JSON Schema drafts 07 and 2020-12. Validates registries, manifest, workspace contract, metadata. |
| [`src/uiao/adapters/`](src/uiao/adapters/) | Connector implementations | 13 adapters across modernization (change-making) and conformance (read-only) classes. |
| [`src/uiao/cli/`](src/uiao/cli/) | Typer CLI entry point | `uiao` console script → `uiao.cli.app:app`. |
| [`tests/`](tests/) | Test suite | Unit, integration, adapter conformance, substrate drift. |
| [`docs/`](docs/) | Documentation source | `.qmd`/`.md`/`.yml` only; Quarto site renders to `docs/_site/` (gitignored). |
| [`scripts/`](scripts/) | Workspace tooling | Bootstrap, schema validators, link check, doc generators. |
| [`inbox/`](inbox/) | Draft staging | Not canon. Promote to `src/uiao/canon/` or `docs/` when ready. |
| [`deploy/windows-server/`](deploy/windows-server/) | Windows IIS deploy artifacts | uvicorn entrypoint + `web.config` referenced by [`src/uiao/api/app.py`](src/uiao/api/app.py). |
| [`.github/workflows/`](.github/workflows/) | CI | Schema validation, pytest, substrate-drift, ruff, mypy (non-blocking), quarto, link-check, release. |

Canon authority lives in [`src/uiao/canon/`](src/uiao/canon/) and is **protected**: changes require a UIAO_NNN allocation in [`document-registry.yaml`](src/uiao/canon/document-registry.yaml), and doctrinal changes require an ADR under [`src/uiao/canon/adr/`](src/uiao/canon/adr/). See [AGENTS.md § Repository Invariants](AGENTS.md#repository-invariants) for the full invariant set.

## Quick start

**New to UIAO?** Walk the [10-minute quickstart](docs/docs/quickstart.md) — it runs a full auditor bundle (evidence, POA&M, SSP narrative) against a synthetic ScubaGear fixture. No Azure tenant, no API keys, no live data.

**Writing an adapter?** Follow the [30-minute adapter authoring tutorial](docs/docs/adapter-authoring-tutorial.md) — walks from zero to a merged PR using the shipped ScubaGear adapter as the worked example.

```bash
# Install the package + CLI in editable mode
pip install -e .

# (Optional) dev tooling
pip install -e ".[dev]"

# Run the 10-minute quickstart end-to-end
uiao ir auditor-bundle examples/quickstart/scuba-normalized.json --out-dir /tmp/uiao-quickstart

# Validate substrate integrity
uiao substrate walk
```

Set `UIAO_WORKSPACE_ROOT` to the absolute path of your local checkout when running tooling that needs to resolve workspace-relative paths:

```bash
# Linux / macOS
export UIAO_WORKSPACE_ROOT="$HOME/src/uiao"

# Windows (PowerShell)
$env:UIAO_WORKSPACE_ROOT = "$env:USERPROFILE\src\uiao"
```

Common Make targets: `make help`, `make walk`, `make drift`, `make test`, `make lint`, `make schemas`, `make docs`.

## Governance gates

Every PR into `main` is gated by CI workflows in [`.github/workflows/`](.github/workflows/):

- `schema-validation` — adapter registries, substrate manifest, workspace contract conform to their schemas.
- `metadata-validator` — canon document frontmatter conforms to [`src/uiao/schemas/metadata-schema.json`](src/uiao/schemas/metadata-schema.json).
- `substrate-drift` — `uiao substrate drift` exit-code gate on canon / substrate-manifest changes.
- `pytest` — substrate walker (fast) + full suite (blocking).
- `ruff` — lint and format check (blocking).
- `quarto` — render docs on PR; deploy to GitHub Pages on push to `main`.

## License

Apache 2.0. See [`LICENSE`](LICENSE).
