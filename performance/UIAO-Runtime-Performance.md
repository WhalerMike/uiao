# UIAO Runtime Optimization & Performance Engineering Layer

## Overview

The UIAO Runtime Optimization & Performance Engineering Layer covers how UIAO stops being "correct" and becomes fast, scalable, predictable, and cost-efficient across Commercial Cloud and GCC-Moderate. This is the layer engineering teams use to tune the system, and SREs use to guarantee SLAs.

Total pipeline target: **< 10 seconds for a full run**.

---

## 1. Pipeline Performance Model

UIAO defines strict latency budgets for each plane:

| Plane | Description | Target Latency |
|-------|-------------|---------------|
| Plane 1 | Evidence Collection | < 3s |
| Plane 2 | IR Normalization | < 1s |
| Plane 3 | KSI Evaluation | < 2s |
| Plane 4 | Evidence Bundle & OSCAL | < 2s |
| Total | End-to-end | < 10s |

---

## 2. Evidence Ingestion Optimization

### 2.1 Parallel Collectors

Each evidence source runs in its own async worker:
- SCuBA
- M365 Graph
- Azure AD
- Defender
- SaaS plugins

### 2.2 Batching

Batch Graph API calls by:
- Tenant
- Resource type
- Time window

### 2.3 Incremental Ingestion

Only fetch deltas when supported:
- M365 delta queries
- AAD delta tokens
- SaaS incremental APIs

### 2.4 Evidence Compression

Raw evidence stored as:
- Zstandard (ZSTD)
- Chunked by 1-4 MB

---

## 3. KSI Evaluation Optimization

KSI is the most compute-intensive part of UIAO.

### 3.1 Rule Grouping

Group rules by:
- Control
- Evidence type
- IR object type

This reduces redundant IR scans.

### 3.2 Vectorized Evaluation

Convert rules into vectorized operations:
- Boolean masks
- Set membership
- Range checks

### 3.3 JIT Compilation

Use:
- Python to C via Numba
- Or Rust micro-kernels for hot paths

### 3.4 Rule Short-Circuiting

If a FAIL is detected:
- Stop evaluating remaining rules
- Emit FAIL immediately

---

## 4. Drift Engine Optimization

Drift detection must be fast and sparse.

### 4.1 Delta-Based Drift

Compute drift only on:
- Changed IR objects
- Changed KSI results
- Changed control packs

### 4.2 Sparse Evaluation

If no IR change for a control:
- Skip re-evaluation
- Reuse cached KSI result

### 4.3 Drift Classification Cache

Cache:
- PASS -> PASS (benign)
- WARN -> WARN (stable)
- FAIL -> FAIL (persistent)

Only compute actual transitions.

---

## 5. OSCAL Generation Optimization

OSCAL generation is CPU-bound and JSON-heavy.

### 5.1 Fragment Caching

Cache:
- Control statements
- Component definitions
- Inventory items

### 5.2 Incremental OSCAL

Only regenerate:
- Controls affected by drift
- Controls affected by enforcement
- Controls affected by evidence changes

### 5.3 Parallel Artifact Generation

Generate SSP, SAP, SAR, and POA&M in parallel.

---

## 6. Caching Strategy

UIAO uses four cache layers.

| Cache Layer | Keyed By |
|-------------|----------|
| IR Cache | Evidence hash + schema version |
| KSI Cache | IR hash + rule version + control pack version |
| Evidence Bundle Cache | KSI hash + evidence schema version |
| OSCAL Cache | Evidence bundle hash + OSCAL fragment version |

Caches are invalidated deterministically.

---

## 7. Memory & Storage Model

UIAO uses a tiered storage model.

### 7.1 Raw Zone

- Compressed
- Immutable
- Retained per policy (e.g., 90 days)
- Used for re-evaluation and audit

### 7.2 Working Zone

- Current IR snapshot
- Current KSI results
- Active evidence bundles
- Active OSCAL artifacts

### 7.3 Archive Zone

- Compressed OSCAL archives
- POA&M history
- ATO package archives
- Retained per compliance policy

---

## Summary: What This Layer Provides

| Component | Optimization |
|-----------|-------------|
| Pipeline Performance Model | Latency budgets per plane, < 10s total |
| Evidence Ingestion | Parallelism, batching, incremental, compression |
| KSI Evaluation | Rule grouping, vectorization, JIT, short-circuiting |
| Drift Engine | Delta-based, sparse evaluation, classification cache |
| OSCAL Generation | Fragment caching, incremental, parallel artifact generation |
| Caching Strategy | Four-layer deterministic cache invalidation |
| Memory & Storage | Tiered zones: raw, working, archive |

This layer makes UIAO performant at scale, predictable for SREs, and cost-efficient for regulated environments.
