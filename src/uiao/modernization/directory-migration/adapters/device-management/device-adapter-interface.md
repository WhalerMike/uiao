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

| Adapter | Use Case | Operational canon |
|---|---|---|
| sccm-intune/ | SCCM co-management to full Intune transition (existing AD-joined fleet) | This interface + the directory-migration five-phase process |
| intune-native/ | Greenfield Intune deployment (net-new asset acquisition) | [`src/uiao/modernization/intune-first-onboarding/`](../../../intune-first-onboarding/README.md), anchored by [ADR-071](../../../../canon/adr/adr-071-intune-first-asset-onboarding.md) |

The `intune-native/` operational canon was hoisted from a sub-adapter
folder under this directory to a top-level sibling under
`src/uiao/modernization/` because the doctrine spans procurement,
endpoints (Windows / macOS / iOS / Android), and servers (Arc) — broader
than this device-management adapter alone. This interface continues to
register the slot for adapter-registry purposes; the operational content
lives at the hoisted location.

## Required Capabilities

### sccm-intune (migration path)

- SCCM collection inventory: all AD-query-based collections
- Map SCCM collections to Entra ID / Intune dynamic device group equivalents
- GPO-to-Intune policy mapping (using Group Policy Analytics)
- Device compliance policy inventory
- Co-management workload status (which workloads are Intune vs. SCCM)
- Device OrgPath attribute assignment (align with user OrgPath model)
- Enrollment status: Entra-joined vs. Hybrid-joined vs. AD-only

### intune-native (greenfield path)

See [`src/uiao/modernization/intune-first-onboarding/process.md`](../../../intune-first-onboarding/process.md) §Phases 1–5 and the per-platform annexes under [`platforms/`](../../../intune-first-onboarding/platforms/).

## Migration Sequence (sccm-intune)

1. Run Group Policy Analytics — identify GPO settings without Intune equivalent
2. Map all SCCM AD-based collections to dynamic device group rules
3. Assign OrgPath extension attributes to device objects
4. Enable Intune co-management with SCCM workload
5. Migrate workloads to Intune incrementally
6. Retire SCCM AD discovery methods last

## Onboarding Sequence (intune-native)

Net-new assets follow the five-phase Intune-first onboarding process (Procure → Pre-stage → Position → Provision → Validate) defined in [`src/uiao/modernization/intune-first-onboarding/process.md`](../../../intune-first-onboarding/process.md). Doctrine is anchored by [ADR-071](../../../../canon/adr/adr-071-intune-first-asset-onboarding.md).
