---
title: "Appendix D: Evidence Fabric"
appendix: "D"
family: "Evidence Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
---

# Appendix D: Evidence Fabric

The Evidence Fabric is the UIAO subsystem responsible for recording, storing, attesting to, and making queryable all governance events. It serves as the immutable audit trail for the entire UIAO framework — the foundation on which compliance assurances, forensic investigations, and governance reports are built.

## Overview

The Evidence Fabric provides:

- **Immutable event storage** — all governance events are written once and never modified
- **Deterministic evidence** — given the same inputs, the Evidence Fabric always produces the same outputs
- **Cryptographic signing** — every evidence record is signed by the originating adapter and countersigned by the Evidence Fabric
- **Evidence lifecycle management** — records move through ACTIVE, ARCHIVED, and SEALED phases
- **Correlation** — evidence records can be queried and correlated by subject, adapter, control, or time window

## Appendix D Contents

| Document | Description |
|---|---|
| [D-01: Evidence Determinism](d-01-evidence-determinism.md) | No-silent-drops, write-once, ordered sequence, and idempotent write guarantees |
| [D-02: Evidence Lifecycle](d-02-evidence-lifecycle.md) | ACTIVE → ARCHIVED → SEALED phases and retention policies |
| [D-03: Evidence Signing](d-03-evidence-signing.md) | Two-layer signing model, key management, and severity-based signing requirements |
| [D-04: Evidence Correlation](d-04-evidence-correlation.md) | Correlation dimensions, evidence diffing, and the correlation API |

## Key Principles

**Write-once:** Evidence records are never modified or deleted. Corrections are appended.

**Non-repudiation:** Every evidence record is cryptographically signed by its originating adapter. The evidence record proves that the claim came from that adapter.

**Determinism:** The same governance inputs always produce the same evidence outputs. Evidence is not sampled, filtered, or selectively recorded.

**Transparency:** All evidence records are queryable by authorized auditors. The Evidence Fabric does not hide records from authorized queries.

## Related ADRs

- ADR-006: Evidence determinism
- ADR-009: Drift ledger immutability
- ADR-011: Multi-adapter correlation
- ADR-014: Evidence severity model
- ADR-016: Evidence bundle lifecycle
- ADR-020: Evidence correlation determinism
- ADR-022: Evidence compression
- ADR-024: Evidence diffing
- ADR-026: Evidence lifecycle guarantees

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
