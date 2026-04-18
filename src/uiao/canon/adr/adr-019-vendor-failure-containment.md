---
title: "ADR-019: Vendor Failure Containment"
adr: "ADR-019"
status: ACCEPTED
date: "2026-02-18"
deciders: ["UIAO Governance Board"]
---

# ADR-019: Vendor Failure Containment

## Status

ACCEPTED

## Context

External vendor systems fail. When they do, the Drift Fabric may receive inconsistent, stale, or no data from the affected adapter. Without explicit containment, these failures could cascade into false drift records, incorrect compliance attestations, or degraded Truth Fabric state.

## Decision

The Drift Fabric implements vendor failure containment with four failure modes (VF-01 through VF-04) and mode-specific containment actions. Key isolation guarantees:
- Vendor failure MUST NOT cause incorrect canonical state in the Truth Fabric
- Vendor failure MUST NOT cause false positive compliance attestations
- All events during a vendor failure window are recorded in the Evidence Fabric with failure context
- Recovery triggers a catch-up drift scan for affected subjects

See Appendix C-03 for the complete containment specification.

## Consequences

**Positive:**
- Vendor failures are contained — no cascade effects on other adapters or fabrics
- Failure periods are completely recorded — auditors know exactly what happened
- Recovery is automated and auditable

**Negative:**
- During VF-01 (unavailability), compliance attestations for affected subjects are suspended
- Catch-up scan after recovery can generate a large volume of drift events if the failure was long

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
