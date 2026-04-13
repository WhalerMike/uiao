---
title: "Appendix B-04: Control Mapping Governance"
appendix: "B-04"
family: "Truth Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-005", "ADR-011"]
---

# Appendix B-04: Control Mapping Governance

## Purpose

This appendix defines how UIAO Canonical Claims are mapped to compliance control frameworks (e.g., NIST SP 800-53, FedRAMP, CMMC). Control mapping enables the Truth Fabric to produce compliance attestations — evidence that a system satisfies specific regulatory controls — based on the claims it receives from adapters.

## Scope

Applies to all Canonical Claims of type `compliance.asserted` and to the Truth Fabric's control mapping engine. The control mapping registry is maintained as a machine artifact in `uiao-core`.

## Control Mapping Model

A control mapping record associates a Canonical Claim type (or a specific claim assertion) with one or more compliance control identifiers. The mapping has:
- `claim_type`: The type of Canonical Claim that satisfies the control
- `claim_assertion_filter`: Optional filter criteria within the claim's assertion fields
- `control_framework`: The compliance framework (e.g., `NIST-800-53-r5`, `FedRAMP-High`, `CMMC-L2`)
- `control_id`: The control identifier within the framework (e.g., `AC-2`, `IA-5`)
- `satisfaction_level`: `full`, `partial`, or `compensating`
- `rationale`: Human-readable explanation of why this claim satisfies this control

## Control Mapping Registry

The Control Mapping Registry is stored in `uiao-core/data/control-mappings/`. It is machine-readable JSON and is versioned alongside the Canonical Claim Schema. Changes to the registry MUST be reviewed by the Governance Plane and recorded in an ADR if they affect existing mappings.

## Compliance Attestation Generation

When the Truth Fabric receives a `compliance.asserted` claim that matches a control mapping, it generates a Compliance Attestation record:
1. The claim is validated (schema, signature, adapter authorization)
2. The claim is matched against the control mapping registry
3. For each matching control: a Compliance Attestation is created and written to the Evidence Fabric
4. The Compliance Attestation is immutable and carries the same signature as the originating claim

## Multi-Adapter Correlation for Controls

Some controls require evidence from multiple adapters to establish full satisfaction. For example, AC-2 (Account Management) may require claims from both an identity provider adapter and an HR system adapter. The Truth Fabric's multi-adapter correlation engine (ADR-011) handles this:
1. When a claim is received that partially satisfies a control, the Truth Fabric marks the control as `satisfaction_level: partial`
2. When a corroborating claim arrives from a second adapter, the Truth Fabric upgrades the satisfaction level to `full` (or `compensating` if the combination only partially satisfies)
3. Both claims are linked in the Compliance Attestation's `evidence_claims` array

## Control Mapping Governance Rules

1. No control mapping may be added or modified without a Governance Plane review
2. Mappings that claim `full` satisfaction MUST include a written rationale reviewed by the Governance Board
3. Mappings for FedRAMP High controls MUST be reviewed by a qualified security assessor before activation
4. Deprecated mappings MUST remain in the registry with `status: DEPRECATED` — they may not be deleted

## Dependencies

- **ADR-005:** Canonical Claim Schema (claim_type definitions)
- **ADR-011:** Multi-adapter correlation decision record
- **uiao-core:** Machine-readable control mapping registry
- **Appendix D-03:** Compliance attestation process

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
