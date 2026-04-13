---
title: "UIAO Governance Hierarchy Diagram"
status: ACTIVE
---

# UIAO Governance Hierarchy Diagram

This page describes the overall UIAO governance hierarchy. The PlantUML source diagram is maintained at [`diagrams/uiao-governance-hierarchy.puml`](https://github.com/WhalerMike/uiao-docs/blob/main/diagrams/uiao-governance-hierarchy.puml).

## Diagram Description

The governance hierarchy diagram shows the authority relationships between the Governance Plane, the three operational fabrics, and the Adapter Plane. Key elements:

- **Governance Plane** — top-level authority; ratifies Canon changes, accepts ADRs, runs consistency checks
- **Truth Fabric** — canonical state authority; manages adapter state records and canonical claims
- **Drift Fabric** — deviation detection; consumes Truth Fabric state, produces Drift Records
- **Evidence Fabric** — immutable audit trail; receives all governance events from all fabrics
- **Adapter Plane** — integration execution layer; hosts adapter sandboxes under Governance Plane authority

See [Canon Overview](../canon/index.md) for the full governance hierarchy description.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
