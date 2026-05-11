---
deliverable_id: Spec2-D5.6
title: "Provisioning Health Dashboard"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 5
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-02
updated: 2026-05-02
canonical_adrs:
  - ADR-003
canonical_docs:
  - UIAO_007
  - UIAO_136
upstream_deliverables:
  - Spec2-D3.7
  - Spec2-D5.5
sibling_deliverables: []
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D5.6: Provisioning Health Dashboard

> **Status (v0.1, 2026-05-02):** Initial canonical dashboard
> specification. Operationalizes the metrics + drift-finding +
> quarantine surfaces from D3.7 + D5.5 + D2.6 into a single
> ops-facing pane-of-glass.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Provisioning Health Dashboard
specification called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 5 → D5.6:

> *Ongoing monitoring dashboard: provisioning success rate,
> quarantine count, sync cycle duration, attribute drift count,
> orphaned account count.*

D5.6 is sister to D3.7 §6 (which sketches the dashboard). D5.6
specifies the canonical layout + per-panel queries + interaction
contract for the steady-state operator-facing pane.

### 1.1 Scope

In scope:

- The canonical dashboard layout (panel inventory).
- Per-panel data source + query.
- Filter / drill-down contract.
- Refresh cadence.
- Audience-specific views.
- Implementation-platform notes.

Out of scope:

- Per-platform implementation (Quarto / Application Insights
  Workbook / custom — tenant choice).
- Specific color schemes / branding (tenant choice).
- Dashboard implementations for non-Spec-2 surfaces.

## 2. Canonical Panel Inventory

The dashboard contains the following panels in canonical order:

### 2.1 Top-row — Overall health status

| Panel | Source | Query |
|---|---|---|
| Substrate state (single indicator: GREEN / YELLOW / RED) | derived | GREEN if no Sev 1/2 alerts open + quarantine within SLA + drift < threshold; YELLOW for elevated; RED for active incidents |
| Last successful sync cycle | provenance store | MAX(cycle_completed_at) where cycle_outcome = success |
| Open Sev 1 alerts (count) | alerting backend | COUNT alerts WHERE severity=1 AND status=open |
| Open Sev 2 alerts (count) | same | COUNT alerts WHERE severity=2 AND status=open |

### 2.2 Sync-cycle row

| Panel | Source | Query |
|---|---|---|
| Records processed (last 24h, by source) | metric `uiao.middleware.records.processed` | SUM by tenant, source, last 24h |
| Cycle duration p95 (last 7 days) | metric `uiao.middleware.cycle.duration` | percentile_cont(0.95) by day |
| Sync cycle success rate | derived | success-cycles / total-cycles per day |
| Last 10 cycle outcomes | provenance | most-recent 10 cycles, each with outcome + record count + duration |

### 2.3 Quarantine row

| Panel | Source | Query |
|---|---|---|
| Quarantine queue depth | quarantine store | COUNT WHERE status IN (open, in-progress) |
| Quarantine rate (% of records) | derived | quarantined-records / total-records-processed per cycle |
| Top failure_reason classes (last 7 days) | quarantine store | GROUP BY failure_reason, last 7 days |
| Quarantine SLA breach count | derived | COUNT WHERE escalation_state.level >= 1 |
| Quarantine triage time p50 / p95 | derived | percentile of (resolved_at - quarantined_at) |

### 2.4 Cascade-latency row

| Panel | Source | Query |
|---|---|---|
| OrgPath cascade stage-4→5 lag p95 | metric `uiao.orgpath.cascade.stage4_to_5_lag` | percentile_cont(0.95) last 24h |
| Stage-5→6 lag (policy targeting) p95 | metric `uiao.orgpath.cascade.stage5_to_6_lag` | same |
| Stage-4→8 lag (device propagation) p95 | metric `uiao.orgpath.cascade.stage4_to_8_lag` | same |
| Cascade stages exceeding 2× planning value (alert count) | derived | COUNT WHERE lag > 2 × planning value |

### 2.5 Graph API row

| Panel | Source | Query |
|---|---|---|
| Graph call rate (per minute) | metric `uiao.middleware.graph.calls` | RATE last 5 min |
| Graph 429 rate | metric `uiao.middleware.graph.429` | same |
| Graph 5xx rate | metric `uiao.middleware.graph.5xx` | same |
| Graph latency p95 | metric `uiao.middleware.graph.latency` | percentile last 1h |
| Token cache hit ratio | metric (derived) | (cache.hit / (cache.hit + acquire)) last 1h |

### 2.6 Provisioning agent row (hybrid deployments only)

| Panel | Source | Query |
|---|---|---|
| Agent health (per-host) | metric `uiao.agent.online` | latest per host |
| AD writeback latency p95 (per host) | metric `uiao.agent.writeback.latency` | percentile last 1h |
| AD writeback failure rate (per host) | derived | failures / attempts per host last 1h |
| Days since agent version update | derived | today - latest-version-deployed-date |

### 2.7 Drift findings row (D5.5 surface)

| Panel | Source | Query |
|---|---|---|
| Open RULE-PROV-ZOMBIE findings (Sev 1) | drift findings | COUNT WHERE rule = RULE-PROV-ZOMBIE AND status = open |
| Open RULE-PROV-ORPHAN findings (Sev 2) | drift findings | same for ORPHAN |
| Open RULE-PROV-ATTR findings (Sev 3) | drift findings | same for ATTR |
| Open RULE-PROV-ORGPATH-STALE findings | drift findings | same for ORGPATH-STALE |
| Drift findings trend (last 30 days, by class) | drift findings | COUNT GROUP BY rule, day |

### 2.8 Provenance integrity row

| Panel | Source | Query |
|---|---|---|
| Provenance emissions (last 24h) | metric `uiao.middleware.provenance.emissions` | SUM last 24h |
| Provenance failures (last 24h) | metric `uiao.middleware.provenance.failures` | SUM last 24h |
| Provenance store reachable (single indicator) | health probe | GREEN if recent successful write; RED otherwise |

### 2.9 Recent activity table (bottom)

Per-record activity table (most recent 50 events) showing:
`external_id`, `event_type`, `outcome`, `timestamp`,
`failure_reason` (if applicable). Filterable by source / event
type / outcome.

## 3. Filter + Drill-Down Contract

The dashboard supports the following filters at the top:

| Filter | Effect |
|---|---|
| Time range | All panels reflect the selected range |
| HR source | All panels filter to records from selected source(s) |
| Worker type | Filters to records of selected worker type(s) |
| Department / OrgPath prefix | Filters to records under selected OrgPath prefix |

Drill-down: clicking any panel opens the underlying data:

- Panel showing aggregate counts → table of constituent records.
- Panel showing latency p95 → distribution histogram + per-record
  list.
- Panel showing a finding count → finding detail page.

## 4. Refresh Cadence

| Panel category | Refresh |
|---|---|
| Top-row indicators | 1 min |
| Sync-cycle row | 5 min |
| Quarantine row | 5 min |
| Cascade row | 5 min |
| Graph API row | 1 min |
| Agent row | 1 min |
| Drift findings row | 15 min |
| Provenance integrity | 1 min |
| Recent activity table | 30 sec (auto-refresh; user-controllable) |

## 5. Audience-Specific Views

The dashboard supports three saved views:

### 5.1 Operator view (default)

All panels visible. Used for daily monitoring + on-call.

### 5.2 Governance view

Subset focused on governance-relevant signals:

- Quarantine row (full).
- Drift findings row (full).
- Cascade-latency row.
- Per-source breakdown panels.
- Activity table filtered to non-success outcomes.

### 5.3 Executive view

High-level rollup:

- Top-row substrate state.
- Quarantine rate (single number; trend).
- Drift findings count by severity.
- Sync cycle success rate (single number; trend).

Used for steering committee / agency CISO briefings.

## 6. Implementation-Platform Notes

The canonical UIAO target is **Application Insights Workbook**
(matches D3.7 §7 ingestion pattern). Quarto-rendered dashboards are
acceptable for tenants standardizing on the existing UIAO Quarto
pipeline; they refresh on a slower cadence (typically scheduled
build).

The dashboard JSON / .qmd source is committed to the deployment
repository at `dashboards/spec2-provisioning-health.{json,qmd}` and
validated in CI per the deployment's dashboard-integrity gate.

## 7. Versioning

The dashboard layout is canon; tenant-specific extensions are
permitted (additional panels) but core panels MUST remain. Adding
a core panel requires:

1. Spec update (this document).
2. Reference dashboard updated.
3. Cross-deployment migration plan (if existing dashboards need
   panel additions).

## 8. Cross-Reference With D3.7

D3.7 §6 sketches the dashboard. D5.6 specifies it. The §2 panel
inventory in this document supersedes / extends the D3.7 sketch.

If a future revision of D3.7 changes its §6 inventory, the canonical
posture: **D5.6 wins** for the steady-state operator dashboard;
D3.7's sketch was an early reference.

## 9. References

### 9.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)

### 9.2 UIAO docs

- [UIAO_007](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 5 → D5.6.

### 9.3 Spec 2 sister deliverables

- [Spec2-D3.7 — Monitoring & Alerting Configuration](./Spec2-D3.7-MonitoringAlertingConfiguration.md) §6 — original dashboard sketch.
- [Spec2-D5.5 — Provisioning Drift Detection Rules](./Spec2-D5.5-ProvisioningDriftDetectionRules.md) — drift findings surface in §2.7.
- [Spec2-D2.6 — Error Handling & Quarantine Specification](./Spec2-D2.6-ErrorHandlingQuarantineSpecification.md) — quarantine surface in §2.3.

### 9.4 Compliance

- NIST SP 800-53 Rev 5: AU-2, AU-6, CA-7 (continuous monitoring), CP-2 (contingency planning — the dashboard is the operator's situational-awareness surface).
