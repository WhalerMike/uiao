---
document_id: UIAO_101
title: "UIAO Platform Overview"
version: "1.1"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-17"
boundary: "GCC-Moderate"
---

# UIAO Platform Overview

This layer describes the UIAO compliance platform — a system that can be extended, integrated, delegated, audited, and operated at scale.

## Positioning in the reconciled layer model (ADR-030 §2)

The UIAO platform described here is not itself a single layer — it
**spans** all four Tier A layers defined in ADR-030 §2 and draws on
the six-plane Control-Plane decomposition of Tier B. This table
names where each subsystem below sits in the reconciled model:

| Subsystem (this doc §) | Tier A layer(s) | Tier B plane(s) |
|---|---|---|
| §1 Compliance Data Lake | Authority Plane (storage authority) + Control Plane (curated zone) | Telemetry + Governance |
| §2 Compliance Query Language (CQL) | Control Plane | Governance |
| §3 Tenancy | Authority Plane (identity scoping) + Control Plane (policy binding) | Identity + Governance |
| §4 Compliance Orchestrator | Control Plane (scheduler + closed-loop automation) | Management + Governance |
| §5 Zero-Trust Integration | Overlay Fabric (enforcement) — detailed in [UIAO_120](./zero-trust.md) | Identity + Policy + Enforcement |

The four-layer model lives in prose (reader-facing); the six-plane
model lives inside Tier A's Control Plane (decision-surface
granularity). Both describe the same substrate at different
abstraction tiers.

---

## 1. Compliance Data Lake (Full Storage Model)

### Zones

**Raw Zone**
- SCuBA raw JSON
- Azure AD logs
- M365 configuration exports
- Defender settings
- Conditional Access policies
- Format: JSON, CSV, NDJSON
- Immutable, append-only

**Normalized Zone**
- UIAO IR objects
- Normalized evidence snapshots
- KSI evaluation inputs
- Drift snapshots

**Curated Zone**
- KSI results
- Control status views
- POA&M views
- OSCAL SSP/SAP/SAR/POA&M
- Auditor-ready datasets

### Partitioning
- `tenant_id/YYYY/MM/DD/source`
- Supports multi-tenant isolation
- Supports time-series queries
- Supports evidence lineage

### Governance
- Every object hashed
- Every object linked to provenance
- No deletes — only superseding versions
- Auditor API reads from curated zone only

---

## 2. Compliance Query Language (CQL)

### Query Types

**Control Status**
```
SHOW CONTROLS WHERE status = 'FAIL' AND severity >= 'Medium';
```

**Evidence Lookup**
```
SHOW EVIDENCE FOR CONTROL 'AC-21' SINCE '2026-04-01';
```

**Drift Queries**
```
SHOW DRIFT WHERE tenant = 'contoso' AND control = 'IA-2';
```

**POA&M Queries**
```
SHOW POAM WHERE status = 'Open' ORDER BY severity DESC;
```

### Execution Model
- CQL translates to graph queries (relationships) and data lake queries (time-series)
- Read-only by default
- Tenant-scoped

---

## 3. Multi-Tenant Isolation Model

### Isolation Dimensions

- **Data Isolation** — Per-tenant namespaces, encryption keys, evidence graphs
- **Execution Isolation** — Per-tenant job queues, SCuBA runs; no cross-tenant process reuse
- **Access Isolation** — Tenant claims in JWT; Auditor API tenant-scoped

### Deployment Models

- **Single-Tenant** — One UIAO instance per customer; maximum isolation; easiest for FedRAMP
- **Multi-Tenant** — Shared control plane with strict tenant boundaries in storage, identity, and logs

---

## 4. Compliance Orchestrator (Multi-Pipeline Scheduler)

### Responsibilities
- Schedule SCuBA runs
- Trigger: normalization, KSI evaluation, drift engine, OSCAL emitters, POA&M generator
- Notify operators and auditors

### Scheduling Model
- `0 2 * * *` — nightly SCuBA
- `0 3 * * *` — drift + POA&M update
- `0 4 * * 1` — weekly OSCAL regeneration

### Failure Handling
- Per-job retries
- Dead-letter queue
- Alerting hooks (email/webhook)
- Evidence of failure stored in provenance

---

## 5. Zero-Trust Integration Layer

### Zero-Trust Pillars Integrated

- **Identity** — MFA, Conditional Access, sign-in risk, user risk
- **Device** — Compliance state, Defender posture, OS patch level
- **Network** — Named locations, VPN/private access logs, session controls
- **Data** — DLP policies, sharing settings, sensitivity labels

### Integration Pattern
```
Zero-Trust Systems
  → Evidence Collectors
  → UIAO IR
  → Controls (NIST/FedRAMP)
  → OSCAL Outputs
  → Enforcement (EPL)
```

---

## What This Layer Enables

This platform layer transforms UIAO from a "compliance engine" into a **compliance platform** — one that can be:
- Extended with new evidence collectors and enforcement adapters
- Operated at multi-tenant scale
- Queried by auditors and operators through CQL
- Orchestrated across tenants on automated schedules
- Aligned to zero-trust architecture
