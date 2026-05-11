---
title: Evidence Fabric Overview — Executive Brief
doc-type: executive-brief
canon-source: docs/docs/15_ProvenanceProfile.qmd
derived-from: uiao/canon
---

# Evidence Fabric Overview

UIAO’s Evidence Fabric is designed to turn runtime telemetry into assessor-ready
compliance artifacts with traceable provenance at every step. Instead of a
single point-in-time screenshot, it produces a deterministic evidence bundle
that can be re-run and independently verified.

## Provenance chain (event → claim → OSCAL artifact)

The intended chain is:

1. **Telemetry event capture** from adapters and governance controls.
2. **Canonical claim normalization** under the provenance envelope defined in
   [15_ProvenanceProfile.qmd](../../15_ProvenanceProfile.qmd).
3. **Evidence bundling and mapping** into OSCAL-native outputs for assessors.

This creates a lineage from source signal to compliance statement, so a 3PAO
can trace any finding back to a concrete, hashed source record.

## Determinism and reproducibility

Per
[ADR-006](../../../../src/uiao/canon/adr/adr-006-evidence-determinism.md),
the fabric is designed for deterministic behavior: no silent drops, append-only
writes, ordered records, integrity hashing, and idempotent ingestion. In
practice this means **same inputs produce the same evidence bundle**, enabling
byte-reproducible regeneration for reassessment, forensics, and dispute
resolution.

## Cryptographic anchoring and signing posture

Evidence integrity is anchored with cryptographic hashes in the provenance
envelope and bundle-level provenance fields defined by
[`evidence-bundle.schema.json`](../../../../src/uiao/schemas/ksi/evidence-bundle.schema.json).
The schema enforces hash-bearing provenance structures at item and bundle scope,
providing the verification substrate for signed, tamper-evident evidence
packages.

## Evidence outputs available today

UIAO currently emits or assembles the following evidence surfaces:

- **System Security Plan (SSP)**
- **POA&M**
- **KSI dashboard artifacts**
- **Component Definitions**

Bundle lifecycle controls (assemble → seal → submit → close) are defined in
[ADR-016](../../../../src/uiao/canon/adr/adr-016-evidence-bundle-lifecycle.md)
to support governed handoff to federal assessors.

## Maturity and current-state honesty

The **event-time capture chain is design-defined but not fully wired in current
production flow**. UIAO already defines deterministic structure, provenance
fields, and bundle lifecycle controls; end-to-end continuous event-time capture
remains a target-state capability and is represented here as aspirational.
