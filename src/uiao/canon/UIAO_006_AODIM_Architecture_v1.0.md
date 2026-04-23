---
document_id: UIAO_006
title: "AODIM — Attribute-Oriented Directory & Identity Model"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-18"
updated_at: "2026-04-18"
boundary: GCC-Moderate
provenance:
  source: "inbox/EntraID Governance/AODIM_Architecture_Document.docx + inbox/EntraID Governance/AODIM_Executive_Whitepaper.docx"
  version: "1.0"
  derived_at: "2026-04-18"
  derived_by: "Copilot Tasks docx extraction; Architecture Document as base with Reference Implementation; Executive Whitepaper language polish applied. Promoted to canon in ADR-044 shadow-canon cleanup on 2026-04-23"
---

# AODIM — Attribute-Oriented Directory & Identity Model

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

Key attributes include:

| Attribute | Purpose |
|-----------|---------|
| `orgPath` | Hierarchical string encoding organizational position |
| `orgCode` | Normalized identifier for the organizational node |
| `department` | Functional department assignment |
| `costCenter` | Financial allocation unit |
| `manager` | Direct reporting relationship |

**Example:**

```
orgPath = CORP/US/EAST/BALTIMORE/IT
```

## Dynamic Group Model

Groups are defined by attribute-matching rules:

- **Node groups** — exact match on a specific organizational position
- **Branch groups** — hierarchical match for subtree membership
- **Functional groups** — role or department-based membership

**Example Rules:**

```
user.orgPath -startsWith "CORP/US/EAST"       # Branch group: all US-East
user.orgPath -eq "CORP/US/EAST/BALTIMORE/IT"   # Node group: Baltimore IT only
```

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
orgtree explain                          # Show current access derivation for a user
orgtree move CORP/US/WEST/SEATTLE/HR     # Simulate access recalculation on transfer
```

These commands demonstrate automatic access recalculation when a user's organizational position changes.

## Strategic Impact

- Enables Zero Trust security models by making identity the control plane
- Aligns HR, IT, and Security operations around a single source of truth
- Supports SaaS and cloud-native environments without directory structure dependencies
- Transforms identity from a static directory into a dynamic, attribute-driven control plane

## Conclusion

AODIM transforms identity systems from static directories into dynamic, attribute-driven control planes. By aligning access with authoritative identity data, organizations achieve greater agility, security, and operational efficiency. Access follows the user — automatically, deterministically, and with full governance traceability.
