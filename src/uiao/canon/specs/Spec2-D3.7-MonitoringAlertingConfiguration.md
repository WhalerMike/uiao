---
deliverable_id: Spec2-D3.7
title: "Monitoring and Alerting Configuration"
spec: UIAO_136 / Spec 2 — HR-Agnostic Provisioning Architecture
phase: 3
status: Draft
version: 0.1
owner: Identity Architecture
created: 2026-05-01
updated: 2026-05-01
canonical_adrs:
  - ADR-003
  - ADR-040
canonical_docs:
  - UIAO_007
  - UIAO_136
upstream_deliverables:
  - Spec2-D3.1
  - Spec2-D3.2
  - Spec2-D3.3
  - Spec2-D3.5
  - Spec2-D3.6
sibling_deliverables:
  - Spec2-D2.6
  - Spec2-D3.8
boundary: GCC-Moderate
classification: Controlled
---

# Spec 2 — D3.7: Monitoring and Alerting Configuration

> **Status (v0.1, 2026-05-01):** Initial draft. v0.2 verification
> against Azure Monitor / Application Insights metric-name
> conventions and Microsoft Graph provisioning-log query syntax.

## 1. Purpose, Scope, and Reference

This deliverable is the canonical Monitoring & Alerting
specification called for in
[`UIAO_136`](../UIAO_136_priority1-transformation-project-plans.md)
§SPEC 2 → Phase 3 → D3.7:

> *Provisioning logs → Azure Monitor → alerts for: provisioning
> failures, quarantine threshold exceeded, sync cycle failures,
> agent offline, attribute mapping errors. Dashboard for
> provisioning health.*

D3.7 binds the observability hooks from D3.2 §8 + D3.3 §8 + D3.5
§9 + D3.6 §6 to actionable alerts, and specifies the dashboard
shape that ops teams use day-to-day.

### 1.1 Scope

In scope:

- The metric catalog (what gets emitted, by whom, at what cardinality).
- The log catalog (structured-log fields per component).
- The trace catalog (spans across the pipeline).
- The alert rule set (per-rule trigger condition, severity, routing).
- The dashboard template (provisioning-health single-pane-of-glass).
- The integration with D2.6 (quarantine state surfaces in the same
  alerting surface).
- Microsoft Graph provisioning logs ingestion.

Out of scope:

- The implementation of the monitoring backend (Azure Monitor /
  Application Insights / Log Analytics — UIAO targets the Azure
  stack but customer deployments may federate to Splunk or
  ELK).
- Per-tenant on-call rotation configuration (operational concern).
- Notification-channel implementation (email / Teams / PagerDuty /
  ServiceNow integrations are tenant-side).

## 2. Metric Catalog

The middleware (D3.2) and agents (D3.3) emit metrics. The
canonical metric set:

### 2.1 Middleware metrics

| Metric | Type | Cardinality | Description |
|---|---|---|---|
| `uiao.middleware.records.processed` | Counter | tenant, source, outcome | Records processed per cycle |
| `uiao.middleware.records.quarantined` | Counter | tenant, failure_reason | Quarantine emissions |
| `uiao.middleware.graph.calls` | Counter | tenant, method, status | bulkUpload calls |
| `uiao.middleware.graph.429` | Counter | tenant | Throttle-rejection events |
| `uiao.middleware.graph.5xx` | Counter | tenant | Transient server errors |
| `uiao.middleware.graph.latency` | Histogram | tenant, percentile | Per-call latency |
| `uiao.middleware.token.cache.hit` | Counter | tenant | Token reuse rate |
| `uiao.middleware.token.acquire` | Counter | tenant | Fresh-token acquisitions |
| `uiao.middleware.provenance.emissions` | Counter | tenant, event_type | Provenance writes |
| `uiao.middleware.provenance.failures` | Counter | tenant | Provenance emit failures |
| `uiao.middleware.batch.size` | Histogram | tenant | Records per batch |
| `uiao.middleware.cycle.duration` | Histogram | tenant | Per-sync-cycle wall time |

### 2.2 Provisioning agent metrics

| Metric | Type | Cardinality | Description |
|---|---|---|---|
| `uiao.agent.online` | Gauge | tenant, host | 1 = online, 0 = offline |
| `uiao.agent.last_sync` | Gauge | tenant, host | Unix timestamp of last successful sync |
| `uiao.agent.writeback.records` | Counter | tenant, host, outcome | AD writebacks |
| `uiao.agent.writeback.latency` | Histogram | tenant, host | AD write latency |
| `uiao.agent.writeback.failures` | Counter | tenant, host, ad_error_class | AD write failures |
| `uiao.agent.host.cpu` | Gauge | tenant, host | CPU utilization |
| `uiao.agent.host.ram` | Gauge | tenant, host | RAM utilization |
| `uiao.agent.host.disk_free` | Gauge | tenant, host | Free disk |

### 2.3 OrgPath cascade metrics

| Metric | Type | Cardinality | Description |
|---|---|---|---|
| `uiao.orgpath.cascade.stage4_to_5_lag` | Histogram | tenant | Stage-4 → 5 latency |
| `uiao.orgpath.cascade.stage5_to_6_lag` | Histogram | tenant | Stage-5 → 6 latency |
| `uiao.orgpath.cascade.stage4_to_8_lag` | Histogram | tenant | Stage-4 → 8 (device) latency |
| `uiao.orgpath.drift.findings` | Counter | tenant, drift_class | Drift engine findings |

## 3. Log Catalog

Structured logs follow D3.2 §7. The required fields per log
entry:

```yaml
timestamp: <ISO-8601 UTC>
level: DEBUG | INFO | WARN | ERROR
component: middleware | agent | drift-engine | provisioning-service
request_id: <UUID>
external_id: <employeeId or null>
tenant: <tenant id>
event: <event-type string>
outcome: success | partial | failure
latency_ms: <int>
graph_request_id: <Microsoft Graph response header>
detail: <component-specific structured payload>
```

PII handling: per D3.2 §7, logs MUST NOT contain HR PII beyond
`external_id` + `upn`. Detail blocks are scoped to non-PII
operational data.

Retention: logs retained per agency policy (typically 1–3 years
operational; up to 7 years for audit-class events). Provenance
records (D3.1 §8) have separate, longer retention.

## 4. Trace Catalog

OpenTelemetry traces span the per-record pipeline:

```
sync-cycle (root span)
  └─ ingest-batch (span per HR-source poll)
       └─ normalize-record (span per record)
            └─ orgpath-calc (span per record)
            └─ upn-generate (span per record; collision-check sub-span)
            └─ worker-type-classify (span per record)
            └─ scim-payload-build (span per record)
       └─ bulk-upload (span per Graph call)
            └─ token-acquire (span when cache miss)
            └─ rate-limit-wait (span when bucket exhausted)
            └─ graph-call (span per HTTP call)
       └─ provenance-emit (span per record)
       └─ retry-or-quarantine (span on non-success)
```

Trace sampling: 10% baseline; 100% on errors. Trace ids surface
in alert payloads for clickthrough investigation.

## 5. Alert Rule Set

### 5.1 Tier-1 alerts (informational; no on-call page)

| Rule | Condition | Routing |
|---|---|---|
| Quarantine rate elevated | `uiao.middleware.records.quarantined` rate > 1% over 1h | Operator queue (D2.6 dashboard) |
| Token cache miss rate elevated | `uiao.middleware.token.cache.hit` ratio < 90% over 1h | Operations channel |
| Agent version > 90 days behind latest | derived from agent telemetry | Operations channel |
| Cascade stage-4→5 lag p95 > 2× planning value (10 min → 20 min) | sustained 30 min | Operations channel |

### 5.2 Tier-2 alerts (page on-call)

| Rule | Condition | Routing |
|---|---|---|
| Provisioning failures sustained | `uiao.middleware.records.quarantined` rate > 5% over 15 min | On-call rotation |
| Quarantine SLA-breach count > 0 | derived from D2.6 quarantine store | On-call rotation |
| Sync cycle failure | `uiao.middleware.cycle.duration` returns failure outcome 2 cycles in a row | On-call rotation |
| Agent offline > 5 min | `uiao.agent.online` = 0 | On-call rotation |
| AD writeback failure rate > 5% | derived from `uiao.agent.writeback.failures` | On-call rotation |
| Attribute-mapping drift detected | `entra-mapping-drift` D2.6 event | On-call rotation |

### 5.3 Tier-3 alerts (page on-call + leadership)

| Rule | Condition | Routing |
|---|---|---|
| 2+ agents offline (writeback halted) | `uiao.agent.online` = 0 for ≥ 2 hosts | Identity engineering lead + on-call |
| Provenance emission failure | `uiao.middleware.provenance.failures` > 0 | Audit-integrity incident |
| Partial-disable detected | D2.3 step-1-succeeded-step-2-failed pattern | Security incident |
| Session-revoke failed | D2.3 `session-revoke-failed` failure | Security incident |
| Graph auth failure sustained | `uiao.middleware.graph.calls` outcome = auth-failure for 5 min | Security + on-call |

The tier-3 set is the integration point with D2.6 §5 escalation
tiers; the SLAs match.

## 6. Dashboard Template

The canonical UIAO provisioning-health dashboard:

| Panel | Source |
|---|---|
| Records processed (last 24h, by source) | `uiao.middleware.records.processed` |
| Quarantine queue depth (open, in-progress, by failure_reason) | D2.6 quarantine store |
| Quarantine SLA status (% in SLA, breach count) | D2.6 + alert state |
| Graph API latency (p50/p95/p99, last 1h) | `uiao.middleware.graph.latency` |
| Graph API call rate / 429 / 5xx | `uiao.middleware.graph.*` |
| Token cache hit ratio | derived |
| Agent health (per-host) | `uiao.agent.online` + `last_sync` |
| AD writeback latency p95 (per-host) | `uiao.agent.writeback.latency` |
| OrgPath cascade lag (p95 per stage) | `uiao.orgpath.cascade.*` |
| Drift findings (last 24h, by class) | `uiao.orgpath.drift.findings` |
| Recent quarantine SLA breaches (table) | D2.6 query |
| Active alerts | alerting backend |

The dashboard is exported as JSON per the Azure-Monitor /
Application-Insights workbook format and version-controlled in the
deployment repository.

## 7. Microsoft Graph Provisioning Logs Ingestion

Microsoft Entra emits its own provisioning logs through Azure
Monitor (when configured). UIAO MUST configure:

- Diagnostic settings on the Entra tenant to forward provisioning
  logs to a Log Analytics workspace.
- A KQL query layer that joins Microsoft-side logs with UIAO-side
  provenance records on `external_id` (Microsoft's
  `sourceIdentity` or the SCIM `externalId` field).
- The dashboard surface for cross-side reconciliation.

Microsoft-side provisioning logs catch failures the middleware
cannot observe directly (e.g., a payload accepted by bulkUpload
returning 202 Accepted but failing async processing in the
provisioning service). The cross-side reconciliation is essential
for D2.6 / D3.7 to produce a complete picture.

Per Microsoft Graph permissions verified at D3.1 v0.2:
`ProvisioningLog.Read.All` MUST be granted on the middleware's
service principal.

## 8. Failure Modes

D3.7-specific failures (delegated to D2.6):

| Failure | `failure_reason` |
|---|---|
| Monitoring backend ingestion failure | `monitoring-ingest-failed` (alert; not record-specific) |
| Provisioning-log diagnostic-setting drift | `provisioning-log-config-drift` (alert) |
| Alert-rule misconfiguration detected | manual / runbook-driven |

## 9. References

### 9.1 Primary canon

- [ADR-003](../adr/adr-003-api-driven-inbound-provisioning.md)
- [ADR-040](../adr/) — drift engine (consumes §6 dashboard).

### 9.2 UIAO docs

- [UIAO_136](../UIAO_136_priority1-transformation-project-plans.md) — §SPEC 2 → Phase 3 → D3.7.

### 9.3 Spec 2 sister deliverables

- [Spec2-D3.1](./Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md)
- [Spec2-D3.2](./Spec2-D3.2-IntegrationMiddlewareSpecification.md) — emits §2.1 metrics.
- [Spec2-D3.3](./Spec2-D3.3-ProvisioningAgentDeploymentArchitecture.md) — emits §2.2 metrics.
- [Spec2-D3.5](./Spec2-D3.5-OrgPathPopulationPipeline.md) — cascade metrics in §2.3.
- [Spec2-D3.6](./Spec2-D3.6-WritebackSpecification.md) — writeback metrics in §2.2.
- [Spec2-D2.6](./Spec2-D2.6-ErrorHandlingQuarantineSpecification.md) — alert tiers integrate.
- [Spec2-D3.8](./Spec2-D3.8-DataFlowSecurityAssessment.md) — security-posture monitoring.

### 9.4 Microsoft documentation (verification pending in v0.2)

- Microsoft Learn — Microsoft Entra ID provisioning logs.
- Microsoft Learn — Azure Monitor metric naming conventions.
- Microsoft Learn — Application Insights KQL query reference.

### 9.5 Compliance

- NIST SP 800-53 Rev 5: AU-2, AU-6 (audit review), AU-12 (audit generation), IR-4 (incident response).
