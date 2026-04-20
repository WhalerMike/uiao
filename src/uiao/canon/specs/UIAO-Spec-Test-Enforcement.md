---
document_id: UIAO_103
title: "UIAO Spec-to-Test Enforcement Layer"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-14"
boundary: "GCC-Moderate"
---

# UIAO Spec-to-Test Enforcement Layer

## Overview

The UIAO Spec-to-Test Enforcement Layer ensures every spec artifact becomes an executable, machine-verifiable test. This is the layer that turns UIAO from well-documented into provably correct, regression-resistant, and governance-grade.

---

## 1. Spec-Driven Test Matrix

Every file in uiao/spec/ must map to one or more test suites.

| Spec File | Test Suite |
|-----------|------------|
| ksi/10-ksi-semantics.md | tests/ksi/test_semantics.py |
| ksi/20-ksi-rule-schema.json | tests/ksi/test_rule_schema.py |
| controls/10-control-pack-schema.json | tests/controls/test_control_pack_schema.py |
| drift/20-drift-to-poam-rules.md | tests/drift/test_poam_triggers.py |
| evidence/10-evidence-bundle-schema.json | tests/evidence/test_bundle_schema.py |
| evidence/20-provenance-manifest-schema.json | tests/evidence/test_provenance_integrity.py |
| pipeline/20-determinism-guarantees.md | tests/pipeline/test_determinism.py |

This matrix is the governance backbone of UIAO.

---

## 2. Spec Compliance Tests

These tests ensure the implementation matches the spec exactly.

### 2.1 Schema Tests

- Validate KSI rule JSON schema
- Validate control pack schema
- Validate evidence bundle schema
- Validate provenance manifest schema

### 2.2 Semantic Tests

- Lattice ordering: PASS < WARN < FAIL
- Monotonicity: adding failing facts cannot improve status
- Rule purity: no side effects

### 2.3 Contract Tests

- Each plane's input/output contract is enforced
- No missing fields
- No extra fields
- No nondeterministic fields

---

## 3. Pipeline Determinism Tests

These tests prove the pipeline is deterministic.

### 3.1 Bit-for-Bit Reproducibility

Given:
- Same raw evidence
- Same control packs
- Same KSI rules
- Same config

Then:
- IR snapshots identical
- KSI results identical
- Evidence bundles identical
- OSCAL artifacts identical

### 3.2 Forbidden Nondeterminism Tests

Fail if:
- Timestamps differ (unless explicitly allowed)
- Ordering differs
- Hashes differ
- JSON key order differs

---

## 4. Control Logic Tests

These tests ensure KSI rules behave correctly.

### 4.1 Rule Correctness Tests

For each rule:
- Provide minimal PASS case
- Provide minimal FAIL case
- Provide WARN case (if applicable)

### 4.2 Composition Tests

For composite controls:
- AND = worst child
- OR = best child

### 4.3 Regression Tests

Every bug becomes a test:
- "This rule misclassified X" becomes a permanent test

---

## 5. Drift & POA&M Tests

These tests ensure drift classification and POA&M triggers are correct.

### 5.1 Drift Classification Tests

| Transition | Classification |
|------------|---------------|
| PASS -> PASS | benign |
| PASS -> WARN | benign |
| PASS -> FAIL | degradation |
| WARN -> FAIL | degradation |
| FAIL -> PASS | improvement |

### 5.2 POA&M Trigger Tests

POA&M must be created when:
- PASS -> FAIL
- WARN -> FAIL

POA&M must NOT be created when:
- FAIL -> WARN
- FAIL -> PASS
- PASS -> WARN

---

## 6. Provenance Integrity Tests

These tests ensure evidence and OSCAL artifacts are cryptographically trustworthy.

### 6.1 Hash Integrity

- Recompute hash for every evidence item
- Must match stored hash

### 6.2 Closure Tests

Every OSCAL control statement must be backed by:
- At least one evidence item
- With valid provenance
- With valid hash

### 6.3 Signature Tests

- Provenance manifest signature must verify
- Key rotation must not break verification

---

## Summary: What This Layer Provides

| Component | Coverage |
|-----------|----------|
| Spec-to-Test Matrix | All spec files mapped to tests |
| Schema Tests | JSON schema validation for all artifacts |
| Semantic Tests | Lattice ordering, monotonicity, rule purity |
| Determinism Tests | Bit-for-bit reproducibility guarantees |
| Control Logic Tests | Rule correctness, composition, regression |
| Drift + POA&M Tests | Classification and trigger correctness |
| Provenance Tests | Hash integrity, closure, signature verification |

This layer makes UIAO provably correct, regression-proof, and governance-grade.

---

## Next Layer

The next layer is the **UIAO Test Harness & CI Enforcement Layer**, covering:
- Test harness architecture
- Golden-file tests
- CI gating rules
- Spec version pinning
- Control pack versioning
- Plugin certification pipeline
