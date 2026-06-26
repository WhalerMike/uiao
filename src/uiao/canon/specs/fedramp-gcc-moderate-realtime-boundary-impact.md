---
document_id: UIAO_139
title: "FedRAMP Moderate Boundary Impact on Real-Time Vendor Reporting — GCC-Moderate Analysis"
version: "1.0"
status: Current
owner: "Michael Stratton"
created_at: "2026-06-25"
updated_at: "2026-06-25"
mas-scope: "in-scope"
---

# UIAO_139 — FedRAMP Moderate Boundary Impact on Real-Time Vendor Reporting

> **Audience:** Agency CISOs, AOs, Cloud Services teams, and 3PAOs assessing
> the observability posture of a GCC-Moderate Microsoft 365 deployment.
>
> **Purpose:** Document the structural impact of the FedRAMP Moderate
> authorization boundary on real-time telemetry and reporting from Microsoft
> and other vendors operating in or adjacent to the GCC-Moderate boundary.
> This analysis is the factual basis for FINDING-001, FINDING-002, and the
> compensating control strategy in ADR-033.

---

## Executive Summary

The FedRAMP Moderate authorization boundary is not merely a compliance
perimeter — it is a **telemetry filter**.  Every signal Microsoft ships to
its commercial analytics pipeline must first cross that boundary.  In
GCC-Moderate, four NIST SP 800-53 controls (SI-4, AU-2, AU-3, SC-7)
structurally constrain or eliminate the outbound telemetry flows that power
Microsoft's higher-order real-time analytics, ML risk scoring, and behavioral
detection surfaces.

The result is a **structural observability gap** that cannot be closed by
configuration alone.  Agencies operating in GCC-Moderate:

1. **Cannot receive Microsoft Informed Network Routing (INR) telemetry** —
   the bi-directional path-quality signal is unavailable for government
   (FINDING-001).
2. **Operate below the ZTMM Advanced tier** in six of seven pillars without
   agency-built compensating analytics.
3. **Cannot satisfy the behavioral observability intent** of CISA BOD 25-01,
   OMB M-22-09, and FedRAMP 20x continuous-monitoring (RFC-0006/0014) from
   Microsoft-native telemetry alone.
4. **Face a three-way compliance conflict** — TIC 3.0, CISA ZTMM, and
   FedRAMP 20x cannot all be fully satisfied simultaneously from within the
   GCC-Moderate boundary without agency-side compensating controls.

This document catalogues every known gap, classifies its root cause, maps it
to the affected mandate, and specifies the compensating control strategy.

---

## 1. The Boundary Constraint Mechanism

### 1.1 Four load-bearing controls

The FedRAMP Moderate authorization boundary constrains real-time vendor
reporting through four controls working in combination:

| Control | Title | Constraint imposed |
|---|---|---|
| **SI-4** | Information System Monitoring | Monitoring data must remain within the authorized boundary unless explicitly scoped and authorized for export.  Continuous rich telemetry to Microsoft's commercial multi-tenant analytics is exactly the cross-boundary flow SI-4 forces agencies to evaluate. |
| **AU-2** | Audit Events | Audit event content shipped to commercial multi-tenant log analytics may exceed authorized export scope.  GCC-Moderate configures audit category routing; categories that would route through commercial Azure Monitor are suppressed or degraded. |
| **AU-3** | Content of Audit Records | Audit records that include behavioral metadata (IP geolocation enrichment, device-state annotations, ML-derived risk tags) require those enrichment services to be within the authorized boundary.  Commercial enrichment pipelines are not. |
| **SC-7** | Boundary Protection | Continuous, rich telemetry to multi-tenant analytics is a high-volume outbound flow.  SC-7 enforcement at the FedRAMP boundary blocks or degrades flows that would traverse the boundary to reach Microsoft commercial endpoints. |

### 1.2 The reverse-inference rule

A critical methodological point: **absence of an explicit "not available in
GCC-Moderate" statement is NOT evidence of availability.**

Many telemetry-dependent features are constrained by the boundary architecture
itself.  The probe:

> If a feature requires telemetry to flow to Microsoft's commercial
> multi-tenant processing pipeline AND the FedRAMP Moderate boundary
> restricts that outbound flow, the signal is **blocked or degraded by
> architecture** — even with no explicit "unavailable" statement.

This is the methodology behind UIAO's boundary-inference framework
(ADR-033) and the `SILENTLY_BLOCKED` probe result class in the
GCC Boundary Probe (`uiao.adapters.modernization.gcc_boundary_probe`).

### 1.3 Telemetry plane vs. management plane

The distinction that matters for compensating control design:

| Plane | Description | GCC-Moderate availability |
|---|---|---|
| **Telemetry plane** | Behavioral, ML-derived, diagnostic signals flowing to Microsoft commercial analytics | **Constrained** — SI-4/AU-2/AU-3/SC-7 restrict outbound flows |
| **Management plane** | Control operations via Microsoft Graph API, Intune management API, ARM | **Available** — Graph/ARM operate within the GCC-Moderate sovereign endpoint set |

UIAO's compensating telemetry strategy (UIAO_138, `telemetry.py`) uses the
**management plane exclusively** — Graph management endpoints, Intune
compliance APIs, WMI/CIM locally — to reconstruct device health signals
blocked on the telemetry plane.

---

## 2. Capability Disposition Matrix

### 2.1 Classification schema

| Class | Definition |
|---|---|
| **Confirmed unavailable** | Explicit Microsoft documentation states feature is unavailable for GCC/GCC-Moderate |
| **Inferred (SILENTLY_BLOCKED)** | Portal accessible; data never arrives; blocked by boundary architecture per reverse-inference rule |
| **Restricted** | Available but with reduced fidelity, reduced retention, or non-default configuration required |
| **Retention-limited** | Available but with mandatory data purge that truncates forensic depth |
| **Available** | Fully functional within GCC-Moderate boundary |

### 2.2 Full capability matrix

#### Real-time network and path analytics

| Capability | Service | Class | Boundary mechanism | KSI impact | FINDING |
|---|---|---|---|---|---|
| **Informed Network Routing (INR)** | M365 Network Connectivity | Confirmed unavailable | Explicitly restricted to WW Commercial | KSI-MLA, KSI-CMT | FINDING-001 |
| **Network Connectivity assessment portal** | M365 Admin | Inferred SILENTLY_BLOCKED | Portal accessible; path-quality signals require telemetry to commercial endpoints | KSI-MLA | FINDING-001 |
| **Call Quality Dashboard (CQD)** | Teams | Available (retention-limited) | EUII data purged at 28 days; aggregate metrics available indefinitely | KSI-MLA | — |
| **Teams Network assessment tool** | Teams | Available | Management-plane tool; no cross-boundary telemetry | — | — |
| **Azure Monitor ARC server metrics** | Azure Monitor | Inferred SILENTLY_BLOCKED | Data Collection Rules route to commercial Azure Monitor Log Analytics; 403 from ARM in GCC-Moderate | KSI-MLA, KSI-CMT | — |
| **SD-WAN path-quality feedback** | Third-party / M365 | Confirmed unavailable | INR is the API surface; INR unavailable blocks all vendor SD-WAN feedback loops | KSI-MLA | FINDING-001 |

#### Identity and access real-time signals

| Capability | Service | Class | Boundary mechanism | KSI impact |
|---|---|---|---|---|
| **Identity Protection ML risk scoring** | Entra ID P2 | Inferred SILENTLY_BLOCKED | ML risk engine runs in commercial multi-tenant; GCC-Moderate receives degraded or delayed risk signals | KSI-IAM |
| **Continuous Access Evaluation (CAE)** | Entra ID | Restricted | CAE revocation signals degrade in fidelity; real-time token revocation latency is higher in GCC-Moderate | KSI-IAM |
| **Conditional Access named-location telemetry** | Entra ID | Restricted | Geolocation enrichment uses commercial GeoIP; cross-boundary flow constrained by AU-3 | KSI-IAM |
| **Sign-in risk real-time evaluation** | Entra ID P2 | Restricted | Real-time risk evaluation present; confidence interval reduced vs. commercial (smaller ML training corpus) | KSI-IAM |
| **Microsoft Authenticator fraud detection** | Entra ID | Inferred SILENTLY_BLOCKED | Fraud-detection ML runs in commercial analytics; GCC-Moderate telemetry routing incomplete | KSI-IAM |
| **SSPR and MFA usage analytics** | Entra ID | Available | Management-plane reporting; no cross-boundary dependency | — |

#### Device and endpoint analytics

| Capability | Service | Class | Boundary mechanism | KSI impact |
|---|---|---|---|---|
| **Endpoint Analytics (standard)** | Intune | Available | Management-plane telemetry; Graph API reachable | KSI-MLA |
| **Endpoint Analytics (Advanced tier)** | Intune | Inferred SILENTLY_BLOCKED | Advanced ML anomaly detection routes through commercial analytics | KSI-MLA |
| **Intune behavioral analytics** | Intune | Inferred SILENTLY_BLOCKED | Behavioral heuristics require telemetry plane cross-boundary flow | KSI-CMT |
| **Windows Update for Business compliance** | Intune / WUfB | Available | Management-plane reporting via Graph | KSI-CMT |
| **Device Locations (Intune network fence)** | Intune | Confirmed unavailable (government) | Explicit 403 from `/deviceManagement/managedDeviceLocations` endpoint in GCC-Moderate | KSI-IAM |
| **Windows Autopilot deployment analytics** | Intune | Restricted | Available; EUII retention constraints apply | KSI-CMT |
| **Azure Arc enrollment health** | Azure Arc | Available | Management-plane; ARC control plane accessible in GCC-Moderate | KSI-CMT |

#### Audit, logging, and SIEM

| Capability | Service | Class | Boundary mechanism | KSI impact |
|---|---|---|---|---|
| **Unified Audit Log (UAL) — Standard** | Purview Audit | Retention-limited | 180-day cliff; Premium required for 1-year / 10-year retention | KSI-MLA |
| **Unified Audit Log (UAL) — Premium** | Purview Audit | Available | Full forensic depth with Premium license | KSI-MLA |
| **MailItemsAccessed events** | Exchange Online | Available | E5/G5 or Purview Premium required; newly available in GCC | KSI-MLA |
| **Non-interactive sign-in logs** | Entra ID P2 | Available | Must be explicitly enabled in diagnostic settings; NOT on by default | KSI-MLA |
| **Service-principal sign-in logs** | Entra ID P2 | Available | Must be explicitly enabled; NOT on by default | KSI-MLA |
| **Managed-identity sign-in logs** | Entra ID P2 | Available | Must be explicitly enabled; NOT on by default | KSI-MLA |
| **Sentinel ingestion from all above** | Microsoft Sentinel | Available | Connector-dependent; all above route correctly once enabled | KSI-MLA |
| **Microsoft Adoption Score** | M365 Admin | Confirmed unavailable | Explicitly documented unavailable for GCC, GCC High, DoD | KSI-PIY |
| **Microsoft 365 Usage Analytics (Power BI)** | M365 Admin | Available (restricted) | GCC-specific connector required; Marketplace template missing variant | KSI-PIY |

#### Behavioral and DLP analytics

| Capability | Service | Class | Boundary mechanism | KSI impact |
|---|---|---|---|---|
| **Purview DLP (policy enforcement)** | Purview | Available | Policy engine runs within boundary | KSI-SVC |
| **Purview DLP behavioral analytics** | Purview | Restricted | Cross-correlation analytics reduced; enrichment from commercial pipeline constrained by AU-3 | KSI-SVC |
| **Insider Risk Management (IRM)** | Purview | Restricted | IRM scoring engine in GCC-Moderate; ML training corpus smaller than commercial | KSI-MLA |
| **Communication Compliance** | Purview | Available | Within boundary; no commercial telemetry dependency | KSI-SVC |
| **Office diagnostic telemetry (Required)** | M365 Apps | Available | Required diagnostic tier transmitted to GCC-Moderate endpoint | KSI-MLA |
| **Office diagnostic telemetry (Optional)** | M365 Apps | Restricted | Optional tier suppressed by default; explicit opt-in required; constrained by AU-2 | KSI-MLA |
| **Copilot/AI prompt-response telemetry** | M365 Copilot | Restricted | Constrained by SI-4/AU-2/AU-3; audit logs available but behavioral analytics suppressed | KSI-MLA |

#### Power Platform and low-code

| Capability | Service | Class | Boundary mechanism | KSI impact |
|---|---|---|---|---|
| **Power Apps / Automate audit events** | Power Platform | Available | Unified audit log coverage available; no native Sentinel connector | KSI-MLA |
| **Power BI activity log** | Power BI | Available | Management-plane event log; Graph API accessible | KSI-MLA |
| **Power Platform DLP policy analytics** | Power Platform | Restricted | Portal available; automated analytics reduced vs. commercial | KSI-SVC |
| **Dynamics 365 security events** | Dynamics 365 | Restricted | Application Insights dependency; security-relevant events limited | KSI-MLA |

---

## 3. Mandate Impact Analysis

### 3.1 CISA BOD 25-01 — Implementing Secure Practices for Cloud Services

| Requirement | GCC-Moderate alone | Gap | With compensating controls |
|---|---|---|---|
| Asset inventory | Partial (Intune management-plane complete; non-enrolled devices missed) | Non-enrolled device blind spot | UIAO OrgPath + in-boundary telemetry closes |
| Authentication visibility | Partial (sign-in logs must be manually enabled; not on by default) | Default config miss | Diagnostic settings enforcement via UIAO substrate |
| Conditional Access coverage | Available | None structural; configuration discipline required | UIAO KSI-009 rule enforces |
| Behavioral anomaly detection | Below intent ("rapid detection") | No commercial ML risk engine equivalent | Agency SIEM with custom KQL / UEBA overlay |
| Continuous monitoring cadence | Met for log categories; not met for behavioral | ML risk scoring latency | ADR-043 CA-7 Pathway 1 + Sentinel health probe |

### 3.2 OMB M-22-09 — Moving the U.S. Government Toward Zero Trust Cybersecurity Principles

ZTMM maturity ceiling for each pillar without agency compensating controls:

| Pillar | GCC-Moderate ceiling | Blocking gap | With agency analytics |
|---|---|---|---|
| **Identity** | Initial | Identity Protection ML risk (SILENTLY_BLOCKED); CAE degraded fidelity | Advanced |
| **Devices** | Initial | Endpoint Analytics Advanced (SILENTLY_BLOCKED); behavioral analytics blocked | Advanced |
| **Networks** | Initial | INR unavailable (FINDING-001); CQD 28-day EUII purge | Advanced (3PAO SD-WAN/SASE) |
| **Applications** | Initial → Advanced | Office Optional diagnostic suppressed; Copilot telemetry constrained | Advanced |
| **Data** | Initial → Advanced | Adoption Score unavailable; DLP behavioral analytics reduced | Advanced |
| **Visibility & Analytics** | Initial → Advanced | All above compound | Advanced |
| **Automation** | Initial | Real-time CAE; automated risk response latency | Advanced |

**Net assessment:** GCC-Moderate alone positions agencies at or near Initial in
all seven ZTMM pillars.  OMB M-22-09's Advanced-tier target by 2026 requires
an agency-built compensating analytics layer.

### 3.3 OMB M-21-31 — Improving the Federal Government's Investigative and Remediation Capabilities

| Tier | Requirement | Status in GCC-Moderate |
|---|---|---|
| **Tier 0** (Minimum) | Basic event logging enabled | Met by default |
| **Tier 1** | Additional event categories | Met with manual diagnostic settings configuration |
| **Tier 2** | Extended categories + SIEM ingestion | Met with Sentinel; sign-in log categories must be explicitly enabled |
| **Tier 3** (Maximum) | Complete logging breadth + rapid access | **Partially met**: UAL 180-day cliff without Premium; non-interactive/service-principal logs not default-on |

**Key gap:** M-21-31 Tier 3's "rapid access" intent requires behavioral observability
that GCC-Moderate's boundary-constrained telemetry does not provide by default.
Achieving Tier 3 in GCC-Moderate requires: (1) Purview Audit Premium for
retention depth; (2) all non-interactive/SP/MI log categories explicitly enabled;
(3) Sentinel workspace correctly routing all categories.

### 3.4 FedRAMP 20x — RFC-0005 and KSI themes (RFC-0006/0014)

| KSI theme | GCC-Moderate gap | Impact on 20x continuous monitoring |
|---|---|---|
| **KSI-IAM** | Identity Protection ML risk degraded; CAE fidelity reduced | Real-time identity risk assessment incomplete; affects KSI-IAM-SUS (suspicious activity response) |
| **KSI-MLA** | Adoption Score unavailable; non-interactive logs not default; UAL 180-day cliff | Continuous monitoring cadence met for log-based KSIs; behavioral completeness below intent |
| **KSI-CMT** | Azure Monitor ARC metrics blocked; Intune behavioral analytics blocked | Change-management observability reduced for ARC-enrolled servers |
| **KSI-CNA** | Endpoint Analytics Advanced blocked | Cloud-native architecture posture assessment incomplete |
| **KSI-SVC** | DLP behavioral analytics reduced | Service configuration deviation detection reduced |
| **KSI-INR** | No real-time ML-driven incident detection | Incident response relies on log-based alerting, not behavioral anomaly |
| **KSI-SCR** | Limited supply-chain telemetry from commercial pipeline | Supply-chain posture assessment relies on static inventory, not behavioral |

**The 20x framework-to-product gap** (FINDING-002): FedRAMP 20x changes how
compliance is assessed — it does not ship new telemetry features into GCC-Moderate.
Until Microsoft files a 20x-aligned package for GCC-Moderate, agencies must
satisfy KSI evidence requirements using the telemetry that the boundary permits,
supplemented by agency-side compensating controls.

### 3.5 TIC 3.0 — Three-Way Compliance Conflict

This is the most structurally intractable gap.  GCC-Moderate cannot simultaneously
satisfy TIC 3.0, CISA ZTMM, and FedRAMP 20x continuous monitoring from
Microsoft-native telemetry alone.

**Conflict axis 1 — TIC 3.0: Inspection Point Without Inspectable Flow**

TIC 3.0 requires CASB inspection of cloud traffic with policy decisions
referencing identity, geolocation, and device posture.  However:

- Microsoft 365 telemetry routes to Azure Commercial multi-tenant endpoints
  that **bypass the agency TIC inspection point**.
- The agency can inspect what flows through TIC, but cannot make TIC 3.0
  policy decisions using signals the boundary keeps from reaching the TIC.
- The CASB has partial context; Microsoft has the full signal context but it
  lives outside the authorized boundary.

**Conflict axis 2 — ZTMM: Posture Verification at Initial Tier**

ZTMM Advanced requires continuous device posture verification and real-time
identity risk evaluation.  The boundary blocks the telemetry that drives both:

- Device posture relies on Endpoint Analytics Advanced (SILENTLY_BLOCKED)
  and Intune behavioral analytics (SILENTLY_BLOCKED)
- Identity risk relies on Identity Protection ML (SILENTLY_BLOCKED) and
  full-fidelity CAE (Restricted)
- Without compensating controls, **both remain at Initial tier**

**Conflict axis 3 — FedRAMP 20x: Clean-Boundary Assumption**

FedRAMP 20x's continuous-monitoring model assumes the authorization boundary
is both coherent and fully observable.  GCC-Moderate is:

- **Observable for control logging** (UAL, Entra diagnostic logs, Defender alerts)
- **Not observable for behavioral/ML analytics** (Identity Protection, Endpoint
  Analytics Advanced, DLP behavioral, Insider Risk ML)

RFC-0005's "rapid detection" intent (20x's continuous-monitoring premise)
requires behavioral observability the current boundary architecture does not
provide without agency-side augmentation.

**Finding shape (canon):**

```yaml
finding_id:              GCC-BOUNDARY-3WAY-001
finding_class:           compliance-conflict
severity:                P1
mandates_affected:
  - TIC-3.0
  - CISA-ZTMM
  - FedRAMP-20x
boundary:                gcc-moderate
root_cause:              >
  SI-4/AU-2/AU-3/SC-7 boundary controls structurally restrict the outbound
  telemetry flows that TIC 3.0, ZTMM Advanced, and FedRAMP 20x continuous
  monitoring all require.  No single configuration change resolves the
  conflict; it requires the MAS 2026 boundary scope refinement path or
  agency-built compensating controls.
remediation_path:        MAS-2026 (boundary scope refinement per RFC-0005)
compensating_controls:
  - agency-side Sentinel KQL analytics
  - 3PAO-validated SD-WAN/SASE for TIC 3.0 posture signals
  - UIAO in-boundary telemetry (management-plane collection)
  - UIAO drift engine for log-based KSI evidence
```

---

## 4. Vendor-Specific Real-Time Reporting Impact

### 4.1 Microsoft — GCC-Moderate sovereign cloud

Microsoft is the primary vendor affected.  The table below maps each Microsoft
service to its real-time reporting capability in GCC-Moderate vs. commercial.

| Service | Commercial real-time capability | GCC-Moderate status | Delta |
|---|---|---|---|
| **Entra ID (Identity Protection)** | ML risk score updated in near-real-time on every sign-in | Degraded — smaller ML training corpus; commercial pipeline unavailable | Latency + confidence reduction |
| **Entra ID (CAE)** | Token revocation propagates in < 60 seconds | Degraded — revocation latency higher; not all apps CAE-capable in GCC | Latency increase |
| **Microsoft Sentinel** | Real-time ingestion from all M365 workloads | Available — but requires explicit diagnostic settings for sign-in categories | Configuration-gated |
| **Defender for Endpoint** | Real-time EDR telemetry, ML-driven alerts | Available — Defender for Endpoint GCC has full EDR capability | None |
| **Defender for Office 365** | Real-time email detonation, Safe Links | Available | None |
| **Defender for Identity** | Real-time AD lateral-movement detection | Available | None |
| **Intune (compliance)** | Real-time compliance state via management plane | Available | None |
| **Intune (behavioral analytics)** | ML-driven anomaly detection in device behavior | SILENTLY_BLOCKED | Full capability lost |
| **Purview DLP** | Real-time policy enforcement | Available | None |
| **Purview DLP (behavioral)** | ML cross-correlation, insider risk signals | Restricted | Reduced confidence |
| **Microsoft Teams (CQD)** | Real-time call quality monitoring with EUII | Available (28-day EUII retention) | Forensic depth limited |
| **INR / SD-WAN integration** | Real-time path-quality feedback loop | Confirmed unavailable | Full capability lost |
| **M365 Adoption Score** | Tenant-wide adoption and productivity analytics | Confirmed unavailable | Full capability lost |
| **Azure Monitor (ARC servers)** | Real-time metric and log collection from ARC | SILENTLY_BLOCKED | Full capability lost |

### 4.2 Third-party SD-WAN vendors (Cisco, VMware, Palo Alto, Juniper, etc.)

SD-WAN vendors that integrate with Microsoft's Informed Network Routing API
to optimize M365 traffic paths are **entirely blocked** in GCC-Moderate.
The INR API is the only Microsoft-provided mechanism for vendors to receive
path-quality feedback for M365 workloads.

Impact:
- SD-WAN appliances cannot receive Microsoft-authenticated traffic-quality
  signals for Teams/Exchange routing decisions
- Path optimization relies on synthetic probes rather than Microsoft-sourced
  telemetry
- TIC 3.0 traffic steering based on M365 path quality is unavailable

Mitigation path: Agency-operated network monitoring (ThousandEyes, SolarWinds,
or equivalent) deployed within the authorized boundary, providing equivalent
path-quality signals without crossing the telemetry boundary.

### 4.3 Third-party UEBA / SIEM vendors (Splunk, IBM QRadar, Exabeam, etc.)

UEBA vendors that enrich events with Microsoft's Identity Protection ML risk
signals face the same constraint.  The Microsoft Graph Identity Protection API
(`/riskyUsers`, `/riskDetections`) is available in GCC-Moderate, but:

- The underlying ML model runs in commercial Azure; GCC-Moderate tenants
  receive the model's **output** but the model is trained on commercial
  telemetry, not GCC-specific behavioral baselines
- The confidence interval of risk scores is demonstrably lower in GCC-Moderate
  due to the smaller training corpus
- Real-time behavioral enrichment (user-behavior baselining from Entra signals)
  requires the UEBA to supplement with agency-side signals rather than rely on
  Microsoft's commercial corpus

### 4.4 Third-party DLP / CASB vendors (Netskope, McAfee MVISION, Zscaler, etc.)

CASB vendors face the inspection-point problem described in §3.5 Conflict Axis 1.

- Inline CASB can inspect traffic flowing through the agency network
- **Microsoft-to-Microsoft flows** (e.g., Teams traffic between Microsoft
  datacenters) bypass the inline CASB
- Signal-based CASB integration (API mode) can read M365 audit logs, but
  behavioral ML enrichment from Microsoft's commercial DLP analytics is
  unavailable

---

## 5. Sentinel Evidence Pipeline — Completeness Scorecard

The UIAO Sentinel probes (`sentinel_probe.py`) test seven evidence pipeline
conditions that underpin the KSI evidence surface.  This scorecard reflects
the **baseline state** of a correctly licensed but minimally configured
GCC-Moderate tenant.

| Product / Symptom | Baseline score | Primary gap | Impact on KSI |
|---|---|---|---|
| Entra ID (SYMPTOM-01) | **75/100** | NonInteractive/SP/MI sign-in logs not on by default | KSI-IAM, KSI-MLA |
| Exchange Online (SYMPTOM-02) | **70/100** | MailItemsAccessed requires operationalization | KSI-MLA |
| SharePoint Online | **65/100** | File access audit latency; detailed activity off by default | KSI-MLA |
| Microsoft Teams | **55/100** | CQD/QER outside Sentinel; PSTN/Direct Routing incomplete | KSI-MLA |
| Microsoft Intune (SYMPTOM-04) | **60/100** | Manual diagnostic settings; Win32-detection filtering required | KSI-CMT |
| Defender for Endpoint | **85/100** | Best-in-class coverage within boundary | KSI-MLA, KSI-CNA |
| Defender for Office 365 | **80/100** | Strong coverage | KSI-SVC |
| Defender for Identity | **80/100** | Strong coverage | KSI-IAM |
| Defender for Cloud Apps | **70/100** | API-mode partial; inline CASB bypass risk | KSI-SVC |
| Purview Audit (SYMPTOM-02) | **60/100** | 180-day cliff; Premium required for Tier 3 forensic depth | KSI-MLA |
| Microsoft Sentinel | **75/100** | Dependent on all above being correctly wired | KSI-MLA |
| Power Platform (SYMPTOM-07) | **45/100** | No native Sentinel connector; unified audit only | KSI-MLA |
| Dynamics 365 | **40/100** | Application Insights dependency; limited security events | KSI-MLA |
| Microsoft Stream | **25/100** | Very limited event coverage | — |
| Windows Autopilot | **30/100** | EUII retention constraints; management-plane only | KSI-CMT |

**Overall baseline pipeline completeness: ~63/100**

Each SYMPTOM-level gap reduces KSI-MLA evidence completeness.  The aggregate
impact: without explicit remediation of all seven SYMPTOM conditions, a
GCC-Moderate tenant cannot satisfy the KSI-MLA completeness requirement for
FedRAMP 20x continuous monitoring.

---

## 6. Compensating Control Strategy

### 6.1 Tier 1 — Configuration remediation (no new software required)

These gaps close through explicit configuration changes within the tenant:

| Gap | Action | UIAO automation |
|---|---|---|
| Non-interactive sign-in logs not on | Enable via Entra Diagnostic Settings | KSI-001 rule + UIAO KSI evaluate |
| Service-principal sign-in logs not on | Enable via Entra Diagnostic Settings | KSI-001 rule |
| Managed-identity sign-in logs not on | Enable via Entra Diagnostic Settings | KSI-001 rule |
| MailItemsAccessed not operationalized | License check + enable E5/G5 or Purview Premium | UIAO conmon check |
| UAL 180-day cliff | Upgrade to Purview Audit Premium | Agency procurement action |
| CA policy scope gaps | Review and fix per UIAO KSI-009 | KSI-009 rule |

### 6.2 Tier 2 — Agency-side analytics overlay (additional tooling required)

These gaps require the agency to build or procure analytics that substitute
for the blocked Microsoft commercial signals:

| Blocked capability | Compensating approach | UIAO support |
|---|---|---|
| Identity Protection ML risk (SILENTLY_BLOCKED) | Custom Sentinel analytics rules + UEBA behavioral baselining from Entra sign-in logs | `uiao scuba evaluate`; custom KQL templates |
| INR / SD-WAN path quality (unavailable) | Agency-operated synthetic monitoring (ThousandEyes equivalent) within boundary | UIAO network boundary probe records gap in FINDING-001 |
| Endpoint Analytics Advanced (SILENTLY_BLOCKED) | In-boundary telemetry via `InBoundaryTelemetry` (WMI/CIM + Graph management) | `uiao.adapters.modernization.gcc_boundary_probe.telemetry` |
| Azure Monitor ARC metrics (SILENTLY_BLOCKED) | ARC management-plane queries via ARM (control-plane available) | UIAO ARC readiness adapter |
| ZTMM Advanced tier | Sentinel KQL analytics suite + custom UEBA rules | UIAO KSI evaluation pipeline |
| TIC 3.0 policy signals | 3PAO-validated SASE/CASB with inline inspection + agency-side enrichment | UIAO boundary probe documents gap |

### 6.3 Tier 3 — Boundary scope refinement (MAS 2026 path)

The long-term resolution is **RFC-0005 Minimum Assessment Scope refinement**.
Under 20x MAS, telemetry flows that route to Microsoft's commercial analytics
pipeline may be classified `metadata-out-of-scope` if they:

- Handle only metadata about substrate operations (not federal information)
- Do not likely impact C/I/A of federal information

This is the mechanism by which the structural conflict dissolves over time:
if Microsoft's commercial analytics pipeline is out of scope, the boundary
no longer constrains the telemetry flows, and GCC-Moderate telemetry parity
with commercial becomes achievable through normal licensing and configuration.

**Timeline:** Contingent on RFC-0010 publication (FedRAMP 20x best-practices
guidance) and Microsoft filing a 20x-aligned GCC-Moderate package.  Tracked
in FINDING-002 §4.

---

## 7. UIAO Substrate Response

### 7.1 What the substrate does today

| Substrate component | Gap addressed | Mechanism |
|---|---|---|
| `gcc_boundary_probe.probe` | Detects SILENTLY_BLOCKED and EXPLICITLY_UNAVAIL features | Graph/ARM probes at launch; emits DRIFT-BOUNDARY findings |
| `gcc_boundary_probe.sentinel_probe` | Tests seven evidence pipeline KQL conditions | KQL queries against Log Analytics; emits DRIFT-EVIDENCE-PIPELINE |
| `gcc_boundary_probe.telemetry` | Collects in-boundary device health | Graph management + WMI/CIM; produces DeviceHealthRecord[] |
| `ksi_emitter.py` | Tags OSCAL artifacts with KSI themes | Injects `fedramp:ksi-*` props on all 11 emission-map rows |
| `ksi/evaluate.py` | Evaluates 14 KSI rules against IR | Pass/fail/inconclusive/excluded verdicts |
| `evidence/collector.py` | Collects evidence from in-boundary sources | AzureSentinel, AzurePolicy, VulnScan collectors |
| `oscal/generator.py` | Generates POA&M + SSP from evidence | Deterministic OSCAL with SLA defaults |

### 7.2 What ADR-106 ratification adds

When ADR-106 moves from PROPOSED to ACCEPTED (after RFC-0010 publication +
stable Moderate KSI catalog + clean dry-run per UIAO_138 §7):

- All 11 emission-map artifacts carry `fedramp:ksi-*` props continuously
- DRIFT-EVIDENCE-STALE class fires on any artifact exceeding cadence budget
- Quarterly cATO package (artifact row 11) certifies KSI completeness
- Modernized pathway (§5.2 of UIAO_133) enables streaming KSI feed to agency
  authorization sponsor

### 7.3 What Microsoft filing a 20x package resolves

If and when Microsoft files a 20x-aligned GCC-Moderate package:

- INR unavailability may be resolved if Microsoft extends INR to sovereign cloud
  as part of 20x scope expansion
- Inherited KSI-CNA and KSI-SVC controls from Microsoft's P-ATO reduce the
  agency's substrate-side evidence burden
- The three-way conflict (§3.5) may partially resolve if MAS classification
  moves commercial analytics pipeline flows out of scope

Until then, all gaps in this document remain open agency-side obligations.

---

## 8. Summary Gap Register

The following table is the machine-readable summary for UIAO drift and
POA&M purposes.  Full evidence bundle finding shape in §3.5.

| Gap ID | Title | Class | Severity | Mandate(s) | KSI themes | Status |
|---|---|---|---|---|---|---|
| GCC-BND-001 | INR unavailable | Confirmed unavailable | P2 | M-22-09, TIC-3.0 | KSI-MLA | FINDING-001 open |
| GCC-BND-002 | Identity Protection ML degraded | SILENTLY_BLOCKED | P1 | M-22-09, FedRAMP-20x | KSI-IAM | Agency compensating |
| GCC-BND-003 | CAE fidelity reduced | Restricted | P2 | M-22-09 | KSI-IAM | Agency compensating |
| GCC-BND-004 | Endpoint Analytics Advanced blocked | SILENTLY_BLOCKED | P2 | M-22-09 | KSI-CNA, KSI-MLA | UIAO in-boundary telemetry |
| GCC-BND-005 | Intune behavioral analytics blocked | SILENTLY_BLOCKED | P2 | M-22-09 | KSI-CMT | UIAO in-boundary telemetry |
| GCC-BND-006 | Azure Monitor ARC metrics blocked | SILENTLY_BLOCKED | P2 | FedRAMP-20x | KSI-CMT, KSI-MLA | UIAO ARC probe |
| GCC-BND-007 | Sign-in log categories not default-on | Configuration gap | P1 | BOD-25-01, M-21-31 | KSI-MLA | Tier 1 remediation |
| GCC-BND-008 | UAL 180-day retention cliff | Retention-limited | P2 | M-21-31 | KSI-MLA | Purview Premium required |
| GCC-BND-009 | M365 Adoption Score unavailable | Confirmed unavailable | P3 | M-22-09 | KSI-PIY | No agency-side equivalent |
| GCC-BND-010 | Device Locations API unavailable | Confirmed unavailable | P2 | M-22-09 | KSI-IAM | No agency-side equivalent |
| GCC-BND-011 | Three-way compliance conflict | Structural | P1 | TIC-3.0, ZTMM, FedRAMP-20x | KSI-IAM, KSI-MLA, KSI-CMT | MAS 2026 long-term; UIAO compensates |
| GCC-BND-012 | SD-WAN path feedback loop blocked | Confirmed unavailable | P2 | TIC-3.0 | KSI-MLA | Agency synthetic monitoring |
| GCC-BND-013 | DLP behavioral analytics reduced | Restricted | P2 | M-22-09 | KSI-SVC | Accept + compensate |
| GCC-BND-014 | Sentinel pipeline completeness < 100% | Configuration gap | P1 | BOD-25-01, FedRAMP-20x | KSI-MLA | SYMPTOM remediation Tier 1 |
| GCC-BND-015 | Power Platform no native Sentinel connector | Architecture gap | P3 | BOD-25-01 | KSI-MLA | Unified audit workaround |

---

## 9. References

### Governance findings
- [FINDING-001 — FedRAMP GCC-Moderate INR unavailability](../../../../docs/findings/fedramp-gcc-moderate-informed-network-routing.md)
- [FINDING-002 — FedRAMP 20x Moderate Pilot active](../../../../docs/findings/fedramp-20x-moderate-pilot.md)

### UIAO canon
- [ADR-033 — GCC Boundary Drift Class and Compensating Controls Architecture](../adr/adr-033-gcc-boundary-drift-class.md)
- [ADR-043 — FedRAMP RFC-0026 CA-7 Integration](../adr/adr-043-fedramp-rfc-0026-ca7-integration.md)
- [ADR-106 — FedRAMP 20x Integration](../adr/adr-106-fedramp-20x-integration.md)
- [`UIAO_133`](./fedramp-20x-integration.md) — FedRAMP 20x operational mechanics
- [`UIAO_137`](./fedramp-cr26-ksi-mapping.md) — KSI rule ↔ CR26 catalog mapping
- [`UIAO_138`](./fedramp-3pao-evidence-interface.md) — 3PAO evidence interface
- `docs/customer-documents/compliance/B1-gcc-moderate-boundary-model.qmd`
- `docs/customer-documents/compliance/B1-1-gcc-moderate-three-way-conflict.qmd`

### Federal mandates
- [CISA BOD 25-01](https://www.cisa.gov/news-events/directives/bod-25-01)
- [OMB M-22-09 Federal Zero Trust Strategy](https://www.whitehouse.gov/wp-content/uploads/2022/01/M-22-09.pdf)
- [OMB M-21-31 Improving Investigative and Remediation Capabilities](https://www.whitehouse.gov/wp-content/uploads/2021/08/M-21-31-Improving-the-Federal-Government_s-Investigative-and-Remediation-Capabilities-Related-to-Cybersecurity-Incidents.pdf)
- [NIST SP 800-207 Zero Trust Architecture](https://csrc.nist.gov/publications/detail/sp/800-207/final)
- [FedRAMP RFC-0005 Minimum Assessment Scope Standard](https://www.fedramp.gov/rfcs/0005/)
- [FedRAMP RFC-0006 Phase One KSIs](https://www.fedramp.gov/rfcs/0006/)
- [FedRAMP RFC-0014 Phase Two KSIs](https://www.fedramp.gov/rfcs/0014/)
- [CISA Zero Trust Maturity Model v2.0](https://www.cisa.gov/zero-trust-maturity-model)
