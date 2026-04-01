# UIAO Provenance Profile
**Document:** 15
**Phase:** 5 — Data Governance Substrate
**Version:** 1.0
**Status:** Draft
**Classification:** CUI/FOUO
**Date:** 2026-04-01

---

## 1. Purpose

The UIAO Provenance Profile defines the mandatory metadata envelope that every canonical claim MUST carry to establish deterministic, machine-verifiable lineage. It transforms UIAO from an adapter framework into the first federated provenance standard for U.S. federal data systems.

---

## 2. Eight Core Concepts Alignment

1. **Single Source of Truth (SSOT)** — Provenance is the enforcement mechanism for SSOT. Every claim traces to exactly one authoritative origin.
2. **Conversation as the atomic unit** — Each claim emission is a bounded event with identity, timestamp, path, and certification metadata.
3. **Identity as the root namespace** — The `issuer_identity` field derives from the UIAO identity plane.
4. **Deterministic addressing** — Provenance records use deterministic claim URIs, not mutable labels.
5. **Certificate-anchored overlay** — Provenance signatures are mTLS-anchored.
6. **Telemetry as control** — Provenance events are emitted to the telemetry plane as first-class signals.
7. **Embedded governance and automation** — Provenance validation is automated at the adapter boundary.
8. **Public service first** — Provenance enables consent and privacy enforcement at the citizen level.

---

## 3. Provenance Envelope Schema

Every canonical claim emitted by a UIAO adapter MUST carry the following provenance envelope:

```yaml
provenance:
  claim_id: "urn:uiao:claim:{domain}:{claim_type}:{uuid}"
  issuer_identity: "{entra_object_id or agency_issuer_id}"
  source_system: "{system_name}:{version}"
  source_classification: "authoritative | derived | synthesized"
  extraction_timestamp: "{ISO8601}"
  extraction_method: "api | batch | stream | manual"
  transformation_chain:
    - step: 1
      transform: "{transform_name}"
      applied_by: "{adapter_id}"
      applied_at: "{ISO8601}"
  lineage_hash: "{SHA-256 of source record at extraction}"
  schema_version: "1.0"
  signature: "{mTLS certificate thumbprint}"
```

---

## 4. Source Classification Definitions

| Classification | Definition | Example |
|---|---|---|
| `authoritative` | Directly emitted by the Truth Source with no transformation | SSA beneficiary record |
| `derived` | Computed or transformed from an authoritative source | Eligibility determination from SSA data |
| `synthesized` | Assembled from multiple sources; confidence-weighted | Combined identity assertion from SSA + IRS |

---

## 5. Lineage Chain Requirements

- Every transformation step MUST be recorded in `transformation_chain`
- No step may be removed or reordered after signing
- Lineage hashes MUST be verified at every adapter boundary
- Chains with breaks (missing steps) MUST be rejected and flagged as `PROVENANCE_BREAK`

---

## 6. Integration Points

| Plane | Integration |
|---|---|
| Identity | `issuer_identity` resolves to Entra ID object |
| Telemetry | Provenance events emitted to SIEM as `uiao.provenance.*` |
| Compliance | Provenance records satisfy AU-3, AU-9, SI-7 control families |
| Adapter Contract | Adapters must attach provenance before emitting claims |
| Drift Detection | Lineage hash mismatches trigger drift severity `P1-CRITICAL` |

---

## 7. Compliance Mapping

| NIST Control | Provenance Field |
|---|---|
| AU-3 (Audit Record Content) | `claim_id`, `issuer_identity`, `extraction_timestamp` |
| AU-9 (Audit Information Protection) | `lineage_hash`, `signature` |
| SI-7 (Software and Firmware Integrity) | `lineage_hash` verification |
| AC-4 (Information Flow Enforcement) | `source_classification`, `transformation_chain` |
