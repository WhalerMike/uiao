---
title: "Appendix A — Adapter Plane Architecture Diagram"
status: ACTIVE
---

# Appendix A — Adapter Plane Architecture Diagram

This page describes the Adapter Plane architecture. The PlantUML source diagram is maintained in the repository at [`diagrams/uiao-adapter-plane.puml`](https://github.com/WhalerMike/uiao-docs/blob/main/diagrams/uiao-adapter-plane.puml).

## Diagram Description

The Adapter Plane diagram shows the relationship between registered adapters, the sandbox execution environment, the Truth Fabric API, and the Adapter Plane orchestration layer. Key elements:

- **Registered Adapters** — individual adapter sandboxes with their resource limits
- **Adapter Plane Orchestration** — the routing and lifecycle management layer
- **Truth Fabric API** — the canonical claim submission endpoint
- **Drift Fabric Monitor** — the health and anomaly detection connection
- **Evidence Fabric Writer** — the audit event recording connection

See [Appendix A](../appendix/a-adapter-plane/index.md) for the full Adapter Plane specification.
