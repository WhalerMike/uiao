# Compound MITRE Chains

When the gap matrix rows compound, two attack chains become difficult
to detect in GCC-Moderate without dedicated agency analytics. This file
records the chains for reference; the per-row gap data lives in
[`canon/data/gcc-moderate-telemetry-gaps.yaml`](../../../data/gcc-moderate-telemetry-gaps.yaml).

## Compensating-control honesty

Every "compensating control" referenced in these chains assumes the
agency has stood up the necessary local analytics. Without that
investment, the gap is full.

## Chain A — Initial access → token theft → exfiltration

**Sequence:** T1190 → T1550.001 → T1048.003

| Stage | TTP | Blocked / degraded signal | Detection gap |
|---|---|---|---|
| Initial access via delayed-patched Intune device | T1190 | WUfB deployment health trends; regression telemetry | Commercial: hours. GCC-M: 3–7 day gap (weekly manual reports). |
| Token theft / session-cookie persistence past CAE absence | T1550.001 | CAE real-time revocation event streams | Commercial: <15 min. GCC-M: up to full token lifetime (60–90 min). |
| Exfiltration via label-stripped OneDrive link | T1048.003 | Sensitivity-label usage analytics; rich DLP behavioral context | Commercial: near-real-time. GCC-M: 24–72 hours, basic incident counts only. |

**End-to-end detection gap.** Commercial cloud: <30 minutes. GCC-Moderate without compensating analytics: days to weeks.

**Gap matrix rows:** `wufb-deployment-health-trends`, `cae-realtime-revocation-paths`, `sensitivity-label-usage-analytics`, `dlp-behavioral-richness`.

## Chain B — Credential stuffing → privilege escalation → MITM

**Sequence:** T1110.004 → T1068 → T1557

| Stage | TTP | Blocked / degraded signal | Detection gap |
|---|---|---|---|
| Credential stuffing without Identity Protection ML | T1110.004 | Identity Protection ML risk detections; aggregated sign-in anomaly models | Commercial: minutes. GCC-M: hours to days. |
| Privilege escalation without EPM analytics | T1068 | EPM operational analytics; elevation behavioral telemetry | Commercial: real-time anomaly flagging. GCC-M: 48+ hours via compliance snapshots. |
| Adversary-in-the-middle without INR path telemetry | T1557 | INR real-time path / latency / jitter telemetry | Commercial: sub-minute. GCC-M: not available. |

**End-to-end detection gap.** Commercial cloud: minutes. GCC-Moderate: undetected until manual investigation.

**Gap matrix rows:** `entra-identity-protection-realtime-risk`, `epm-elevation-operational-analytics`, `inr-realtime-path-metrics`.

## "Ghost compromise" scenario

A three-step concrete walkthrough of a nation-state-grade exfiltration
that stays below static-rule thresholds inside the GCC-Moderate
boundary:

1. **Identity.** Adversary signs in via residential proxy. Degraded
   global behavioral signals (Identity Protection ML inferred blocked)
   classify the session as low risk.
2. **Device.** Adversary uses BYOD with sideloaded grey-ware. Advanced
   compliance telemetry (Endpoint Analytics Advanced inferred
   unavailable) cannot see the grey-ware; the device reports
   compliant.
3. **Data.** Adversary performs low-and-slow exfiltration of
   sensitivity-labeled data. Suppressed Office "Optional" diagnostic
   telemetry hides the read-to-bulk-sync behavioral shift; rich DLP
   behavioral context is inferred blocked, so static DLP fires no
   alerts.

**Net.** A sophisticated actor can exfiltrate substantial data over
weeks without ever crossing a "high" severity threshold, because each
individual action stays below the static-rule line inside
GCC-Moderate.

**Gap matrix rows touching this scenario:** `entra-identity-protection-realtime-risk`, `device-boot-performance`, `app-reliability-crashcount-hangrate`, `resource-performance-cpu-memory`, `office-optional-diagnostic-data`, `dlp-behavioral-richness`, `sensitivity-label-usage-analytics`.

## Why the chains matter

The gap matrix presents per-row impacts. The chains show that the
**compound** detection latency is multiplicative across rows: each gap
extends the dwell time of an attacker who is already past the previous
stage. Closing one row helps; closing the chain requires either
compensating analytics across all stages or removal of the constraint
at the boundary level (the MAS 2026 / 20x scope refinement path).
