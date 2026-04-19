---
document_id: MOD_A
title: "Appendix A — OrgPath Codebook"
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

# Appendix A — OrgPath Codebook

Purpose

This appendix defines the complete enumeration of OrgPath codes used to encode organizational hierarchy in Entra ID extension attributes. Every valid OrgPath in the system must exist in this codebook. An OrgPath that does not appear here is, by definition, invalid and will be flagged as drift.

Scope

Covers all hierarchical levels (0 through 4) of the OrgTree. Applies to every user object, every dynamic group membership rule, and every Administrative Unit scope within the M365 GCC-Moderate boundary. The codebook is the single source of truth for organizational structure encoding.

Canonical Structure

The OrgPath hierarchy has five levels:

Level 0 — Enterprise Root: The single root node representing the entire organization. Code: ORG.

Level 1 — Agency/Division: Top-level organizational divisions. Pattern: ORG-[A-Z]{2,6}. Examples: ORG-FIN, ORG-HR, ORG-IT, ORG-OPS, ORG-LEG.

Level 2 — Department: Departments within divisions. Pattern: ORG-[A-Z]{2,6}-[A-Z]{2,6}. Examples: ORG-FIN-AP, ORG-IT-SEC.

Level 3 — Unit: Units within departments. Pattern adds a third segment. Examples: ORG-FIN-AP-EAST, ORG-IT-SEC-SOC.

Level 4 — Team: Teams within units. Pattern adds a fourth segment. Examples: ORG-IT-SEC-SOC-T1.

Regex Validation Pattern: ^ORG(-[A-Z]{2,6}){0,4}$

Technical Scaffolding

Boundary Rules

All OrgPath codes must match the regex ^ORG(-[A-Z]{2,6}){0,4}$.

Maximum hierarchy depth is 4 segments below root (Level 4).

Each segment must be between 2 and 6 uppercase ASCII letters.

OrgPath values are stored in extensionAttribute1 within Entra ID, which is within the M365 GCC-Moderate boundary.

No OrgPath may reference external systems or identifiers outside the M365 SaaS perimeter.

Drift Considerations

Value Drift: A user's extensionAttribute1 contains a value not present in this codebook. Severity: High. Auto-remediate: No (requires investigation).

Format Drift: A user's OrgPath does not match the regex pattern. Severity: Critical. Auto-remediate: No (requires manual correction).

Orphan Drift: An OrgPath code exists in the codebook but its parent path does not. Severity: Critical. Auto-remediate: No.

Phantom Drift: An OrgPath exists in user attributes but has been deprecated in the codebook. Severity: Medium. Auto-remediate: Yes (flag for reassignment).

Governance Alignment

This codebook implements Principle 2 (Schema Fixity): the codebook structure is fixed; only values (specific OrgPath entries) change through the OrgPath Registration workflow (Appendix E, Workflow 1). Every addition, deprecation, or modification to this codebook requires a governed PR through the contributor workflow (Appendix V), passing all validation gates (Appendix J, Schema Tests), and receiving approval from the Governance Board.
