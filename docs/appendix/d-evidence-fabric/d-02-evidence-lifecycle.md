---
title: "Appendix D-02: Evidence Lifecycle"
appendix: "D-02"
family: "Evidence Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-016", "ADR-026"]
---

# Appendix D-02: Evidence Lifecycle

## Purpose

This appendix defines the lifecycle of evidence records in the UIAO Evidence Fabric — from creation through active use to archival. While evidence records are immutable (they can never be modified or deleted), they do pass through distinct lifecycle phases that affect their accessibility, storage tier, and audit status.

## Scope

Applies to all records in the Evidence Fabric: audit events, drift records, compliance attestations, lifecycle transition records, and correction records.

## Evidence Record Lifecycle Phases

### ACTIVE
The record was recently written and is in the primary storage tier. It is immediately accessible for queries, correlation, and compliance reporting. New records enter ACTIVE phase at write time.

**Retention in ACTIVE:** Configurable (default: 90 days for standard events, 365 days for compliance attestations and CRITICAL events)

### ARCHIVED
The record has aged out of the primary storage tier and been moved to the archive tier. It is still accessible but may require a slightly longer retrieval time. Archived records are queryable through the same API as ACTIVE records — the transition is transparent to callers.

**Retention in ARCHIVED:** Configurable (default: 7 years for compliance attestations; 3 years for standard audit events — aligned with FedRAMP continuous monitoring requirements)

### SEALED
Records that have passed a governance review period are sealed. Sealing means the record has been included in a governance report, its hash has been verified, and it is considered a finalized part of the audit trail. Sealed records cannot be corrected (a new correction record can still be written, but the sealed record itself is unalterable in every sense).

**When sealing occurs:** During annual governance reviews or when a FedRAMP assessment is conducted

## Evidence Bundle Lifecycle

Per ADR-016, Evidence Bundles are collections of evidence records assembled for a specific governance purpose (e.g., a FedRAMP continuous monitoring package, an incident investigation package). Evidence Bundles have their own lifecycle:

1. **ASSEMBLING** — Records are being collected into the bundle
2. **SEALED** — The bundle is finalized; no new records may be added
3. **SUBMITTED** — The bundle has been submitted to an external assessor or regulatory body
4. **CLOSED** — The bundle submission has been acknowledged and closed

Evidence Bundles are immutable once SEALED.

## Retention Policy Governance

Changes to retention periods require Governance Plane approval and MUST be recorded in an ADR. Retention periods may only be increased, not decreased. Decreasing a retention period for existing records requires regulatory review.

## Evidence Compression

Per ADR-022, evidence records that have been in ARCHIVED phase for more than 1 year are eligible for compression. Compression reduces storage costs while preserving the full record content and hash chain integrity. Compressed records are automatically decompressed on access — the compression is transparent to callers.

## Dependencies

- **ADR-016:** Evidence bundle lifecycle decision record
- **ADR-022:** Evidence compression decision record
- **ADR-026:** Evidence lifecycle guarantees decision record
- **Appendix D-01:** Evidence determinism
- **Appendix D-03:** Compliance attestation process

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
