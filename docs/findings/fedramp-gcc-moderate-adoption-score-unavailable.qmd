---
title: "FedRAMP GCC-Moderate — Microsoft Adoption Score unavailable"
finding_id: "FINDING-003"
status: Awaiting-External-Remediation
severity: P2
created_at: "2026-04-27"
updated_at: "2026-04-27"
owner: "Michael Stratton"
related_canon: ["UIAO_003", "UIAO_109", "UIAO_113"]
related_ksi: ["KSI-SI-04", "KSI-AU-02", "KSI-AU-03"]
related_findings: ["FINDING-001"]
related_data: ["src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml"]
gap_matrix_rows:
  - communication-patterns-chat-vs-email
  - content-collaboration-attachments-vs-cloudlinks
  - mobility-multiplatform-usage
  - meetings-participation
  - apps-health-version-channel
  - network-connectivity-scores-per-location
  - endpoint-readiness-baselines-tenant-wide
supersedes: []
superseded_by: []
---

# FedRAMP GCC-Moderate — Microsoft Adoption Score unavailable

## 1. Constraint

**Microsoft Adoption Score** — the tenant-level behavioral-baseline
report covering People Experiences (Communication, Meetings, Content
Collaboration, Teamwork, Mobility) and Technology Experiences (M365 Apps
health, Network connectivity, Endpoint readiness) — is **not available**
to tenants in Microsoft 365 GCC-Moderate, GCC High, or DOD. This is a
Microsoft-stated restriction documented on Microsoft Learn.

## 2. Evidence

### Primary source (Microsoft Learn)

- **[Microsoft Adoption Score report overview — Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-365/admin/adoption/adoption-score?view=o365-worldwide)**
  Direct quote:
  > "This feature isn't available in GCC High, GCC, and DOD tenants."

The "GCC" item in that list is GCC-Moderate, per Microsoft's own naming
convention.

### Live-assessment validation

In an agency tenant, navigate **Microsoft 365 Admin Center → Adoption
Score** and expect the explicit "not available" banner. This converts
the Microsoft-documented constraint into directly observed evidence per
the live-assessment plan in the Boundary Assessment §1.1.

## 3. Capability gap

### Telemetry signals lost

**People Experiences:**

- Communication patterns: ChatCount vs EmailCount ratios, reply-cadence
  baselines.
- Meetings participation: attendance, engagement-pattern shifts.
- Content Collaboration: PhysicalAttachments vs CloudLinks frequency.
- Mobility: multi-platform usage patterns.

**Technology Experiences:**

- Microsoft 365 Apps health: update-channel adoption, version telemetry
  over time.
- Network connectivity scores to Microsoft 365 (per location).
- Endpoint readiness baselines (tenant-wide).

Specific telemetry fields named: AppCrashCount, BlueScreenCount
(Endpoint Experience overlap), communication ratios, attachment-vs-link
frequency, multi-platform mobility flags.

### What UIAO cannot do

1. **Build identity-pillar baselines from communication patterns** — no
   "expected communication behavior" baseline for identity verification
   or insider-flight-risk signals.
2. **Detect bulk regression to legacy collaboration methods** as a DLP
   bypass signal — high-severity content-collaboration gap.
3. **Use unusual-platform usage as an account-takeover signal** — the
   mobility pillar feed is absent.
4. **Establish tenant-wide endpoint readiness baselines** for
   Zero-Trust policy tuning.

### Compliance impact

- **CISA BOD 25-01**: core logging unaffected. The "rapid detection and
  investigation" intent for behavioral anomalies is weakened.
- **OMB M-22-09**: Identity pillar continuous-monitoring intent
  partially affected (digital-disengagement / flight-risk signals
  unavailable).
- **ZTMM v2.0**: Identity, Data, Visibility & Analytics, and Devices
  pillars cap near Initial → Advanced without compensating analytics.

## 4. Proposed remedy

### Internal remedy

1. **Custom Power BI over Sentinel / Log Analytics** modeling the same
   ratios from raw audit-log events (Exchange message-trace,
   SharePoint cloud-link counts, Teams chat counts). Fidelity loss:
   no Microsoft-tuned thresholds; no cross-tenant context.
2. **Behavioral-baseline overlay** in `gcc_boundary_probe`'s analytics
   layer once the queries directory is wired into `probe.py` (Phase 5
   of the integration plan).
3. **Document the gap in the SSP** as agency-side risk; do not assert
   Adoption Score capability in any control narrative.

### External remedy

1. **Microsoft** ships Adoption Score to GCC-Moderate. Possible if the
   underlying telemetry is descoped under MAS-CSO-MDI (see
   `canon/data/fedramp-20x.yml` `gap_matrix_scope_effect` —
   *unfavorable* for behavioral baselines because user-behavior signals
   tied to identifiable communication fail prong 1).
2. **MAS 2026** boundary refinement removing Microsoft's commercial
   behavioral-analytics pipeline from the agency's authorization scope
   rather than blocking the data flow at the network boundary.

## 5. Related

- **FINDING-001** — INR unavailable (companion confirmed-unavailable
  finding; same Microsoft-documented pattern).
- **Gap matrix**: 7 rows (`communication-patterns-chat-vs-email`,
  `content-collaboration-attachments-vs-cloudlinks`,
  `mobility-multiplatform-usage`, `meetings-participation`,
  `apps-health-version-channel`,
  `network-connectivity-scores-per-location`,
  `endpoint-readiness-baselines-tenant-wide`).
- **Canon spec**: `src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/capabilities.md` §2.1.
- **Customer doc**: `docs/customer-documents/compliance/boundary-authorization/B1-gcc-moderate-boundary-model.qmd`.
- **20x scope effect**: Mixed to unfavorable — behavioral baselines
  tied to identifiable communication.

## Status tracking

| Date | Status | Note |
|---|---|---|
| 2026-04-27 | Awaiting-External-Remediation | Initial landing |
