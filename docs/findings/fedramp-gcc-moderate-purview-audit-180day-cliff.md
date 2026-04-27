---
title: "FedRAMP GCC-Moderate — Purview Audit Standard 180-day retention cliff"
finding_id: "FINDING-008"
status: Awaiting-Internal-Remediation
severity: P2
created_at: "2026-04-27"
updated_at: "2026-04-27"
owner: "Michael Stratton"
related_canon: ["UIAO_003", "UIAO_109", "UIAO_113"]
related_findings: ["FINDING-007"]
related_data: ["src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml"]
gap_matrix_rows:
  - m365-usage-analytics-historical-pivots
supersedes: []
superseded_by: []
---

# FedRAMP GCC-Moderate — Purview Audit Standard 180-day retention cliff

## 1. Constraint

**Microsoft Purview Audit Standard** (E3 / G3 license tier) retains
audit log data for a maximum of **180 days**. **Audit Premium** extends
retention to **1 year**, with a **10-year add-on** available. The
GCC-Moderate licensing footprint typical of agency E3 / G3 deployments
creates a **forensic blind spot** when measured against typical
advanced-persistent-threat dwell times.

The 180-day cliff sits inside the symptom #10 catalog from the boundary
assessment §10.1: *"Audit Standard retains 180 days max; Premium
extends to 1 year (10-year add-on). E3 / G3 licensing creates a
forensic blind spot vs. APT dwell times."*

## 2. Evidence

### Primary source

- **[Microsoft Purview auditing solutions overview — Microsoft Learn](https://learn.microsoft.com/en-us/purview/audit-solutions-overview)**
  — Audit Standard 180-day retention; Audit Premium 1 year; long-term
  retention add-ons up to 10 years.

### Live-assessment validation

Query audit log data older than 180 days; if absent on Standard, the
gap is confirmed:

```kql
search in (AuditLogs, OfficeActivity)
  TimeGenerated < ago(180d)
| summarize Count = count() by bin(TimeGenerated, 30d)
```

If `Count` is zero for all bins older than 180 days while the
agency operates on Audit Standard, the cliff is in effect. (For agencies
already on Audit Premium or with a 10-year add-on, this finding does
not apply or applies at a longer horizon.)

## 3. Capability gap

### What is lost past 180 days (on Audit Standard)

- All Microsoft 365 unified-audit events: Exchange, SharePoint, OneDrive,
  Teams, Entra ID, Power Platform.
- Cross-product 12+ month historical pivots — covers gap-matrix row
  `m365-usage-analytics-historical-pivots`.
- Long-tail forensic reconstruction for APT-class dwell scenarios
  (45+ days to 12+ months).

### What UIAO cannot do

1. **Reconstruct multi-month attack timelines** — adversary actions
   prior to the 180-day window are no longer in unified audit.
2. **Detect "low and slow" attacks across months** — the trend
   analysis surface that exposes these attacks is unavailable past
   180 days.
3. **Build long-term access-shift insider-risk baselines** — the
   12+ month historical pivot data this depends on is purged.

### Compliance impact

- **OMB M-21-31 Tier 3 logging**: requires extended retention. **At
  Audit Standard, the directive's spirit is not met for the
  long-tail.** Premium or 10-year add-on (or agency-side long-term
  store) is required.
- **CISA BOD 25-01**: core requirement met for recent activity.
  "Rapid detection and investigation" intent for older incidents is
  weakened.
- **ZTMM v2.0**: Visibility & Analytics pillar — Advanced maturity
  achievable for recent windows; long-tail forensic capability
  requires Premium or compensating storage.

## 4. Proposed remedy

### Internal remedy (load-bearing)

Three options, in increasing cost:

1. **Sentinel / Log Analytics with long-retention archive tier** for
   audit log shipping. Cheapest path; audit data lives in agency
   storage at the agency's chosen retention SLA. This is the canonical
   item 7 of the compensating-architecture stack (long-term forensic
   store).
2. **Microsoft Purview Audit Premium upgrade** (1-year retention).
   Per-user license cost; gives in-product retention without
   agency-side pipeline build.
3. **Microsoft Purview Audit Premium with 10-year add-on**. Higher
   per-user cost; the only in-product option that meets the
   high-impact-system 10-year retention bar.

The compensating-architecture stack favors option 1 (Sentinel + long
retention) because it generalizes across all audit sources, not just
Purview, and produces a single-pane long-tail forensic store.

### External remedy

This is a Microsoft licensing-tier characteristic, not a boundary
constraint. **20x does not address it.** No external remedy on the
MAS-CSO path.

## 5. Related

- **FINDING-007** — CQD EUII 28-day cliff (sibling retention-limited
  finding; same forensic-cliff pattern, shorter horizon).
- **Gap matrix**: 1 row (`m365-usage-analytics-historical-pivots`).
- **Canon spec**: `src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/capabilities.md` §10 (Operational Findings, symptom 10).
- **Compensating stack**: `methodology.md` §13.2 — long-term forensic
  store is item 7.
- **OMB M-21-31**: this is the primary mandate driver.

## Status tracking

| Date | Status | Note |
|---|---|---|
| 2026-04-27 | Awaiting-Internal-Remediation | Initial landing — agency-side long-retention archive is the canonical fix |
