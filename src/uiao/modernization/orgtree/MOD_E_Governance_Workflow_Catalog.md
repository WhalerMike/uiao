---
document_id: MOD_E
title: "Appendix E — Governance Workflow Catalog"
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

# Appendix E — Governance Workflow Catalog

Purpose

This appendix defines all governance workflows as deterministic, acyclic state machines. Every governance operation that modifies the canonical corpus or tenant configuration must follow one of these workflows. Ad hoc changes are drift by definition.

Scope

Covers all modification workflows for OrgPath codes, dynamic groups, attribute schemas, delegation assignments, drift responses, SLA escalations, and governance artifact updates. All workflows operate within the M365 GCC-Moderate boundary.

Canonical Structure

Each workflow is defined by its trigger event, a set of ordered states, transition conditions, terminal states, SLA bounds, an owner role, and an escalation path.

Technical Scaffolding

Workflow 1: New OrgPath Registration

Trigger: Request to add a new OrgPath code to the codebook (Appendix A).

States: Requested → Validated → Approved → Provisioned → Verified → Canonical

SLA: 5 business days end-to-end. Owner: Governance Steward. Escalation: Governance Board at SLA+2 days.

[Requested]--validate format-->[Validated]--governance review-->[Approved]      |                              |                              |    invalid                        reject                      provision      v                              v                           in tenant [Rejected]                    [Rejected]                          |                                                                   v                                                            [Provisioned]                                                                   |                                                             run tests                                                                   v                                                            [Verified]                                                                   |                                                            merge to repo                                                                   v                                                            [Canonical]

Workflow 2: OrgPath Deprecation

Trigger: Request to deprecate an existing OrgPath code.

States: Requested → Impact Assessed → Users Reassigned → Groups Updated → AUs Updated → Deprecated → Archived

SLA: 10 business days. Owner: Governance Steward. Escalation: Governance Board at SLA+3 days.

[Requested]--assess impact-->[Impact Assessed]--reassign users-->[Users Reassigned]                                                                         |                                                                   update groups                                                                         v                                                                [Groups Updated]                                                                         |                                                                   update AUs                                                                         v                                                                 [AUs Updated]                                                                         |                                                                set status=deprecated                                                                         v                                                                 [Deprecated]                                                                         |                                                                after 90 days                                                                         v                                                                  [Archived]

Workflow 3: Dynamic Group Creation/Modification

Trigger: New group needed or existing group rule change.

States: Drafted → Schema Validated → Boundary Checked → Approved → Deployed → Membership Verified → Canonical

SLA: 3 business days. Owner: Identity Engineer. Escalation: Governance Steward at SLA+1 day.

Workflow 4: Attribute Schema Change Request

Trigger: Request to add, modify, or remove an attribute mapping (Appendix C).

States: Requested → Impact Analyzed → Schema Updated → Validation Rules Updated → Tests Updated → Approved → Deployed → Canonical

SLA: 10 business days. Owner: Governance Steward. Escalation: Governance Board at SLA+3 days.

Workflow 5: Delegation Change (AU/Role Modification)

Trigger: Request to add, modify, or remove an AU or role assignment (Appendix D).

States: Requested → Security Reviewed → Boundary Validated → Approved → Provisioned → Tested → Canonical

SLA: 5 business days. Owner: Security Steward. Escalation: Governance Board at SLA+2 days.

Workflow 6: Drift Detection Response

Trigger: Drift detection engine (Appendix M) raises an alert.

States: Detected → Classified → Assigned → Investigating → Remediating → Verified → Closed

SLA: Varies by severity: Critical=4 hours, High=8 hours, Medium=24 hours, Low=72 hours. Owner: Assigned per drift category. Escalation: Per Appendix Q.

[Detected]--classify-->[Classified]--assign owner-->[Assigned]                                                         |                                                    investigate                                                         v                                                   [Investigating]                                                         |                                                    apply fix                                                         v                                                   [Remediating]                                                         |                                                   run validation                                                         v                                                    [Verified]--pass-->[Closed]                                                         |                                                       fail                                                         v                                                   [Remediating] (loop)

Workflow 7: SLA Breach Escalation

Trigger: SLA timer exceeds threshold for any governance operation.

States: Warning → Breached → Escalated → Emergency → Resolved

SLA: Defined per escalation level (see Appendix Q). Owner: Current operation owner. Escalation: Automatic per ladder.

Workflow 8: Governance Artifact Update (PR-Based)

Trigger: Any change to any canonical document in the Governance OS repository.

States: Branched → Authored → Self-Validated → PR Submitted → CI Validated → Peer Reviewed → Approved → Merged → Post-Merge Validated → Published

SLA: 5 business days for review. Owner: Author (initial), Reviewer (after PR). Escalation: Governance Steward at SLA+2 days.

[Branched]--write changes-->[Authored]--run local tests-->[Self-Validated]                                                                 |                                                            open PR                                                                 v                                                         [PR Submitted]                                                                 |                                                            CI pipeline                                                                 v                                                         [CI Validated]--fail-->[Authored]                                                                 |                                                             pass                                                                 v                                                         [Peer Reviewed]--reject-->[Authored]                                                                 |                                                            approve                                                                 v                                                          [Approved]                                                                 |                                                          squash merge                                                                 v                                                           [Merged]                                                                 |                                                        post-merge CI                                                                 v                                                    [Post-Merge Validated]                                                                 |                                                            publish                                                                 v                                                         [Published]

Boundary Rules

All workflow actions must execute within the M365 GCC-Moderate boundary.

No workflow may invoke external orchestration services (Azure Logic Apps, Azure Functions, etc.).

Automation steps within workflows use Power Automate (GCC) or PowerShell via Graph API only.

Drift Considerations

A change executed outside a defined workflow is drift by definition.

Workflow state must be tracked; if a workflow stalls in a non-terminal state beyond its SLA, the SLA Breach Escalation workflow (Workflow 7) triggers automatically.

Governance Alignment

This catalog implements Principle 3 (Provenance Traceability): every change is attributable because every change must traverse a workflow with recorded states and responsible actors. It also implements Principle 4 (Drift Resistance): by defining the only valid paths for change, any change outside these paths is detectable drift.
