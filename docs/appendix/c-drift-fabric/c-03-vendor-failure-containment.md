---
title: "Appendix C-03: Vendor Failure Containment"
appendix: "C-03"
family: "Drift Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
related_adrs: ["ADR-010", "ADR-019"]
---

# Appendix C-03: Vendor Failure Containment

## Purpose

This appendix defines the vendor failure containment model for the UIAO Drift Fabric. When an external vendor system (the target of an adapter) fails, becomes unavailable, or produces inconsistent data, the Drift Fabric must contain the failure to prevent cascading effects on the Truth Fabric, Evidence Fabric, and dependent adapters.

## Scope

Applies to all adapters whose target systems are third-party vendor platforms. Vendor failure containment is distinct from adapter failure isolation (ADR-013), which covers failures within the UIAO adapter itself.

## Vendor Failure Modes

The Drift Fabric recognizes four vendor failure modes:

**VF-01: Unavailability** — The vendor system is unreachable. Adapters cannot connect or receive timeouts on all requests.

**VF-02: Degraded Response** — The vendor system responds but with elevated error rates or latency beyond configured thresholds.

**VF-03: Inconsistent Data** — The vendor system responds but the data it provides contradicts the canonical state record (e.g., a user that the Truth Fabric knows exists is returned as non-existent).

**VF-04: Stale Data** — The vendor system responds with data that has not been updated within the expected freshness window, suggesting the vendor's own data pipeline is stuck.

## Containment Actions by Failure Mode

| Failure Mode | Drift Fabric Action | Evidence Fabric Event |
|---|---|---|
| VF-01: Unavailability | Suspend drift comparison for affected adapter; use last known good state; set adapter health to DEGRADED | WARN event with `vendor_failure_type: VF-01` |
| VF-02: Degraded Response | Continue drift comparison with reduced confidence; flag drift records with `confidence: low` | WARN event with `vendor_failure_type: VF-02` |
| VF-03: Inconsistent Data | Halt drift comparison for affected subjects; generate DT-05 Drift Record; notify Governance Plane | HIGH event with `vendor_failure_type: VF-03` |
| VF-04: Stale Data | Continue drift comparison; flag all claims from affected adapter with `staleness_warning: true`; escalate to HIGH if stale for >2x freshness window | MEDIUM event with `vendor_failure_type: VF-04` |

## Vendor Baseline Versioning

Per ADR-010, the Drift Fabric maintains a versioned baseline for each vendor's data schema and expected response characteristics. When a vendor deploys an update that changes their data schema or response format, the baseline must be updated before drift detection resumes.

Baseline version mismatches are treated as VF-03 (Inconsistent Data) until the baseline is updated and approved by the Governance Plane.

## Isolation Guarantees

Vendor failure MUST NOT:
- Cause the Drift Fabric to write incorrect canonical state to the Truth Fabric
- Cause the Evidence Fabric to record false positive compliance attestations
- Cause drift records to be silently dropped (all drift records, including those generated during vendor failures, are written to the Evidence Fabric)
- Affect adapters connected to other vendor systems (per CR-004, fabric orthogonality)

## Recovery from Vendor Failure

When a vendor system recovers from a failure:
1. The Drift Fabric detects recovery (vendor adapter returns to HEALTHY status)
2. A full drift scan is triggered for all subjects that were affected during the failure window
3. Any drift detected during the catch-up scan is recorded with `failure_window: true` to distinguish it from normal drift
4. Evidence Fabric records the recovery event with the failure window start/end timestamps

## Dependencies

- **ADR-010:** Vendor baseline versioning decision record
- **ADR-019:** Vendor failure containment decision record
- **Appendix C-01:** Drift detection algorithm
- **Appendix C-02:** Drift taxonomy (VF failure modes use DT-05 classification)
- **Appendix A-04:** Adapter health and liveness (VF-01/VF-02 correlated with adapter health)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
