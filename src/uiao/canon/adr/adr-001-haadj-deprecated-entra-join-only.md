---
adr_id: adr-001
title: "HAADJ Deprecated — Entra ID Join as Sole Device Join Target"
status: ACCEPTED
decided: 2026-04-28
deciders: Michael Stratton
updated: 2026-04-28
next_review: 2026-11-01
review_trigger: Microsoft Ignite 2026; any Autopilot or device identity announcement
impact: UIAO_136 Spec 1 (Computer Object Transformation)
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
---

# ADR-001: HAADJ Deprecated — Entra ID Join as Sole Device Join Target

## Status

**ACCEPTED** — April 28, 2026

## Context

Active Directory domain-joined devices have historically been the sole trust model for enterprise endpoints. Microsoft introduced Hybrid Azure AD Join (HAADJ) as a bridge — devices simultaneously joined to on-prem AD and registered in Entra ID — allowing organizations to begin consuming cloud identity signals while retaining AD membership.

UIAO must define the canonical device join target for the Computer Object Transformation specification. The decision determines:

- Whether the migration path is staged (domain-joined → HAADJ → Entra joined) or direct (domain-joined → wipe & re-provision as Entra joined)
- Whether HAADJ is an acceptable interim state or a dead-end that delays full cloud-native posture
- Whether Autopilot deployment profiles should include HAADJ scenarios

## Decision

**Entra ID Join is the sole device join target for all new and migrated endpoints. HAADJ is not an acceptable interim state for new devices and should be treated as a transitional state to be eliminated for existing devices.**

## Rationale

1. **Microsoft has explicitly deprecated HAADJ for new devices.** The official Microsoft Learn documentation states: *"Microsoft recommends deploying new devices as cloud-native using Microsoft Entra join. Deploying new devices as Microsoft Entra hybrid join devices isn't recommended, including through Windows Autopilot."*

2. **Autopilot v2 (Device Preparation) dropped HAADJ support entirely.** The next-generation Autopilot experience does not support hybrid join scenarios. Investing in HAADJ Autopilot profiles creates technical debt against a deprecated platform.

3. **HAADJ retains the AD dependency.** A device that is hybrid joined still requires line-of-sight to a domain controller, still authenticates via Kerberos to AD, and still processes GPOs. This negates the operational benefits of cloud-native management.

4. **Intune management is equivalent for Entra joined devices.** All Intune capabilities — Settings Catalog, Compliance Policies, Endpoint Security, App Protection — work identically (or better) on Entra joined devices vs. HAADJ devices.

## Consequences

### Positive
- Eliminates the HAADJ → Entra join re-migration step (devices go directly to target state)
- Removes DC line-of-sight requirement for endpoint authentication
- Simplifies Autopilot deployment (single profile type, no Intune Connector for AD needed)
- Enables full Conditional Access device trust without AD dependency
- Aligns with Microsoft's stated strategic direction

### Negative
- **Existing HAADJ devices require wipe & re-provision** to reach Entra joined state (no in-place conversion exists as of April 2026)
- **Applications requiring Kerberos authentication** to on-prem resources need Cloud Kerberos Trust or App Proxy configured before device migration
- **User disruption** during re-provisioning — devices must be wiped, data must be backed up or synced via OneDrive Known Folder Move
- **Network printer access** via AD may break — requires Universal Print or IP-direct printing
- **File share access** via Kerberos may require Cloud Kerberos Trust or migration to SharePoint/OneDrive

### Risks
- If Microsoft reverses position and re-invests in HAADJ (low probability), this decision remains valid as Entra join is strictly a superset capability
- Applications with hard Kerberos dependencies may block device migration — these must be inventoried in Phase 1 (D1.4)

## Verification Sources

| Source | URL | Last Verified |
|---|---|---|
| Microsoft Learn — Autopilot HAADJ Enrollment | https://learn.microsoft.com/en-us/autopilot/windows-autopilot-hybrid | 2026-04-28 |
| Microsoft Learn — Cloud-native endpoints guidance | https://learn.microsoft.com/en-us/mem/solutions/cloud-native-endpoints/cloud-native-endpoints-planning-guide | 2026-04-28 |
| Autopilot v2 announcement — HAADJ not supported | https://learn.microsoft.com/en-us/autopilot/device-preparation/overview | 2026-04-28 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] Microsoft announces in-place HAADJ → Entra join conversion capability
- [ ] Microsoft reverses HAADJ deprecation guidance
- [ ] Autopilot v2 adds HAADJ support
- [ ] Windows Server gains native Entra join without Arc (affecting server device identity strategy)
- [ ] Microsoft Ignite 2026 (November) — scheduled review
- [ ] Microsoft Build 2027 (May) — scheduled review

## Related Documents

- UIAO_135 — Identity & Directory Transformation Inventory (Transformation #5: Device Identity)
- UIAO_136 — Spec 1: Computer Object Transformation (D2.2: Migration Pattern Catalog)
- ADR-002 — Arc-Enabled Servers Require Non-Domain-Joined State
