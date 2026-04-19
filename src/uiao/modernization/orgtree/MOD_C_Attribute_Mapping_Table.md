---
document_id: MOD_C
title: "Appendix C — Attribute Mapping Table"
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

# Appendix C — Attribute Mapping Table

Purpose

This appendix defines the complete mapping between legacy Active Directory attributes and Entra ID attributes used in the OrgTree model. Every identity attribute that participates in the OrgTree governance model is mapped, typed, validated, and documented here.

Scope

Covers all user object attributes referenced by dynamic group rules (Appendix B), delegation models (Appendix D), validation modules (Appendix I), and drift detection rules (Appendix M). Applies to all identity objects within the M365 GCC-Moderate boundary.

Canonical Structure

Each mapping defines a one-to-one correspondence between a legacy AD attribute and its Entra ID counterpart, including data type constraints, validation rules, and the specific OrgTree function the attribute serves.

Technical Scaffolding

Boundary Rules

All attributes must be readable and writable (where applicable) through Microsoft Graph API within M365 GCC-Moderate.

Extension attributes (1-5) are used exclusively for OrgTree governance data; no other system may write to these attributes without governance authorization.

No attribute mapping may reference external directory services, LDAP endpoints, or non-M365 identity providers.

Drift Considerations

Value Drift: An attribute value does not conform to its validation rule (e.g., department does not match OrgPath Level 1 mapping). Severity: High.

Missing Required Attribute: A required attribute is null or empty. Severity: Critical.

Format Drift: An attribute value is present but does not match expected format (e.g., employeeId with lowercase characters). Severity: Medium.

Governance Alignment

This mapping implements Principle 2 (Schema Fixity): the set of mapped attributes and their types are fixed. Validation rules are enforced by the PowerShell module (Appendix I) and tested by the enforcement test suite (Appendix J). Any change to this mapping requires Workflow 4 (Attribute Schema Change Request) in Appendix E.
