---
title: "ADR-013: Adapter Failure Isolation"
adr: "ADR-013"
status: ACCEPTED
date: "2026-02-03"
deciders: ["UIAO Governance Board"]
---

# ADR-013: Adapter Failure Isolation

## Status

ACCEPTED

## Context

When an adapter fails — crashes, hangs, or produces invalid outputs — it should not affect other adapters or the core UIAO fabrics. Without explicit isolation, a misbehaving adapter could exhaust shared resources, corrupt shared state, or cause cascade failures.

## Decision

Each adapter runs in an isolated sandbox (Appendix A-02) with hard resource limits (CPU, memory, network). An adapter failure causes only that adapter to transition to SUSPENDED state. No other adapter is affected. The Drift Fabric and Evidence Fabric continue operating normally during an adapter failure. The Truth Fabric marks the adapter's canonical state as SUSPENDED and stops accepting claims from it until it is restored.

## Consequences

**Positive:**
- Adapter failures are contained — no cascade effects
- The UIAO framework continues operating for all healthy adapters during any single adapter failure
- Evidence records of the failure are written without interruption

**Negative:**
- Compliance attestations that depend on the failed adapter cannot be produced until the adapter is restored
- Adapter sandboxing adds infrastructure complexity

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
