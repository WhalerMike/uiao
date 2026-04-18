---
document_id: UIAO_203
title: "UIAO Information Security Continuous Monitoring (ISCM) Strategy"
version: "1.0"
status: Draft
classification: OPERATIONAL
owner: "Michael Stratton"
created_at: "2026-04-18"
updated_at: "2026-04-18"
boundary: "GCC-Moderate"
---

# UIAO Information Security Continuous Monitoring (ISCM) Strategy

> Closes open item **C2** in `core/CONMON.md` §10. Satisfies **NIST SP 800-137 §3.1** (Define ISCM strategy). Operational runbook referenced by `core/CONMON.md` §2.1 and by `ADR-032` (VDR Rev5 Open Beta adoption decision).

**Scope:** All modules of the consolidated `WhalerMike/uiao` monorepo under a single FedRAMP-Moderate posture. Applies whether UIAO adopts the FedRAMP VDR Rev5 Open Beta (see ADR-032) or continues under the traditional FedRAMP ConMon Playbook v1.0 model; differences between the two adoption paths are called out explicitly below.

---

## 1. Organizational risk tolerance

UIAO operates at **FedRAMP Moderate** impact (`UIAO-SSOT.md`; `VISION.md` pillar 1). Risk tolerance is framed accordingly:

| Risk class | Tolerance |
|---|---|
| Confidentiality | Low — the substrate handles governance artifacts that include tenant-identifying metadata. `tenant-id-hash` (SHA-256 truncation) is used instead of raw tenant IDs in evidence bundles (`CONMON.md` §4.1). |
| Integrity | Very low — canon artifacts are source-of-truth. Tamper-evident via GPG-signed commits and SHA-256 integrity manifests per evidence bundle (`VISION.md` pillar 4). |
| Availability | Moderate — canon is public; the authorization-data pipeline requires agency-AO review cadence but is not time-critical. |
| Privacy | Not applicable in-boundary — no federal customer PII is stored. |

Agency-AO-provided risk tolerance will supersede this posture once a FedRAMP authorization partner is engaged.

---

## 2. Scope and boundary

### 2.1 Boundary declaration

- **Primary boundary:** GCC-Moderate (Microsoft 365 SaaS tenant) — per `AGENTS.md` and `core/schemas/metadata-schema.json` `boundary` enum.
- **Sole commercial exception:** Amazon Connect Contact Center — documented per `AGENTS.md` and the `boundary-exception` frontmatter escape hatch.
- **Out of scope:** Any identity, telemetry, policy, or enforcement surface not registered in `core/canon/adapter-registry.yaml` or `core/canon/modernization-registry.yaml`.

### 2.2 Tenant identifiers (obfuscated)

Evidence bundles carry `tenant-id-hash` (SHA-256 of the M365 tenant GUID, truncated per `CONMON.md` §4.1). Raw tenant IDs are never committed to the repo. Phase 2+ adds Azure Government subscription IDs via the same hash pattern.

### 2.3 Asset classes monitored

Per the UIAO_003 adapter taxonomy × mission-class product:

- **Conformance adapters** (read-only posture assessment) — ScubaGear today; expansion slots reserved in `adapter-registry.yaml`.
- **Modernization adapters** (change-making integrations) — 9 active + 1 reserved per the repo README badge.
- **Substrate canon** — schemas, registries, ADRs, specs — monitored by substrate-walker (`impl/src/uiao/impl/substrate/walker.py`) and the blocking `substrate-drift.yml` CI workflow.

---

## 3. Monitoring frequencies (by control family)

Frequencies are stated at two tiers: the **authoritative cadence** (what the canonical source requires) and the **UIAO cadence** (what the substrate actually runs).

### 3.1 If UIAO is operating under the traditional ConMon Playbook model

| Control family | Authoritative cadence (Playbook v1.0) | UIAO cadence |
|---|---|---|
| AC, IA, SC, SI (identity + access + comms + integrity) | Monthly POA&M | Monthly via `conmon-scheduled.yml` (`CONMON.md` §5.2) — `cron: 0 2 1 * *` |
| RA (risk — vulnerability scans) | Monthly raw scan files | Monthly via ScubaGear conformance adapter (`CONMON.md` §5.1) |
| CA-7 (continuous monitoring) | Monthly deliverables + annual assessment | Monthly evidence bundles + annual 3PAO assessment hand-off |
| CM (configuration management) | On-change via SCR process | Per `CONMON.md` §6 — pre-change + post-change evidence snapshots |
| IR (incident response) | Event-triggered | `repository_dispatch` on the `scr-evidence-requested` event |

### 3.2 If UIAO has adopted the VDR Rev5 Open Beta (ADR-032 OPT IN)

VDR's supersession clause retires the POA&M cadence. Replacement cadences:

| VDR requirement | Cadence | UIAO implementation |
|---|---|---|
| VDR-TFR-PSD (Persistent Sample Detection) | ≥ every 7 days on representative samples of similar machine-based information resources | Weekly adapter runs against sampled tenant configurations |
| VDR-TFR-PDD (Persistent Drift Detection) | ≥ every 30 days on all information resources likely to drift | Monthly full-adapter runs; matches UIAO's substrate-drift rhythm |
| VDR-TFR-PCD (Persistent Complete Detection) | ≥ every 6 months on all information resources NOT likely to drift | Semi-annual full sweep with extended evidence-bundle retention |
| VDR-TFR-EVU (Evaluate Vulnerabilities Quickly) | ≤ 7 days from detection | Evaluation pipeline integrates with adapter finding normalization (`CONMON.md` §4.2 + §4 of UIAO_204) |
| VDR-TFR-PVR (Mitigation / Remediation Expectations) | Days-from-evaluation per the LEV/IRV/N-rating matrix — see UIAO_204 | Automated overdue-check in `vdr_aggregate.py`; GitHub issue raised on SLA breach |
| VDR-TFR-MAV (Mark Accepted Vulnerabilities) | ≥ 192 days unresolved → `accepted` | Automated state transition; requires `explanation` populated per VDR-RPT-AVI |
| VDR-TFR-MHR (Monthly Activity Report) | ≥ monthly, human-readable | `evidence/vdr-reports/monthly/YYYY-MM.md` (ADR-032 D5) |
| VDR-RPT-PER (Persistent Reporting) | Continuous, machine-readable | `evidence/vdr-reports/machine/current.json` (ADR-032 D5), subject to the FedRAMP ADS process |

---

## 4. Roles and responsibilities

Per FedRAMP ConMon Playbook §2 and VDR Agency Guidance §VDR-AGM-*.

| Role | Party | Primary responsibilities |
|---|---|---|
| **CSP (UIAO)** | Michael Stratton (`owner` of all canon) | Operate ISCM program; produce evidence; maintain POA&M (pre-VDR) or VDR reports (post-VDR); submit SCR packages. |
| **Agency AO** | TBD — agency partner | Accept or reject the authorization package; review ConMon deliverables; review SCRs. |
| **FedRAMP PMO** | FedRAMP | Policy authority; coordinate agency reuse via the FedRAMP secure repository (USDA Connect.gov for LI-SaaS/Low/Moderate). |
| **CISA** | CISA | Incident-report recipient (Playbook §Incident communications); KEV catalog publisher (VDR-TFR-KEV post-adoption). |
| **3PAO** | TBD — selected prior to initial assessment | Annual assessment (Playbook §4); on-demand security impact analysis review (Playbook §5). |
| **`canon-steward` subagent** | Automated (in-repo) | Author ISCM strategy updates; review reference-document drift per `CONMON.md` §9.2; open regression issues. |

UIAO does **not** host agency customer data. This strategy applies to UIAO's own posture as a CSP; once an agency authorization is in place, the matrix expands to cover agency-side duties (VDR-AGM-RVR / VDR-AGM-MAP / VDR-AGM-DRE / VDR-AGM-NFR on adoption of VDR).

---

## 5. Metrics and success criteria

### 5.1 Program-level KPIs

| KPI | Target | Measurement |
|---|---|---|
| Substrate drift detection latency | < 120 s per commit and per scheduled run | `VISION.md` pillar 5 — contract of the substrate-walker |
| ConMon evidence freshness (per adapter) | ≤ 31 days (pre-VDR); per-class VDR-TFR-PSD/PDD/PCD cadence (post-VDR) | Evidence-bundle `started-at` vs. now |
| POA&M submission on-time rate (pre-VDR) | 100% of monthly submissions on or before the agency-AO due date | Manual CSP attestation; logged in `poam/` tracking folder |
| VDR overdue rate (post-VDR) | 0% across the LEV/IRV/N-rating matrix | Automated in `vdr_aggregate.py` |
| KSI compliance score (cross-cutting) | ≥ 95% across 163 KSIs | `dashboard/conmon-dashboard.json` |
| Reference-document drift detection (NIST 800-137, Playbook, ScubaGear) | Monthly check, zero undetected drift | `CONMON.md` §9.1 three-track pattern |

### 5.2 Adoption-gate criteria

UIAO's ISCM strategy is considered **operational** (status transitions from `Draft` to `Current`) when:

1. The substrate-walker CI gate has been green on `main` for ≥ 30 consecutive days.
2. At least one conformance-adapter evidence bundle has been produced end-to-end via `conformance-run.yml`.
3. The monthly POA&M aggregation (pre-VDR) or the monthly Activity Report (post-VDR) has been produced and manually submitted once.
4. An agency AO is identified (even informally) as the intended ongoing-authorization partner.

---

## 6. Review and update cadence

Per NIST SP 800-137 §3.6. The strategy doc version-bumps **annually**, plus **on-change** whenever any of the following occurs:

- A new authoritative reference (NIST 800-137 update, FedRAMP Playbook update, VDR process revision, new Balance Improvement Release) is published.
- A new adapter class is added to UIAO (beyond the dual-axis taxonomy).
- The boundary changes (new cloud subscription, new commercial exception).
- An ADR supersedes or extends this strategy.

Change log at the bottom of this document is append-only.

---

## 7. References

| Authority | Local copy / source | Role |
|---|---|---|
| NIST SP 800-137 | `core/compliance/reference/nist-sp-800-137/NIST.SP.800-137.pdf` | ISCM lifecycle, Appendix D 11-domain taxonomy |
| FedRAMP ConMon Playbook v1.0 (2025-11-17) | `core/compliance/reference/fedramp-conmon-playbook/FedRAMP_Continuous_Monitoring_Playbook.pdf` | Rev5 cadence, POA&M, SCR, incident comms |
| FedRAMP VDR Rev5 process | External — https://fedramp.gov/docs/rev5/balance/vulnerability-detection-and-response/ | Optional Open Beta from 2026-02-02 |
| CISA ScubaGear | External — https://github.com/cisagov/ScubaGear | M365 SCuBA baseline assessment |
| CISA KEV catalog | External — CISA.gov | VDR-TFR-KEV reference (post-adoption) |
| `core/canon/adr/adr-025-continuous-monitoring-program.md` | In-repo | ConMon program architecture |
| `core/canon/adr/adr-028-monorepo-consolidation-gos-integration.md` | In-repo | Retires federal/commercial firewall |
| `core/canon/adr/adr-032-fedramp-vdr-rev5-open-beta.md` | In-repo | VDR adoption decision |
| `core/CONMON.md` | In-repo | Operational companion (Playbook model); partially superseded on VDR adoption |
| `core/canon/conmon/vdr-rev5-gap-map.md` (UIAO_204) | In-repo | Cross-walks VDR-* IDs to UIAO artifacts (conditional on VDR adoption) |

---

## 8. Change log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-04-18 | 1.0 | Initial draft (status `Draft`). Closes open item C2 in `CONMON.md` §10. Covers both traditional ConMon Playbook and VDR Open Beta cadences so the strategy survives the ADR-032 decision either way. Adoption-gate criteria in §5.2 — status promotes to `Current` once all four gates are met. | Claude (Cowork, session `claude/fedramp-continuous-monitoring-WXbxO`) |
