---
title: "Appendix E-03: Cross-Fabric Consistency"
appendix: "E-03"
family: "Governance Plane"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-005", "ADR-006", "ADR-009"]
---

# Appendix E-03: Cross-Fabric Consistency

## Purpose

This appendix defines the cross-fabric consistency model for the UIAO Governance Plane. While CR-004 (Fabric Orthogonality) requires that the three fabrics operate independently, the Governance Plane must verify that the three fabrics collectively present a consistent view of the governance state. This appendix defines how that consistency is verified without violating orthogonality.

## Scope

Applies to the Governance Plane's periodic consistency verification activities. This does not apply to normal fabric operations — fabrics remain orthogonal in their day-to-day operations.

## The Consistency Problem

The three fabrics are orthogonal, but they must ultimately tell a consistent story:
- The Truth Fabric says: "Subject X has role Y"
- The Drift Fabric says: "No drift detected for subject X in the last 30 days"
- The Evidence Fabric says: "Compliance attestation for Subject X, control AC-2, issued 15 days ago"

These three statements should be mutually consistent. If they are not — for example, if the Evidence Fabric has a compliance attestation but the Truth Fabric has no corresponding canonical state — that inconsistency is itself a governance event requiring investigation.

## Consistency Verification Protocol

The Governance Plane runs a cross-fabric consistency check on a quarterly schedule (or on demand for mission-critical subjects). The check:

1. **Truth-Evidence Consistency:** For every compliance attestation in the Evidence Fabric, verify that the corresponding canonical claim exists in the Truth Fabric. Flag any attestation without a corresponding claim.

2. **Drift-Evidence Consistency:** For every Drift Record in the Evidence Fabric, verify that the corresponding canonical state exists in the Truth Fabric. Flag any Drift Record for a subject that has no canonical state.

3. **Adapter-Fabric Consistency:** For every adapter in ACTIVE state in the Adapter Plane, verify that at least one Canonical Claim has been received from that adapter within the expected freshness window. Flag any ACTIVE adapter that has not produced a recent claim.

4. **Lifecycle-Evidence Consistency:** For every adapter lifecycle transition recorded in the Evidence Fabric, verify that the adapter's current state in the Truth Fabric matches what the Evidence Fabric shows as the last transition. Flag any discrepancy.

## Consistency Violations

Consistency violations are recorded as CRITICAL Evidence Fabric events and trigger:
1. Immediate Governance Plane notification
2. Halt of any ongoing drift detection or compliance attestation for affected subjects
3. Manual investigation by the Governance Board
4. Root cause analysis within 5 business days
5. Corrective ADR if the root cause is architectural

## Consistency vs. Orthogonality

Cross-fabric consistency verification does NOT violate CR-004. Orthogonality means that normal fabric operations do not create cross-fabric dependencies. Consistency verification is a Governance Plane operation — it reads from the fabrics without introducing any operational coupling between them.

The Governance Plane is specifically authorized by CR-005 to perform cross-cutting checks. The three fabrics remain operationally orthogonal.

## Dependencies

- **CR-004:** Fabric orthogonality (the constraint that consistency verification must not violate)
- **CR-005:** Governance Plane authority (authorizes cross-cutting checks)
- **ADR-005:** Canonical Claim Schema (basis for Truth-Evidence consistency check)
- **ADR-006:** Evidence determinism (basis for evidence record completeness)
- **ADR-009:** Drift ledger immutability (basis for Drift-Evidence consistency check)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
