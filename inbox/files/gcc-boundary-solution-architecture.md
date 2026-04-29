# The UIAO Invisible Boundary Solution
## Governing, Compensating, and Documenting GCC-Moderate FedRAMP Gaps

**Document type:** Solution Architecture
**Audience:** Enterprise Architects, Identity Engineers, Security Engineers, ISSO
**Status:** Active — implementation in progress
**Date:** April 2026
**Canon reference:** ADR-030, UIAO_GCC_001

---

## Executive Summary

The UIAO Governance OS resolves the invisible boundary problem through
four integrated capabilities that transform undocumented, silent feature
gaps into governed, compensated, and ATO-documented architectural facts.

The solution does not require Microsoft to fix anything. It works within
the actual capabilities of GCC-Moderate today, providing equivalent
governance value through in-boundary mechanisms, and producing the
compliance artifacts that authorizing officials and 3PAOs require.

---

## 1. Solution Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    INVISIBLE BOUNDARY (Current State)                │
│                                                                      │
│  M365 GCC-Moderate Portal shows:  │  What actually functions:       │
│  ✓ Endpoint Analytics             │  ✗ Empty — telemetry blocked    │
│  ✓ Device Health Attestation      │  ✗ Planning phase — unavailable │
│  ✓ Locations / Network Fence      │  ✗ Explicitly unavailable       │
│  ✓ ARC Server Monitoring          │  ✗ Monitor endpoints blocked    │
│  ✓ Expedited Updates              │  ✗ Planning phase               │
└───────────────────┬─────────────────────────────────────────────────┘
                    │
                    ▼ UIAO resolves each gap
┌─────────────────────────────────────────────────────────────────────┐
│                    UIAO SOLUTION ARCHITECTURE                        │
│                                                                      │
│  ┌─────────────────────┐   ┌──────────────────────────────────────┐ │
│  │  1. BOUNDARY PROBE  │   │  2. IN-BOUNDARY TELEMETRY            │ │
│  │                     │   │                                      │ │
│  │ Detects every gap   │   │ WMI/CIM device health               │ │
│  │ Tests functionally  │   │ Graph management plane data          │ │
│  │ Emits DRIFT-BOUNDARY│   │ Replaces blocked DiagTrack pipeline  │ │
│  │ Weekly schedule     │   │ Satisfies NIST 800-137 ConMon        │ │
│  └──────────┬──────────┘   └──────────────┬───────────────────────┘ │
│             │                             │                          │
│             ▼                             ▼                          │
│  ┌─────────────────────┐   ┌──────────────────────────────────────┐ │
│  │  3. GAP REGISTRY    │   │  4. ORGPATH DEVICE TARGETING         │ │
│  │                     │   │                                      │ │
│  │ Machine-generated   │   │ Replaces blocked Locations feature   │ │
│  │ NIST control mapped │   │ OrgPath on device objects            │ │
│  │ ATO artifact        │   │ Dynamic group-scoped compliance      │ │
│  │ SSP evidence base   │   │ Org-hierarchy policy targeting       │ │
│  └─────────────────────┘   └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Capability 1: The GCC Boundary Probe

### What It Does

The `gcc-boundary-probe-v1` adapter runs automated functional tests
against the M365 GCC-Moderate tenant and Azure subscription. Unlike
documentation review (which finds what Microsoft says), the probe finds
what Microsoft actually delivers in the specific tenant.

For each feature in the gap inventory, the probe:
1. Attempts to invoke the feature via Graph API or ARM API
2. Waits for expected data signals
3. Classifies the result as FUNCTIONAL, SILENTLY_BLOCKED,
   EXPLICITLY_UNAVAIL, or PLANNING_PHASE
4. Emits a DRIFT-BOUNDARY finding with severity, NIST control mapping,
   and compensating control reference

### Why This Matters

The probe transforms the invisible boundary from an operational surprise
into a governed drift class. Once the probe runs:

- Every gap is documented with a timestamp and functional test evidence
- The gap registry is a canonical artifact that feeds the SSP
- The probe runs weekly — if Microsoft ships a government feature that
  was previously blocked, the probe detects it and closes the gap
- Administrators stop wasting weeks diagnosing empty dashboards

### Running the Probe

```bash
# Via UIAO CLI
uiao substrate walk --include-boundary-probe

# Via API (Windows Auth required)
POST https://uiao-api.corp.contoso.com/api/v1/boundary/run
{
  "include_arc": true,
  "subscription_id": "your-azure-sub-id"
}
```

### What the Probe Reports

```json
{
  "gap_id": "GAP-INT-001",
  "feature": "Endpoint Analytics",
  "probe_result": "SILENTLY_BLOCKED",
  "probe_detail": "API responds but returns no insights.
                   DiagTrack telemetry pipeline likely blocked.",
  "severity": "P2",
  "nist_controls": ["SI-4"],
  "compensating_control": "UIAO-TELEM-001",
  "compensating_status": "COMPENSATED"
}
```

---

## 3. Capability 2: In-Boundary Telemetry Aggregation

### The Problem It Solves

Endpoint Analytics, ARC server monitoring, and device health reporting
all fail because they depend on telemetry flowing to Microsoft's
commercial endpoints. UIAO provides equivalent operational intelligence
using data sources that function within the FedRAMP boundary.

### Data Sources (All In-Boundary)

| Source | Data Collected | Endpoint Required |
|---|---|---|
| Graph `/deviceManagement/managedDevices` | Enrollment, compliance, OS version, disk, memory | `graph.microsoft.com` — available in GCC-Moderate |
| Graph compliance reports | Policy compliance state per device | `graph.microsoft.com` — available |
| Graph audit logs | Admin actions, policy changes | `graph.microsoft.com` — available |
| WMI/CIM (local query) | CPU, RAM, disk, TPM state, last boot | None — local Windows API |
| WMI/CIM (remote via WinRM) | Same as above for remote servers | Internal network only |
| AD survey adapter output | OrgPath, OU classification, group membership | Internal LDAP |

### What This Replaces

| Blocked Microsoft Capability | UIAO In-Boundary Replacement |
|---|---|
| Endpoint Analytics boot score | WMI last boot time + event log analysis |
| Device performance (CPU/RAM) | WMI/CIM hardware data via Graph or local query |
| App reliability reporting | Intune device config state via Graph |
| Update compliance dashboard | Graph managed device OS version + WUfB policy state |
| ARC server health (Azure Monitor) | WMI bulk collection via PowerShell jobs |
| ARC change tracking | WMI software inventory delta comparison |

### Compliance Mapping

The in-boundary telemetry aggregation satisfies:
- **NIST 800-137**: Continuous monitoring information security program
  — the ConMon obligation is met through in-boundary collection, not
  Microsoft's commercial telemetry pipeline
- **SI-4 (System Monitoring)**: Device health data is collected and
  available for analysis
- **AU-2 (Audit Events)**: Governance actions are recorded via Graph
  audit log API
- **CM-8 (System Component Inventory)**: Device inventory maintained
  through Graph enrollment data + WMI software inventory

---

## 4. Capability 3: The Gap Registry as ATO Artifact

### Structure

The `gcc-boundary-gap-registry.yaml` is a canonical UIAO document that:
- Lists every identified boundary gap with a unique ID
- Maps each gap to NIST 800-53 controls
- Documents the compensating control or unmitigated status
- Provides ATO documentation guidance
- Feeds the KSI (Key Security Indicator) signal set

### Using It in the SSP

The gap registry directly populates SSP Section 13 (Inherited Controls).
For each gap:

**If COMPENSATED:**
```
Control: SI-4 (System Monitoring)
Implementation: [Microsoft Intune Endpoint Analytics — BLOCKED]
Compensating Control: UIAO in-boundary telemetry aggregation
                     (UIAO-TELEM-001) provides equivalent device
                     health monitoring via Graph management plane
                     and WMI/CIM within the authorized boundary.
Evidence: gcc-boundary-gap-registry.yaml GAP-INT-001, probe report
          dated [date], device-health-report.json
```

**If GAP_UNMITIGATED:**
```
Control: SI-7 (Software and Information Integrity)
Implementation: [Device Health Attestation — UNAVAILABLE]
Risk Acceptance: AO accepted residual risk [date], Memo reference [X]
Remediation Plan: Track Microsoft government roadmap. Estimated
                  resolution: unknown. Review at next ATO renewal.
Evidence: gcc-boundary-gap-registry.yaml GAP-INT-008, AO acceptance memo
```

### Maintenance

The probe regenerates the registry weekly. Changes are submitted as
governed PRs through the Appendix V contributor workflow. The registry
version history provides an audit trail — if Microsoft ships a feature
that was previously blocked, the registry records the closure with
the probe run date as evidence.

---

## 5. Capability 4: OrgPath as the Locations Replacement

### The Problem

The Intune Locations feature (network fence) allowed device compliance
policies to be scoped to physical or network locations. It is explicitly
unavailable in government tenants. This eliminates a primary tool for
replacing GPO's OU-scoped policy targeting with Intune.

### The Solution

OrgPath-encoded device objects provide a superior replacement for
organizational policy targeting — not just equivalent.

**Why OrgPath is better than geographic location for this environment:**

Your AD forest was centralized to two East Coast datacenters over the
last decade. Devices are no longer where their OU says they are. A device
in `OU=Baltimore,OU=East` is physically in a Virginia datacenter.
Geographic targeting would be wrong. OrgPath targets the organizational
unit the device *belongs to*, not where it *is*.

**Implementation:**

The AD survey adapter writes OrgPath to `extensionAttribute1` on computer
objects. Entra Connect syncs this to Entra ID device objects. Dynamic device
groups are created on the same OrgPath rules as user groups:

```
OrgTree-IT-SEC-SOC (devices)
  Rule: device.extensionAttribute1 -eq "ORG-IT-SEC-SOC"

OrgTree-FIN-All (devices)
  Rule: device.extensionAttribute1 -startsWith "ORG-FIN"
```

Intune configuration profiles and compliance policies target these groups.
The result is organizational policy targeting that accurately reflects the
current enterprise structure — which geographic targeting never did.

**Network boundary compliance:**

For cases where network location compliance IS needed (e.g., requiring
devices to be on the corporate network for certain resource access),
Entra ID Conditional Access Named Locations (IP-range based) provide
this capability and ARE available in GCC-Moderate. This covers the
network fence use case for authentication policy. OrgPath covers the
device configuration policy use case.

---

## 6. The Integrated Solution in Context

### How the Four Capabilities Work Together

```
Weekly probe run
  → Gap registry updated
    → SSP evidence base current
    → KSI signals updated (Appendix T risk scoring)
      → If new gap detected: DRIFT-BOUNDARY finding emitted
        → Governance workflow triggered (Appendix E, Workflow 6)
        → Owner assigned
        → Compensating control assessed or AO acceptance documented

Continuous telemetry collection
  → Device health data in UIAO dashboards
  → Compliance state visible to administrators
  → ConMon obligation satisfied
  → Matches or exceeds pre-migration SCCM/AD operational visibility

OrgPath device targeting
  → Device objects get OrgPath on AD write-back
  → Entra Connect syncs on next cycle (30 min default)
  → Dynamic groups compute membership
  → Intune profiles apply to correct organizational populations
  → ARC Policy assignments follow same OrgPath structure

Gap registry as ATO artifact
  → ISSO reviews registry at each ATO renewal
  → 3PAO receives registry as evidence package
  → AO reviews unmitigated P1 gaps for risk acceptance
  → Audit trail shows gap discovery date, compensating control date
```

### What Administrators Actually Experience

**Before UIAO:**
- Log into Intune admin center
- Navigate to Endpoint Analytics
- See empty dashboards
- Spend weeks troubleshooting
- Find no configuration errors
- Never determine root cause
- Proceed with migration assuming dashboard will eventually populate
- Discover during 3PAO assessment that SSP claims are inaccurate

**After UIAO:**
- Log into Intune admin center
- Navigate to Endpoint Analytics
- Correctly expected to be empty (probe has classified this as SILENTLY_BLOCKED)
- Navigate to UIAO governance dashboard
- See equivalent device health data from in-boundary telemetry
- SSP accurately documents the gap and the compensating control
- 3PAO receives gap registry as evidence — no findings

---

## 7. Migration Impact: What This Means for AD Retirement

The invisible boundary has direct implications for the AD migration
sequencing that were not previously understood. The corrected sequence:

**Cannot retire AD until:**
- UIAO in-boundary telemetry aggregation is operational and producing
  equivalent device health visibility to SCCM/on-premises monitoring
- OrgPath device targeting is deployed and validated as equivalent to
  OU-scoped GPO policy targeting
- Device Health Attestation gap is formally accepted or Microsoft
  delivers government support (whichever comes first)
- ARC server monitoring is confirmed reachable or UIAO WMI aggregation
  is deployed for server visibility

**Can proceed in parallel:**
- OrgPath assignment to device objects (AD write-back, no user impact)
- Hybrid Entra join for workstations (compatible with parallel AD operation)
- Intune policy deployment for configuration management (GPO removal
  can lag Intune deployment — no dependency on features that are blocked)
- ARC enrollment for servers (management plane works; visibility through UIAO)

**The key insight:**
The invisible boundary does not prevent the migration. It changes the
monitoring and compliance architecture alongside the migration. UIAO
provides that architecture. The migration can proceed on the planned
timeline with UIAO deployed as the operational visibility layer.

---

## 8. Implementation Checklist

**Phase 1 — Discover (Week 1)**
- [ ] Deploy UIAO API to Windows Server 2026 (project plan complete)
- [ ] Run `gcc-boundary-probe-v1` against production tenant
- [ ] Review gap registry output — confirm which gaps are present
- [ ] Identify any tenant-specific gaps not in the default registry

**Phase 2 — Document (Weeks 2–3)**
- [ ] Submit gap registry as canonical artifact via PR (Appendix V)
- [ ] Update SSP Section 13 with gap documentation
- [ ] Prepare AO risk acceptance memos for P1 unmitigated gaps
- [ ] Schedule 3PAO briefing on compensating controls approach

**Phase 3 — Compensate (Weeks 3–6)**
- [ ] Deploy in-boundary telemetry aggregation service
- [ ] Validate device health data equivalent to Endpoint Analytics
- [ ] Deploy OrgPath to device objects (AD survey adapter write-back)
- [ ] Create OrgPath-scoped dynamic device groups
- [ ] Wire device groups to Intune compliance policies and profiles

**Phase 4 — Sustain (Ongoing)**
- [ ] Weekly boundary probe scheduled (GitHub Actions or Windows Task)
- [ ] Monthly gap registry review
- [ ] Track Microsoft government roadmap for planning-phase gaps
- [ ] Update registry and SSP when gaps close (Microsoft ships feature)
- [ ] Annual ATO renewal includes gap registry as evidence artifact

---

## 9. What UIAO Cannot Do

Complete transparency requires stating what remains outside UIAO's scope:

- **UIAO cannot enable blocked Microsoft features.** Device Health
  Attestation will remain unavailable until Microsoft delivers government
  support. UIAO documents and compensates; it does not fix Microsoft.

- **UIAO's WMI telemetry is not identical to DiagTrack telemetry.**
  Microsoft's machine learning models (anomaly detection, predictive
  battery health) require the DiagTrack payload. UIAO provides operational
  equivalence for ConMon and SSP purposes, not feature identity.

- **ARC management plane limitations are separate from observability.**
  Some ARC management features (Defender for Servers, advanced policy
  enforcement) depend on connectivity that may also be restricted.
  UIAO's probe detects these; it cannot route around them.

- **This solution is specific to GCC-Moderate.**
  GCC-High customers have different (often more restrictive) gaps.
  Commercial customers have no gaps. The UIAO solution is calibrated
  for the GCC-Moderate boundary specifically.

---

## 10. Appendix: NIST 800-53 Control Coverage Summary

| NIST Control | Gap | UIAO Compensating Control | Status |
|---|---|---|---|
| SI-4 System Monitoring | Endpoint Analytics blocked | UIAO-TELEM-001 (in-boundary) | Compensated |
| SI-7 Software Integrity | Device Health Attestation unavailable | None currently | **Unmitigated** |
| SI-2 Flaw Remediation | Expedited updates unavailable | Compressed update rings | Compensated |
| SI-3 Malicious Code | Defender for Servers telemetry | Verify Defender endpoints | Partially compensated |
| AU-2 Audit Events | Diagnostics Settings unavailable | Graph audit log API | Compensated |
| AU-6 Audit Review | Workbooks unavailable | UIAO dashboards | Compensated |
| AC-17 Remote Access | Locations unavailable | Named Locations (IP) + OrgPath | Compensated |
| CM-6 Config Settings | BIOS/DFCI policies unavailable | OEM management tools + WMI drift | Compensated |
| CM-8 Component Inventory | ARC change tracking blocked | WMI software inventory | Compensated |
| CM-3 Config Change Control | ARC change tracking blocked | UIAO drift detection | Compensated |
| IA-3 Device Authentication | DHA unavailable | Enrollment-based trust + Entra join | Partially compensated |
