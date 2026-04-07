---
title: "Appendix B — Truth Fabric Architecture Diagram"
status: ACTIVE
---

# Appendix B — Truth Fabric Architecture Diagram

This page describes the Truth Fabric architecture. The PlantUML source diagram is maintained at [`diagrams/uiao-truth-fabric.puml`](https://github.com/WhalerMike/uiao-docs/blob/main/diagrams/uiao-truth-fabric.puml).

## Diagram Description

The Truth Fabric diagram shows the claim intake pipeline from adapter submission through validation, identity anchoring, and canonical state storage. Key elements:

- **Claim Ingress API** — receives signed Canonical Claims from adapters
- **Schema Validator** — validates claims against the Canonical Claim Schema
- **Signature Verifier** — verifies adapter digital signatures
- **Identity Anchoring Engine** — correlates subject identifiers to Canonical Identity Records
- **Canonical State Store** — authoritative storage for all accepted claims and identity records
- **Control Mapping Engine** — maps claims to compliance controls and generates Compliance Attestations
- **Drift Fabric Interface** — exposes canonical state for drift detection queries

See [Appendix B](../appendix/b-truth-fabric/index.md) for the full Truth Fabric specification.
