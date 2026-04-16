---
title: "Appendix D-03: Evidence Signing"
appendix: "D-03"
family: "Evidence Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-006", "ADR-014"]
---

# Appendix D-03: Evidence Signing

## Purpose

This appendix defines the cryptographic signing model for UIAO evidence records. Signing ensures that evidence records can be verified as authentic and untampered, providing a non-repudiation guarantee for all governance events.

## Scope

Applies to all records written to the Evidence Fabric. Signing is mandatory — unsigned records are rejected.

## Signing Architecture

The Evidence Fabric uses a two-layer signing model:

**Layer 1 — Adapter Signature:** The originating adapter signs the Canonical Claim or governance event before submitting it to the UIAO framework. This signature is carried through to the evidence record, proving that the claim originated from the registered adapter.

**Layer 2 — Evidence Fabric Countersignature:** When the Evidence Fabric writes a record, it adds its own countersignature over the complete record (including the adapter signature). This proves that the Evidence Fabric received and stored the record as-is, without modification.

## Signing Algorithm

The UIAO framework requires RSA-2048 or RSA-4096 with SHA-256 (RS256) for all signatures. ECDSA with P-256 (ES256) is also accepted. MD5 and SHA-1 are explicitly prohibited.

## Key Management

Adapter signing keys are:
- Generated per adapter at registration time
- Stored in the key management service configured in `uiao-core`
- Rotated on a configurable schedule (default: annually, or immediately on suspected compromise)
- Retired keys are retained for verification of historical evidence records even after rotation

The Evidence Fabric's countersignature key is managed by the Governance Plane and rotated on the same schedule as adapter keys.

## Evidence Severity Model

Per ADR-014, evidence records are classified by severity. The severity level affects signing and handling requirements:

| Severity | Signing Requirement | Storage Requirement |
|---|---|---|
| INFO | Adapter signature required | Standard retention |
| LOW | Adapter signature required | Standard retention |
| MEDIUM | Adapter signature + Evidence Fabric countersignature | Standard retention |
| HIGH | Adapter signature + Evidence Fabric countersignature | Extended retention (5 years) |
| CRITICAL | Adapter signature + Evidence Fabric countersignature + Governance Plane notification | Extended retention (7 years) + sealed immediately |

## Signature Verification

The Evidence Fabric exposes a verification API that allows auditors to verify the signatures on any evidence record. The verification API:
1. Retrieves the record from the Evidence Fabric
2. Verifies the adapter signature against the adapter's registered public key at the time the record was written
3. Verifies the Evidence Fabric countersignature against the Evidence Fabric's public key at the time the record was written
4. Verifies the content hash matches the record's stored hash
5. Returns a verification result with pass/fail for each check

## Hash Chain

Evidence records for a given subject are linked in a hash chain: each record contains the hash of the previous record for the same subject. This enables detection of gaps in the evidence timeline — if a record is missing, the hash chain breaks.

## Dependencies

- **ADR-006:** Evidence determinism (no silent drops, content integrity)
- **ADR-014:** Evidence severity model
- **uiao-core:** Key management configuration
- **Appendix D-01:** Evidence determinism principles

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
