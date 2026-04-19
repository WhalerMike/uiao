---
document_id: MOD_D
title: "Appendix D — Delegation Matrix (AUs + Roles)"
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

# Appendix D — Delegation Matrix (AUs + Roles)

Purpose

This appendix defines the complete delegation model using Entra ID Administrative Units (AUs) and role assignments. It specifies which administrators can manage which identity objects, within which scopes, and with which permissions.

Scope

Covers all Administrative Units, their membership rules, and all scoped role assignments within the M365 GCC-Moderate boundary. Applies to every administrative action on identity objects governed by the OrgTree.

Canonical Structure

Delegation follows a three-tier model: (1) Administrative Units define the scope of management; (2) Entra ID built-in roles define the set of permissions; (3) Role assignments bind a role to an AU, granting scoped permissions to designated administrator groups.

Technical Scaffolding

Administrative Unit Registry

Role Assignment Matrix

Delegation Decision Tree

[Administrative Action Required]          |          v Is the action scoped to a single division?     |                          |    YES                        NO     |                          |     v                          v Identify OrgPath        Is actor a Governance of target user(s)       Steward?     |                      |          |     v                     YES         NO Map OrgPath to AU          |          | (Level 1 = division AU)    v          v     |                  Use AU-ORG-    DENY:     v                  Enterprise     Insufficient Does actor hold            |          scope required role in           v that AU?               Execute with     |         |        enterprise    YES        NO       scope     |         |     v         v Execute    Is there a within     department-level AU scope   AU (Level 2)?                |         |               YES        NO                |         |                v         v            Check role    DENY:            in dept AU    No valid                |         delegation               YES--> Execute within dept AU scope

Boundary Rules

All AUs and role assignments must be created and managed within Entra ID in the M365 GCC-Moderate boundary.

No AU membership rule may reference external directory attributes or services outside M365.

Restricted management AUs prevent unscoped Global Administrators from managing members without explicit AU-scoped assignment.

Role assignments must use Entra ID built-in roles only; custom role definitions require governance approval through Appendix E, Workflow 5.

Drift Considerations

AU Membership Drift: An AU's membership rule in the tenant does not match the canonical rule. Severity: High. Auto-remediate: Yes.

Role Assignment Drift: A role assignment exists that is not in this matrix. Severity: Critical. Auto-remediate: No (requires investigation).

Orphaned AU: An AU exists with no role assignments. Severity: Low. Auto-remediate: No (flag for review).

Governance Alignment

This matrix implements Principle 1 (Deterministic State) for administration: every administrative action has exactly one authorized path. It also enforces Principle 5 (Boundary Enforcement): no delegation extends beyond M365 GCC-Moderate. Changes follow Workflow 5 (Delegation Change) in Appendix E.
