---
title: "Appendix D — Evidence Fabric Architecture Diagram"
status: ACTIVE
---

# Appendix D — Evidence Fabric Architecture Diagram

This page describes the Evidence Fabric architecture. The PlantUML source diagram is maintained at [`diagrams/uiao-evidence-fabric.puml`](https://github.com/WhalerMike/uiao-docs/blob/main/diagrams/uiao-evidence-fabric.puml).

## Diagram Description

The Evidence Fabric diagram shows the write pipeline from event ingestion through signing, hash chaining, and storage tiering. Key elements:

- **Event Ingress** — receives adapter-signed governance events
- **Signature Verifier** — validates adapter signature and deduplicates by event_id
- **Evidence Fabric Countersigner** — adds Evidence Fabric countersignature
- **Hash Chain Writer** — appends content hash and chain link
- **Active Storage** — primary tier for recent records (default: 90 days)
- **Archive Storage** — secondary tier for older records (3–7 year retention)
- **Correlation Engine** — serves correlation and diff queries

See [Appendix D](../appendix/d-evidence-fabric/index.md) for the full Evidence Fabric specification.
