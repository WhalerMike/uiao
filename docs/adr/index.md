---
title: "Architectural Decision Records"
status: ACTIVE
version: "1.0"
last_updated: "2026-04-07"
---

# Architectural Decision Records (ADRs)

This index lists all UIAO Architectural Decision Records. ADRs document significant architectural decisions — the context that drove them, the decision made, and the consequences of that decision. Per CR-003, accepted ADRs are immutable.

## ADR Status Definitions

| Status | Meaning |
|---|---|
| PROPOSED | Under review, not yet accepted |
| ACCEPTED | Approved by Governance Board — immutable Decision field |
| DEPRECATED | Superseded by a newer ADR but retained for audit trail |
| SUPERSEDED | Replaced by a specific ADR (see superseded_by field) |

## ADR Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [ADR-005](adr-005-canonical-claim-schema.md) | Canonical Claim Schema | ACCEPTED | 2026-01-15 |
| [ADR-006](adr-006-evidence-determinism.md) | Evidence Determinism | ACCEPTED | 2026-01-15 |
| [ADR-007](adr-007-multi-cloud-adapter.md) | Multi-Cloud Adapter Model | ACCEPTED | 2026-01-20 |
| [ADR-008](adr-008-zero-trust-identity.md) | Zero-Trust Identity Anchoring | ACCEPTED | 2026-01-22 |
| [ADR-009](adr-009-drift-ledger-immutability.md) | Drift Ledger Immutability | ACCEPTED | 2026-01-22 |
| [ADR-010](adr-010-vendor-baseline-versioning.md) | Vendor Baseline Versioning | ACCEPTED | 2026-01-25 |
| [ADR-011](adr-011-multi-adapter-correlation.md) | Multi-Adapter Correlation | ACCEPTED | 2026-01-28 |
| [ADR-012](adr-012-canonical-drift-taxonomy.md) | Canonical Drift Taxonomy | ACCEPTED | 2026-02-01 |
| [ADR-013](adr-013-adapter-failure-isolation.md) | Adapter Failure Isolation | ACCEPTED | 2026-02-03 |
| [ADR-014](adr-014-evidence-severity-model.md) | Evidence Severity Model | ACCEPTED | 2026-02-05 |
| [ADR-015](adr-015-adapter-extensibility.md) | Adapter Extensibility | ACCEPTED | 2026-02-08 |
| [ADR-016](adr-016-evidence-bundle-lifecycle.md) | Evidence Bundle Lifecycle | ACCEPTED | 2026-02-10 |
| [ADR-017](adr-017-adapter-sandbox-execution.md) | Adapter Sandbox Execution | ACCEPTED | 2026-02-12 |
| [ADR-018](adr-018-mission-channel-enforcement.md) | Mission Channel Enforcement | ACCEPTED | 2026-02-15 |
| [ADR-019](adr-019-vendor-failure-containment.md) | Vendor Failure Containment | ACCEPTED | 2026-02-18 |
| [ADR-020](adr-020-evidence-correlation-determinism.md) | Evidence Correlation Determinism | ACCEPTED | 2026-02-20 |
| [ADR-021](adr-021-adapter-hot-swap-rollback.md) | Adapter Hot-Swap and Rollback | ACCEPTED | 2026-02-22 |
| [ADR-022](adr-022-evidence-compression.md) | Evidence Compression | ACCEPTED | 2026-02-25 |
| [ADR-023](adr-023-adapter-concurrency.md) | Adapter Concurrency | ACCEPTED | 2026-03-01 |
| [ADR-024](adr-024-evidence-diffing.md) | Evidence Diffing | ACCEPTED | 2026-03-03 |
| [ADR-025](adr-025-adapter-health-liveness.md) | Adapter Health and Liveness | ACCEPTED | 2026-03-05 |
| [ADR-026](adr-026-evidence-lifecycle-guarantees.md) | Evidence Lifecycle Guarantees | ACCEPTED | 2026-03-08 |
| [ADR-027](adr-027-adapter-retirement.md) | Adapter Retirement | ACCEPTED | 2026-03-10 |

## ADR Governance Rules

Per **CR-003 (ADR Immutability)**, once an ADR is ACCEPTED:
- The **Context**, **Decision**, and **Date** fields are immutable
- Amendments require a new superseding ADR
- The superseding ADR must include `supersedes: ADR-NNN`
- The superseded ADR must be updated with `superseded_by: ADR-MMM`

All ADR changes require Governance Plane approval.
