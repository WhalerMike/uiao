---
title: "Appendix C — Drift Fabric Architecture Diagram"
status: ACTIVE
---

# Appendix C — Drift Fabric Architecture Diagram

This page describes the Drift Fabric architecture. The PlantUML source diagram is maintained at [`diagrams/uiao-drift-fabric.puml`](https://github.com/WhalerMike/uiao-docs/blob/main/diagrams/uiao-drift-fabric.puml).

## Diagram Description

The Drift Fabric diagram shows the drift detection pipeline from canonical state comparison through drift record generation to Evidence Fabric writing. Key elements:

- **Truth Fabric State Reader** — consumes canonical state records
- **Drift Comparator** — computes deltas between observed and canonical state
- **Drift Classifier** — assigns drift type (DT-01..DT-05) and severity
- **Evidence Fabric Writer** — writes immutable Drift Records
- **Reconciliation Trigger** — escalates HIGH/CRITICAL drift to the Governance Plane

See [Appendix C](../appendix/c-drift-fabric/index.md) for the full Drift Fabric specification.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
