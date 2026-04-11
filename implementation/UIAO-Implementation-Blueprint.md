# UIAO Implementation Blueprint Layer

## Overview

The UIAO Implementation Blueprint Layer is the point where the reference architecture becomes an implementable system. This is the layer engineering teams use to build the platform, and auditors use to understand its operational boundaries.

---

## 1. Module Boundaries (Logical Decomposition)

UIAO is decomposed into nine modules, each with strict responsibilities and no cross-contamination of concerns:

| Module | Responsibility |
|--------|---------------|
| Evidence Collector | Raw evidence ingestion from all sources |
| Normalizer | Raw evidence to IR conversion |
| KSI Evaluator | IR to KSI results evaluation |
| Evidence Bundler | KSI results to Evidence Bundle (Plane 3) |
| OSCAL Emitter | Evidence bundles to OSCAL SSP/SAP/SAR/POA&M |
| Drift Engine | Evidence snapshot comparison and drift detection |
| Enforcement Runtime | EPL policy evaluation and adapter execution |
| Orchestrator | Job scheduling and pipeline coordination |
| API Gateway | Operator, Auditor, Plugin, and Tenant API surfaces |

Each module has a strict interface contract. No module accesses another's internal state.

---

## 2. Service Boundaries (Runtime Decomposition)

UIAO is decomposed into six independently deployable services:

### 2.1 Evidence Service
- Runs collectors
- Normalizes evidence
- Writes to Raw/Normalized Zones

### 2.2 Evaluation Service
- Runs KSI engine
- Generates KSI results
- Writes to Curated Zone

### 2.3 Enforcement Service
- Executes EPL policies
- Calls enforcement adapters
- Writes post-enforcement evidence

### 2.4 OSCAL Service
- Generates SSP/SAP/SAR/POA&M
- Validates OSCAL JSON
- Publishes artifacts

### 2.5 Orchestrator Service
- Schedules SCuBA runs
- Schedules drift checks
- Schedules OSCAL regeneration
- Manages job queues

### 2.6 API Gateway
- Operator API
- Auditor API
- Plugin API
- Tenant API

Each service is stateless, with state stored in the compliance data lake or evidence graph.

---

## 3. API Contracts (Internal + External)

### 3.1 Internal API Contracts

| API | Direction | Contract |
|-----|-----------|----------|
| Evidence Service | In: raw source, Out: normalized IR | JSON schema |
| Evaluation Service | In: IR, Out: KSI results | JSON schema |
| Evidence Bundler | In: KSI results, Out: evidence bundle | JSON schema |
| OSCAL Service | In: evidence bundles, Out: OSCAL JSON | OSCAL schema |
| Drift Engine | In: snapshot N + N+1, Out: drift delta | JSON schema |
| Enforcement Runtime | In: EPL policy + IR, Out: enforcement result | JSON schema |

### 3.2 External API Contracts

| API | Consumers | Contract |
|-----|-----------|----------|
| Operator API | Operators, CLI | REST/JSON |
| Auditor API | Auditors, AOs | REST/JSON, read-only |
| Plugin API | Evidence/enforcement plugins | Plugin SDK contract |
| Tenant API | Tenant provisioning service | REST/JSON |

All APIs are versioned, documented, and schema-validated.

---

## 4. Deployment Topology (Single-Tenant + Multi-Tenant)

### 4.1 Single-Tenant Topology

    +----------------------------------+
    |  UIAO Instance (Tenant A)        |
    |  - All 6 services                |
    |  - Dedicated data lake           |
    |  - Dedicated evidence graph      |
    +----------------------------------+

Use case: FedRAMP, GCC-Moderate, maximum isolation.

### 4.2 Multi-Tenant Topology

    +--------------------------------------------------+
    |  UIAO Control Plane (Shared)                     |
    |  - Orchestrator Service                          |
    |  - API Gateway                                   |
    |  - Plugin Registry                               |
    +--------------------------------------------------+
    |  Tenant Partitions (per-tenant isolation)        |
    |  - Evidence Service                              |
    |  - Evaluation Service                            |
    |  - Enforcement Service                           |
    |  - Dedicated data lake partitions                |
    +--------------------------------------------------+

Use case: SaaS deployment, commercial cloud.

---

## 5. Scaling Model (Horizontal + Vertical)

### 5.1 Horizontal Scaling

| Service | Scaling Axis |
|---------|-------------|
| Evidence Service | Scale by number of sources |
| Evaluation Service | Scale by KSI rule count |
| Enforcement Service | Scale by enforcement frequency |
| OSCAL Service | Scale by tenant count |
| Orchestrator Service | Scale by job queue depth |
| API Gateway | Scale by request volume |

### 5.2 Vertical Scaling

| Service | Scaling Constraint |
|---------|--------------------|
| Evidence Service | Memory-bound (large raw evidence files) |
| Evaluation Service | CPU-bound (KSI evaluation) |
| OSCAL Service | I/O-bound (file generation) |

### 5.3 Stateless Design

All services are stateless. State is stored in:
- Compliance data lake (evidence, OSCAL)
- Evidence graph (relationships)
- Job queue (orchestration state)

---

## 6. Failure Domains & Observability Model

### 6.1 Failure Domains

| Domain | Impact | Isolation |
|--------|--------|-----------|
| Evidence Service failure | Evidence collection stops; no drift | Retry + dead-letter |
| Evaluation Service failure | KSI evaluation stops; last results preserved | Retry + dead-letter |
| Enforcement Service failure | Enforcement stops; findings preserved | Advisory-only fallback |
| OSCAL Service failure | OSCAL generation stops; evidence preserved | Retry |
| Orchestrator failure | Scheduling stops; jobs re-queued on recovery | Dead-letter + recovery |
| API Gateway failure | External access stops; internal ops continue | Load balancer failover |

No failure domain causes data loss — all evidence is write-once, append-only.

### 6.2 Observability Model

UIAO is fully observable via:

**Metrics:**
- Evidence ingestion rate
- KSI evaluation latency
- Drift detection count
- Enforcement success/failure rate
- OSCAL generation latency
- API request rate / error rate

**Logs:**
- Per-job execution logs
- Per-evidence provenance logs
- Per-enforcement action logs
- Per-API request logs

**Traces:**
- End-to-end pipeline traces (SCuBA to OSCAL)
- Per-tenant traces

All observability data is stored in the compliance data lake and is auditor-accessible via the Auditor API.

---

## Summary

The UIAO Implementation Blueprint Layer establishes:

1. **Module Boundaries** — 9 modules with strict, non-overlapping responsibilities
2. **Service Boundaries** — 6 independently deployable services
3. **API Contracts** — Internal and external API contracts, versioned and schema-validated
4. **Deployment Topology** — Single-tenant (FedRAMP/GCC-M) and multi-tenant (SaaS/commercial) topologies
5. **Scaling Model** — Horizontal scaling per service, stateless design, no shared mutable state
6. **Failure Domains & Observability** — Per-service failure isolation, full metrics/logs/traces

This is the layer that engineering teams use to **build UIAO**, and auditors use to **trust UIAO**.
