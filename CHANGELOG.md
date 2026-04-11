Changelog

All notable changes to the uiao-core project are documented in this file. This project adheres to **Semantic Versioning**.

\[2.0.0\] --- 2026-04-11

Architecture

- 4-Plane Pipeline Architecture redesign with 21 source modules and 31 workflows

- Deterministic, provenance-first pipeline from SCuBA JSON to OSCAL artifacts

- Modular package structure under src/uiao_core/

Core Pipeline

- **scuba** --- ScubaGear JSON to IR transformation (Plane 1)

- **ksi** --- IR to KSI control evaluation with YAML control library (Plane 2)

- **evidence** --- Evidence bundle building with HMAC-SHA256 signing (Plane 3)

- **oscal** --- OSCAL 1.1.2 SSP, POA&M, and SAR generation (Plane 4)

- **ir** --- Intermediate Representation core models and envelope

- **models** --- Pydantic v2 data models with runtime validation

Canon and Configuration

- KSI control library YAML configuration

- Notification configuration (Teams webhook + SMTP)

- Retention policy configuration

- Adapter registry configuration

Post-Processing

- **ssp** --- SSP narrative export and lineage tracing

- **diff** --- Diff engine for change detection between assessment runs

- **freshness** --- Evidence freshness grading (Fresh / Stale / Expired)

- **coverage** --- Control coverage export and trend reporting

- **dashboard** --- Governance dashboard rendering (HTML + JSON)

- **monitoring** --- Monitoring dashboard for pipeline observability

Governance

- **governance** --- Governance action framework (Remediate, Accept, Mitigate, Transfer)

- **auditor** --- Auditor bundle packaging for ATO delivery

Adapters and Collectors

- **adapters** --- Pluggable ComplianceAdapter ABC framework

- **scuba adapter** --- Built-in ScubaGear adapter

- **collectors** --- Data collection framework

- **cyberark collector** --- CyberArk sync integration

CLI

- Typer-based CLI with 10 command groups: scuba, ksi, evidence, oscal, ssp, diff, dashboard, coverage, governance, auditor

Infrastructure

- **generators** --- Document and artifact generation (diagrams, briefings)

- **validators** --- Input and schema validation framework

- **abstractions** --- Base classes and interfaces

- **onboarding** --- First-run onboarding flow

- **utils** --- Shared utilities (mover logic, workflow serialization)

- **config** --- Root configuration with layered loading

Testing

- 44 test files with \~398 tests

- 4 plane-specific test suites (98 tests): test_scuba_transform_plane.py, test_ksi_eval_plane.py, test_evidence_build_plane.py, test_oscal_generate_plane.py

- 35 core module test files (\~275 tests)

- 3 end-to-end test files: test_e2e.py, test_e2e_atlas_flow.py, test_integration.py

- 2 determinism test files: test_scuba_transformer_determinism.py, test_ir_hash_stability.py

- 45% coverage floor enforced in CI

CI/CD

- ci.yml --- Core test + coverage pipeline

- lint.yml --- Ruff linting

- ai-security-audit.yml --- AI-assisted security review

- security-scan.yml --- Dependency vulnerability scanning

- verify-signatures.yml --- Evidence signature verification

- generate-docs.yml --- Documentation generation

- generate-docx-exports.yml --- DOCX export pipeline

- deploy-docs.yml --- Documentation site deployment

- docs.yml --- Documentation build validation

- generate-artifacts.yml --- Artifact generation

- generate_artifacts.yml --- Legacy artifact generation

- render-and-insert-diagrams.yml --- PlantUML diagram rendering

- adapter-run-scuba.yml --- Manual SCuBA adapter execution

- scuba-nightly.yml --- Nightly SCuBA assessment

- compliance-mapping.yml --- Compliance matrix generation

- canon-validation.yml --- Canon configuration validation

- crosswalk-regeneration.yml --- Control crosswalk updates

- drift-detection.yml --- Configuration drift detection

- drift-scan.yml --- Drift scanning

- dashboard-export.yml --- Dashboard export

- metadata-validator.yml --- Metadata validation

- changelog.yml --- Changelog automation

- repo-hygiene.yml --- Repository hygiene checks

- rename-visuals.yml --- Visual asset renaming

Documentation

- Master Test Plan (MASTER_TEST_PLAN.md)

- SCuBA Architecture Guide (scuba-architecture-guide.md)

- SCuBA Operator Runbook (scuba-operator-runbook.md)

- API Reference (api-reference.md)

- Configuration Reference (configuration-reference.md)

- Adapter Development Guide (adapter-development-guide.md)

- Deployment Guide (deployment-guide.md)

- Compliance Mapping Matrix (compliance-mapping-matrix.md)

Distribution

- pyproject.toml with PEP 621 metadata and entry points

- Multi-stage Dockerfile with non-root runtime user

Security

- HMAC-SHA256 evidence signing

- SHA-256 stable hash for determinism verification

- stable_hash excludes volatile fields (collected_at, run_id, pipeline_version)

- Non-root Docker container execution

- Environment-based secrets management (no secrets in source)

Compliance

- FedRAMP Moderate: 78 automated, 42 supplemental, 205 manual controls

- BOD 25-01: 9 of 11 requirements automated

- OSCAL 1.1.2 compliant artifact generation

Known Issues

  ------------------------------------------------------------------------------------------------------
  **Issue**                                      **Impact**                          **Status**
  ---------------------------------------------- ----------------------------------- -------------------
  Pydantic Policy.scope.boundaries field error   CI test failures                    Fix committed

  \_stable_hash includes volatile fields         Non-deterministic evidence hashes   Fix committed

  Ruff SIM108 ternary warnings                   Lint warnings (non-blocking)        Fixes in progress

  CI passing 7--9 of 15 checks                   Partial CI failures                 Active repair
  ------------------------------------------------------------------------------------------------------

\[1.0.0\] --- 2026-03-01

Initial Release

- Monolithic IR pipeline with 8 sequential stages

- SCuBA adapter for ScubaGear JSON ingestion

- Basic CLI with run, transform, and status commands

- Initial test suite with unit and integration tests

- Single-plane architecture (replaced by 4-plane in v2.0.0)

Document Conventions

  ----------------------------------------------------------
  **Label**        **Meaning**
  ---------------- -----------------------------------------
  **Added**        New features or capabilities

  **Changed**      Modifications to existing functionality

  **Deprecated**   Features scheduled for removal

  **Removed**      Features removed in this release

  **Fixed**        Bug fixes

  **Security**     Security-related changes
  ----------------------------------------------------------

**UIAO-Core SCuBA Documentation Suite** --- 9 Files --- v2.0.0 --- 2026-04-11

Classification: Controlled --- For internal use only
