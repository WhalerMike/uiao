---
title: "ADR-006: Evidence Determinism"
adr: "ADR-006"
status: ACCEPTED
date: "2026-01-15"
deciders: ["UIAO Governance Board"]
---

# ADR-006: Evidence Determinism

## Status

ACCEPTED

## Context

The Evidence Fabric must serve as a reliable audit trail for compliance assessments and forensic investigations. If evidence records could be silently dropped, modified, or produced non-deterministically, auditors would not be able to trust the Evidence Fabric as an authoritative source. We needed formal guarantees about what the Evidence Fabric will and will not do.

## Decision

The Evidence Fabric adopts the following determinism guarantees:

1. **No silent drops:** Every governance event submitted to the Evidence Fabric is recorded. There is no sampling.
2. **Write-once:** Evidence records are never modified or deleted after writing. Corrections are appended as new records.
3. **Ordered sequence:** Records for a given subject are ordered by recorded_at timestamp with sequence number tie-breaking.
4. **Content integrity:** Every record carries a cryptographic content hash. Periodic hash chain verification detects tampering.
5. **Idempotent writes:** Duplicate submissions (same event_id) are deduplicated without creating new records.

## Consequences

**Positive:**
- Auditors can trust the Evidence Fabric as a complete, unmodified record
- Forensic investigations are reproducible
- Compliance assessments are consistent across multiple runs

**Negative:**
- Storage grows monotonically — evidence records are never pruned (only archived/compressed)
- Correction records add complexity to audit queries (must distinguish original from correction)
- Hash chain verification adds computational overhead
