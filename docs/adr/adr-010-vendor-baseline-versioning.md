---
title: "ADR-010: Vendor Baseline Versioning"
adr: "ADR-010"
status: ACCEPTED
date: "2026-01-25"
deciders: ["UIAO Governance Board"]
---

# ADR-010: Vendor Baseline Versioning

## Status

ACCEPTED

## Context

External vendor systems evolve — they update their APIs, change their data schemas, and modify their response formats. When a vendor update changes the data the Drift Fabric expects, drift detection can produce false positives (everything looks like drift because the format changed) or false negatives (real drift is masked by schema mismatches). We needed a way to manage vendor schema evolution without disrupting drift detection.

## Decision

The Drift Fabric maintains a versioned **vendor baseline** for each integrated vendor system. The baseline captures the expected data schema and response characteristics for that vendor at a specific version. Drift detection runs against the versioned baseline, not against the latest raw vendor output.

When a vendor deploys an update that changes their schema:
1. The adapter detects the schema change and reports it as VF-03 (Inconsistent Data)
2. The Governance Plane reviews and approves the new baseline version
3. The baseline is updated in `uiao-core`
4. Drift detection resumes against the new baseline

Baseline version mismatches are treated as VF-03 until resolved.

## Consequences

**Positive:**
- Vendor updates do not cause spurious drift alerts
- The baseline version provides a precise record of what each vendor's data looked like at each point in time
- Baseline changes are governed and auditable

**Negative:**
- Baseline updates require Governance Plane approval — vendor updates can temporarily suspend drift detection
- The baseline registry in `uiao-core` must be kept current with each vendor's release cadence
