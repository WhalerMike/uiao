# The Invisible Boundary Problem
## Microsoft GCC-Moderate FedRAMP Feature Gaps in Intune and Azure Arc

**Document type:** Problem Statement
**Audience:** Agency CIO, ISSO, System Owners, Authorizing Official
**Status:** Active — requires AO review and SSP update
**Date:** April 2026
**Canon reference:** ADR-030, UIAO_GCC_001

---

## Executive Summary

Organizations operating Microsoft 365 GCC-Moderate tenants are systematically
discovering that significant portions of the Intune and Azure Arc capabilities
they have planned, budgeted, and in some cases documented in their System
Security Plans do not function as documented. This is not a configuration error.
It is a structural characteristic of how Microsoft's GCC-Moderate authorization
boundary operates that Microsoft does not clearly document.

The result is what practitioners have named the **invisible boundary** — a set
of features that appear available in administrative portals, are described in
Microsoft's commercial documentation, and may be referenced in SSPs and
migration plans, but silently produce no data, emit no errors, and have no
documented resolution path in the GCC-Moderate context.

This problem statement defines the scope of the invisible boundary, its
compliance impact, and why it requires formal governance action.

---

## 1. Background: What GCC-Moderate Actually Is

Microsoft 365 GCC-Moderate is not a separate cloud. It is a tenancy designation
on Microsoft's commercial (.com) infrastructure with a FedRAMP Moderate
authorization, data residency commitments, and specific compliance controls
applied at the tenant level. Every administrative endpoint, every API call,
every management operation uses the same commercial Microsoft infrastructure
as any enterprise customer.

Critically, Microsoft's own documentation states explicitly:

> *"GCC is the same instance as Microsoft Intune in the commercial space.
> Intune doesn't have a separate GCC instance."*

This means GCC-Moderate customers are using commercial Intune. The FedRAMP
Moderate authorization for GCC-Moderate covers M365 productivity services
(Exchange, SharePoint, Teams, Entra ID). Intune operates on the commercial
infrastructure with commercial feature availability — but FedRAMP Moderate
compliance requirements create restrictions that Microsoft's commercial
documentation does not account for.

---

## 2. The Mechanism: How Features Become Silently Unavailable

### 2.1 Telemetry Pipeline Dependency

Many Intune features depend on the Windows diagnostic telemetry pipeline —
specifically the Connected User Experiences and Telemetry service (DiagTrack)
sending data to Microsoft's commercial public cloud endpoints
(`*.events.data.microsoft.com`, `vortex.data.microsoft.com`).

Correctly-hardened FedRAMP Moderate deployments block or restrict these
endpoints. This is not misconfiguration — it is the expected implementation
of NIST 800-53 SI (System and Information Integrity) and SC (System and
Communications Protection) controls.

When these endpoints are blocked:
- The Intune administrative portal shows features as enabled and configured
- Device enrollment and policy management continues normally
- Analytics dashboards, device health reports, and compliance reporting
  remain permanently empty
- No error is raised anywhere in the system
- Administrators spend weeks diagnosing the silence

### 2.2 Explicit Government Restrictions

Some features are documented as unavailable for government customers in
Microsoft's GCC-High service description — but because GCC-Moderate uses
commercial Intune (not GCC-High Intune), this documentation does not apply.
The features may or may not be available, and the only way to determine
availability is operational testing.

### 2.3 Planning Phase Gaps

Some capabilities are documented as "in planning phase" for government
environments. These represent future capabilities that do not currently
exist in any government Microsoft tenant. They cannot be enabled, configured,
or compensated for through tenant settings.

### 2.4 Why Microsoft Does Not Document This

Microsoft's Intune documentation is written for commercial customers.
The government service description addresses GCC-High and DoD only.
GCC-Moderate customers are directed to commercial documentation, which
describes full commercial feature availability. The intersection of
correct FedRAMP compliance hardening with commercial Intune infrastructure
creates the invisible boundary — a gap that exists in the operational
experience but not in any single document.

---

## 3. Scope: What Is Affected

### 3.1 Intune — Confirmed Affected Capabilities

| Capability | Status | Security Impact |
|---|---|---|
| Endpoint Analytics | Silently blocked when telemetry restricted | Operational |
| Advanced Analytics (Intune Suite) | Silently blocked | Operational |
| Device Health Attestation | Planning phase — not available | **High** |
| Expedited Windows Quality Updates | Planning phase — not available | **High** |
| Feature Updates for Windows | Planning phase — not available | Medium |
| Locations / Network Fence | Explicitly unavailable | Medium |
| Diagnostics Settings | Explicitly unavailable | Operational |
| Workbooks | Explicitly unavailable | Operational |
| BIOS Configuration Policies | Planning phase | Medium |
| Device Firmware Config Interface | Planning phase | Medium |
| Windows Autopilot Self-Deploy | Planning phase | Operational |
| Delivery Optimization (Win32) | Planning phase | Operational |

### 3.2 Azure Arc — Confirmed Affected Capabilities

| Capability | Status | Security Impact |
|---|---|---|
| Azure Monitor telemetry | Silently blocked when endpoints restricted | **High** |
| Defender for Servers reporting | Silently blocked when endpoints restricted | **High** |
| Change Tracking / Inventory | Silently blocked | Medium |
| VM Insights performance | Silently blocked | Operational |

### 3.3 Cascading Impact on AD Migration

The AD-to-Intune/ARC migration program assumes Intune and ARC provide
equivalent or superior operational visibility to the current AD/GPO model.
The invisible boundary means:

- **GPO-to-Intune mapping that relies on analytics features cannot be
  validated.** Administrators cannot see whether policies are applying
  as intended through the expected reporting channels.

- **Device compliance without Health Attestation is weaker than
  AD domain membership.** AD trust is hardware-independent but well-
  understood. Intune device trust without DHA is enrollment-based only.

- **ARC server monitoring cannot replace on-premises monitoring** if
  Azure Monitor telemetry is blocked. The observability gap is larger
  than anticipated.

- **The Locations feature cannot replace OU-scoped GPO targeting.**
  The network fence that would have provided location-aware compliance
  scoping does not exist in GCC-Moderate.

---

## 4. Compliance Impact

### 4.1 SSP Accuracy

If an SSP documents Intune Endpoint Analytics as contributing to SI-4
(System Monitoring) control implementation, and Endpoint Analytics is
silently non-functional, the SSP contains inaccurate control implementation
claims. This creates a finding during 3PAO assessment.

### 4.2 Continuous Monitoring Gap

NIST 800-137 continuous monitoring requires maintained visibility into
system state. If the monitoring tools relied upon for ConMon are silently
non-functional, the ConMon program has an undocumented gap. This is a
FedRAMP continuous monitoring obligation failure.

### 4.3 Device Trust Degradation

The absence of Device Health Attestation means device trust signals in
Conditional Access rely on Intune enrollment state rather than hardware
attestation. This is a weaker trust model than documented in Zero Trust
architecture plans that assumed DHA availability.

### 4.4 Risk Acceptance Requirement

Three gaps have no compensating controls and require formal Authorizing
Official risk acceptance:

1. **Device Health Attestation** — fundamental device trust signal
   for Zero Trust architecture. No Microsoft ETA for GCC-Moderate.

2. **Defender for Servers telemetry** — security monitoring for
   ARC-enrolled servers. Requires verification of Defender endpoint
   allowlisting or alternative EDR deployment.

3. **Expedited Windows quality updates** — rapid patch deployment
   capability for zero-day response. Compensated by compressed update
   rings but not equivalent.

---

## 5. What Is Known vs. Unknown

### Known — confirmed through operational testing and documentation review:
- Endpoint Analytics requires telemetry endpoints that FedRAMP controls block
- Locations feature explicitly unavailable per Microsoft documentation
- Diagnostics Settings and Workbooks explicitly unavailable
- Device Health Attestation in planning phase with no GCC-Moderate ETA
- Expedited updates and Feature updates in planning phase

### Unknown — requires operational verification per tenant:
- Whether specific Defender for Endpoint telemetry endpoints are in
  the tenant's FedRAMP network allowlist
- Current status of planning-phase features (Microsoft ships
  government features without broad announcement)
- Whether ARC Azure Monitor endpoints are reachable from specific
  network segments in the environment
- Which additional features may be silently blocked that have not
  yet been discovered operationally

### Principle for undiscovered gaps:
> **Assume blocked until tested.** Any Intune or ARC feature that
> depends on Windows diagnostic telemetry, Azure Monitor ingestion,
> or services not explicitly listed as available in the GCC-Moderate
> FedRAMP package should be assumed non-functional until confirmed
> through operational probe testing.

---

## 6. The Governance Failure Mode

The invisible boundary creates a specific organizational failure mode:

1. Migration project plans Intune as replacement for AD/GPO management
2. Plan references Endpoint Analytics, Device Compliance dashboards,
   ARC server monitoring as equivalent to current SCCM/AD visibility
3. Deployment proceeds normally — enrollment works, policies deploy
4. Administrators notice dashboards are empty
5. Weeks of troubleshooting find no configuration errors
6. Eventually determined to be a systemic FedRAMP boundary constraint
7. Migration is partially complete with no fallback position
8. SSP contains inaccurate control claims
9. ConMon program has undocumented gaps
10. 3PAO assessment finds findings

This failure mode is preventable. The problem is known. The gaps are
documentable. Compensating controls exist for most gaps. The remaining
gaps require AO risk acceptance. None of this requires waiting for
Microsoft to fix anything — it requires governance action now.

---

## 7. Immediate Required Actions

**For the ISSO:**
1. Review current SSP for any claims about Intune or ARC capabilities
   listed in Section 3.1 and 3.2 above
2. Flag inaccurate control implementation claims for correction
3. Schedule 3PAO discussion on compensating controls approach

**For the System Owner:**
4. Authorize deployment of the UIAO GCC boundary probe against the
   M365 tenant and Azure subscription
5. Review the gap registry output for tenant-specific findings
6. Confirm which gaps are present in this specific deployment

**For the Authorizing Official:**
7. Review the three P1 unmitigated gaps
8. Issue formal risk acceptance for gaps that cannot be compensated
9. Establish remediation timeline criteria tied to Microsoft roadmap

**For the Migration Program:**
10. Do not retire AD/SCCM-based monitoring until UIAO in-boundary
    telemetry aggregation is operational and validated
11. Revise migration plans to account for the absent features
12. Build OrgPath-scoped device targeting as Locations replacement
    into the Intune profile deployment architecture

---

## 8. Reference

- Microsoft Learn: Intune Government Service Description
  (GCC High/DoD) — note: GCC Moderate uses commercial Intune
- Microsoft Tech Community: Understanding Compliance Between
  Commercial, Government, DoD & Secret Offerings (July 2025)
- NIST SP 800-53 Rev 5: SI-4, SI-7, AU-2, AU-6, AC-17
- NIST SP 800-137: Information Security Continuous Monitoring
- UIAO ADR-030: GCC Boundary Drift Class and Compensating
  Controls Architecture
- UIAO gcc-boundary-gap-registry.yaml: Canonical gap registry
  with NIST control mapping and compensating control status
