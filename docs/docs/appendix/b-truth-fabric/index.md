---
title: "Appendix B: Truth Fabric"
appendix: "B"
family: "Truth Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
---

# Appendix B: Truth Fabric

The Truth Fabric is the UIAO subsystem responsible for maintaining the authoritative canonical state of all registered adapters and integrated systems. It is the single source of truth for identity records, canonical claims, compliance mappings, and adapter state — the foundation on which the Drift Fabric and Evidence Fabric operate.

## Overview

The Truth Fabric provides:

- **Canonical Claim storage** — receives, validates, and stores all Canonical Claims from adapters
- **Canonical Identity Records** — maintains authoritative identities for all subjects across integrated systems
- **Control mapping** — maps Canonical Claims to compliance framework controls and generates Compliance Attestations
- **State records** — maintains the current and historical canonical state for every registered adapter

## Appendix B Contents

| Document | Description |
|---|---|
| [B-01: Canonical Claim Schema](b-01-canonical-claim-schema.md) | The data structure for all UIAO integration assertions |
| [B-02: Identity Anchoring](b-02-identity-anchoring.md) | Cross-system identity correlation and Canonical Identity Records |
| [B-03: Multi-Cloud Identity Matrix](b-03-multi-cloud-identity-matrix.md) | Mapping of cloud provider identity constructs to canonical types |
| [B-04: Control Mapping Governance](b-04-control-mapping-governance.md) | How claims map to compliance controls and attestations |

## Key Principles

**Immutability of accepted claims:** Once a Canonical Claim is accepted and stored, it is immutable. Corrections require a new superseding claim.

**Schema enforcement:** The Truth Fabric validates all incoming claims against the Canonical Claim Schema. Invalid claims are rejected — they are never silently stored with partial data.

**Zero-trust identity:** No identity anchor is trusted by default. All anchors require verification before HIGH trust is assigned.

**Control mapping versioning:** The control mapping registry is versioned. Old mappings are never deleted — only deprecated. This ensures that historical Compliance Attestations remain traceable.

## Related ADRs

- ADR-005: Canonical Claim Schema design
- ADR-008: Zero-trust identity anchoring
- ADR-011: Multi-adapter correlation

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
