---
document_id: MOD_K
title: "Appendix K — Enforcement Decision Trees"
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

# Appendix K — Enforcement Decision Trees

Purpose

This appendix defines deterministic decision trees for all governance enforcement scenarios. Each tree provides an unambiguous path from an input condition to a terminal decision, eliminating interpretive discretion.

Scope

Covers five decision trees: OrgPath Validation, Drift Classification, Escalation, Migration Readiness, and Boundary Compliance. All decisions apply within the M365 GCC-Moderate boundary.

Canonical Structure

Each decision tree has labeled decision nodes (questions), branch conditions (yes/no or enumerated values), and terminal nodes (ACCEPT, REJECT, COMPLIANT, NON-COMPLIANT, or specific action codes).

Technical Scaffolding

Decision Tree 1: OrgPath Validation

[INPUT: OrgPath string]          |          v [Q1] Does format match ^ORG(-[A-Z]{2,6}){0,8}$ ?     |                    |    YES                   NO --> REJECT: GOV-SCH-001 (Invalid format)     |     v [Q2] Does parent path exist in codebook?     |                    |    YES                   NO --> REJECT: GOV-HIR-001 (Orphan path)     |     v [Q3] Is hierarchy depth within maxDepth of parent?     |                    |    YES                   NO --> REJECT: GOV-HIR-002 (Depth exceeded)     |     v [Q4] Is OrgPath status = "active" in codebook?     |                    |    YES                   NO --> REJECT: GOV-SCH-002 (Deprecated/pending)     |     v ACCEPT: OrgPath is valid.

Decision Tree 2: Drift Classification

[INPUT: Detected change on identity object]          |          v [Q1] Is the attribute that changed part of the OrgTree schema (Appendix C)?     |                    |    YES                   NO --> CLASSIFY: Out-of-Scope (not OrgTree drift)     |     v [Q2] Was the change executed through a governed workflow (Appendix E)?     |                    |    YES                   NO --> Go to Q3     |     v CLASSIFY: Authorized Change (no action required)  [Q3] Does the new value conform to the attribute's validation rule?     |                    |    YES                   NO --> CLASSIFY: Schema Violation     |                              Severity: Critical     v                              Auto-remediate: No [Q4] Does the new value exist in the codebook/enumeration?     |                    |    YES                   NO --> CLASSIFY: Value Drift     |                              Severity: High     v                              Auto-remediate: No [Q5] Is the parent-child relationship still valid?     |                    |    YES                   NO --> CLASSIFY: Hierarchy Drift     |                              Severity: Critical     v                              Auto-remediate: No CLASSIFY: Unauthorized Drift     Severity: High     Auto-remediate: No     Action: Assign to owner for investigation

Decision Tree 3: Escalation

[INPUT: Governance operation with SLA timer]          |          v [Q1] What is the severity of the operation?     |              |           |          |   CRITICAL       HIGH       MEDIUM      LOW     |              |           |          |     v              v           v          v   SLA=4hr       SLA=8hr    SLA=24hr   SLA=72hr     |     v [Q2] Has 75% of SLA elapsed?     |                    |    YES                   NO --> NORMAL: Owner continues working     |     v ESCALATE Level 1: Notify owner (warning)  [Q3] Has 100% of SLA elapsed?     |                    |    YES                   NO --> MONITOR: Level 1 active     |     v ESCALATE Level 2: Notify manager, escalate ticket  [Q4] Has 150% of SLA elapsed?     |                    |    YES                   NO --> MONITOR: Level 2 active     |     v ESCALATE Level 3: Governance Board review, assign backup  [Q5] Has 200% of SLA elapsed OR severity = CRITICAL?     |                    |    YES                   NO --> MONITOR: Level 3 active     |     v ESCALATE Level 4: EMERGENCY     Executive notification     Mandatory remediation within 4 hours

Decision Tree 4: Migration Readiness

[INPUT: Request to begin migration phase N]          |          v [Q1] Has Phase N-1 validation criteria been met?     |                    |    YES                   NO --> HOLD: Blocker MIG-BLK-001 (prerequisite unmet)     |     v [Q2] Are all required roles assigned to migration team?     |                    |    YES                   NO --> HOLD: Blocker MIG-BLK-002 (missing roles)     |     v [Q3] Is the rollback procedure documented and tested?     |                    |    YES                   NO --> HOLD: Blocker MIG-BLK-003 (no rollback)     |     v [Q4] Has the governance steward signed off on phase plan?     |                    |    YES                   NO --> HOLD: Blocker MIG-BLK-004 (no approval)     |     v PROCEED: Begin Phase N execution.

Decision Tree 5: Boundary Compliance

[INPUT: Governance artifact or instruction set]          |          v [Q1] Does the artifact reference any external service by name or endpoint?     |                    |    YES                   NO --> COMPLIANT: No boundary references     |     v [Q2] Is the referenced service in the M365 GCC-Moderate service list (Appendix U)?     |                    |    YES                   NO --> NON-COMPLIANT: GOV-BND-001     |                              Violation: Out-of-scope service     v                              Action: Reject artifact [Q3] Does the artifact use the GCC-Moderate API endpoint for that service?     |                    |    YES                   NO --> NON-COMPLIANT: GOV-BND-002     |                              Violation: Wrong endpoint     v COMPLIANT: All service references are within boundary.

Boundary Rules

Decision Tree 5 is itself the boundary compliance enforcement mechanism.

All decision outcomes reference error codes from the Error Taxonomy (Appendix W).

Drift Considerations

If a decision tree is not followed for a governance action, the action itself constitutes procedural drift.

Decision trees are governance artifacts; changes require Workflow 8.

Governance Alignment

These trees implement Principle 1 (Deterministic State): every enforcement decision has exactly one outcome for any given input. They eliminate interpretive ambiguity from governance operations.
