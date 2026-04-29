---
adr_id: adr-048
title: "ADR‑048: OrgPath Attribute Selection — extensionAttributes over Custom Security Attributes"
adr: "ADR‑048"
status: Accepted
date: "2026-04-28"
deciders: Michael Stratton
---

# ADR‑048: OrgPath Attribute Selection — extensionAttributes over Custom Security Attributes

## Status
**Accepted — 2026‑04‑28**

## Context
UIAO’s organizational addressing model (OrgPath) requires a canonical attribute stamped on every user and device object in Entra ID. This attribute encodes the deterministic organizational path (e.g., `CORP/US/EAST/BALTIMORE/IT`) that replaces the legacy AD X.500 OU tree. OrgPath is the single most cross‑cutting decision in the identity transformation — it drives dynamic group membership, Administrative Unit scoping, Conditional Access targeting, Intune Scope Tags, and HR provisioning attribute mapping.

Three candidate attribute types exist in Entra ID:

1. **extensionAttributes** (extensionAttribute1–15) — Exchange Online schema attributes, synced from AD via Entra Connect
2. **Custom Security Attributes** — Entra ID native, structured attribute sets with ABAC capability
3. **Directory Extensions** — Registered via Graph API app registration, unlimited count

The decision must satisfy all five OrgPath consumers simultaneously:

| Consumer | Requirement |
|---------|-------------|
| Dynamic Security Groups | Attribute must be usable in dynamic membership rules for both users AND devices |
| Administrative Units | Attribute must be usable in dynamic AU membership rules |
| Conditional Access | Attribute must be usable in device filter expressions |
| Intune Scope Tags | Attribute must be readable by Intune for scope tag assignment |
| HR Inbound Provisioning | Attribute must be writable by Entra ID Governance provisioning flows |

## Decision
**Use `extensionAttribute1` for OrgPath.**
Reserve `extensionAttribute2` for OrgPath depth level.
Reserve `extensionAttribute3–5` for future identity transformation attributes.
Document the full allocation table in the canon to prevent drift.

## Attribute Allocation Table

| Attribute | Purpose | Example Value | Object Types |
|----------|---------|---------------|--------------|
| extensionAttribute1 | OrgPath canonical address | `CORP/US/EAST/BALTIMORE/IT` | User, Device |
| extensionAttribute2 | OrgPath depth | `5` | User, Device |
| extensionAttribute3 | Reserved | — | — |
| extensionAttribute4 | Reserved | — | — |
| extensionAttribute5 | Reserved | — | — |
| extensionAttribute6–15 | Unallocated | — | — |

## Evaluation Matrix

| Criterion | extensionAttributes | Custom Security Attributes | Directory Extensions |
|----------|---------------------|----------------------------|----------------------|
| Dynamic group rules (users) | ✔ Supported | ✖ Not supported | ✔ Supported |
| Dynamic group rules (devices) | ✔ Supported | ✖ Not supported | ✖ Not supported |
| Conditional Access device filter | ✔ Supported | ✖ Not supported | ✖ Not supported |
| Admin Unit membership | ✔ Supported | ✖ Not supported | ✖ Partial |
| Intune visibility | ✔ Yes | ✔ Yes | ✔ Yes |
| AD sync (coexistence period) | ✔ Via Entra Connect | ✖ Cloud‑only | ✔ Via Entra Connect |
| ABAC / Azure RBAC | ✖ Not supported | ✔ Purpose‑built | ✖ Not supported |
| Structured data | ✖ Flat strings | ✔ Sets + definitions | ✖ Flat values |
| Capacity | 15 total | Unlimited | Unlimited |
| Setup required | None | Attribute set + definition creation | App registration |

## Scoring Summary
- **extensionAttributes**: 7/10 — the only option satisfying ALL five OrgPath consumers
- **Custom Security Attributes**: 3/10 — excellent for ABAC but cannot drive dynamic groups, CA, or Intune
- **Directory Extensions**: 4/10 — unlimited capacity but no device dynamic groups or CA filters

## Consequences
### Positive
1. **Zero infrastructure setup** — extensionAttributes exist on every Entra ID tenant with no provisioning required
2. **Full consumer coverage** — the only attribute type usable in dynamic group rules (users + devices), CA device filters, AU membership, and Intune scope tags
3. **AD coexistence** — extensionAttributes sync bidirectionally via Entra Connect, enabling OrgPath population during the hybrid period
4. **HR provisioning native** — API‑driven inbound provisioning and cloud HR connectors can write extensionAttributes directly
5. **Proven at scale** — Microsoft’s own documentation uses extensionAttributes for organizational hierarchy examples

### Negative
1. **Capacity constraint** — only 15 slots total, shared with Exchange Online and any existing usage
2. **Flat string only** — no structured data, no attribute sets, no typed validation
3. **No ABAC** — extensionAttributes cannot be used in Azure RBAC condition expressions
4. **Collision risk** — any existing extensionAttribute1 usage must be inventoried and migrated before OrgPath deployment

## Compliance Notes
- **GCC‑Moderate**: extensionAttributes fully supported
- **FedRAMP**: No boundary implications — extensionAttributes are standard Entra ID schema
- **UIAO Canon**: This ADR supersedes the “TBD” notation in UIAO_135 Section 5 regarding OrgPath attribute implementation

## References
- UIAO_135 — Identity & Directory Transformation Inventory
- UIAO_136 — Priority 1 Project Plans (OrgPath)
- ADR‑035 — OrgPath Codebook Binding
- ADR‑036 — Dynamic Group Provisioning
- ADR‑037 — Admin Unit Provisioning
- ADR‑038 — Device Plane OrgPath
- ADR‑039 — Policy Targeting
