---
document_id: MOD_V
title: "Appendix V — Canonical Contributor Workflow (PR to Validation to Merge)"
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

# Appendix V — Canonical Contributor Workflow (PR to Validation to Merge)

Purpose

This appendix defines the deterministic workflow for contributing changes to the Governance OS repository. Every modification to any canonical artifact must follow this workflow without exception.

Scope

Covers the ten-step contribution process from branch creation through post-merge publication. Applies to all contributors regardless of role.

Canonical Structure

The workflow is a linear, gated process with automated and manual validation checkpoints. Each step has defined inputs, outputs, and pass/fail criteria.

Technical Scaffolding

Workflow Steps

Fork/Branch: Create a branch with naming convention governance/[type]/[short-description] where type is one of: codebook, schema, module, runbook, workflow, model, glossary, docs.

Author Change: Make modifications following the canonical schemas and style guidelines. All JSON must validate. All PowerShell must lint clean.

Self-Validate: Run local validation before submitting: Invoke-Pester for PowerShell, JSON schema validation for data files, and manual review against the relevant appendix requirements.

Submit PR: Open a pull request using the PR template (see below). All fields must be completed.

Automated Validation (CI): CI pipeline runs: JSON schema validation (validate-schema.yml), PowerShell lint (validate-powershell.yml), boundary compliance check (scan for excluded service references).

Governance Review: CODEOWNERS-designated reviewers are assigned automatically. Reviewers validate: technical correctness, governance principle compliance, boundary adherence, and impact assessment completeness.

Approval: Minimum 2 approvals required for canonical artifacts. Schema changes require Governance Board approval. No open objections may remain.

Merge: Squash merge to main branch. Commit message must include PR number and change summary.

Post-Merge Validation: CI re-runs all validation against the merged main branch. If validation fails, merge is automatically reverted.

Publication: Upon successful post-merge validation, the artifact status transitions to Canonical in the state machine (Appendix S).

PR Template

## Change Summary [Brief description of what changed and why]  ## Change Type - [ ] Codebook Update (Appendix A) - [ ] Schema Change (Appendix H) - [ ] Module Update (Appendix I) - [ ] Workflow Modification (Appendix E) - [ ] Documentation Update - [ ] New Artifact - [ ] Other: _______________  ## Affected Appendices [List all appendices affected by this change]  ## Boundary Impact - [ ] No boundary impact - [ ] Boundary impact assessed (attach assessment)  ## Drift Risk Assessment [Describe any new drift vectors this change introduces]  ## Rollback Plan [Steps to reverse this change if post-merge validation fails]  ## Validation Checklist - [ ] JSON schemas validate against JSON Schema 2020-12 - [ ] PowerShell passes PSScriptAnalyzer with zero warnings - [ ] No references to excluded services (Appendix U) - [ ] All OrgPath codes match regex ^ORG(-[A-Z]{2,6}){0,4}$ - [ ] No tenant-specific values, GUIDs, or PII - [ ] Error codes follow GOV-[CAT]-[NUM] format (Appendix W)

Validation Gates

Workflow Diagram

[1. Branch]-->[2. Author]-->[3. Self-Validate]-->[4. Submit PR]                                                        |                                                   [5. CI Validation]                                                     |           |                                                   PASS         FAIL-->[2. Author]                                                     |                                               [6. Governance Review]                                                     |           |                                                  APPROVE      REJECT-->[2. Author]                                                     |                                               [7. Approval (2+)]                                                     |                                               [8. Squash Merge]                                                     |                                             [9. Post-Merge CI]                                                     |           |                                                   PASS         FAIL-->REVERT                                                     |                                              [10. Published]

Boundary Rules

The CI pipeline itself runs within the repository platform; it does not interact with live M365 tenants during PR validation.

Boundary scan specifically checks for references to services listed in the Excluded Services table (Appendix U).

Drift Considerations

A change merged outside this workflow (e.g., direct push to main) constitutes governance process drift. Severity: Critical.

Branch protection rules must enforce this workflow. Disabling branch protection is a governance violation.

Governance Alignment

This workflow implements Principle 3 (Provenance Traceability) by ensuring every change has a PR with documented rationale, and Principle 2 (Schema Fixity) by validating all changes against canonical schemas before merge.
