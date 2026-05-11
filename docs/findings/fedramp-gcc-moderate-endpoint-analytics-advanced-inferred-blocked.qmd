---
title: "FedRAMP GCC-Moderate — Endpoint Analytics Advanced tier inferred unavailable"
finding_id: "FINDING-004"
status: Awaiting-External-Remediation
severity: P2
created_at: "2026-04-27"
updated_at: "2026-04-27"
owner: "Michael Stratton"
related_canon: ["UIAO_003", "UIAO_109", "UIAO_113"]
related_ksi: ["KSI-SI-04", "KSI-AU-02", "KSI-SC-07"]
related_findings: ["FINDING-001", "FINDING-003"]
related_data: ["src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml"]
gap_matrix_rows:
  - device-boot-performance
  - app-reliability-crashcount-hangrate
  - resource-performance-cpu-memory
  - stop-error-restarts
  - battery-health-wfa-readiness
  - device-performance-anomalies-regression
supersedes: []
superseded_by: []
---

# FedRAMP GCC-Moderate — Endpoint Analytics Advanced tier inferred unavailable

## 1. Constraint

**Microsoft Intune Endpoint Analytics — Advanced Analytics tier** —
covering device performance (boot time, GP processing, desktop load),
application reliability (AppCrashCount, hang rates, stability trends),
stop-error restarts, battery health, work-from-anywhere readiness, and
device performance anomalies (post-config / policy / OS regression) — is
**inferred unavailable** in GCC-Moderate. Microsoft's Advanced Analytics
overview lists sovereign-cloud support as **GCC High and DoD only**;
GCC-Moderate is not enumerated.

This finding is **inferred**, not confirmed: the supporting docs do not
explicitly say "not available in GCC Moderate," but the affirmative
sovereign-cloud list omits it. Per the boundary-inference framework
(`canon/compliance/reference/gcc-moderate-boundary-assessment/methodology.md`),
absence from an affirmative-list is treated as inferred unavailable.

Whether the **base-tier** Endpoint Analytics is available is not
explicitly addressed; treat it as available in principle but unverified
for GCC-Moderate. This finding addresses only the Advanced tier.

## 2. Evidence

### Primary source

- **[Advanced Analytics overview — Microsoft Intune](https://learn.microsoft.com/en-us/intune/advanced-analytics/)**
  Sovereign-cloud support stated as: "U.S. Government Community Cloud
  (GCC) High" and "U.S. Department of Defense (DoD)". GCC-Moderate not
  listed.
- **Microsoft Intune Government Service overview** —
  [`intune-govt-service-description`](https://learn.microsoft.com/en-us/intune/intune-service/fundamentals/intune-govt-service-description)
  Advanced Analytics enumerated under GCC High and DoD support tables.

### Live-assessment validation

Navigate **Intune → Reports → Endpoint Analytics → Advanced Analytics**.
Expect a 403 or "not available in your region" response. This converts
the inferred finding to directly observed evidence per the live
boundary-assessment plan §1.1.

## 3. Capability gap

### Telemetry signals at risk

- Device performance: startup / boot time (median total and core), GP
  processing duration, desktop load time, top boot processes by CPU,
  path, or publisher.
- Application reliability: **AppCrashCount, hang rates, stability
  trends per app**.
- Stop-error restarts and sensor diagnostics.
- Battery health.
- Work-from-anywhere readiness scoring.
- Device performance anomalies — regressions after configuration,
  policy, or OS changes.
- Resource performance: **AverageProcessorUsage, TotalPhysicalMemory
  spikes** — the "**grey-ware** signal": attacks that don't trigger
  EDR but do show up as performance outliers.

### What UIAO cannot do

1. **Use boot-time outliers, app instability, or resource-performance
   anomalies as compromise indicators** — the grey-ware detection
   surface that complements EDR.
2. **Detect post-config / post-policy device-performance regressions**
   — automated anomaly detection across the fleet.
3. **Reconstruct device performance around an incident window** —
   forensic correlation of CPU / RAM history with data egress events.

### Compliance impact

- **CISA BOD 25-01**: device-state visibility weakened; "rapid
  detection and investigation" intent for performance-driven
  compromise indicators is unattainable from native Intune signals.
- **OMB M-22-09**: Device pillar requires supplementation with OS-level
  logs to credibly demonstrate posture.
- **ZTMM v2.0**: Devices pillar caps at **Initial → Advanced**, not
  Optimal, without compensating endpoint-side analytics.

## 4. Proposed remedy

### Internal remedy

1. **Custom DCRs in `gcc_boundary_probe`** to ingest equivalent
   performance signals from OS-level logs (Windows Event Log,
   Performance Monitor counters, Defender for Endpoint timeline data
   where available).
2. **Custom Power BI over Log Analytics** modeling regression
   detection across configuration changes — fidelity loss: no
   Microsoft-tuned anomaly thresholds.
3. **Document the gap in the SSP** under the M-22-09 Device pillar
   risk register.

### External remedy

1. **Microsoft** extends Advanced Analytics to GCC-Moderate. Possible
   under MAS-CSO-MDI for the anonymized perf-counter subset (see
   `canon/data/fedramp-20x.yml` `gap_matrix_scope_effect` —
   *favorable, with caveats* for endpoint performance counters).
2. **MAS 2026** boundary refinement narrowing scope so Microsoft's
   commercial endpoint-analytics ML pipeline sits outside the agency
   ATO.

## 5. Related

- **FINDING-003** — Adoption Score unavailable (sibling
  Microsoft-documented finding; the Endpoint Readiness component
  overlaps with this finding's resource-performance scope).
- **Gap matrix**: 6 rows (`device-boot-performance`,
  `app-reliability-crashcount-hangrate`,
  `resource-performance-cpu-memory`, `stop-error-restarts`,
  `battery-health-wfa-readiness`,
  `device-performance-anomalies-regression`).
- **Canon spec**: `src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/capabilities.md` §3.1.
- **MITRE Chain B** — Privilege escalation (T1068) without EPM
  analytics is part of the same Devices-pillar gap. See
  `canon/compliance/reference/gcc-moderate-boundary-assessment/mitre-chains.md`.

## Status tracking

| Date | Status | Note |
|---|---|---|
| 2026-04-27 | Awaiting-External-Remediation | Initial landing |
