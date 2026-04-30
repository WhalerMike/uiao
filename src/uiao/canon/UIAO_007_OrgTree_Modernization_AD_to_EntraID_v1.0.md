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

## OrgPath Discovery Feeders — Ingestion Contract

> **Added 2026-04-30 per [ADR-049](adr/adr-049-microsoft-adapter-coverage-expansion.md) §Decision 3.** This section defines, for each OrgPath input stream, the authoritative adapter id that owns ingestion. Replaces the earlier informal "discovery feeders" framing in inbox-scratch material with an adapter-anchored contract that the substrate walker can verify.

OrgPath as a cross-plane dependency graph (per [UIAO_009](UIAO_009_Microsoft_Coverage_And_Gap_Doctrine_v1.0.md) §3.1) ingests evidence from multiple sources. Each source is owned by exactly one adapter declaration (per [`adapter-registry.yaml`](adapter-registry.yaml) or [`modernization-registry.yaml`](modernization-registry.yaml)). The substrate walker uses this mapping to detect undeclared dependencies as `DRIFT-PROVENANCE` findings.

### Input streams and authoritative owners

| OrgPath input stream | What it contributes | Authoritative adapter | Class | Source registry |
|---|---|---|---|---|
| Entra sign-in logs | Identity → app access edges; user → tenant edges | `entra-id` | modernization | modernization-registry |
| Entra audit logs | Configuration-change provenance for identity-plane edges | `entra-id` | modernization | modernization-registry |
| AD DS security events (LDAP binds, Kerberos tickets, NTLM auth) | Legacy auth-protocol edges (app → DC; service → server) | `active-directory` | modernization | modernization-registry |
| AD DS object inventory (users, groups, OUs, GPOs, SPNs, trusts) | Pre-modernization OrgPath baseline; identity-side topology | `active-directory` | modernization | modernization-registry |
| Intune device inventory | Device → user edges; device cohort membership | `intune` (modernization side) | modernization | modernization-registry |
| Intune compliance state | Device-plane compliance signals (input to drift, not OrgPath edges) | `intune` (conformance side) | conformance | adapter-registry |
| Defender for Endpoint device exposure / vuln inventory | Device → app edges (apps installed on device); device-risk weighting | `defender-for-endpoint` | conformance | adapter-registry |
| Defender for Cloud Apps OAuth inventory | App → identity edges (which user authorized which OAuth app) | `defender-for-cloud-apps` | conformance | adapter-registry |
| Defender for Cloud Apps Shadow IT discovery | App → app edges (shadow apps consuming sanctioned-app data) | `defender-for-cloud-apps` | conformance | adapter-registry |
| Defender for Servers EDR / posture | Server → vulnerability edges; server-risk weighting | `defender-for-servers` | conformance | adapter-registry |
| Azure Migrate dependency map | Server → server edges (port + protocol + service-call graph). **Primary native feed for cross-server dependencies — Gap #4 per UIAO_009 §3.4.** | `azure-migrate` | conformance | adapter-registry |
| Arc-enabled server inventory | Server → cloud edges; OrgPath ARM tag membership | `entra-device-orgpath` (MOD_C) | modernization | modernization-registry |
| Azure Policy for Arc compliance state | Server-plane policy compliance edges | `azure-policy-arc` | modernization | modernization-registry |
| M365 audit logs (Exchange, SharePoint, Teams, Purview, Defender for O365) | App-plane access and configuration-change edges | `m365` | modernization | modernization-registry |
| ScubaGear assessment findings | M365 baseline conformance signals (input to drift) | `scubagear` | conformance | adapter-registry |
| Entra ID Governance signals (Access Reviews, Entitlement Mgmt, LCW, PIM) | Identity-plane lifecycle edges; access decisions | `entra-id-governance` | modernization | modernization-registry |
| Entra Workload Identity inventory | Service-account → workload identity edges; credential-rotation evidence | `entra-workload-identity` | modernization | modernization-registry |

### What the contract requires

For each input stream:

1. **Exactly one** authoritative adapter id is named. If a Microsoft surface produces multiple stream types, the same adapter declares all of them via its `scope` field; if two adapters could plausibly own the same stream, the table above is the tiebreaker.
2. The adapter id MUST resolve to an entry in either `adapter-registry.yaml` or `modernization-registry.yaml`.
3. The adapter's `outputs` field MUST include the stream's evidence filename(s).
4. The adapter's `evidence-class` (interval / baseline / incident) MUST be appropriate to the stream's nature (continuous telemetry vs. point-in-time snapshot vs. ticket-driven event).
5. Drift findings derived from the stream MUST classify into one of the five canonical drift classes (per [ADR-040](adr/adr-040-drift-engine.md): SCHEMA, SEMANTIC, PROVENANCE, AUTHZ, IDENTITY).

### Substrate walker enforcement

The substrate walker (`uiao substrate walk` and `uiao substrate drift`) reads the OrgPath input set during execution and verifies that every active stream traces to a declared adapter id. An undeclared stream produces a `DRIFT-PROVENANCE` finding.

This is the mechanism that prevents silent expansion of the OrgPath ingestion footprint — every new stream is forced through canon declaration before it can contribute to the dependency graph.

### Adapter activation prerequisites

Most adapters in the table above are currently `status: reserved` (the nine ADR-049 entries plus Phase 2+ slots). Activation of any reserved adapter MUST occur via per-adapter ADR (modeled on [ADR-035](adr/adr-035-orgpath-codebook-binding.md)) and MUST update this section if the activation changes the input-stream → adapter mapping in any way.

The reverse holds also: a change to the input-stream contract (a new stream, a renamed stream, a stream moving between adapters) requires an ADR amendment. This section is intended to be load-bearing documentation, not free-text commentary.
