---
title: "20 Adapter Contract & Certification Framework"
author: "UIAO Canon Steward"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Adapter Contract & Certification Framework

**This document is the normative specification** for all adapters in the UIAO ecosystem. It defines the contract, invariants, and certification process that enables vendors, states, integrators, and agencies to build and certify interoperable adapters.

## 1. Purpose

The Adapter Contract transforms UIAO from a bespoke internal architecture into a scalable **platform**. It enforces deterministic behavior, safety invariants, and compliance guarantees even when adapters are developed by third parties.

This specification builds upon and formalizes the adapter registry defined in [`13_FIMF_AdapterRegistry.md`](./13_FIMF_AdapterRegistry.md).

## 2. BaseAdapter Contract

All UIAO adapters **must** inherit from `BaseAdapter` and implement the following contract:

### Required Methods

| Method | Signature | Purpose |
|---|---|---|
| `connect()` | `async def connect(config: dict) -> bool` | Establish identity-bound, certificate-anchored connection |
| `extract_claims()` | `async def extract_claims(filter: ClaimFilter) -> list[CanonicalClaim]` | Deterministic extraction from source |
| `detect_drift()` | `async def detect_drift() -> DriftReport` | Execute standardized drift detection |
| `transform_to_canonical()` | `async def transform_to_canonical(raw) -> CanonicalClaim` | Apply normalization and validation |
| `generate_lineage()` | `async def generate_lineage() -> ProvenanceRecord` | Produce full provenance record |
| `generate_ksi_bundle()` | `async def generate_ksi_bundle() -> KSIBundle` | Create signed evidence bundle |
| `get_metadata()` | `def get_metadata() -> AdapterMetadata` | Return adapter capabilities and version |

### Mandatory Invariants (Enforced at Runtime)

- Read-only by default on all source systems
- Strict query cost, row count, and execution time limits
- No side effects on the source system
- Full provenance and KSI evidence generation on every extraction
- Drift detection **must** run before any claim is emitted
- All outputs must be identity-rooted and carry a valid Provenance Record (see `15_ProvenanceProfile.md`)

## 3. Certification Levels

| Level | Name | Requirements |
|---|---|---|
| 0 | Basic | Implements BaseAdapter + registry registration |
| 1 | Database Adapter | Full schema mapping, extraction, drift detection, and provenance |
| 2 | Provenance & Compliance | KSI bundles, OSCAL artifacts, Continuous ATO support |
| 3 | Certified & Audited | Independent validation, continuous monitoring hooks, third-party review |

Only Level 1+ adapters may be used with federal Truth Sources.

## 4. Certification Process

1. Self-attestation against this contract + test harness
2. Submission to UIAO Adapter Registry (`13_FIMF_AdapterRegistry.md`)
3. Automated conformance testing (drift scenarios, safety invariants, KSI validation)
4. Optional third-party audit for Level 3
5. Publication in the public UIAO Adapter Registry upon approval

Certified adapters receive a permanent `adapter_id` and versioned certification badge.

## 5. Governance Rule

All adapters operating within UIAO **must** conform to this contract. Non-compliant adapters are prohibited from emitting canonical claims. Violations trigger automatic drift events and POA&M entries.

**This specification is frozen.** Any change requires Canon Steward approval and a KSI-signed update to this document.

---

**Cross-references:**
- [`13_FIMF_AdapterRegistry.md`](./13_FIMF_AdapterRegistry.md) -- Registry and discovery
- [`16_DriftDetectionStandard.md`](./16_DriftDetectionStandard.md) -- Drift taxonomy and remediation
- [`15_ProvenanceProfile.md`](./15_ProvenanceProfile.md) -- Mandatory provenance record
- [`19_ReconciliationModel.md`](./19_ReconciliationModel.md) -- Conflict resolution for multi-source claims
