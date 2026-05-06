---
title: "Appendix A: Adapter Plane"
appendix: "A"
family: "Adapter Plane"
status: DRAFT
version: "1.0"
last_updated: "2026-04-07"
---

# Appendix A: Adapter Plane

The Adapter Plane is the UIAO subsystem responsible for hosting, managing, and orchestrating all registered integration adapters. It provides the execution environment, lifecycle management, health monitoring, and security isolation for adapters that connect external systems to the UIAO framework.

## Overview

Adapters are the fundamental building blocks of UIAO integration. Each adapter represents a bounded translation layer between an external system's native protocol or schema and the UIAO canonical schema. The Adapter Plane provides:

- **Lifecycle management** — registration, authorization, suspension, and retirement of adapters
- **Sandbox execution** — isolated execution environments that prevent cross-adapter contamination and unauthorized resource access
- **Hot-swap and rollback** — zero-downtime adapter version upgrades with automatic rollback on anomaly detection
- **Health and liveness monitoring** — continuous monitoring of adapter health metrics with automatic lifecycle actions on degradation

## Appendix A Contents

| Document | Description |
|---|---|
| [A-01: Adapter Lifecycle Management](a-01-adapter-lifecycle.md) | State machine, transition rules, and governance checkpoints for adapter lifecycle |
| [A-02: Adapter Sandbox Execution](a-02-adapter-sandbox-execution.md) | Isolation model, boundary enforcement, and sandbox escape detection |
| [A-03: Adapter Hot-Swap and Rollback](a-03-adapter-hot-swap-rollback.md) | Zero-downtime upgrade protocol and rollback guarantee |
| [A-04: Adapter Health and Liveness](a-04-adapter-health-liveness.md) | Health check protocol, liveness probing, and automatic recovery |

## Key Principles

**Idempotency:** All adapter operations MUST be idempotent. Applying the same operation multiple times produces the same result as applying it once.

**Statelessness:** Adapters MUST be stateless. All state is maintained by the Truth Fabric. An adapter may not retain state between requests.

**Schema conformance:** All adapter inputs and outputs MUST conform to the canonical schema registered in the Truth Fabric.

**Isolation:** Adapters operate within sandboxes with explicit resource limits. No adapter may access the resources of another adapter.

## Related ADRs

- ADR-007: Multi-cloud adapter model
- ADR-013: Adapter failure isolation
- ADR-015: Adapter extensibility
- ADR-017: Adapter sandbox execution
- ADR-021: Adapter hot-swap and rollback
- ADR-023: Adapter concurrency
- ADR-025: Adapter health and liveness
- ADR-027: Adapter retirement

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
