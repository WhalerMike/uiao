# UIAO

**Unified Identity-Addressing-Overlay Architecture** — a YAML-driven governance platform for FedRAMP Moderate, Zero Trust, and TIC 3.0 compliance automation.

UIAO turns a single YAML source of truth (SSOT) into OSCAL artifacts, continuous KSI validation, and drift-to-POA&M workflows — so compliance teams can stop hand-authoring SSPs and start governing from code.

## Key Benefits

- **YAML SSOT → OSCAL:** Automatically generate FedRAMP-compliant SSPs and POA&Ms from a single canonical YAML definition.
- **KSI validation:** Continuous Key Security Indicator checks against your live control posture.
- **Drift detection in <120 seconds:** Detect configuration drift and open POA&M items automatically.
- **Standards coverage:** FedRAMP Moderate, Zero Trust Architecture (ZTA), and TIC 3.0 out of the box.
- **Single install:** `pip install uiao` — no more sibling-folder `--canon-path` fragility.

## Installation

From source (during active development):

```bash
git clone https://github.com/WhalerMike/uiao.git
cd uiao
pip install .
```

From PyPI (once released):

```bash
pip install uiao
```

## Quick Start

```bash
# Show available commands
uiao --help

# Validate your canon YAML
uiao validate path/to/canon.yml

# Generate an OSCAL SSP
uiao oscal ssp path/to/canon.yml --out build/ssp.json

# Run KSI checks
uiao ksi run path/to/canon.yml

# Detect drift
uiao drift check path/to/canon.yml
```

## Documentation

Full documentation lives in [`docs/`](./docs) and is published via Quarto. Once the docs pipeline is wired up, the rendered site will be available at the project's GitHub Pages URL.

## Architecture Overview

UIAO is organized around **six control planes** and **eight core concepts**.

**Six control planes:**

1. Identity
2. Addressing
3. Overlay / Network
4. Policy
5. Telemetry
6. Governance

**Eight core concepts:**

1. Canon (YAML SSOT)
2. Adapters (OSCAL, POA&M, KSI, drift)
3. Schemas (validation)
4. Rules (policy-as-code)
5. GOS (governance operating system)
6. KSI (Key Security Indicators)
7. Drift (continuous posture checks)
8. Artifacts (SSP, POA&M, dashboards, briefings)

See `docs/` for the full architectural model and control mappings.

## Status

Currently in **active development and consolidation into a single repository**. The previous multi-repo layout (`uiao-core`, `uiao-impl`, `uiao-docs`, `uiao-gos`) is being folded into this monorepo. Expect breaking changes until `v1.0`.

## License

Licensed under the [Apache License 2.0](./LICENSE).

## Contributing

Contributions are welcome. See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for development setup, coding standards, and the AI-assisted workflow used on this project.
