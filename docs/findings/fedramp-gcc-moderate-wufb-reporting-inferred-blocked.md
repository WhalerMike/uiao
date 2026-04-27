---
title: "FedRAMP GCC-Moderate — Windows Update for Business reporting depth inferred blocked"
finding_id: "FINDING-009"
status: Awaiting-External-Remediation
severity: P3
created_at: "2026-04-27"
updated_at: "2026-04-27"
owner: "Michael Stratton"
related_canon: ["UIAO_003", "UIAO_109", "UIAO_113"]
related_findings: ["FINDING-004"]
related_data: ["src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml"]
gap_matrix_rows:
  - wufb-deployment-health-trends
  - app-protection-policy-violation-analytics
  - epm-elevation-operational-analytics
supersedes: []
superseded_by: []
---

# FedRAMP GCC-Moderate — Windows Update for Business reporting depth inferred blocked

## 1. Constraint

**Windows Update for Business (WUfB) reporting** depth and trend
telemetry — covering per-device update state, patch success/failure,
deferral status, safeguard holds, error codes and timing, and
fleet-wide patch-compliance trend scoring — is **inferred blocked** in
GCC-Moderate by the FedRAMP Moderate authorization-boundary
architecture.

The outbound flow to **"Commercial Global Service" endpoints** that the
full WUfB reporting depth requires is **often blocked by boundary
firewalls** in agency environments. Agencies fall back to local
GPO-based reporting or third-party inventory tools. The fidelity loss
is real-time fleet-wide patch-compliance scoring; the **asset-visibility
requirement of CISA BOD 25-01 is harder to satisfy** as a result.

This finding co-locates with two adjacent Intune-pillar gaps —
app-protection policy violation analytics and EPM elevation operational
analytics — which share the same root cause (continuous behavioral
telemetry to Microsoft's commercial Intune analytics pipeline is
restricted by SI-4 / AU-2 / AU-3 / SC-7).

## 2. Evidence

### Boundary-inference rationale

No direct GCC-Moderate (.com) Microsoft documentation confirms or
denies WUfB reporting depth at parity with commercial. Public Intune
docs describe data collection in the global Azure commercial environment
without explicit GCC-Moderate addressing; Government-specific Intune
docs are Azure Government (.us) — out of scope under the documentation
purity rule.

The commercial Intune analytics endpoints (the *"Commercial Global
Service"* destinations) are commonly blocked by GCC-Moderate boundary
firewalls. This is observable in agency packet captures and firewall
logs.

### Constraining controls

| Control | Constraint applied to WUfB telemetry |
|---|---|
| SI-4 | Continuous device-update monitoring is sensitive monitoring data. |
| AU-2 / AU-3 | Patch-success / patch-failure / safeguard-hold events are audit records. |
| SC-7 | Outbound to *Commercial Global Service* endpoints is restricted. |

### Live-assessment validation

In the agency tenant, navigate **Intune → Reports → Windows Update**;
expect reduced depth or absent trend dashboards. Cross-check by
querying the `IntuneOperationalLogs` table for WUfB-related events
(use the
`03-intune-ingestion.kql` query in
`src/uiao/adapters/modernization/gcc_boundary_probe/queries/`).

## 3. Capability gap

### Telemetry signals lost / degraded

- WUfB per-device update state: patch success / failure detail,
  deferral status, safeguard holds, error codes and timing.
- Real-time fleet-wide patch-compliance scoring.
- Cross-device patch-trend regression detection.
- Co-located in the same gap class:
  - **App-protection policy violation analytics** — sideloaded /
    shadow-app detection on BYOD.
  - **EPM elevation operational analytics** — process metadata for
    elevation requests, approvals, denials.

### What UIAO cannot do

1. **Detect delayed-patch exploitation** in real time — MITRE T1190 /
   T1068. Commercial cloud detection: hours; GCC-Moderate: 3–7 day
   gap (weekly manual reports).
2. **Detect malicious app sideloading on BYOD** in real time — MITRE
   T1474 / T1574.002. Commercial: real-time; GCC-Moderate: 24–48 hours.
3. **Score privilege-escalation attempts as a continuous risk signal**
   — MITRE T1068 EPM-bypass detection. Commercial: real-time anomaly;
   GCC-Moderate: 48+ hours via compliance snapshots.
4. **Satisfy BOD 25-01 asset-visibility** at full fidelity — patch
   posture lag is the primary gap.

### Compliance impact

- **CISA BOD 25-01 (asset visibility + patch posture)**: harder to
  satisfy without compensating reporting.
- **OMB M-22-09 Device pillar**: continuous patch-state monitoring
  intent partially met; needs supplementation with OS-level logs.
- **ZTMM v2.0**: Devices + Visibility & Analytics pillars cap at
  Advanced (not Optimal) without compensating reporting.

## 4. Proposed remedy

### Internal remedy

1. **Local GPO-based reporting** — fallback already in place at most
   agencies. Coarse-grained but in-boundary.
2. **Graph API exports of Intune compliance + update state** into Log
   Analytics, with custom Power BI / Sentinel rules modeling
   patch-trend regression.
3. **Third-party inventory tools** for fleet-wide asset / patch posture
   when Microsoft-native reporting is insufficient (out-of-scope for
   ATO if not already authorized).
4. **Custom DCRs in `gcc_boundary_probe`** to ingest WUfB-related
   Windows Event Log entries (event IDs 2003–2006, 19, 20) directly
   from endpoints, sidestepping the commercial telemetry path.
5. **Validate ingestion** via the `03-intune-ingestion.kql` query
   (`gcc_boundary_probe/queries/`).

### External remedy

1. **Microsoft** ships full WUfB reporting depth to GCC-Moderate. Per
   `canon/data/fedramp-20x.yml` `gap_matrix_scope_effect`, anonymized
   patch-state data is **favorable, with caveats** under MAS-CSO —
   anonymized fleet-wide patch posture rollups likely qualify as
   descoped metadata; per-user-identified patch state may not.
2. **MAS 2026** boundary refinement — Microsoft's Intune commercial
   analytics pipeline outside the agency ATO scope.

## 5. Related

- **FINDING-004** — Endpoint Analytics Advanced inferred unavailable
  (sister Devices-pillar finding addressing the performance-telemetry
  side; this finding addresses the patch-state side).
- **MITRE Chain A** — T1190 (initial access via delayed-patched device)
  is the explicit attack pattern this finding maps to.
- **Gap matrix**: 3 rows (`wufb-deployment-health-trends`,
  `app-protection-policy-violation-analytics`,
  `epm-elevation-operational-analytics`).
- **Canon spec**: `src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/capabilities.md` §5.2 + §5.5.
- **20x scope effect**: Favorable, with caveats — anonymized
  patch-state subset likely qualifies as descoped under MAS-CSO-MDI.

## Status tracking

| Date | Status | Note |
|---|---|---|
| 2026-04-27 | Awaiting-External-Remediation | Initial landing |
