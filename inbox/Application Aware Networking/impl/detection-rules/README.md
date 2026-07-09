# In-Boundary Detection Rule Library — Vol VI Book 03

**Status:** Draft · **Date Code:** 2026-07-09 15:13 ET
**INTERNAL — NOT FOR PUBLIC DISTRIBUTION**

## What this is

The deployable analytics-rule library for **Vol VI Book 03 — Detection
Engineering**, the implementation counterpart to the **Vol III SIEM/XDR
Detection** architecture book. These rules reconstruct, **inside the agency's
own FedRAMP-authorized boundary**, the commercial-cloud ML detections that the
authorization boundary places out of scope — running over the telemetry the
Vol III connector fabric already lands.

They are production-shaped: entity mappings, MITRE ATT&CK tags, tuning
thresholds flagged `// TUNE:`, and a cross-reference to the architecture book
and the controls each operationalizes.

## The in-boundary principle

The boundary constrains the **destination** of raw telemetry, not the data.
These rules run over telemetry that stays inside the agency's own analytics
workspace — an authorized in-boundary SI-4 / AU-2/AU-3 monitoring flow. Every
component that touches identity-attributed or behavioral telemetry must itself
be authorized and in-boundary. Shipping this telemetry to an out-of-scope
analytics service recreates the flow the boundary forbids.

## Rule index

| File | Reconstructs (commercial signal) | Controls |
|---|---|---|
| `01-impossible-travel.yaml` | Identity Protection ML impossible-travel | SI-4, AC-7, IA-2 |
| `02-atypical-ip-asn.yaml` | Identity Protection atypical-IP / unfamiliar properties | SI-4, AC-2, IA-2 |
| `03-password-spray-lowandslow.yaml` | ML spray / low-and-slow (incl. non-interactive) | SI-4, AC-7 |
| `04-token-theft-session-anomaly.yaml` | Session-anomaly heuristic (triggers CAE-approximation response) | SI-4, AC-12 |
| `05-mass-label-removal-decrypt.yaml` | Sensitivity-label usage analytics | SI-4, AU-6, AC-4 |
| `06-dlp-override-pattern.yaml` | Behavioral-DLP override / near-miss richness | SI-4, AU-6, AC-4 |
| `07-anomalous-elevation-epm.yaml` | Endpoint privilege-management elevation analytics | SI-4, AC-6(9) |

## Prerequisites (Vol III connector fabric)

Minimum tables landing before these rules can fire:

- `SigninLogs`, `AADNonInteractiveUserSignInLogs`
- `IdentityInfo` (XDR connector) — atypical-IP baseline join
- `OfficeActivity` (unified audit / Management Activity API) — label + DLP ops
- `DeviceEvents` or an equivalent elevation-event source — EPM analytics

## Deployment

Files use the Microsoft Sentinel scheduled-analytics-rule YAML schema
(`kind: Scheduled`) — Sentinel is the **deployed example**; the mechanism is
portable to Splunk (SPL) / Elastic (EQL). Deploy through the SIEM repository
connection or `Az.SecurityInsights`, via the change-controlled pipeline (Vol VI
Book 00). **Tune every threshold against the agency's own baseline before
enabling.**

## Honest limits

- Minutes-to-hours, not commercial-minutes fidelity.
- No global threat intelligence — own-tenant only; TI joins bounded by the
  agency's subscribed feed.
- Rule 04 approximates session revocation at minutes, not sub-second (Vol VI
  Book 04 carries the response playbook it triggers).
- Detections rot; the operate-and-tune capability is the standing cost
  (validation in Vol VI Book 08).
