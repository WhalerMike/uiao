# UIAO Compliance Science Layer

## Overview

The UIAO Compliance Science Layer provides the formal theoretical foundations that underpin UIAO's deterministic compliance evaluation. This layer establishes the mathematical and logical frameworks that make UIAO's outputs reproducible, verifiable, and formally correct.

---

## 1. Formal Semantics of KSI (Key Security Indicators)

A KSI is a formal predicate over an IR object:

    KSI(ir, rule) -> { PASS | WARN | FAIL }

Where:
- ir = an IR object (normalized evidence)
- rule = a deterministic evaluation function
- The result is one of three values: PASS, WARN, or FAIL

### 1.1 KSI Semantics

    PASS:  rule(ir) evaluates to TRUE with no exceptions
    WARN:  rule(ir) evaluates to PARTIAL_COMPLIANCE or THRESHOLD_BREACH
    FAIL:  rule(ir) evaluates to FALSE or MISSING_FIELD

### 1.2 KSI Composition

Multiple KSIs can be composed:

    KSI_composite(ir) = AND(KSI_1(ir), KSI_2(ir), ..., KSI_n(ir))

A control is PASS only if all required KSIs pass.

### 1.3 KSI Determinism

For any given IR state s and rule r:
    KSI(s, r) always produces the same result.

No randomness, no heuristics, no ML inference — pure deterministic function evaluation.

---

## 2. Control Evaluation Algebra

UIAO's control evaluation follows a formal algebra:

### 2.1 Control States

    C = { PASS | WARN | FAIL | NOT_EVALUATED }

### 2.2 Control Evaluation Function

    eval(c, KSI_results) -> C

Where:
- c = a control (e.g., AC-2, IA-2)
- KSI_results = the set of KSI results for that control

### 2.3 Partial Order

UIAO defines a partial order over control states:

    PASS > WARN > FAIL > NOT_EVALUATED

This enables aggregation:
    aggregate([PASS, WARN, PASS]) = WARN  (minimum)

### 2.4 Control Family Aggregation

For a control family (e.g., IA):

    eval_family(IA) = min(eval(IA-2), eval(IA-3), ...)

### 2.5 Overall Posture Score

    posture = min(eval_family(AC), eval_family(IA), eval_family(AU), ...)

---

## 3. Drift Classification Theory

Drift is the formal detection of state change in the IR model.

### 3.1 Drift Definition

Let s_n = IR state at time n, s_{n+1} = IR state at time n+1.

    drift(s_n, s_{n+1}) = { field: (v_n, v_{n+1}) | v_n != v_{n+1} }

A drift event is any non-empty drift function result.

### 3.2 Drift Severity Classification

    severity(drift_event) = f(control_family, field_type, change_direction)

Where:
- LOW: benign configuration change (no control impact)
- MEDIUM: policy weakening (threshold degradation)
- HIGH: control violation (boolean flip from compliant to non-compliant)

### 3.3 Drift Monotonicity

UIAO's drift model is monotonic — drift events accumulate. A drift event is only closed when evidence satisfies the original compliant state.

### 3.4 Drift-to-POA&M Mapping

For each drift event of severity >= MEDIUM:

    poam_entry = generate_poam(drift_event, control, severity)

This is a deterministic function with no human interpretation.

---

## 4. Evidence Provenance Formalism

UIAO defines provenance as a formal chain of custody.

### 4.1 Provenance Manifest Structure

    P = { timestamp, source, hash_algorithm, hash_value, environment, pipeline_plane }

### 4.2 Provenance Chain

For a sequence of evidence transformations:

    P_1 = provenance(raw_evidence)
    P_2 = provenance(IR, P_1)
    P_3 = provenance(KSI_results, P_2)
    P_4 = provenance(evidence_bundle, P_3)
    P_5 = provenance(OSCAL_artifact, P_4)

Each provenance record references its parent, forming an immutable chain.

### 4.3 Provenance Verification

An auditor can verify any OSCAL artifact by:

1. Reconstructing the provenance chain
2. Verifying each hash
3. Confirming the source environment
4. Confirming the pipeline plane

This verification is algorithmic — no human judgment required.

### 4.4 Provenance Immutability

Provenance records are write-once, append-only. There is no mechanism to modify or delete a provenance record.

---

## 5. Deterministic Pipeline Proofs

UIAO makes four formal claims about its pipeline:

### 5.1 Claim: Output Determinism

For any given input state (IR snapshot + control pack version), UIAO will always produce the same KSI results.

**Proof sketch:** KSI rules are pure functions. IR is schema-validated. Control pack versions are pinned. Therefore output is deterministic.

### 5.2 Claim: Completeness

For every control in the active control pack, UIAO will produce a KSI result (PASS, WARN, or FAIL).

**Proof sketch:** Control packs require evidence bindings for every control. Evidence collectors are required to produce evidence for every declared control. The KSI evaluator processes every binding.

### 5.3 Claim: Soundness

A PASS result means the IR satisfies the KSI rule. A FAIL result means the IR violates the KSI rule.

**Proof sketch:** KSI rules are formally specified predicates. Evaluation is a direct function application with no approximation.

### 5.4 Claim: Provenance Completeness

Every OSCAL artifact produced by UIAO has a complete, verifiable provenance chain to its source evidence.

**Proof sketch:** Provenance is appended at every pipeline plane. OSCAL emitters reference provenance IDs. Provenance records are immutable.

---

## Summary

The UIAO Compliance Science Layer establishes:

1. **Formal Semantics of KSI** — KSI as a deterministic predicate: KSI(ir, rule) -> {PASS, WARN, FAIL}
2. **Control Evaluation Algebra** — Formal partial order over control states, composition, and family aggregation
3. **Drift Classification Theory** — Formal drift definition, severity classification, and drift-to-POA&M mapping
4. **Evidence Provenance Formalism** — Formal provenance chain with cryptographic integrity
5. **Deterministic Pipeline Proofs** — Four formal claims: output determinism, completeness, soundness, provenance completeness

This is the layer that makes UIAO **formally correct**, **mathematically verifiable**, and **auditor-trustworthy** at the deepest level.
