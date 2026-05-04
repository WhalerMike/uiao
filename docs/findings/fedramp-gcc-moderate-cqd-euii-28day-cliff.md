---
title: "FedRAMP GCC-Moderate — Teams CQD EUII 28-day forensic cliff"
finding_id: "FINDING-007"
status: Awaiting-Internal-Remediation
severity: P3
created_at: "2026-04-27"
updated_at: "2026-04-27"
owner: "Michael Stratton"
related_canon: ["UIAO_003", "UIAO_109", "UIAO_113"]
related_ksi: ["KSI-AU-11"]
related_findings: []
related_data: ["src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml"]
gap_matrix_rows:
  - cqd-euii-long-term
supersedes: []
superseded_by: []
---

# FedRAMP GCC-Moderate — Teams CQD EUII 28-day forensic cliff

## 1. Constraint

**Microsoft Teams Call Quality Dashboard (CQD) is available** in
GCC-Moderate, but **End-User Identifiable Information (EUII)** — the
fields that make CQD's call-quality data forensically useful, including
**BSSID, public IP, and subnet / building mapping** — is **purged after
28 days** as a Microsoft retention policy. This is a forensic-retention
constraint, not a feature-absence constraint.

This 28-day cliff combines with the longer Purview Audit Standard
180-day retention cliff (FINDING-008) and typical advanced-persistent-threat
dwell times (~45+ days) to produce an **incident-discovery dead zone**:
incidents discovered 45+ days after initial access find the EUII has
been purged, even though all other CQD telemetry remains queryable.

## 2. Evidence

### Primary sources

- **[Data and reports in CQD — Microsoft Learn](https://learn.microsoft.com/en-us/microsoftteams/cqd-data-and-reports)**
  — feature is supported; documentation does not exclude GCC-Moderate.
- **[Turn on and use Call Quality Dashboard — Microsoft Learn](https://learn.microsoft.com/en-us/microsoftteams/turning-on-and-using-call-quality-dashboard)**
  — operational guidance.
- **EUII retention** — 28 days is the documented retention horizon for
  EUII fields (BSSID, public IP, subnet/building).

### Modernization note

The legacy CQD portal has been deprecated. The GA pathway is
**QER v5.0 Power BI templates** (M365 Admin announcement, October 2024)
plus **Real-Time Analytics (RTA)** in the Teams admin center. Both
target the same underlying data, including the same 28-day EUII
retention.

## 3. Capability gap

### What is lost after 28 days

- Per-call **BSSID** — wireless association forensic anchor.
- Per-call **public IP** — attribution / geolocation reconstruction.
- Per-call **subnet / building mapping** — physical location of caller.

What remains queryable past 28 days: aggregate call-quality metrics,
non-EUII dimensions, packet-loss / jitter / RTT trends. Forensic
attribution at the individual-call level is what is lost.

### What UIAO cannot do

1. **Reconstruct caller location** for incidents discovered 28+ days
   after the fact — the building/subnet mapping is gone.
2. **Trace adversary infrastructure across calls** beyond the
   28-day window — public-IP attribution is purged.
3. **Validate impossible-travel claims** for older Teams sessions —
   the location-pinning data has aged out.

### Compliance impact

- **CISA BOD 25-01**: core call-quality logging unaffected.
  Long-tail forensic reconstruction is not directly mandated but is
  closely aligned with "rapid investigation" intent.
- **APT dwell-time gap**: typical APT dwell times of 45+ days exceed
  the 28-day EUII retention; forensic-grade reconstruction requires
  agency-side mitigation.
- **ZTMM v2.0**: Networks pillar — affects long-tail Optimal-tier
  forensic capability, not baseline operations.

## 4. Proposed remedy

### Internal remedy (load-bearing — this is fixable agency-side)

1. **Scheduled CQD export to Log Analytics with extended retention** —
   the canonical mitigation. QER v5.0 Power BI exports run on a
   regular cadence; pump the EUII fields into a dedicated
   long-retention table before they purge.
2. **Long-term forensic store** — 1+ year for general audit; 10 years
   for high-impact systems per the compensating-architecture stack
   (see
   `canon/compliance/reference/gcc-moderate-boundary-assessment/methodology.md`
   §13.2).
3. **Retention SLA** documented in the SSP under M-21-31 Tier 3
   logging — agencies can self-certify EUII retention well past 28
   days via this mechanism.

### External remedy

1. **Microsoft** extends EUII retention in GCC-Moderate. Possible but
   not on the MAS-CSO scope path — EUII fields handle federal customer
   data and are unfavorable under MAS-CSO-IIR.
2. **MAS 2026** boundary refinement — see FINDING-005 / FINDING-006
   for the same mechanism applied to identity / CAE telemetry.

## 5. Related

- **FINDING-008** — Purview Audit 180-day cliff (sibling
  retention-limited finding; same incident-discovery-dead-zone pattern
  at a longer time horizon).
- **Gap matrix**: 1 row (`cqd-euii-long-term`).
- **Canon spec**: `src/uiao/canon/compliance/reference/gcc-moderate-boundary-assessment/capabilities.md` §4.1.
- **20x scope effect**: Not specifically addressed (retention is
  inherent to commercial pipeline).
- **Compensating stack**: `methodology.md` §13.2 — long-term forensic
  store is item 7 of the canonical agency-side stack.

## Status tracking

| Date | Status | Note |
|---|---|---|
| 2026-04-27 | Awaiting-Internal-Remediation | Initial landing — internal CQD-export remedy is the load-bearing fix |
