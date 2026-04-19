---
document_id: MOD_B
title: "Appendix B — Dynamic Group Library"
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

# Appendix B — Dynamic Group Library

Purpose

This appendix defines all dynamic group definitions that implement the OrgTree structure in Entra ID using membership rules. Every OrgPath-scoped group in the tenant must conform to a definition in this library. Groups not listed here are non-canonical.

Scope

Covers all dynamic security groups and Microsoft 365 groups whose membership is derived from OrgPath values stored in extensionAttribute1. Applies to all group-based access control, delegation, licensing, and policy targeting within the M365 GCC-Moderate boundary.

Canonical Structure

Each dynamic group has a deterministic membership rule that evaluates user.extensionAttribute1 against codebook-defined OrgPath values. Groups follow a naming convention: OrgTree-[Scope]-[Purpose], where Scope is the OrgPath prefix and Purpose describes the group function.

Technical Scaffolding

Boundary Rules

All membership rules must reference only Entra ID user attributes available within M365 GCC-Moderate.

Dynamic membership rules must not reference external data sources, Azure services, or cross-tenant attributes.

Group names must follow the OrgTree-[Scope]-[Purpose] naming convention.

No group may have manually assigned members if its definition appears in this library (dynamic membership only).

Drift Considerations

Rule Drift: A dynamic group's membership rule in the tenant does not match the canonical rule in this library. Severity: High. Auto-remediate: Yes (overwrite rule from canonical source).

Phantom Group: A group exists in the tenant with OrgTree- prefix but has no entry in this library. Severity: Medium. Auto-remediate: No (investigate, then delete or canonize).

Membership Drift: Group membership does not reflect expected user set due to stale attribute values. Root cause is in Appendix A (OrgPath values), not group rules.

Governance Alignment

This library implements Principle 1 (Deterministic State): every group's membership is fully determined by its rule and the current state of user attributes. No discretionary membership exists. Changes to this library follow Workflow 3 (Dynamic Group Creation/Modification) in Appendix E and require validation per Appendix J Group Tests.
