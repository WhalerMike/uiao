---
title: "FedRAMP GCC-Moderate — Entra Identity Protection ML risk scoring inferred blocked"
finding_id: "FINDING-005"
status: Awaiting-External-Remediation
severity: P1
created_at: "2026-04-27"
updated_at: "2026-04-27"
owner: "Michael Stratton"
related_canon: ["UIAO_003", "UIAO_109", "UIAO_113"]
related_ksi: ["KSI-SI-04", "KSI-AU-02", "KSI-AU-03", "KSI-SC-07", "KSI-AC-02"]
related_findings: ["FINDING-001", "FINDING-006"]
related_data: ["src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml"]
gap_matrix_rows:
  - entra-identity-protection-realtime-risk
  - cross-tenant-access-telemetry
supersedes: []
superseded_by: []
---

# FedRAMP GCC-Moderate — Entra Identity Protection ML risk scoring inferred blocked

## 1. Constraint

**Microsoft Entra Identity Protection** real-time ML risk scoring —
covering impossible-travel detection, atypical-IP, leaked-credentials
correlation, anonymous-IP / malware-linked-IP attribution, unfamiliar
sign-in properties, and the user-risk / sign-in-risk score timelines
that drive Conditional Access trust decisions — is **inferred blocked**
in GCC-Moderate by the FedRAMP Moderate authorization-boundary
architecture (SI-4 / AU-2 / AU-3 / SC-7).

This is the **highest-severity identity-pillar finding** in the gap
matrix. The detection-gap order of magnitude moves from **minutes**
(commercial cloud) to **hours-to-days** (GCC-Moderate). MITRE Chain B
(T1110.004 → T1068 → T1557 — credential stuffing → privilege escalation
→ adversary-in-the-middle) becomes effectively undetectable in
GCC-Moderate without compensating agency-side analytics.

## 2. Evidence

### Boundary-inference rationale

No direct GCC-Moderate (.com) Microsoft documentation confirms or denies
availability. Entra government docs that exist are Azure Government
(.us) — **not applicable** under the documentation purity rule
(`canon/compliance/reference/gcc-moderate-boundary-assessment/methodology.md`).

The **constraining controls**:

| Control | Constraint applied to Identity Protection telemetry |
|---|---|
| SI-4 | Raw user-identifiable sign-in and risk telemetry export to commercial multi-tenant analytics conflicts with in-boundary monitoring requirement. |
| AU-2 / AU-3 | Full-fidelity sign-in and risk events shipped off-boundary may exceed authorized audit export. |
| SC-7 | Continuous rich telemetry to multi-tenant analytics is exactly the cross-boundary flow SC-7 constrains. |

### Live-assessment validation

Inspect Entra Identity Protection blade in the Entra admin center for
the "Sign-in risk policy" and "User risk policy" surfaces; verify
whether risk-scored events appear with non-trivial latency or are
absent. Cross-check against `xms_cc` claim presence in issued tokens to
confirm whether continuous-evaluation paths are at least negotiated
(see FINDING-006 for the CAE subset).

## 3. Capability gap

### Telemetry signals lost

- **Per-sign-in evaluation data**: device, location, client app,
  network, sign-in risk, session details.
- **Identity Protection risk detections**: leaked credentials, atypical
  travel, anonymous IP, malware-linked IP, unfamiliar sign-in
  properties.
- **User-risk and sign-in-risk scores** and their evolution over time.
- **Cross-tenant access telemetry**: B2B and B2B-direct-connect events;
  cross-tenant access settings evaluations.

### What UIAO cannot do

1. **Detect impossible-travel and atypical-IP patterns in near-real-time
   ** — the ML-driven detection latency moves from minutes to hours/days.
2. **Detect low-and-slow credential spraying** — the volume-of-attempts
   ML model that flags this in commercial cloud is unavailable.
3. **Correlate cross-tenant anomalies** — the B2B / Direct-Connect
   telemetry that reveals external-collaboration insider patterns is
   absent.
4. **Feed continuous risk scores into Conditional Access** — CA falls
   back to static rules without behavioral context.

### Compliance impact

- **CISA BOD 25-01**: core logging achievable if logs export and retain;
  the directive's "rapid detection and investigation" intent is **harder
  to meet** without local analytics.
- **OMB M-22-09 Identity pillar**: continuous identity-behavior
  monitoring and risk-based access required. Agencies must implement
  equivalent agency-side risk scoring to credibly claim Advanced
  maturity. Optimal is **difficult without** equivalent continuous risk
  scoring.
- **ZTMM v2.0**: Identity pillar caps at **Initial → Advanced**.

## 4. Proposed remedy

### Internal remedy

1. **Graph API export** of sign-in and audit logs into Sentinel /
   Log Analytics with appropriate retention.
2. **Custom KQL risk rules** for impossible-travel, MFA-fatigue,
   anonymous-IP, leaked-credential correlation. Fidelity loss: no
   Microsoft proprietary continuously-tuned ML models; no real-time
   cross-tenant correlation; no vendor-supplied global threat-intel
   context. Detection-gap order of magnitude: commercial **minutes**;
   GCC-Moderate **hours-to-days**.
3. **Local risk-scoring overlay** that consumes the above and produces
   a continuous user-risk and device-risk signal feeding the Policy
   Engine — this is the canonical M-22-09 Identity-pillar response.
4. **Telemetry validation** via the
   `01-entra-diagnostic-completeness.kql` query
   (`gcc_boundary_probe/queries/`) to confirm all required diagnostic
   tables are routed.

### External remedy

1. **Microsoft** ships Entra Identity Protection ML to GCC-Moderate.
   Per `canon/data/fedramp-20x.yml` `gap_matrix_scope_effect`,
   sign-in-event-driven ML is **unfavorable** under MAS-CSO — sign-in
   events handle federal customer data by routine and fail prong (1)
   directly. External remedy is therefore **not on the MAS-CSO path**.
2. **MAS 2026** boundary refinement that excludes Microsoft's
   commercial identity-analytics pipeline from the agency ATO scope
   (changes the conversation from "can the data leave?" to "is the
   receiving service in scope of my ATO?").

## 5. Related

- **FINDING-001** — INR unavailable.
- **FINDING-006** — CAE real-time revocation degraded (sister
  Identity-pillar finding addressing the token-state problem).
- **MITRE Chain A & B** — both rely on Entra Identity Protection ML
  for first-stage detection. See
  `canon/compliance/reference/gcc-moderate-boundary-assessment/mitre-chains.md`.
- **Gap matrix**: 2 rows (`entra-identity-protection-realtime-risk`,
  `cross-tenant-access-telemetry`).
- **Canon spec**: `src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/capabilities.md` §5.1.
- **20x scope effect**: Unfavorable.

## Status tracking

| Date | Status | Note |
|---|---|---|
| 2026-04-27 | Awaiting-External-Remediation | Initial landing |
