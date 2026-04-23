---
document_id: UIAO_007
title: "OrgTree Modernization — Active Directory to Entra ID Migration Guide"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-18"
updated_at: "2026-04-18"
boundary: GCC-Moderate
provenance:
  source: "inbox/EntraID Governance/AD to EntraID Tree.docx"
  version: "1.0"
  derived_at: "2026-04-18"
  derived_by: "Copilot Tasks docx extraction; source document truncated during extraction, Section 4 (Delegation) tail is partial, core content complete. Promoted to canon in ADR-044 shadow-canon cleanup on 2026-04-23"
---

# OrgTree Modernization — Active Directory to Entra ID Migration Guide

## Overview

Active Directory uses an X.500 container model (OUs) to represent organizational hierarchy. Entra ID uses a flat structure. This guide describes how to replicate an organizational tree in Entra ID using attributes, dynamic groups, and Administrative Units — replacing the container-based model with an attribute-driven model.

**Core mental shift:** Stop thinking "tree of containers" and start thinking "tree of attributes + groups + delegation."

## 1. Core Pattern: Org Tree Becomes Attributes + Dynamic Groups

In Entra ID, the organizational tree lives in two constructs:

### User Attributes (HR-Driven)

**Built-in attributes:**

- `manager`
- `department`
- `companyName`
- `jobTitle`
- `officeLocation`

**Custom / extension attributes:**

- Cost center
- Org unit code
- Region
- Line of business

### Dynamic Groups

Dynamic groups replace OUs as the scoping mechanism:

```
user.department -eq "Finance"
user.extensionAttribute1 -eq "OU=MD,OU=East,DC=contoso,DC=com"
```

These groups become "virtual OUs" for:

- App assignment
- Conditional Access scoping
- License assignment
- Access packages / governance

**Mental model:** An AD OU is equivalent to "users whose attributes match rule X" — represented as a dynamic group.

## 2. Representing Hierarchy: Mimicking a Tree

Hierarchy is encoded into attributes, then layered with groups.

### 2.1 Encode the Org Path

Select a canonical attribute (or extension attribute) to hold the organizational path:

```
OrgPath = "CORP/US/EAST/BALTIMORE/IT"
```

Or in X.500-style notation:

```
OrgDnCode = "OU=IT,OU=Baltimore,OU=East,OU=US,DC=corp,DC=contoso,DC=com"
```

This encoding enables two query patterns:

**Exact node match:**

```
user.extensionAttribute1 -eq "CORP/US/EAST/BALTIMORE/IT"
```

**Branch / subtree match:**

```
user.extensionAttribute1 -startsWith "CORP/US/EAST"
```

### 2.2 Example Dynamic Group Definitions

| Group Name | Rule | Scope |
|------------|------|-------|
| `US-East-All` | `user.extensionAttribute1 -startsWith "CORP/US/EAST"` | All users in US-East subtree |
| `Baltimore-IT` | `user.extensionAttribute1 -eq "CORP/US/EAST/BALTIMORE/IT"` | Exact node: Baltimore IT only |

This is the organizational tree — expressed as string hierarchy + group rules.

## 3. Manager-Based Org Tree for HR Workflows

For HR-style management (approvals, access reviews, joiner/mover/leaver), the `manager` attribute serves as the organizational chart spine.

### HR Provisioning Flow

```
HR System → Entra ID (via HR connector / provisioning) → populates:
  - manager
  - department
  - jobTitle
  - OrgPath / OrgDnCode
```

### Entra ID Governance Integration

- **Manager as approver** for access packages
- **Manager-based access reviews** — periodic re-certification
- **Manager-scoped reports** — who reports to whom

This produces a true HR org tree, independent of any OU structure.

## 4. Delegation: Replacing OU-Scoped Admin

In Active Directory, administrative delegation is scoped to OUs. In Entra ID, the equivalent is achieved through Administrative Units (AUs) combined with scoped role assignments.

### Administrative Units

AUs scope helpdesk and admin roles to a subset of users:

| AU Name | Membership Rule | Equivalent AD Scope |
|---------|----------------|-------------------|
| `US-East AU` | `OrgPath -startsWith "CORP/US/EAST"` | East region OU subtree |
| `Baltimore AU` | `OrgPath -eq "CORP/US/EAST/BALTIMORE"` | Baltimore OU |

Membership can be:

- **Static** — manually assigned
- **Dynamic** — using the same org attributes (e.g., `OrgPath -startsWith "CORP/US/EAST"`)

### Entra ID Roles + AU Scope

"User Administrator" scoped to "Baltimore AU" is equivalent to delegated admin on the Baltimore OU in Active Directory.

**Mapping:** OU for delegation → AU + dynamic membership rules + scoped Entra ID role.

## Summary: AD to Entra ID Translation Table

| AD Concept | Entra ID Equivalent |
|------------|-------------------|
| Organizational Unit (OU) | Dynamic group with attribute-matching rule |
| OU hierarchy / tree | `OrgPath` string attribute with `-startsWith` queries |
| OU-scoped delegation | Administrative Unit + scoped Entra ID role |
| Group Policy scoping | Conditional Access policy + dynamic group targeting |
| Manager chain | `manager` attribute populated by HR connector |
| Org chart | Manager-based reporting + `OrgPath` hierarchy |
