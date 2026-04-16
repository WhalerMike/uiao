---
title: "ADR-022: Evidence Compression"
adr: "ADR-022"
status: ACCEPTED
date: "2026-02-25"
deciders: ["UIAO Governance Board"]
---

# ADR-022: Evidence Compression

## Status

ACCEPTED

## Context

The Evidence Fabric stores records indefinitely (no deletion). Over time, storage costs for ARCHIVED records become significant. We needed a cost reduction mechanism that preserves the full record content and audit integrity.

## Decision

Evidence records in ARCHIVED phase for more than 1 year are eligible for transparent compression. Compression reduces storage size while preserving: full record content, cryptographic hash, and signature chain. Compressed records are automatically decompressed on access — the compression is transparent to API callers. Records are never discarded or truncated during compression.

## Consequences

**Positive:**
- Significant storage cost reduction for long-lived evidence records
- No impact on audit integrity — full record content is preserved
- Transparent to API callers

**Negative:**
- Decompression on access adds latency for archived record queries
- Compression algorithm choices must be documented and versioned — if an algorithm is deprecated, a migration is required

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
