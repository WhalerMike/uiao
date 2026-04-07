---
title: "Appendix C: Drift Fabric"
appendix: "C"
family: "Drift Fabric"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
---

# Appendix C: Drift Fabric

The Drift Fabric is the UIAO subsystem responsible for detecting, classifying, and triggering remediation of state drift across all integrated systems. It operates orthogonally to the Truth Fabric (which stores canonical state) and the Evidence Fabric (which records governance events), consuming from the former and producing to the latter.

## Overview

The Drift Fabric provides:

- **Drift detection** — continuous comparison of observed claims against canonical state records
- **Drift classification** — taxonomic classification of detected drift by type and severity
- **Vendor failure containment** — isolation of vendor system failures to prevent cascade effects
- **Reconciliation triggering** — automatic escalation and remediation initiation for HIGH and CRITICAL drift

## Appendix C Contents

| Document | Description |
|---|---|
| [C-01: Drift Detection](c-01-drift-detection.md) | Detection algorithm, schedule, scope filters, and immutability guarantees |
| [C-02: Drift Taxonomy](c-02-drift-taxonomy.md) | Classification of drift types (DT-01 through DT-05) and severity levels |
| [C-03: Vendor Failure Containment](c-03-vendor-failure-containment.md) | Containment of external vendor failures and baseline versioning |

## Key Principles

**Drift is expected:** The Drift Fabric assumes that drift will occur and is designed to detect and record it deterministically — not to prevent it. Prevention is the responsibility of governance processes and adapter controls.

**Immutable drift ledger:** All Drift Records are written to the Evidence Fabric and never modified. Corrections are appended, not overwrites.

**Orthogonality:** Drift detection failures MUST NOT affect Truth Fabric or Evidence Fabric operations. A Drift Fabric outage delays drift detection but does not corrupt canonical state or evidence records.

## Related ADRs

- ADR-009: Drift ledger immutability
- ADR-010: Vendor baseline versioning
- ADR-012: Canonical drift taxonomy
- ADR-019: Vendor failure containment
