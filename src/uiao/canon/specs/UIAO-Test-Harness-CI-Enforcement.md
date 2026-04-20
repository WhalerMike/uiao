---
document_id: UIAO_104
title: "UIAO Test Harness & CI Enforcement Layer"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-14"
boundary: "GCC-Moderate"
---

# UIAO Test Harness & CI Enforcement Layer

## Overview

The UIAO Test Harness & CI Enforcement Layer ensures the spec-driven tests become enforced, gated, repeatable, and non-bypassable. This is the layer that turns UIAO from "provably correct in theory" into provably correct in every commit.

---

## 1. Test Harness Architecture

UIAO test harness is composed of four test classes, each with strict boundaries.

### 1.1 Unit Tests

- Pure functions
- KSI rule evaluation
- IR normalization
- Evidence bundle generation
- OSCAL fragment assembly

Goal: correctness of smallest units.

### 1.2 Property-Based Tests

- Lattice monotonicity
- Determinism under random fact permutations
- Drift classification invariants
- Provenance closure invariants

Goal: mathematical correctness.

### 1.3 Golden-File Tests

Golden files represent canonical outputs for:
- IR snapshots
- KSI results
- Evidence bundles
- OSCAL artifacts

Goal: detect regressions instantly.

### 1.4 Integration Tests

- Full pipeline: Plane 1 -> Plane 4
- Multi-tenant isolation
- Plugin sandboxing
- Enforcement runtime

Goal: system correctness.

---

## 2. Golden-File Infrastructure

Golden files are stored under:

```
uiao/tests/golden/
  ir/
  ksi/
  evidence/
  oscal/
```

Each golden file has:
- `input/` - raw evidence, config, control packs
- `output/` - expected IR/KSI/Evidence/OSCAL
- `manifest.json` - hashes and provenance

### 2.1 Golden-File Update Protocol

Golden files cannot be updated manually.

To update:
1. Engineer runs: `uiao dev golden --update`
2. Tool regenerates outputs
3. Tool compares against spec version
4. Tool opens PR with:
   - diff
   - spec references
   - justification

This prevents accidental drift.

---

## 3. CI Gating Rules

CI enforces non-negotiable gates. A PR cannot merge unless:

### 3.1 All Tests Pass

- Unit
- Property
- Golden
- Integration

### 3.2 Spec Compliance Passes

- Schema validation
- Semantic validation
- Determinism validation

### 3.3 No Unapproved Golden-File Changes

Golden diffs require:
- Spec reference
- Architecture approval
- Security approval (if enforcement-related)

### 3.4 Control Pack Compatibility Passes

- No breaking changes
- No missing mappings
- No orphaned KSI rules

### 3.5 Plugin Certification Passes (if plugin touched)

- Sandbox tests
- Capability tests
- Evidence schema tests

This is the governance firewall.

---

## 4. Spec Version Pinning

Every pipeline run is pinned to:
- Spec version
- Control pack version
- KSI rule version
- Evidence schema version
- OSCAL fragment version

Pinned in `uiao/spec/version.json`:

```json
{
  "spec": "1.4.0",
  "ksi": "2.1.3",
  "controls": "3.0.0",
  "evidence": "1.2.0",
  "oscal": "1.0.5"
}
```

CI enforces:
- No unpinned changes
- No implicit upgrades
- No mixed versions

This guarantees reproducibility.

---

## 5. Control Pack Versioning

Control packs follow semantic versioning:
- **MAJOR**: breaking changes to control logic
- **MINOR**: new controls, new rules
- **PATCH**: bug fixes, clarifications

UIAO maintains a compatibility matrix. CI enforces:
- No incompatible combinations
- No silent upgrades
- No missing mappings

---

## 6. Plugin Certification Pipeline

Plugins must pass a certification pipeline before being accepted into the marketplace.

### 6.1 Certification Steps

1. Schema validation - plugin manifest matches schema
2. Sandbox execution - plugin runs in isolated environment
3. Capability declaration - plugin declares all capabilities
4. Evidence schema test - plugin outputs valid evidence bundles
5. Determinism test - plugin produces identical outputs for identical inputs
6. Security review - no privilege escalation, no data leakage

### 6.2 Certification Enforcement

- Uncertified plugins are rejected at the marketplace gateway
- Re-certification required on any breaking change
- Certification tied to spec version

---

## Summary: What This Layer Provides

| Component | Purpose |
|-----------|--------|
| Test Harness Architecture | Four-class test structure with strict boundaries |
| Golden-File Infrastructure | Regression detection with protocol-controlled updates |
| CI Gating Rules | Non-bypassable governance firewall for all PRs |
| Spec Version Pinning | Guaranteed reproducibility across all pipeline runs |
| Control Pack Versioning | Semantic versioning with compatibility matrix enforcement |
| Plugin Certification Pipeline | Marketplace safety, determinism, and security validation |

This layer ensures UIAO cannot regress, drift, or violate its own spec.
