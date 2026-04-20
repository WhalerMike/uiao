---
document_id: DM_080
title: "DFS Adapter Interface"
version: "0.1-draft"
status: DRAFT
owner: "Michael Stratton"
created_at: "2026-04-19"
updated_at: "2026-04-19"
boundary: GCC-Moderate
core_concepts: ["#8 User experience first"]
priority: MEDIUM
risk: "Silent UNC path failure post AD retirement"
---

# DFS Adapter Interface

**Priority:** MEDIUM | **Risk:** Silent UNC path failure post AD retirement

## Required Capabilities

- Inventory all DFS namespaces (domain-based and standalone)
- Inventory all DFS replication groups and members
- Map namespace access to user OrgPath (who uses which namespaces)
- Migration path: SharePoint Online, Azure Files, or standalone DFS
- Validate namespace resolution before and after transition
