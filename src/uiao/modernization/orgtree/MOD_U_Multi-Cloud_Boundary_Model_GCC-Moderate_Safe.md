---
document_id: MOD_U
title: "Appendix U — Multi-Cloud Boundary Model (GCC-Moderate Safe)"
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

# Appendix U — Multi-Cloud Boundary Model (GCC-Moderate Safe)

Purpose

This appendix defines the authoritative service classification for M365 GCC-Moderate, explicitly enumerating which services are in scope and which are excluded, with boundary enforcement rules.

Scope

Covers all M365 services potentially relevant to identity governance, with clear in/out classifications. Applies to every artifact, script, and configuration in the Governance OS.

Canonical Structure

Services are classified as In-Scope (available and authorized for Governance OS use) or Excluded (not available or not authorized). Boundary enforcement rules provide machine-evaluable compliance checks.

Technical Scaffolding

Service Classification Table

Excluded Services Table

Boundary Enforcement Rules

Cross-Cloud Interaction Rules

External systems cannot directly interact with the Governance OS. If an external system needs to trigger a governance operation or consume governance data, the following rules apply:

The external system must submit a request through an approved M365 channel (e.g., a SharePoint form, a Teams message, or an email to a governance mailbox).

The request is reviewed by a governance steward before any action is taken.

No automated API integration between external systems and the Governance OS is permitted without Governance Board approval.

Data exported from the Governance OS for external consumption must be sanitized to remove tenant-specific values and classified appropriately.

Boundary Rules

This appendix is itself the authoritative boundary definition. All other appendices reference this table for service classification.

Adding a service to the In-Scope list requires a boundary impact assessment (Appendix P) and Governance Board approval.

Drift Considerations

Any governance artifact that references an excluded service constitutes boundary drift. Detection rule DDE-015 (Appendix M) monitors for this.

Service availability changes by Microsoft must be reflected in this table through Workflow 8.

Governance Alignment

This appendix is the definitive implementation of Principle 5 (Boundary Enforcement). Every boundary check in every decision tree, validation function, and CI pipeline ultimately references this classification table.
