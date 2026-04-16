---
title: "Adapter-Contract"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Adapter Contract (Human-Readable Specification)
**UIAO Adapter Suite — Document 4 of 4**
**Version 1.0.0 — Canonical, Frozen**

This document is the **human-readable, governance-aligned, implementation-neutral** description of the UIAO Adapter Contract.

It corresponds exactly to:
- The canonical definition (Document 1)
- The diagram suite (Document 2)
- The Python abstract base class (Document 3)

No new canon is introduced here. This document simply **explains the contract in human terms** for adapter authors, reviewers, and governance bodies.

---

# 1. Purpose of the Adapter Contract

The UIAO Adapter Contract defines:
- What a UIAO adapter **must do**
- What a UIAO adapter **must not do**
- How it interacts with the UIAO truth fabric
- How it satisfies governance, provenance, and drift requirements
- How it ensures boundary safety and minimization
- How it participates in certification

This contract is **mandatory** for all adapters. Vendor adapters (Entra, Cisco, InfoBlox, AWS, DMV, EHR, etc.) MUST conform to this contract.

---

# 2. The 10 Responsibility Domains

A UIAO adapter MUST implement all ten domains. These domains are **canonical** and **frozen**.

---

## Domain 1 — API Structure

Every adapter MUST implement:
- `discover()`
- `pull_state(scope)`
- `pull_changes(since, scope)`
- `normalize(raw)`
- `publish(claims)`
- `health()`

```text
discover → pull_state → pull_changes → normalize → publish → health
```

---

## Domain 2 — Identity Requirements

Adapters MUST:
- Produce deterministic `uiao_id` values
- Extract stable `local_id` values
- Map subjects to canonical schemas
- Maintain identity stability across runs

---

## Domain 3 — Certs and Tokens

Adapters MUST:
- Authenticate to source systems using secure credentials
- Authenticate to UIAO truth fabric using mTLS or signed tokens
- Store credentials securely
- Rotate credentials according to policy

Credentials MUST NOT appear in logs or claims.

---

## Domain 4 — Provenance Encoding

Every canonical object MUST include a provenance envelope conforming to:
`/schemas/provenance.schema.json`

Provenance MUST include:
- `source_system`
- `source_adapter`
- `collected_at`
- `observed_at`
- `method`
- `evidence_pointer`

---

## Domain 5 — Normalization & Canonicalization

Adapters MUST:
- Convert raw vendor data → canonical schemas
- Use declarative mapping rules where possible
- Validate canonical objects against JSON Schemas
- Enforce minimization (no raw logs, no unnecessary PII)

---

## Domain 6 — Drift Detection

Adapters MUST detect:
- State transitions
- Value changes
- Conflicts with previous values
- Missing or withdrawn truth

Drift MUST conform to: `/schemas/drift.schema.json`

---

## Domain 7 — Confidence Scoring

Adapters SHOULD compute confidence when:
- Truth is inferred
- Evidence is partial
- Source system is degraded
- Identity mapping is uncertain

Confidence is a float between `0.0` and `1.0`.

---

## Domain 8 — Error Semantics & Recovery

Adapters MUST:
- Distinguish transient vs. permanent errors
- Retry transient errors with backoff
- Fail fast on permanent errors
- Quarantine malformed records
- Never publish invalid canonical objects

---

## Domain 9 — Publication Rules

Adapters MUST:
- Publish canonical claims
- Ensure idempotency
- Preserve ordering per entity
- Support batch or streaming modes
- Include provenance and drift

---

## Domain 10 — Security Controls

Adapters MUST:
- Run inside the source boundary
- Enforce minimization
- Restrict outbound connectivity
- Log security events
- Protect credentials
- Never export raw telemetry

---

# 3. Adapter Lifecycle

The lifecycle is deterministic:

1. Discover
2. Pull state
3. Pull changes
4. Normalize
5. Detect drift
6. Attach provenance
7. Publish claims
8. Emit telemetry
9. Report health
10. Repeat

---

# 4. Governance Alignment

Adapters are governed by:
- Adapter Steward
- Privacy Board
- Federated Council

Adapters MUST:
- Pass certification
- Maintain conformance
- Support audits
- Provide introspection metadata

---

# 5. Certification Requirements

Adapters MUST pass:
1. Static validation
2. Dynamic testing
3. Security review
4. Governance review
5. Final certification

Certification is required for production use.

---

# 6. Summary

A UIAO Adapter is:
- **Canonical**
- **Deterministic**
- **Provenance-first**
- **Drift-aware**
- **Boundary-safe**
- **Governance-aligned**

This document is the **human-readable contract** that all adapters MUST follow.
It is **frozen**, **canonical**, and **authoritative**.
