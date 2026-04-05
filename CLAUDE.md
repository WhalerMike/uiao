# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**uiao-core** is the generation engine and adapter framework for the Unified Identity-Addressing-Overlay Architecture (UIAO) — a federal network modernization program targeting FedRAMP Moderate Rev 5 compliance. It transforms YAML definitions into OSCAL JSON, Markdown, DOCX, PPTX, and CycloneDX SBOM artifacts.

This repo is the **engine**, not the documentation source. The canonical `.qmd` documents, YAML data schemas, and rendered site live in [uiao-docs](https://github.com/WhalerMike/uiao-docs).

## Build & Development Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Lint
ruff check --fix src/

# Type check (mypy strict mode, excludes scripts/ and tests/)
mypy src/uiao_core/

# Run CI test subset (what CI actually runs)
pytest tests/test_models.py tests/test_cli.py tests/test_workflow_serialization.py -v --tb=short

# Run full test suite
pytest

# Run a single test file
pytest tests/test_generators.py -v --tb=short

# Run a single test
pytest tests/test_models.py::test_function_name -v

# Pre-commit hooks (ruff + trailing whitespace + YAML check)
pre-commit run --all-files
```

## CLI

The `uiao` CLI (typer-based) is the primary interface. Entry point: `src/uiao_core/cli/app.py`.

```bash
uiao --version
uiao generate-ssp --canon <path> --data-dir data/ --output exports/
uiao generate-diagrams  # Renders PlantUML (.puml) -> PNG from generation-inputs/diagrams.yaml
uiao generate-docs      # Full doc generation (auto-calls diagram generation)
uiao generate-sbom --output sbom.cyclonedx.json
uiao validate <path>
uiao canon-check --dir <path>
```

## Architecture

### Two-repo model

- **uiao-core** (this repo): Python engine, adapters, schemas, generation pipeline
- - **uiao-docs**: Quarto pipeline, `.qmd` source files, rendered HTML site
 
  - ### Source layout (`src/uiao_core/`)
 
  - - `cli/` — Typer CLI app and subcommands
    - - `generators/` — OSCAL, SSP, POA&M, DOCX, PPTX, SBOM, diagram generators
      - - `adapters/` — Vendor system interfaces (Entra, Infoblox, CyberArk, ServiceNow, Palo Alto, Cisco, SD-WAN)
        - - `collectors/` — Data collectors for vendor systems
          - - `evidence/` — Bundler, collector, linker for compliance evidence (OSCAL back-matter)
            - - `validators/` — Schema and drift validators
              - - `models/` — Pydantic models
                - - `monitoring/` — Telemetry and health checks
                  - - `onboarding/` — JML (Joiner/Mover/Leaver) scenarios
                    - - `abstractions/` — Provider interface contracts
                     
                      - ### Key data directories
                     
                      - - `generation-inputs/` — YAML definitions that drive the generation engine (diagrams, briefing, pitch, plan)
                        - - `data/control-library/` — NIST control YAML files (~131+, expanding to full FedRAMP Moderate baseline)
                          - - `data/vendor-overlays/` — Big 7 vendor integration specs (9 files)
                            - - `schemas/` — JSON validation schemas (KSI, UDC, UIAO API)
                              - - `templates/` — Jinja2 templates for DOCX/PPTX rendering
                                - - `visuals/` — PlantUML source files (.puml)
                                 
                                  - ### Diagram pipeline
                                 
                                  - `generation-inputs/diagrams.yaml` is SSOT for all PlantUML diagrams. The flow:
                                 
                                  - `diagrams.yaml` → `generate_diagrams_from_canon()` → `visuals/*.puml` → `render_plantuml_file()` → `assets/images/plantuml/*.png`
                                 
                                  - > **Note:** Mermaid has been fully removed. All diagrams now use PlantUML (.puml) rendered via `plantweb` (pure-Python, no Node.js/mmdc required).
                                    >
                                    > ## Governance
                                    >
                                    > Read **PROJECT-CONTEXT.md** before making architecture decisions. It defines:
                                    >
                                    > - Format authority hierarchy (FORMAT-CANON.md > schemas/ > AGENTS.md > PROJECT-CONTEXT.md)
                                    > - - AI orchestration roles (Claude Code = Canon Steward + Lead Architect)
                                    >   - - Quality gates and current priorities
                                    >    
                                    >     - ### Quality gates (non-negotiable)
                                    >    
                                    >     - - All code must pass `ruff check` and CI
                                    >       - - OSCAL artifacts must validate with compliance-trestle
                                    >         - - Evidence must include `prop:id` prefix and valid UUIDv4
                                    >           - - GPG-signed commits required (advisory now, hard gate planned)
                                    >             - - POA&M statuses: `open`, `closed`, `risk-accepted`, `false-positive`, `operational-requirement`, `vendor-dependency`, `not-applicable`
                                    >              
                                    >               - ## Code Style
                                    >              
                                    >               - - **Python >= 3.10**, line length 120
                                    >                 - - **Ruff** rules: E, F, I, UP, B, SIM (with specific ignores — see pyproject.toml)
                                    >                   - - **mypy** strict mode (`disallow_untyped_defs`, `check_untyped_defs`)
                                    >                     - - Import ordering: `known-first-party = ["uiao_core"]`
                                    >                       - - YAML keys use hyphens (`BA-05`); Jinja2 templates normalize to underscores (`BA_05`)
                                    >                        
                                    >                         - ## CI/CD
                                    >                        
                                    >                         - 23 GitHub Actions workflows in `.github/workflows/`. The main CI (`ci.yml`) runs on push to main and PRs:
                                    >                        
                                    >                         - 1. Ruff lint
                                    >                           2. 2. mypy type check (continue-on-error)
                                    >                              3. 3. pytest (subset: test_models, test_cli, test_workflow_serialization)
                                    > 4. pip-audit + safety dependency scans
                                    > 5. 5. SBOM generation (Python 3.12 only)
                                    >   
                                    >    6. Matrix: Python 3.11 + 3.12 on ubuntu-latest.
                                    >   
                                    >    7. ## Classification
                                    >   
                                    >    8. This is a **CUI/FOUO** project. Never commit CUI or production artifacts to this public repo.
                                    >    9. 
