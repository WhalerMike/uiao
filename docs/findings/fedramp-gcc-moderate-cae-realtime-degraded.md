---
title: "FedRAMP GCC-Moderate — Continuous Access Evaluation real-time revocation degraded"
finding_id: "FINDING-006"
status: Awaiting-External-Remediation
severity: P1
created_at: "2026-04-27"
updated_at: "2026-04-27"
owner: "Michael Stratton"
related_canon: ["UIAO_003", "UIAO_109", "UIAO_113"]
related_ksi: ["KSI-SI-04", "KSI-AU-02", "KSI-AU-03", "KSI-SC-07", "KSI-AC-12", "KSI-IA-11"]
related_findings: ["FINDING-005"]
related_data: ["src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml"]
gap_matrix_rows:
  - cae-realtime-revocation-paths
supersedes: []
superseded_by: []
---

# FedRAMP GCC-Moderate — Continuous Access Evaluation real-time revocation degraded

## 1. Constraint

**Microsoft Entra Continuous Access Evaluation (CAE)** — the near-real-time
event stream between Entra ID and resource services (Exchange,
SharePoint, Teams) that enables sub-second token revocation on policy
events (password change, account disablement, device-compliance change,
location change, high-risk detection) — is **inferred degraded** in
GCC-Moderate by the FedRAMP Moderate authorization boundary architecture.

Basic CAE policy enforcement appears available with Entra ID licensing.
The **real-time signaling fidelity** required for sub-minute revocation
may be throttled by boundary inspection or proxies. CAE-capable client
behavior is signaled in tokens via the `xms_cc` claim, which agencies
can audit to confirm the path is **at least negotiated**, but not
necessarily that revocation is sub-second.

The token-theft exposure window moves from **<15 minutes** (commercial
cloud) to **up to the full 60–90 minute token lifetime** (GCC-Moderate),
which is the gap that drives MITRE T1550.001 (session persistence after
network change) into the *undetectable until expiry* class.

## 2. Evidence

### Boundary-inference rationale

No direct GCC-Moderate (.com) Microsoft documentation confirms or denies
real-time CAE fidelity. The xms_cc claim presence is documented as a
client-side capability indicator, not a service-side fidelity guarantee.

### Constraining controls

| Control | Constraint applied to CAE signaling |
|---|---|
| SI-4 | CAE event streams are continuous monitoring data. |
| AU-2 / AU-3 | CAE-triggering events (sign-in changes, device-compliance changes, high-risk detections) are audit events. |
| SC-7 | Cross-boundary signaling to non-GCC services constrained. |

### Live-assessment validation

Read the **`xms_cc` claim** in issued tokens (e.g., via JWT decoding of
captured Entra-issued tokens) to confirm whether CAE is at least
negotiated. Verify against the assessment plan's check 1.1:
"Reading the xms_cc claim presence in issued tokens to confirm whether
Continuous Access Evaluation (CAE) is at least negotiated." Negotiation
≠ sub-second revocation; document this distinction in the SSP.

## 3. Capability gap

### Telemetry signals lost / degraded

- Token issuance, refresh, and revocation events at sub-second cadence.
- Session state changes (revoked, invalidated) propagated in
  near-real-time.
- Policy-relevant event streams between Entra ID and resource services.
- Near-real-time enforcement of password changes, account disablement,
  device-compliance changes, location changes, and high-risk
  detections.

### What UIAO cannot do

1. **Cut compromised sessions in under 15 minutes** — the commercial-cloud
   sub-second revocation behavior is degraded toward the full token
   lifetime.
2. **Trigger automated containment on detected token theft** — the CAE
   event stream that drives this in commercial cloud is throttled.
3. **Reach Optimal maturity in the Identity or Automation &
   Orchestration ZTMM pillars** without compensating engineering.

### Compliance impact

- **CISA BOD 25-01**: not directly mandating CAE but closely aligned
  with continuous-enforcement intent.
- **OMB M-22-09 Identity pillar**: emphasizes continuous verification
  and rapid revocation. Without full CAE, agencies must compensate
  with **shorter token lifetimes** and strong monitoring.
- **ZTMM v2.0**: Identity + Automation & Orchestration pillars
  **difficult to push to Optimal**.

## 4. Proposed remedy

### Internal remedy

1. **Short access-token lifetimes** (60–90 minutes) to bound the
   exposure window without CAE.
2. **Frequent re-authentication and CA re-evaluation** triggers in
   Conditional Access policy.
3. **SIEM-triggered Graph API revocation scripts** for high-risk
   sign-in events — agency-side equivalent of the CAE event stream.
   Effective revocation latency: minutes-to-tens-of-minutes (better
   than full token lifetime, worse than sub-second).
4. **xms_cc claim audit** as a continuous health check (validate that
   CAE is at least negotiated end-to-end).

### External remedy

1. **Microsoft** confirms or extends CAE real-time fidelity to
   GCC-Moderate. Per `canon/data/fedramp-20x.yml`
   `gap_matrix_scope_effect`, CAE is classified **Neutral** under
   MAS-CSO — "not a scope problem; a cross-boundary signaling
   architecture problem. 20x does not address."
2. **MAS 2026** boundary refinement that places Entra real-time
   signaling outside the agency ATO scope — same mechanism as
   FINDING-005.

## 5. Related

- **FINDING-005** — Entra Identity Protection ML inferred blocked
  (sister Identity-pillar finding addressing the data-feed problem;
  CAE is the actuation problem).
- **MITRE Chain A** — T1550.001 (session persistence after network
  change) is the explicit attack pattern this finding maps to.
- **Gap matrix**: 1 row (`cae-realtime-revocation-paths`).
- **Canon spec**: `src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/capabilities.md` §5.4.
- **20x scope effect**: Neutral — 20x does not address.

## Status tracking

| Date | Status | Note |
|---|---|---|
| 2026-04-27 | Awaiting-External-Remediation | Initial landing |
