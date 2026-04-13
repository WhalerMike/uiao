---
title: "Appendix D-01: Evidence Determinism"
appendix: "D-01"
family: "Evidence Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-006", "ADR-020"]
---

# Appendix D-01: Evidence Determinism

## Purpose

This appendix defines the evidence determinism model for the UIAO Evidence Fabric. Evidence determinism means that given the same set of inputs (adapter claims, drift records, governance events), the Evidence Fabric will always produce the same set of evidence records, in the same order, with the same content. Determinism is essential for auditability and reproducibility.

## Scope

Applies to all records written to the Evidence Fabric: audit events, drift records, compliance attestations, lifecycle events, and correction records.

## Why Determinism Matters

Without evidence determinism:
- Two auditors reviewing the same governance period might reach different conclusions because the evidence records they see are inconsistent
- Automated compliance checks would be unreliable — the same check run twice might return different results
- Forensic investigation of a governance incident would be impossible to reproduce

Evidence determinism enables the Evidence Fabric to serve as the reliable foundation for all UIAO governance assurances.

## Determinism Principles

### No Silent Drops

Every event that reaches the Evidence Fabric MUST be recorded. There are no silent drops, no sampling, and no conditional recording based on event content. If an event is received, it is recorded.

### Write-Once

Evidence records are written once. They are never updated, overwritten, or deleted. Corrections are appended as separate records with a reference to the original.

### Ordered Sequence

Evidence records for a given subject are ordered by `recorded_at` timestamp. The Evidence Fabric guarantees that records with the same `recorded_at` timestamp are ordered by a deterministic tie-breaking mechanism (a sequence number assigned at write time).

### Content Integrity

Each evidence record carries a cryptographic hash of its content. Any tampering with the record content after write would invalidate the hash. Periodic hash chain verification is performed by the Evidence Fabric to detect tampering.

### Idempotent Writes

If the same event is submitted to the Evidence Fabric twice (e.g., due to network retry), the second submission is deduplicated. Deduplication is based on the `event_id` field. A duplicate write produces no new record but returns success to the caller.

## Evidence Correlation Determinism

The Evidence Fabric supports correlation queries: given a drift record, find all related compliance attestations and audit events. Correlation is deterministic — the same correlation query run at different times will return the same results (records are never deleted, so the result set only grows over time, it never shrinks). See ADR-020 for the correlation determinism decision.

## Dependencies

- **ADR-006:** Evidence determinism decision record
- **ADR-020:** Evidence correlation determinism decision record
- **Appendix D-02:** Audit event taxonomy
- **Appendix D-03:** Compliance attestation process

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
