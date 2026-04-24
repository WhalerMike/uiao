---
document_id: UIAO_114
title: "UIAO High-Availability & Fault-Tolerance Layer"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-14"
boundary: "GCC-Moderate"
---

# UIAO High-Availability & Fault-Tolerance Layer

## Overview

The UIAO High-Availability & Fault-Tolerance Layer defines how UIAO becomes always-on, geo-resilient, and failure-tolerant without sacrificing determinism or provenance.

---

## 1. Availability Objectives and Failure Model

**Target Availability:**
- Commercial: 99.9%
- GCC-Moderate / regulated: 99.95%

**Primary Failure Modes:**
- Zone/region outage
- Data store degradation
- Orchestrator failure
- Plugin/enforcement blast radius
- Network partition between planes

All other design decisions in this layer exist to contain, absorb, or route around those failures.

---

## 2. Active-Passive Topology (Control Plane)

Control plane services:
- Evidence Service
- Evaluation Service
- Enforcement Service
- OSCAL Service
- Orchestrator
- API Gateway

**Pattern:**
- Active-passive per region, not active-active writes
- One primary region per tenant cohort, one standby region
- Writes only in primary; standby is read-only and warm

**Failover Trigger:**
- Health checks fail for N consecutive intervals
- Error budget for region exceeded
- Manual or automated promotion of standby

Determinism is preserved because only one writer region exists at a time.

---

## 3. Data Durability and Replication

**UIAO Data Zones:**
- Raw Zone (immutable evidence)
- Normalized Zone (IR)
- Curated Zone (KSI + evidence bundles)
- OSCAL Zone (SSP/SAP/SAR/POA&M)
- Metadata Store (jobs, tenants, versions)

**Replication Strategy:**

| Zone | Strategy |
|------|----------|
| Raw Zone | Multi-AZ, cross-region replicated; write-once, read-many |
| Normalized/Curated/OSCAL Zones | Multi-AZ, async cross-region; rebuildable from Raw Zone |
| Metadata Store | Strongly consistent in primary; async replicated to standby; promotion on failover |

Durability target: 11+ nines for Raw Zone, 9+ nines for others (rebuildable).

---

## 4. Plane-Level Fault Isolation

Each plane has its own failure domain and degradation mode:

| Plane | Degradation Mode |
|-------|------------------|
| Plane 1 (Ingestion) | Pause new ingestion; keep existing evidence; downstream planes operate on last known snapshot |
| Plane 2 (IR + KSI) | No new evaluations; last known KSI remains valid; drift engine pauses with no false positives |
| Plane 3 (Evidence Bundles) | OSCAL generation uses last valid bundles; provenance remains intact |
| Plane 4 (OSCAL) | Existing OSCAL artifacts remain available and verifiable; no partial outputs published |

This ensures graceful degradation instead of total failure.

---

## 5. Geo-Replication and Tenant Placement

**Tenant Placement Model:**
- Each tenant is assigned a home region and a backup region
- Evidence and OSCAL are logically tenant-scoped, physically sharded by region

**Geo-Replication Rules:**
- Evidence and OSCAL replicate home to backup
- Enforcement actions are never executed from backup until promotion
- On promotion, backup becomes the new home; a new backup is assigned

This keeps enforcement single-writer, even across regions.

---

## 6. Failover and Failback Procedures

### Failover (Primary to Standby)

1. Detect regional/control plane failure
2. Freeze writes in primary (if reachable)
3. Promote standby metadata store to primary
4. Promote standby services to active
5. Resume ingestion, evaluation, enforcement, OSCAL in new primary
6. Log and sign failover event for provenance

### Failback (Standby to New Primary)

1. Stabilize original region
2. Re-establish replication from current primary
3. Promote original region back (optional) or keep new primary
4. Re-run drift and OSCAL to ensure consistency

All transitions are logged, signed, and bound into provenance.

---

## 7. SLA, SLOs, and Error Budgets

**Key SLOs:**

| Metric | Target |
|--------|--------|
| Availability | 99.9% (Commercial) / 99.95% (GCC-Moderate) |
| Evidence freshness (M365/AAD) | < 15 minutes lag (normal) |
| Drift detection latency | < 5 minutes from evidence arrival |
| OSCAL regeneration latency | < 10 minutes after material change |

**Error Budget:**
- Defined per tenant cohort and per region
- When error budget is exhausted: freeze risky changes (control packs, plugins), prioritize reliability work over features

---

## 8. Disaster Recovery (DR) Posture

**Assumptions:**
- Total regional loss is rare but possible
- Raw Zone is the source of truth

**DR Strategy:**
1. Restore Raw Zone from cross-region copies
2. Rebuild IR, KSI, evidence bundles from Raw Zone
3. Regenerate OSCAL artifacts
4. Reconstruct provenance manifests (hashes remain valid)

**RPO (Recovery Point Objective):**
- Raw evidence: near-zero (async replication)
- Derived artifacts: rebuildable, so RPO is effectively bounded by rebuild time, not data loss

---

## Summary: What This Layer Provides

| Component | Purpose |
|-----------|--------|
| Availability Objectives | 99.9%-99.95% targets with defined failure modes |
| Active-Passive Topology | Single-writer control plane preserving determinism |
| Data Durability | Tiered replication with 11+ nines for Raw Zone |
| Plane-Level Fault Isolation | Graceful degradation per plane without false positives |
| Geo-Replication | Tenant placement with enforcement single-writer guarantee |
| Failover/Failback | Signed, provenance-bound transition procedures |
| SLA/SLOs/Error Budgets | Quantified targets with budget-driven freeze policies |
| Disaster Recovery | Raw Zone as source of truth with full rebuild capability |

---

## Next Layer

The next layer is the **UIAO Tenant & Environment Strategy Layer**, covering:
- Dev/stage/prod separation
- Sandboxes
- Canary tenants
- Feature flags
- Migration environments
