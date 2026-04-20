---
document_id: DM_060
title: "Device Management Adapter Interface"
version: "0.1-draft"
status: DRAFT
owner: "Michael Stratton"
created_at: "2026-04-19"
updated_at: "2026-04-19"
boundary: GCC-Moderate
core_concepts: ["#7 Embedded governance"]
priority: HIGH
risk: "Non-deterministic policy application without clean device groups"
---

# Device Management Adapter Interface

**Priority:** HIGH | **Risk:** Non-deterministic policy application without clean device groups

## Registered Implementations

| Adapter | Use Case |
|---|---|
| sccm-intune/ | SCCM co-management to full Intune transition |
| intune-native/ | Greenfield Intune deployment |

## Required Capabilities

- SCCM collection inventory: all AD-query-based collections
- Map SCCM collections to Entra ID / Intune dynamic device group equivalents
- GPO-to-Intune policy mapping (using Group Policy Analytics)
- Device compliance policy inventory
- Co-management workload status (which workloads are Intune vs. SCCM)
- Device OrgPath attribute assignment (align with user OrgPath model)
- Enrollment status: Entra-joined vs. Hybrid-joined vs. AD-only

## Migration Sequence

1. Run Group Policy Analytics — identify GPO settings without Intune equivalent
2. Map all SCCM AD-based collections to dynamic device group rules
3. Assign OrgPath extension attributes to device objects
4. Enable Intune co-management with SCCM workload
5. Migrate workloads to Intune incrementally
6. Retire SCCM AD discovery methods last
