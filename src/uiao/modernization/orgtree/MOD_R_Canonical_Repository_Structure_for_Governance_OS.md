---
document_id: MOD_R
title: "Appendix R — Canonical Repository Structure for Governance OS"
version: "1.0"
status: DRAFT
classification: CANONICAL
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
namespace: MOD
parent_canon: UIAO_008
---

# Appendix R — Canonical Repository Structure for Governance OS

Purpose

This appendix defines the canonical directory structure for the Governance OS repository, including file descriptions, CODEOWNERS rules, and CI/CD workflow definitions.

Scope

Covers the complete repository layout including documentation, schemas, PowerShell modules, tests, telemetry configurations, and CI workflows. All repository contents govern M365 GCC-Moderate operations.

Canonical Structure

uiao-governance-os/ |-- README.md                          # Repository overview and quick-start guide |-- GOVERNANCE.md                      # Governance principles and contribution rules |-- .github/ |   |-- CODEOWNERS                     # Maps directories to governance role reviewers |   |-- workflows/ |       |-- validate-schema.yml        # CI: Validates JSON schemas on every PR |       |-- validate-powershell.yml    # CI: Lints PowerShell modules on every PR |       |-- drift-check.yml           # Scheduled: Runs drift detection daily |-- docs/ |   |-- master-document.md            # Part 1: Master document (Sections 1-7) |   |-- appendices/ |       |-- A-orgpath-codebook.md      # Appendix A |       |-- B-dynamic-group-library.md # Appendix B |       |-- C-attribute-mapping.md     # Appendix C |       |-- D-delegation-matrix.md     # Appendix D |       |-- E-governance-workflows.md  # Appendix E |       |-- F-migration-runbook.md     # Appendix F |       |-- G-diagram-pack.md         # Appendix G |       |-- H-json-schemas.md         # Appendix H |       |-- I-powershell-module.md    # Appendix I |       |-- J-test-suite.md           # Appendix J |       |-- K-decision-trees.md       # Appendix K |       |-- L-sla-model.md            # Appendix L |       |-- M-drift-engine.md         # Appendix M |       |-- N-execution-substrate-integration.md # Appendix N |       |-- O-mock-tenant.md          # Appendix O |       |-- P-boundary-impact.md      # Appendix P |       |-- Q-escalation-playbooks.md # Appendix Q |       |-- R-repo-structure.md       # Appendix R (this document) |       |-- S-state-machine.md        # Appendix S |       |-- T-risk-scoring.md         # Appendix T |       |-- U-boundary-model.md       # Appendix U |       |-- V-contributor-workflow.md  # Appendix V |       |-- W-error-taxonomy.md       # Appendix W |       |-- X-telemetry-model.md      # Appendix X |       |-- Y-normalization-model.md  # Appendix Y |       |-- Z-glossary.md             # Appendix Z |-- schemas/ |   |-- orgpath-entry.schema.json     # OrgPathEntry JSON Schema |   |-- orgpath-codebook.schema.json  # OrgPathCodebook JSON Schema |   |-- dynamic-group.schema.json     # DynamicGroupDefinition JSON Schema |   |-- attribute-mapping.schema.json # AttributeMapping JSON Schema |   |-- instruction-set.schema.json   # InstructionSet JSON Schema |   |-- drift-report.schema.json      # DriftReport JSON Schema |-- modules/ |   |-- OrgTreeValidation/ |       |-- OrgTreeValidation.psd1    # Module manifest |       |-- OrgTreeValidation.psm1    # Module script (6 functions) |       |-- Tests/ |           |-- OrgTreeValidation.Tests.ps1 # Pester tests for module |-- tests/ |   |-- governance-enforcement/       # Test definitions from Appendix J |   |-- mock-tenant/                  # Mock tenant harness from Appendix O |-- telemetry/ |   |-- schemas/                      # Telemetry event schemas |   |-- dashboards/                   # Dashboard specifications |-- diagrams/                         # ASCII diagram source files

CODEOWNERS Rules

# Governance OS CODEOWNERS # Each line maps a path pattern to required reviewers (by governance role)  # Master document and governance rules /GOVERNANCE.md                   @governance-board /docs/master-document.md         @governance-board  # Appendices (grouped by governance domain) /docs/appendices/A-*             @governance-steward @identity-engineer /docs/appendices/B-*             @identity-engineer /docs/appendices/C-*             @identity-engineer @governance-steward /docs/appendices/D-*             @security-steward /docs/appendices/E-*             @governance-steward /docs/appendices/F-*             @identity-engineer @governance-steward /docs/appendices/G-*             @governance-steward /docs/appendices/H-*             @governance-steward @identity-engineer /docs/appendices/I-*             @identity-engineer /docs/appendices/J-*             @governance-steward @identity-engineer /docs/appendices/K-*             @governance-steward /docs/appendices/L-*             @governance-steward /docs/appendices/M-*             @identity-engineer @security-steward /docs/appendices/N-*             @governance-steward @identity-engineer /docs/appendices/O-*             @identity-engineer /docs/appendices/P-*             @governance-board /docs/appendices/Q-*             @governance-steward /docs/appendices/R-*             @governance-board /docs/appendices/S-*             @governance-board /docs/appendices/T-*             @security-steward /docs/appendices/U-*             @security-steward @governance-board /docs/appendices/V-*             @governance-steward /docs/appendices/W-*             @governance-steward /docs/appendices/X-*             @governance-steward @identity-engineer /docs/appendices/Y-*             @identity-engineer /docs/appendices/Z-*             @governance-steward  # Schemas require governance board approval /schemas/                        @governance-board @identity-engineer  # PowerShell modules /modules/                        @identity-engineer  # Tests /tests/                          @identity-engineer @governance-steward  # CI/CD /.github/                        @governance-board

Boundary Rules

The repository itself may be hosted on any platform; the governance artifacts within it govern M365 GCC-Moderate operations exclusively.

CI workflows that interact with live tenants must use M365 GCC-Moderate API endpoints.

Drift Considerations

Files in the repository that do not conform to this directory structure constitute structural drift.

CODEOWNERS must be updated whenever governance roles change.

Governance Alignment

This structure implements Principle 3 (Provenance Traceability) through CODEOWNERS-enforced review, and Principle 2 (Schema Fixity) through a fixed directory layout that accommodates content changes without structural changes.
