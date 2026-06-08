---
document_id: UIAO_006
title: "AODIM — Attribute-Oriented Directory & Identity Model"
version: "1.1"
status: Current
owner: "Michael Stratton"
created_at: "2026-04-18"
updated_at: "2026-06-03"
provenance:
  source: "inbox/EntraID Governance/AODIM_Architecture_Document.docx + inbox/EntraID Governance/AODIM_Executive_Whitepaper.docx"
  version: "1.0"
  derived_at: "2026-04-18"
  derived_by: "Copilot Tasks docx extraction; Architecture Document as base with Reference Implementation; Executive Whitepaper language polish applied. Promoted to canon in ADR-044 shadow-canon cleanup on 2026-04-23"
  reconciled_at: "2026-06-03"
  reconciled_by: "v1.1 — Attribute Model, Dynamic Group Model, and CLI examples reconciled from the retired composite-path orgPath (Model A/B) to the 15-facet multi-attribute schema (Model C) per ADR-078. Conceptual framing preserved unchanged."
---

# AODIM — Attribute-Oriented Directory & Identity Model

> **Data-model note (v1.1).** AODIM is the *conceptual* charter of UIAO's
> organizational addressing: *attributes define structure; access is
> computed, not assigned.* That thesis is unchanged. The concrete
> `orgPath` data model has, however, evolved: the original
> single composite path string (`CORP/US/EAST/BALTIMORE/IT`) was
> **Model B (composite-slash)**, which **[ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md)
> superseded** with **Model C — the 15-facet multi-attribute schema**
> (10 named facets across `extensionAttribute1`–`10`, 5 reserved). The
> Attribute Model, Dynamic Group Model, and CLI sections below reflect
> Model C. See the [OrgPath Codebook (UIAO_151)](UIAO_151_OrgPath_Codebook.md)
> for the canonical facet→slot map.

## Executive Summary

Enterprises transitioning to cloud identity platforms face a structural mismatch between dynamic organizational models and static access control systems. AODIM (Attribute-Oriented Directory & Identity Model) resolves this by making identity attributes the authoritative driver of access, policy, and governance.

This approach enables automated access alignment, reduces operational overhead, and strengthens security through continuous least privilege enforcement.

## Core Principle

> Identity attributes define organizational structure; access is computed, not assigned.

## Problem Statement

Traditional directory systems rely on hierarchical placement (OUs), which do not translate well to cloud environments. This leads to:

- Manual access management processes
- Inefficient handling of role changes (movers)
- Over-permissioning and access drift
- Audit and compliance complexity
- Misalignment between HR, IT, and Security

## Architecture Overview

```
HR System → Identity Attributes → Dynamic Groups → Access & Policy Enforcement
```

## Attribute Model

OrgPath is **not** a single hierarchical string. Under Model C
([ADR-078](adr/adr-078-orgpath-attribute-schema-15-facet.md)) the
organizational position of every principal is decomposed into **10 named
facets**, each bound to exactly one Entra `extensionAttribute` slot. Each
facet is queried directly rather than parsed out of a composite path.

| Facet | Slot | Purpose |
|-------|------|---------|
| `Region` | `extensionAttribute1` | Geographic / organizational region |
| `Department` | `extensionAttribute2` | Functional department assignment |
| `Division` | `extensionAttribute3` | Sub-department division |
| `Role` | `extensionAttribute4` | Role / role-tier |
| `CostCenter` | `extensionAttribute5` | Financial allocation unit |
| `Classification` | `extensionAttribute6` | Account classification (Employee / Contractor / …) |
| `HireDate` | `extensionAttribute7` | Hire date (typed, ISO 8601) |
| `TermDate` | `extensionAttribute8` | Termination date (typed, empty = active) |
| `ClearanceLevel` | `extensionAttribute9` | Clearance band |
| `AccountType` | `extensionAttribute10` | Account type (Privileged / Service / …) |

Slots `extensionAttribute11`–`15` are reserved for tenant-declared facets
introduced via governed PR. The native `manager` relationship is consumed
alongside these facets but is a standard directory attribute, not an
OrgPath facet.

**Example (per-facet values on one principal):**

```
extensionAttribute1 = EASTUS        # Region
extensionAttribute2 = IT            # Department
extensionAttribute3 = InfraOps      # Division
extensionAttribute4 = Engineer      # Role
```

## Dynamic Group Model

Groups are defined by **boolean composition over facet predicates** — not
by text-parsing a single composite path. Under Model C every membership
rule uses one of three patterns:

- **Single-facet** (`-eq` / `-in`) — all principals carrying a value (or
  value set) in one facet.
- **Multi-facet AND** — principals matching every clause across multiple
  facets.
- **Multi-facet OR / set** — cross-cutting groupings. This replaces the
  retired Model A/B Branch (`-startsWith`) and Node (`-eq` on the path)
  distinction: because each facet is already a discrete attribute, you
  query the facet directly rather than parsing its position inside a
  string.

**Example Rules:**

```
(attr2 -eq "IT")                          # All IT department users
(attr2 -eq "IT") and (attr3 -eq "InfraOps")   # IT / Infrastructure division
(attr1 -in ["NCR","EASTUS","WESTUS"])     # All US-region users
```

See the [Dynamic Group Library (UIAO_152)](UIAO_152_Dynamic_Group_Library.md)
for the canonical inventory.

## Delegation Model

Administrative Units and scoped roles replace traditional OU-based delegation. Admin roles are scoped to AUs whose membership is driven by the same canonical attributes, preserving the principle that access is computed, not manually assigned.

## Operational Flow

```
HR updates → Attribute change → Group recalculation → Access update
```

1. HR system updates user data (hire, transfer, termination)
2. Attributes are updated in the identity platform via HR connector
3. Dynamic groups recalculate membership automatically
4. Access and policies update without manual intervention

## Key Benefits

- **Automatic access alignment** — access follows the user through organizational changes
- **Deterministic and explainable access** — every permission traces to an attribute rule
- **Reduced operational overhead** — no manual group membership management
- **Continuous least privilege enforcement** — access revokes automatically on role change
- **Improved audit readiness** — complete traceability from attribute to access

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Data quality issues | Implement validation pipelines between HR and identity platform |
| Group sprawl | Enforce naming standards and lifecycle management |
| Complexity | Apply governance model and documentation |
| Delegation gaps | Align administrative units with major organizational segments |

## Reference Implementation

The AODIM reference implementation includes:

- Attribute schema definition
- Dynamic group rule library
- CLI tool for simulation and explanation

### CLI Examples

```shell
# Assign per-facet OrgPath values from an AD export and report findings
uiao orgtree assess --from-export ad-users.json --out assignments.json

# Run one governance pass over a tenant snapshot (dry-run by default):
# detects per-facet drift and reports the remediation it would apply
uiao orgtree govern snapshot.json --out report.json
```

`uiao orgtree govern` in its default dry-run mode is the simulation /
explanation surface: it recomputes per-facet assignments against the
codebook and reports the access recalculation a transfer or role change
would produce, without writing.

## Strategic Impact

- Enables Zero Trust security models by making identity the control plane
- Aligns HR, IT, and Security operations around a single source of truth
- Supports SaaS and cloud-native environments without directory structure dependencies
- Transforms identity from a static directory into a dynamic, attribute-driven control plane

## Conclusion

AODIM transforms identity systems from static directories into dynamic, attribute-driven control planes. By aligning access with authoritative identity data, organizations achieve greater agility, security, and operational efficiency. Access follows the user — automatically, deterministically, and with full governance traceability.
